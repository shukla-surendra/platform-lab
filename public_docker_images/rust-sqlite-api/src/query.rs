//! Read path — filtered queries over stored telemetry, plus trace assembly.
//!
//! Filters are composed into SQL dynamically rather than with the tidier
//! `(?1 IS NULL OR col = ?1)` trick. That trick reads better but makes the
//! predicate non-sargable: SQLite cannot prove the column comparison holds
//! before binding, so it falls back to a full scan and the indexes in `db.rs`
//! never get used. On a telemetry table that is the difference between an
//! index seek and reading every row ever ingested. Building the `WHERE` clause
//! from only the filters actually supplied keeps each query indexable — the
//! parameters are still bound, never interpolated, so this is not string-built
//! SQL in the injection sense.

use std::collections::HashMap;

use axum::Json;
use axum::extract::{Path, Query, State};
use rusqlite::types::Value as SqlValue;
use rusqlite::{Row, params_from_iter};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

use crate::error::AppError;
use crate::model::{LogRow, MetricRow, SpanRow};
use crate::state::AppState;

const MAX_LIMIT: i64 = 1000;
const DEFAULT_LIMIT: i64 = 100;

fn clamp_limit(l: Option<i64>) -> i64 {
    l.unwrap_or(DEFAULT_LIMIT).clamp(1, MAX_LIMIT)
}

/// Accumulates `WHERE` fragments and their bound values in lockstep.
#[derive(Default)]
struct Filters {
    clauses: Vec<String>,
    params: Vec<SqlValue>,
}

impl Filters {
    fn eq_str(&mut self, col: &str, v: Option<String>) {
        if let Some(v) = v.filter(|s| !s.is_empty()) {
            self.params.push(SqlValue::Text(v));
            self.clauses.push(format!("{col} = ?{}", self.params.len()));
        }
    }

    fn cmp_i64(&mut self, col: &str, op: &str, v: Option<i64>) {
        if let Some(v) = v {
            self.params.push(SqlValue::Integer(v));
            self.clauses
                .push(format!("{col} {op} ?{}", self.params.len()));
        }
    }

    fn contains(&mut self, col: &str, v: Option<String>) {
        if let Some(v) = v.filter(|s| !s.is_empty()) {
            self.params.push(SqlValue::Text(format!("%{v}%")));
            self.clauses
                .push(format!("{col} LIKE ?{}", self.params.len()));
        }
    }

    fn where_sql(&self) -> String {
        if self.clauses.is_empty() {
            String::new()
        } else {
            format!(" WHERE {}", self.clauses.join(" AND "))
        }
    }

    fn with_limit(mut self, limit: i64) -> (Vec<SqlValue>, String) {
        self.params.push(SqlValue::Integer(limit));
        let placeholder = format!("?{}", self.params.len());
        (self.params, placeholder)
    }
}

// ---------------------------------------------------------------------------
// Logs
// ---------------------------------------------------------------------------

#[derive(Debug, Deserialize)]
pub struct LogQuery {
    pub service: Option<String>,
    pub severity: Option<String>,
    pub trace_id: Option<String>,
    /// Substring match on the log body. `LIKE '%x%'` cannot use an index —
    /// acceptable here because it is always combined with an indexed filter in
    /// practice; a real deployment would put an FTS5 table behind this.
    pub q: Option<String>,
    pub since: Option<i64>,
    pub until: Option<i64>,
    pub limit: Option<i64>,
}

pub async fn logs(
    State(st): State<AppState>,
    Query(q): Query<LogQuery>,
) -> Result<Json<Value>, AppError> {
    let limit = clamp_limit(q.limit);
    let mut f = Filters::default();
    f.eq_str("service_name", q.service);
    f.eq_str("severity_text", q.severity.map(|s| s.to_uppercase()));
    f.eq_str("trace_id", q.trace_id.map(|s| s.to_lowercase()));
    f.contains("body", q.q);
    f.cmp_i64("ts_unix_nano", ">=", q.since);
    f.cmp_i64("ts_unix_nano", "<=", q.until);

    let where_sql = f.where_sql();
    let (params, limit_ph) = f.with_limit(limit);
    let sql = format!(
        "SELECT ts_unix_nano, severity_number, severity_text, body, service_name,
                scope_name, trace_id, span_id, attributes, resource_attributes
         FROM logs{where_sql} ORDER BY ts_unix_nano DESC LIMIT {limit_ph}"
    );

    let rows = st
        .fetch(move |conn| {
            let mut stmt = conn.prepare(&sql)?;
            let out = stmt
                .query_map(params_from_iter(params), row_to_log)?
                .collect::<rusqlite::Result<Vec<_>>>()?;
            Ok(out)
        })
        .await?;

    Ok(Json(json!({ "count": rows.len(), "logs": rows })))
}

fn row_to_log(row: &Row<'_>) -> rusqlite::Result<Value> {
    let r = LogRow {
        ts_unix_nano: row.get(0)?,
        severity_number: row.get(1)?,
        severity_text: row.get(2)?,
        body: row.get(3)?,
        service_name: row.get(4)?,
        scope_name: row.get(5)?,
        trace_id: row.get(6)?,
        span_id: row.get(7)?,
        attributes: row.get(8)?,
        resource_attributes: row.get(9)?,
    };
    Ok(inflate(json!(r), &["attributes", "resource_attributes"]))
}

/// Attribute columns hold JSON *text*. Serialising the struct directly would
/// emit them as escaped strings, so they are parsed back into real objects at
/// the response boundary — the client should never see `"{\"k\":\"v\"}"`.
fn inflate(mut v: Value, fields: &[&str]) -> Value {
    if let Some(obj) = v.as_object_mut() {
        for f in fields {
            if let Some(Value::String(s)) = obj.get(*f)
                && let Ok(parsed) = serde_json::from_str::<Value>(s)
            {
                obj.insert((*f).to_string(), parsed);
            }
        }
    }
    v
}

// ---------------------------------------------------------------------------
// Metrics (stored series, not this service's own /metrics)
// ---------------------------------------------------------------------------

#[derive(Debug, Deserialize)]
pub struct MetricQuery {
    pub name: Option<String>,
    pub service: Option<String>,
    pub kind: Option<String>,
    pub since: Option<i64>,
    pub until: Option<i64>,
    pub limit: Option<i64>,
}

pub async fn metrics(
    State(st): State<AppState>,
    Query(q): Query<MetricQuery>,
) -> Result<Json<Value>, AppError> {
    let limit = clamp_limit(q.limit);
    let mut f = Filters::default();
    f.eq_str("name", q.name);
    f.eq_str("service_name", q.service);
    f.eq_str("kind", q.kind);
    f.cmp_i64("ts_unix_nano", ">=", q.since);
    f.cmp_i64("ts_unix_nano", "<=", q.until);

    let where_sql = f.where_sql();
    let (params, limit_ph) = f.with_limit(limit);
    let sql = format!(
        "SELECT ts_unix_nano, name, description, unit, kind, value, count, buckets,
                service_name, scope_name, attributes
         FROM metrics{where_sql} ORDER BY ts_unix_nano DESC LIMIT {limit_ph}"
    );

    let rows = st
        .fetch(move |conn| {
            let mut stmt = conn.prepare(&sql)?;
            let out = stmt
                .query_map(params_from_iter(params), |row| {
                    let r = MetricRow {
                        ts_unix_nano: row.get(0)?,
                        name: row.get(1)?,
                        description: row.get(2)?,
                        unit: row.get(3)?,
                        kind: row.get(4)?,
                        value: row.get(5)?,
                        count: row.get(6)?,
                        buckets: row.get(7)?,
                        service_name: row.get(8)?,
                        scope_name: row.get(9)?,
                        attributes: row.get(10)?,
                    };
                    Ok(inflate(json!(r), &["attributes", "buckets"]))
                })?
                .collect::<rusqlite::Result<Vec<_>>>()?;
            Ok(out)
        })
        .await?;

    Ok(Json(json!({ "count": rows.len(), "metrics": rows })))
}

// ---------------------------------------------------------------------------
// Traces
// ---------------------------------------------------------------------------

#[derive(Debug, Deserialize)]
pub struct TraceListQuery {
    pub service: Option<String>,
    /// Only traces slower than this, in milliseconds — the filter you actually
    /// reach for when hunting a latency regression.
    pub min_duration_ms: Option<i64>,
    pub since: Option<i64>,
    pub limit: Option<i64>,
}

/// Lists traces by their **root span**: the span with no parent. Grouping by
/// `trace_id` and taking `MIN(start)`/`MAX(end)` would also work and would
/// survive a missing root, but it cannot name the trace, and an unnamed trace
/// is useless in a list.
pub async fn trace_list(
    State(st): State<AppState>,
    Query(q): Query<TraceListQuery>,
) -> Result<Json<Value>, AppError> {
    let limit = clamp_limit(q.limit);
    let mut f = Filters::default();
    f.clauses.push("parent_span_id IS NULL".to_string());
    f.eq_str("service_name", q.service);
    f.cmp_i64(
        "duration_nano",
        ">=",
        q.min_duration_ms.map(|ms| ms * 1_000_000),
    );
    f.cmp_i64("start_unix_nano", ">=", q.since);

    let where_sql = f.where_sql();
    let (params, limit_ph) = f.with_limit(limit);
    let sql = format!(
        "SELECT trace_id, name, service_name, start_unix_nano, duration_nano, status_code,
                (SELECT COUNT(*) FROM spans s2 WHERE s2.trace_id = spans.trace_id) AS span_count
         FROM spans{where_sql} ORDER BY start_unix_nano DESC LIMIT {limit_ph}"
    );

    let rows = st
        .fetch(move |conn| {
            let mut stmt = conn.prepare(&sql)?;
            let out = stmt
                .query_map(params_from_iter(params), |row| {
                    Ok(json!({
                        "trace_id": row.get::<_, String>(0)?,
                        "root_name": row.get::<_, String>(1)?,
                        "service_name": row.get::<_, String>(2)?,
                        "start_unix_nano": row.get::<_, i64>(3)?,
                        "duration_ms": row.get::<_, i64>(4)? as f64 / 1e6,
                        "status_code": row.get::<_, Option<i64>>(5)?,
                        "span_count": row.get::<_, i64>(6)?,
                    }))
                })?
                .collect::<rusqlite::Result<Vec<_>>>()?;
            Ok(out)
        })
        .await?;

    Ok(Json(json!({ "count": rows.len(), "traces": rows })))
}

#[derive(Debug, Serialize)]
pub struct SpanNode {
    #[serde(flatten)]
    pub span: Value,
    pub children: Vec<SpanNode>,
}

/// Reassembles one trace into a span tree.
///
/// Deliberately **not** a recursive CTE. A recursive CTE walks the tree one
/// level per iteration, re-probing the index at every step; a trace is a small
/// bounded partition (tens to low thousands of spans), so a single indexed
/// fetch of the whole partition followed by an O(n) link-up in memory is both
/// simpler and strictly less work. Recursive SQL earns its keep when the
/// working set is too large to hold — not here.
pub async fn trace_by_id(
    State(st): State<AppState>,
    Path(trace_id): Path<String>,
) -> Result<Json<Value>, AppError> {
    let trace_id = trace_id.to_lowercase();
    let tid = trace_id.clone();

    let spans = st
        .fetch(move |conn| {
            let mut stmt = conn.prepare(
                "SELECT trace_id, span_id, parent_span_id, name, kind, start_unix_nano,
                        end_unix_nano, duration_nano, status_code, status_message,
                        service_name, scope_name, attributes
                 FROM spans WHERE trace_id = ?1 ORDER BY start_unix_nano ASC",
            )?;
            let out = stmt
                .query_map([tid], |row| {
                    Ok(SpanRow {
                        trace_id: row.get(0)?,
                        span_id: row.get(1)?,
                        parent_span_id: row.get(2)?,
                        name: row.get(3)?,
                        kind: row.get(4)?,
                        start_unix_nano: row.get(5)?,
                        end_unix_nano: row.get(6)?,
                        duration_nano: row.get(7)?,
                        status_code: row.get(8)?,
                        status_message: row.get(9)?,
                        service_name: row.get(10)?,
                        scope_name: row.get(11)?,
                        attributes: row.get(12)?,
                    })
                })?
                .collect::<rusqlite::Result<Vec<_>>>()?;
            Ok(out)
        })
        .await?;

    if spans.is_empty() {
        return Err(AppError::NotFound);
    }

    let total = spans.len();
    let trace_start = spans.iter().map(|s| s.start_unix_nano).min().unwrap_or(0);
    let trace_end = spans.iter().map(|s| s.end_unix_nano).max().unwrap_or(0);
    let error_count = spans.iter().filter(|s| s.status_code == Some(2)).count();
    let services: Vec<String> = {
        let mut v: Vec<String> = spans.iter().map(|s| s.service_name.clone()).collect();
        v.sort();
        v.dedup();
        v
    };

    let roots = build_tree(spans, trace_start);

    Ok(Json(json!({
        "trace_id": trace_id,
        "span_count": total,
        "services": services,
        "error_count": error_count,
        "start_unix_nano": trace_start,
        "duration_ms": (trace_end - trace_start) as f64 / 1e6,
        // More than one root means the trace is partial — the parent spans have
        // not arrived, or never will. Surfaced rather than hidden, because a
        // silently truncated trace is how people misread a latency waterfall.
        "partial": roots.len() > 1,
        "spans": roots,
    })))
}

fn build_tree(spans: Vec<SpanRow>, trace_start: i64) -> Vec<SpanNode> {
    let present: std::collections::HashSet<String> =
        spans.iter().map(|s| s.span_id.clone()).collect();

    // Two passes, both O(n): bucket every span under its parent, then descend
    // from the roots. The alternative — scanning for children per span — is
    // O(n²) and shows up immediately on a wide trace.
    let mut children: HashMap<String, Vec<SpanRow>> = HashMap::new();
    let mut roots: Vec<SpanRow> = Vec::new();

    for s in spans {
        match &s.parent_span_id {
            // An orphan (parent referenced but not stored) is promoted to root
            // rather than dropped — losing spans is worse than a flatter tree.
            Some(p) if present.contains(p) => children.entry(p.clone()).or_default().push(s),
            _ => roots.push(s),
        }
    }

    roots
        .into_iter()
        .map(|r| attach(r, &mut children, trace_start))
        .collect()
}

fn attach(
    span: SpanRow,
    children: &mut HashMap<String, Vec<SpanRow>>,
    trace_start: i64,
) -> SpanNode {
    let kids = children.remove(&span.span_id).unwrap_or_default();
    let mut node = json!(span);
    let start = span_start(&node);
    let duration = span_duration(&node);
    if let Some(o) = node.as_object_mut() {
        // Offset from trace start is what a waterfall UI actually renders;
        // computing it here saves every client from re-deriving it.
        o.insert(
            "relative_start_ms".into(),
            json!((start - trace_start) as f64 / 1e6),
        );
        o.insert("duration_ms".into(), json!(duration as f64 / 1e6));
    }
    let node = inflate(node, &["attributes"]);

    SpanNode {
        span: node,
        children: kids
            .into_iter()
            .map(|c| attach(c, children, trace_start))
            .collect(),
    }
}

fn span_start(v: &Value) -> i64 {
    v["start_unix_nano"].as_i64().unwrap_or(0)
}

fn span_duration(v: &Value) -> i64 {
    v["duration_nano"].as_i64().unwrap_or(0)
}

// ---------------------------------------------------------------------------
// Overview
// ---------------------------------------------------------------------------

/// What is actually in the store — the first call to make when nothing looks
/// like it is arriving, because it separates "nothing sent" from "sent wrong".
pub async fn summary(State(st): State<AppState>) -> Result<Json<Value>, AppError> {
    let stored = st
        .fetch(|conn| {
            let count = |t: &str| -> rusqlite::Result<i64> {
                conn.query_row(&format!("SELECT COUNT(*) FROM {t}"), [], |r| r.get(0))
            };
            let services: Vec<String> = {
                let mut stmt = conn.prepare(
                    "SELECT service_name FROM logs
                     UNION SELECT service_name FROM spans
                     UNION SELECT service_name FROM metrics
                     ORDER BY 1",
                )?;
                stmt.query_map([], |r| r.get(0))?
                    .collect::<rusqlite::Result<Vec<_>>>()?
            };
            Ok(json!({
                "logs": count("logs")?,
                "metrics": count("metrics")?,
                "spans": count("spans")?,
                "traces": conn.query_row(
                    "SELECT COUNT(DISTINCT trace_id) FROM spans", [], |r| r.get::<_, i64>(0))?,
                "services": services,
            }))
        })
        .await?;

    Ok(Json(json!({
        "stored": stored,
        "queue_depth": st.metrics.queue_depth.load(std::sync::atomic::Ordering::Relaxed),
    })))
}

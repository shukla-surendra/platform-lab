//! OTLP/HTTP JSON wire types, and the flattening from OTLP's nested envelope
//! into flat rows.
//!
//! Two encoding quirks of OTLP/JSON drive most of the awkwardness here, and
//! both come from the proto3 JSON mapping rather than from OpenTelemetry:
//!
//! * **64-bit integers are encoded as strings.** `timeUnixNano` arrives as
//!   `"1754661000000000000"`, not as a number, because IEEE-754 doubles cannot
//!   represent the full u64 range and JSON numbers are doubles. Some emitters
//!   send a bare number anyway, so `u64_flex` accepts both.
//! * **`traceId` / `spanId` are lowercase hex**, not the base64 that proto3
//!   JSON normally uses for `bytes` — OTLP overrides that specifically so trace
//!   IDs stay greppable.
//!
//! The envelope itself is three levels deep: resource → scope → record. Each
//! level carries attributes that the records below it inherit. Flattening
//! copies `service.name` down onto every row, because every useful query
//! filters on it and a join per log line would be absurd.

use serde::Deserialize;
use serde_json::{Map, Value, json};

use crate::model::{LogRow, MetricRow, SpanRow};

// ---------------------------------------------------------------------------
// Primitives
// ---------------------------------------------------------------------------

/// Accepts `"123"` or `123` for a 64-bit field. See the module note.
mod u64_flex {
    use serde::{Deserialize, Deserializer};

    #[derive(Deserialize)]
    #[serde(untagged)]
    enum StrOrNum {
        Str(String),
        Num(u64),
    }

    pub fn opt<'de, D: Deserializer<'de>>(d: D) -> Result<Option<u64>, D::Error> {
        let v = Option::<StrOrNum>::deserialize(d)?;
        Ok(match v {
            Some(StrOrNum::Num(n)) => Some(n),
            Some(StrOrNum::Str(s)) => s.parse().ok(),
            None => None,
        })
    }
}

/// One OTLP `AnyValue` — a oneof, so exactly one field is populated.
#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct AnyValue {
    pub string_value: Option<String>,
    pub bool_value: Option<bool>,
    #[serde(deserialize_with = "u64_flex::opt")]
    pub int_value: Option<u64>,
    pub double_value: Option<f64>,
    pub array_value: Option<ArrayValue>,
    pub kvlist_value: Option<KvList>,
    pub bytes_value: Option<String>,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct ArrayValue {
    pub values: Vec<AnyValue>,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct KvList {
    pub values: Vec<KeyValue>,
}

#[derive(Debug, Default, Deserialize)]
#[serde(default)]
pub struct KeyValue {
    pub key: String,
    pub value: AnyValue,
}

impl AnyValue {
    fn to_json(&self) -> Value {
        if let Some(s) = &self.string_value {
            return json!(s);
        }
        if let Some(b) = self.bool_value {
            return json!(b);
        }
        if let Some(i) = self.int_value {
            return json!(i);
        }
        if let Some(d) = self.double_value {
            return json!(d);
        }
        if let Some(a) = &self.array_value {
            return Value::Array(a.values.iter().map(|v| v.to_json()).collect());
        }
        if let Some(kv) = &self.kvlist_value {
            return Value::Object(kv_map(&kv.values));
        }
        if let Some(b) = &self.bytes_value {
            return json!(b);
        }
        Value::Null
    }

    fn as_text(&self) -> Option<String> {
        match self.to_json() {
            Value::Null => None,
            Value::String(s) => Some(s),
            other => Some(other.to_string()),
        }
    }
}

fn kv_map(kvs: &[KeyValue]) -> Map<String, Value> {
    kvs.iter()
        .map(|kv| (kv.key.clone(), kv.value.to_json()))
        .collect()
}

/// Attributes are stored as a JSON string column rather than an EAV side table.
/// SQLite can index and filter into it with `json_extract`, and telemetry
/// attributes are read whole far more often than they are joined on.
fn attrs_json(kvs: &[KeyValue]) -> String {
    Value::Object(kv_map(kvs)).to_string()
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct Resource {
    pub attributes: Vec<KeyValue>,
}

impl Resource {
    /// `service.name` is the one resource attribute every query filters on, so
    /// it is denormalised onto each row instead of being read back out of JSON.
    fn service_name(&self) -> String {
        self.attributes
            .iter()
            .find(|kv| kv.key == "service.name")
            .and_then(|kv| kv.value.as_text())
            .unwrap_or_else(|| "unknown_service".to_string())
    }
}

fn norm_id(s: &str) -> Option<String> {
    let t = s.trim();
    // All-zero IDs are OTLP's "absent" encoding, not a real ID.
    if t.is_empty() || t.chars().all(|c| c == '0') {
        None
    } else {
        Some(t.to_ascii_lowercase())
    }
}

// ---------------------------------------------------------------------------
// Logs
// ---------------------------------------------------------------------------

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct ExportLogsRequest {
    pub resource_logs: Vec<ResourceLogs>,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct ResourceLogs {
    pub resource: Resource,
    pub scope_logs: Vec<ScopeLogs>,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct ScopeLogs {
    pub scope: Scope,
    pub log_records: Vec<LogRecord>,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct Scope {
    pub name: String,
    pub version: String,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct LogRecord {
    #[serde(deserialize_with = "u64_flex::opt")]
    pub time_unix_nano: Option<u64>,
    #[serde(deserialize_with = "u64_flex::opt")]
    pub observed_time_unix_nano: Option<u64>,
    pub severity_number: Option<i64>,
    pub severity_text: Option<String>,
    pub body: AnyValue,
    pub attributes: Vec<KeyValue>,
    pub trace_id: Option<String>,
    pub span_id: Option<String>,
}

impl ExportLogsRequest {
    pub fn flatten(self) -> Vec<LogRow> {
        let mut out = Vec::new();
        for rl in self.resource_logs {
            let service = rl.resource.service_name();
            let resource_attrs = attrs_json(&rl.resource.attributes);
            for sl in rl.scope_logs {
                for r in sl.log_records {
                    out.push(LogRow {
                        // Fall back to observed time, then to now: a record with
                        // no timestamp is still worth keeping, and a 0 timestamp
                        // would silently sort to the beginning of time.
                        ts_unix_nano: r
                            .time_unix_nano
                            .or(r.observed_time_unix_nano)
                            .unwrap_or_else(now_unix_nano)
                            as i64,
                        severity_number: r.severity_number,
                        severity_text: r.severity_text.unwrap_or_default().to_uppercase(),
                        body: r.body.as_text().unwrap_or_default(),
                        service_name: service.clone(),
                        scope_name: sl.scope.name.clone(),
                        trace_id: r.trace_id.as_deref().and_then(norm_id),
                        span_id: r.span_id.as_deref().and_then(norm_id),
                        attributes: attrs_json(&r.attributes),
                        resource_attributes: resource_attrs.clone(),
                    });
                }
            }
        }
        out
    }
}

// ---------------------------------------------------------------------------
// Traces
// ---------------------------------------------------------------------------

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct ExportTraceRequest {
    pub resource_spans: Vec<ResourceSpans>,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct ResourceSpans {
    pub resource: Resource,
    pub scope_spans: Vec<ScopeSpans>,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct ScopeSpans {
    pub scope: Scope,
    pub spans: Vec<Span>,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct Span {
    pub trace_id: String,
    pub span_id: String,
    pub parent_span_id: Option<String>,
    pub name: String,
    pub kind: Option<i64>,
    #[serde(deserialize_with = "u64_flex::opt")]
    pub start_time_unix_nano: Option<u64>,
    #[serde(deserialize_with = "u64_flex::opt")]
    pub end_time_unix_nano: Option<u64>,
    pub attributes: Vec<KeyValue>,
    pub status: Status,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct Status {
    pub code: Option<i64>,
    pub message: Option<String>,
}

impl ExportTraceRequest {
    pub fn flatten(self) -> Vec<SpanRow> {
        let mut out = Vec::new();
        for rs in self.resource_spans {
            let service = rs.resource.service_name();
            for ss in rs.scope_spans {
                for s in ss.spans {
                    let start = s.start_time_unix_nano.unwrap_or_else(now_unix_nano);
                    let end = s.end_time_unix_nano.unwrap_or(start);
                    out.push(SpanRow {
                        trace_id: norm_id(&s.trace_id).unwrap_or_default(),
                        span_id: norm_id(&s.span_id).unwrap_or_default(),
                        parent_span_id: s.parent_span_id.as_deref().and_then(norm_id),
                        name: s.name,
                        kind: s.kind,
                        start_unix_nano: start as i64,
                        end_unix_nano: end as i64,
                        // Precomputed rather than derived on read: every trace
                        // query sorts or filters on duration, and SQLite cannot
                        // index an expression over two columns cheaply.
                        duration_nano: end.saturating_sub(start) as i64,
                        status_code: s.status.code,
                        status_message: s.status.message.unwrap_or_default(),
                        service_name: service.clone(),
                        scope_name: ss.scope.name.clone(),
                        attributes: attrs_json(&s.attributes),
                    });
                }
            }
        }
        // A span with no ID is unusable — it can be neither found nor linked.
        out.retain(|s| !s.trace_id.is_empty() && !s.span_id.is_empty());
        out
    }
}

// ---------------------------------------------------------------------------
// Metrics
// ---------------------------------------------------------------------------

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct ExportMetricsRequest {
    pub resource_metrics: Vec<ResourceMetrics>,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct ResourceMetrics {
    pub resource: Resource,
    pub scope_metrics: Vec<ScopeMetrics>,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct ScopeMetrics {
    pub scope: Scope,
    pub metrics: Vec<Metric>,
}

/// The five metric shapes are a oneof on the metric itself, not a `type` field —
/// which is why this has one `Option` per shape rather than an enum tag.
#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct Metric {
    pub name: String,
    pub description: String,
    pub unit: String,
    pub gauge: Option<DataPoints>,
    pub sum: Option<Sum>,
    pub histogram: Option<HistogramPoints>,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct DataPoints {
    pub data_points: Vec<NumberDataPoint>,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct Sum {
    pub data_points: Vec<NumberDataPoint>,
    pub is_monotonic: bool,
    pub aggregation_temporality: Option<i64>,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct NumberDataPoint {
    #[serde(deserialize_with = "u64_flex::opt")]
    pub time_unix_nano: Option<u64>,
    pub as_double: Option<f64>,
    #[serde(deserialize_with = "u64_flex::opt")]
    pub as_int: Option<u64>,
    pub attributes: Vec<KeyValue>,
}

impl NumberDataPoint {
    fn value(&self) -> f64 {
        self.as_double
            .or_else(|| self.as_int.map(|i| i as f64))
            .unwrap_or(0.0)
    }
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct HistogramPoints {
    pub data_points: Vec<HistogramDataPoint>,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct HistogramDataPoint {
    #[serde(deserialize_with = "u64_flex::opt")]
    pub time_unix_nano: Option<u64>,
    #[serde(deserialize_with = "u64_flex::opt")]
    pub count: Option<u64>,
    pub sum: Option<f64>,
    pub bucket_counts: Vec<serde_json::Value>,
    pub explicit_bounds: Vec<f64>,
    pub attributes: Vec<KeyValue>,
}

impl ExportMetricsRequest {
    pub fn flatten(self) -> (Vec<MetricRow>, u64) {
        let mut out = Vec::new();
        let mut skipped = 0u64;

        for rm in self.resource_metrics {
            let service = rm.resource.service_name();
            for sm in rm.scope_metrics {
                for m in sm.metrics {
                    let base = |kind: &str, ts: Option<u64>, attrs: &[KeyValue]| MetricRow {
                        ts_unix_nano: ts.unwrap_or_else(now_unix_nano) as i64,
                        name: m.name.clone(),
                        description: m.description.clone(),
                        unit: m.unit.clone(),
                        kind: kind.to_string(),
                        value: 0.0,
                        count: None,
                        buckets: None,
                        service_name: service.clone(),
                        scope_name: sm.scope.name.clone(),
                        attributes: attrs_json(attrs),
                    };

                    if let Some(g) = &m.gauge {
                        for dp in &g.data_points {
                            let mut row = base("gauge", dp.time_unix_nano, &dp.attributes);
                            row.value = dp.value();
                            out.push(row);
                        }
                    } else if let Some(s) = &m.sum {
                        let kind = if s.is_monotonic {
                            "counter"
                        } else {
                            "updowncounter"
                        };
                        for dp in &s.data_points {
                            let mut row = base(kind, dp.time_unix_nano, &dp.attributes);
                            row.value = dp.value();
                            out.push(row);
                        }
                    } else if let Some(h) = &m.histogram {
                        for dp in &h.data_points {
                            let mut row = base("histogram", dp.time_unix_nano, &dp.attributes);
                            row.value = dp.sum.unwrap_or(0.0);
                            row.count = dp.count.map(|c| c as i64);
                            // Buckets stay as JSON: their cardinality varies per
                            // metric, so no fixed set of columns fits them.
                            row.buckets = Some(
                                json!({
                                    "bounds": dp.explicit_bounds,
                                    "counts": dp.bucket_counts,
                                })
                                .to_string(),
                            );
                            out.push(row);
                        }
                    } else {
                        // Exponential histograms and summaries are accepted at
                        // the wire level and counted, not stored. Silently
                        // dropping them would make the ingest counters lie.
                        skipped += 1;
                    }
                }
            }
        }
        (out, skipped)
    }
}

pub fn now_unix_nano() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos() as u64)
        .unwrap_or(0)
}

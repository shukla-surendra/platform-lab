//! Flat row types — the boundary between the OTLP envelope and SQLite.
//!
//! These are deliberately *not* the `otlp` types. Ingest flattens once, at the
//! edge, so the writer never walks a nested structure while holding the single
//! SQLite write lock, and the query layer never has to know OTLP exists.

use serde::Serialize;

#[derive(Debug, Clone, Serialize)]
pub struct LogRow {
    pub ts_unix_nano: i64,
    pub severity_number: Option<i64>,
    pub severity_text: String,
    pub body: String,
    pub service_name: String,
    pub scope_name: String,
    pub trace_id: Option<String>,
    pub span_id: Option<String>,
    pub attributes: String,
    pub resource_attributes: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct MetricRow {
    pub ts_unix_nano: i64,
    pub name: String,
    pub description: String,
    pub unit: String,
    /// `gauge` | `counter` | `updowncounter` | `histogram`
    pub kind: String,
    pub value: f64,
    pub count: Option<i64>,
    pub buckets: Option<String>,
    pub service_name: String,
    pub scope_name: String,
    pub attributes: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct SpanRow {
    pub trace_id: String,
    pub span_id: String,
    pub parent_span_id: Option<String>,
    pub name: String,
    pub kind: Option<i64>,
    pub start_unix_nano: i64,
    pub end_unix_nano: i64,
    pub duration_nano: i64,
    pub status_code: Option<i64>,
    pub status_message: String,
    pub service_name: String,
    pub scope_name: String,
    pub attributes: String,
}

/// What travels down the channel to the writer task.
///
/// One enum rather than three channels: a single queue preserves arrival order
/// across signals and gives one place to observe depth and apply backpressure.
#[derive(Debug)]
pub enum Record {
    Log(LogRow),
    Metric(MetricRow),
    Span(SpanRow),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Signal {
    Logs,
    Metrics,
    Traces,
}

impl Signal {
    pub fn as_str(self) -> &'static str {
        match self {
            Signal::Logs => "logs",
            Signal::Metrics => "metrics",
            Signal::Traces => "traces",
        }
    }
}

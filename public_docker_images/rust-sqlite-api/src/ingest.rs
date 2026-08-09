//! OTLP/HTTP ingest endpoints.
//!
//! Handlers do three things and nothing else: parse, flatten, enqueue. No
//! database work happens on the request path — see `writer.rs` for why.
//!
//! Overload is handled with `try_send`, not `send`. Awaiting a full queue would
//! apply backpressure all the way up into the client's exporter, which sounds
//! principled but in practice stalls the caller's own request path and turns a
//! telemetry problem into an application outage. Shedding, counting, and
//! reporting the shed count back through OTLP's `partialSuccess` is what a
//! collector is supposed to do: telemetry is lossy by contract.

use std::sync::atomic::Ordering::Relaxed;

use axum::Json;
use axum::extract::State;
use serde_json::{Value, json};

use crate::model::{Record, Signal};
use crate::otlp::{ExportLogsRequest, ExportMetricsRequest, ExportTraceRequest};
use crate::state::AppState;

pub async fn logs(State(st): State<AppState>, Json(req): Json<ExportLogsRequest>) -> Json<Value> {
    let rows = req.flatten();
    st.metrics
        .logs
        .received
        .fetch_add(rows.len() as u64, Relaxed);
    let rejected = enqueue(&st, Signal::Logs, rows.into_iter().map(Record::Log));
    Json(response("rejectedLogRecords", rejected))
}

pub async fn traces(
    State(st): State<AppState>,
    Json(req): Json<ExportTraceRequest>,
) -> Json<Value> {
    let rows = req.flatten();
    st.metrics
        .traces
        .received
        .fetch_add(rows.len() as u64, Relaxed);
    let rejected = enqueue(&st, Signal::Traces, rows.into_iter().map(Record::Span));
    Json(response("rejectedSpans", rejected))
}

pub async fn metrics(
    State(st): State<AppState>,
    Json(req): Json<ExportMetricsRequest>,
) -> Json<Value> {
    let (rows, skipped) = req.flatten();
    st.metrics
        .metrics
        .received
        .fetch_add(rows.len() as u64, Relaxed);
    st.metrics.metrics.skipped.fetch_add(skipped, Relaxed);
    let rejected = enqueue(&st, Signal::Metrics, rows.into_iter().map(Record::Metric));
    Json(response("rejectedDataPoints", rejected + skipped))
}

fn enqueue(st: &AppState, signal: Signal, records: impl Iterator<Item = Record>) -> u64 {
    let mut rejected = 0u64;
    for rec in records {
        if st.tx.try_send(rec).is_err() {
            rejected += 1;
        }
    }
    if rejected > 0 {
        st.metrics
            .signal(signal)
            .dropped
            .fetch_add(rejected, Relaxed);
        // Warn, not error: shedding under overload is designed behaviour. It is
        // the sustained *rate* that is the alert, and that lives in /metrics.
        tracing::warn!(
            signal = signal.as_str(),
            rejected,
            "writer queue full, shedding"
        );
    }
    st.metrics.queue_depth.store(
        st.tx.max_capacity().saturating_sub(st.tx.capacity()) as u64,
        Relaxed,
    );
    rejected
}

/// OTLP requires 200 with an `ExportServiceResponse` body even on partial
/// failure — an empty `partialSuccess` means everything was accepted. Returning
/// a 4xx here would make well-behaved exporters retry the whole payload,
/// duplicating the records that did land.
fn response(rejected_field: &str, rejected: u64) -> Value {
    if rejected == 0 {
        json!({ "partialSuccess": {} })
    } else {
        json!({
            "partialSuccess": {
                rejected_field: rejected.to_string(),
                "errorMessage": "writer queue full or record unsupported; records shed"
            }
        })
    }
}

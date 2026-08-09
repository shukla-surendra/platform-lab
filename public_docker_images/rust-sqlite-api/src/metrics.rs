//! Self-instrumentation, exposed at `GET /metrics` in Prometheus text format.
//!
//! This is the collector describing its own health, not the telemetry it has
//! been sent — that lives in the database and is read through `/api/*`.
//! Confusing the two is a common mistake: if the only metrics you export are
//! the ones you were handed, you cannot tell a quiet system from a broken
//! ingest path.
//!
//! Plain atomics rather than a metrics crate: every counter here is a
//! monotonic add on a hot path, and `Relaxed` ordering is correct because no
//! counter guards access to other memory — they are read for display only.

use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering::Relaxed};

use crate::model::Signal;

#[derive(Default)]
pub struct SignalCounters {
    pub received: AtomicU64,
    pub written: AtomicU64,
    pub dropped: AtomicU64,
    pub skipped: AtomicU64,
    pub deduped: AtomicU64,
}

#[derive(Default)]
pub struct Metrics {
    pub logs: SignalCounters,
    pub metrics: SignalCounters,
    pub traces: SignalCounters,

    pub batches: AtomicU64,
    pub batch_rows: AtomicU64,
    pub write_seconds_total_micros: AtomicU64,
    pub write_errors: AtomicU64,
    pub queue_depth: AtomicU64,
    pub queue_capacity: AtomicU64,
}

impl Metrics {
    pub fn signal(&self, s: Signal) -> &SignalCounters {
        match s {
            Signal::Logs => &self.logs,
            Signal::Metrics => &self.metrics,
            Signal::Traces => &self.traces,
        }
    }

    pub fn render(self: &Arc<Self>) -> String {
        let mut out = String::with_capacity(2048);

        let counter = |out: &mut String, name: &str, help: &str, vals: [(Signal, u64); 3]| {
            out.push_str(&format!("# HELP {name} {help}\n# TYPE {name} counter\n"));
            for (sig, v) in vals {
                out.push_str(&format!("{name}{{signal=\"{}\"}} {v}\n", sig.as_str()));
            }
        };

        let by = |f: fn(&SignalCounters) -> u64| {
            [
                (Signal::Logs, f(&self.logs)),
                (Signal::Metrics, f(&self.metrics)),
                (Signal::Traces, f(&self.traces)),
            ]
        };

        counter(
            &mut out,
            "telemetry_received_total",
            "Records accepted at the HTTP edge, before queueing.",
            by(|c| c.received.load(Relaxed)),
        );
        counter(
            &mut out,
            "telemetry_written_total",
            "Records durably committed to SQLite.",
            by(|c| c.written.load(Relaxed)),
        );
        counter(
            &mut out,
            "telemetry_dropped_total",
            "Records shed because the writer queue was full. Non-zero means ingest outran the disk.",
            by(|c| c.dropped.load(Relaxed)),
        );
        counter(
            &mut out,
            "telemetry_deduped_total",
            "Records rejected by the uniqueness constraint, i.e. exporter re-deliveries. A healthy non-zero value; a rising one means exporters are timing out.",
            by(|c| c.deduped.load(Relaxed)),
        );
        counter(
            &mut out,
            "telemetry_skipped_total",
            "Records parsed but not storable (unsupported metric shape, missing span id).",
            by(|c| c.skipped.load(Relaxed)),
        );

        let g = |out: &mut String, name: &str, help: &str, ty: &str, v: String| {
            out.push_str(&format!(
                "# HELP {name} {help}\n# TYPE {name} {ty}\n{name} {v}\n"
            ));
        };

        g(
            &mut out,
            "telemetry_batches_total",
            "Write batches committed.",
            "counter",
            self.batches.load(Relaxed).to_string(),
        );
        g(
            &mut out,
            "telemetry_batch_rows_total",
            "Rows written across all batches. Divide by batches_total for mean batch size — the number that tells you whether batching is doing anything.",
            "counter",
            self.batch_rows.load(Relaxed).to_string(),
        );
        g(
            &mut out,
            "telemetry_write_seconds_total",
            "Cumulative time inside commit. Rising toward wall-clock means the writer is the bottleneck.",
            "counter",
            format!(
                "{:.6}",
                self.write_seconds_total_micros.load(Relaxed) as f64 / 1e6
            ),
        );
        g(
            &mut out,
            "telemetry_write_errors_total",
            "Batches that failed to commit.",
            "counter",
            self.write_errors.load(Relaxed).to_string(),
        );
        g(
            &mut out,
            "telemetry_queue_depth",
            "Records queued for the writer. Sustained non-zero is the early warning that precedes drops.",
            "gauge",
            self.queue_depth.load(Relaxed).to_string(),
        );
        g(
            &mut out,
            "telemetry_queue_capacity",
            "Configured writer queue size.",
            "gauge",
            self.queue_capacity.load(Relaxed).to_string(),
        );

        out
    }
}

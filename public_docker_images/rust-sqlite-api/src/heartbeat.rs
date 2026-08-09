//! Periodic liveness logging.
//!
//! A service that only logs on error is indistinguishable from a service that
//! has silently stopped: an empty log panel means "healthy and quiet" and
//! "wedged" equally well, and you cannot tell which without going and looking
//! at the process. A heartbeat removes that ambiguity — absence of the line
//! becomes evidence, which is the whole point.
//!
//! It also gives a log pipeline something to carry. Promtail, Loki, and a
//! Grafana panel all look identical when they are working on no input and when
//! they are broken; a steady heartbeat is the smallest thing that tells those
//! two states apart end to end.
//!
//! The line carries counters, not just a timestamp. "Still alive" is worth
//! little on its own; "still alive, 41k received, 0 dropped" is a health check
//! that survives being read from a log aggregator with no access to /metrics.

use std::sync::Arc;
use std::sync::atomic::Ordering::Relaxed;
use std::time::{Duration, Instant};

use crate::metrics::Metrics;

pub fn spawn(metrics: Arc<Metrics>, interval: Duration) -> tokio::task::JoinHandle<()> {
    tokio::spawn(async move {
        let started = Instant::now();
        let mut ticker = tokio::time::interval(interval);
        // The first tick fires immediately, which is wanted here: it proves the
        // pipeline works at startup rather than one interval later.
        ticker.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Delay);

        loop {
            ticker.tick().await;

            let received = metrics.logs.received.load(Relaxed)
                + metrics.metrics.received.load(Relaxed)
                + metrics.traces.received.load(Relaxed);
            let written = metrics.logs.written.load(Relaxed)
                + metrics.metrics.written.load(Relaxed)
                + metrics.traces.written.load(Relaxed);
            let dropped = metrics.logs.dropped.load(Relaxed)
                + metrics.metrics.dropped.load(Relaxed)
                + metrics.traces.dropped.load(Relaxed);

            // INFO, deliberately. At DEBUG it would be invisible under the
            // default RUST_LOG=info, which is exactly when a heartbeat matters.
            tracing::info!(
                uptime_secs = started.elapsed().as_secs(),
                received,
                written,
                dropped,
                queue_depth = metrics.queue_depth.load(Relaxed),
                write_errors = metrics.write_errors.load(Relaxed),
                "alive"
            );
        }
    })
}

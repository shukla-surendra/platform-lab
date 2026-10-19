//! Periodic liveness logging.
//!
//! A service that only logs on error is indistinguishable from a service that
//! has silently stopped: an empty log stream means "healthy and quiet" and
//! "wedged" equally well, and you cannot tell which without going and looking
//! at the process. A heartbeat removes that ambiguity — absence of the line
//! becomes evidence, which is the whole point.
//!
//! It also gives a log pipeline something to carry when there is no other
//! traffic. Promtail, Loki, and a dashboard panel all look identical when they
//! are working on no input and when they are broken; a steady heartbeat is the
//! smallest thing that tells those two states apart end to end.

use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering::Relaxed};
use std::time::{Duration, Instant};

/// Total requests served, incremented by `routes::track_requests`. Shared with
/// the heartbeat purely so "alive" can report a number that changes — a
/// heartbeat with nothing but a timestamp is easy to mistake for a cron job
/// that forgot to check anything.
#[derive(Default)]
pub struct RequestCounter(AtomicU64);

impl RequestCounter {
    pub fn increment(&self) {
        self.0.fetch_add(1, Relaxed);
    }
    fn get(&self) -> u64 {
        self.0.load(Relaxed)
    }
}

pub fn spawn(counter: Arc<RequestCounter>, interval: Duration) -> tokio::task::JoinHandle<()> {
    tokio::spawn(async move {
        let started = Instant::now();
        let mut ticker = tokio::time::interval(interval);
        // The first tick fires immediately, which is wanted here: it proves
        // logging works at startup rather than one interval later.
        ticker.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Delay);

        loop {
            ticker.tick().await;
            // INFO, deliberately. At DEBUG it would be invisible under the
            // default RUST_LOG=info, which is exactly when a heartbeat matters.
            tracing::info!(
                uptime_secs = started.elapsed().as_secs(),
                requests_served = counter.get(),
                "alive"
            );
        }
    })
}

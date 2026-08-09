//! `POST /debug/logstorm` — deliberately emit a lot of log lines.
//!
//! Exists to exercise a log pipeline end to end. A shipper, an aggregator, and
//! a dashboard all look the same whether they are working correctly on a
//! trickle of input or broken; the only way to tell is to produce a known
//! number of lines at known levels and check that exactly that many arrive.
//! Every hop — stdout capture, the runtime's unwrap stage, label attachment,
//! ingestion, the query language on the other end — is either proven or
//! falsified in one request.

use std::time::Duration;

use axum::Json;
use axum::extract::Query;
use serde::Deserialize;
use serde_json::{Value, json};

#[derive(Debug, Deserialize)]
pub struct StormParams {
    /// Lines to emit. Capped — see below.
    #[serde(default = "default_count")]
    pub count: usize,
    /// Milliseconds between lines. 0 emits as fast as the subscriber allows,
    /// which is the useful setting for testing whether a pipeline drops under
    /// burst; a non-zero value spreads them out so a rate panel has shape.
    #[serde(default)]
    pub delay_ms: u64,
    /// `mixed` (default) spreads lines across DEBUG/INFO/WARN/ERROR so every
    /// level filter has something to match. Otherwise one of debug|info|warn|error.
    #[serde(default = "default_level")]
    pub level: String,
    /// Tag echoed into every line, so a specific run can be isolated in Loki
    /// with `|= "<tag>"` rather than guessing from timestamps.
    #[serde(default)]
    pub tag: Option<String>,
}

fn default_count() -> usize {
    100
}
fn default_level() -> String {
    "mixed".to_string()
}

/// Hard ceiling. Without one, a stray `?count=100000000` fills the node's disk
/// with container logs — the failure mode is the *node*, not this process, so
/// it does not announce itself as this service's fault.
const MAX_COUNT: usize = 50_000;

pub async fn storm(Query(p): Query<StormParams>) -> Json<Value> {
    let count = p.count.min(MAX_COUNT);
    let tag = p.tag.unwrap_or_else(|| "logstorm".to_string());
    let started = std::time::Instant::now();

    // Count only what the subscriber will ACTUALLY emit, not what was
    // attempted. `RUST_LOG=info` silently discards every debug! call, and a
    // response that reports them as emitted turns a log-level setting into an
    // apparent pipeline loss — you go looking for 200 missing lines in
    // Promtail and Loki that were never produced. The whole point of this
    // endpoint is to be a trustworthy reference count.
    let on_debug = tracing::enabled!(tracing::Level::DEBUG);
    let on_info = tracing::enabled!(tracing::Level::INFO);
    let on_warn = tracing::enabled!(tracing::Level::WARN);
    let on_error = tracing::enabled!(tracing::Level::ERROR);

    let (mut n_debug, mut n_info, mut n_warn, mut n_error) = (0u64, 0u64, 0u64, 0u64);
    let mut suppressed = 0u64;

    for i in 0..count {
        // A rotating shape rather than one repeated line: identical lines are
        // indistinguishable from a stuck producer re-sending the same message,
        // and some pipelines deduplicate them.
        let level = if p.level == "mixed" {
            match i % 10 {
                0 => "error",
                1 | 2 => "warn",
                3..=5 => "info",
                _ => "debug",
            }
        } else {
            p.level.as_str()
        };

        match level {
            "error" => {
                tracing::error!(tag = %tag, seq = i, kind = "synthetic", "logstorm: simulated failure");
                if on_error {
                    n_error += 1
                } else {
                    suppressed += 1
                }
            }
            "warn" => {
                tracing::warn!(tag = %tag, seq = i, kind = "synthetic", "logstorm: simulated degradation");
                if on_warn {
                    n_warn += 1
                } else {
                    suppressed += 1
                }
            }
            "info" => {
                tracing::info!(tag = %tag, seq = i, kind = "synthetic", "logstorm: simulated event");
                if on_info {
                    n_info += 1
                } else {
                    suppressed += 1
                }
            }
            _ => {
                tracing::debug!(tag = %tag, seq = i, kind = "synthetic", "logstorm: simulated detail");
                if on_debug {
                    n_debug += 1
                } else {
                    suppressed += 1
                }
            }
        }

        if p.delay_ms > 0 {
            tokio::time::sleep(Duration::from_millis(p.delay_ms)).await;
        }
    }

    let elapsed = started.elapsed();
    tracing::info!(
        tag = %tag,
        kind = "synthetic",
        elapsed_ms = elapsed.as_millis(),
        "logstorm: complete"
    );

    // `emitted` is the number to compare against Loki. `suppressed` accounts
    // for the rest, so requested == emitted + suppressed always holds and a
    // shortfall in Loki can only mean the pipeline lost something.
    let emitted = n_debug + n_info + n_warn + n_error;
    Json(json!({
        "requested": count,
        "emitted": emitted,
        "suppressed_by_log_level": suppressed,
        "by_level": { "debug": n_debug, "info": n_info, "warn": n_warn, "error": n_error },
        "active_levels": {
            "debug": on_debug, "info": on_info, "warn": on_warn, "error": on_error
        },
        "tag": tag,
        "elapsed_ms": elapsed.as_millis(),
        "note": "compare `emitted` (+1 completion line) against Loki, not `requested`",
        // Two details make this an EXACT reference count rather than an
        // approximate one:
        //
        // 1. `fields_kind`, not `kind`. tracing nests custom fields under
        //    "fields", and Loki's `| json` flattens nested objects with an
        //    underscore. Filtering on `kind` silently matches nothing and
        //    reports zero, which reads as total pipeline loss.
        // 2. The kind filter at all. A bare `|= "<tag>"` also matches
        //    tower_http's request lines, because they echo the URI and the tag
        //    lives in the query string — that over-counts by three and reads
        //    as duplication.
        "verify": format!(
            "sum(count_over_time({{app=\"rust-api\"}} |= \"{tag}\" | json | fields_kind=\"synthetic\" [5m]))"
        )
    }))
}

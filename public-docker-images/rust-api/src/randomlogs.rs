//! `POST /debug/random-logs` — call it, get a burst of realistic-looking,
//! randomly generated log lines.
//!
//! This is a different tool from `logstorm`, on purpose, and the difference is
//! the point of having both:
//!
//! * **`logstorm`** answers "did every line I asked for arrive downstream?" —
//!   a fixed count, a known level split, one synthetic message per level. Its
//!   whole design is being an exact, boring, reproducible reference count.
//! * **`random-logs`** answers "what does my dashboard/parser/alert do with
//!   traffic that looks like production?" — a random volume, a realistic
//!   level mix (mostly INFO/DEBUG, occasional WARN, rare ERROR), and message
//!   content drawn from a pool of templates with randomised fields (user ids,
//!   latencies, status codes, paths). Nothing about a single call is
//!   predictable except that it will look plausible.
//!
//! Both tag every line with a `run_id`, because "which lines came from my
//! call" is the same real question a burst-of-real-traffic caller asks whether
//! the content is synthetic or randomised — it just needs a different fix than
//! a hardcoded `tag` when nobody supplied one.

use std::time::Duration;

use axum::Json;
use axum::extract::Query;
use rand::rngs::StdRng;
use rand::seq::IndexedRandom;
use rand::{RngExt, SeedableRng};
use serde::Deserialize;
use serde_json::{Value, json};

/// Every request gets a random volume in this range unless `count` is given.
/// The randomness is part of the feature — a caller who does not care how many
/// lines they get is testing "handle unpredictable volume", and a fixed
/// default would quietly turn into a de facto fixed count once every example
/// and script copies it verbatim.
const DEFAULT_MIN: usize = 20;
const DEFAULT_MAX: usize = 300;

/// Same ceiling as `logstorm`, same reason: an uncapped count turns a stray
/// request into a disk-filling event on the *node*, which is a failure that
/// does not look like this service's fault.
const MAX_COUNT: usize = 50_000;

#[derive(Debug, Deserialize)]
pub struct RandomParams {
    /// Exact line count. Omit it to get a random volume instead — that is the
    /// default experience, not a fallback.
    pub count: Option<usize>,
    /// Groups lines from one call under a shared id, so they can be isolated
    /// in a log store with `|= "<run_id>"` instead of guessing from
    /// timestamps. Auto-generated when omitted, so "just call it" needs zero
    /// query parameters and is still traceable afterward from the response.
    pub run_id: Option<String>,
    /// Milliseconds between lines. 0 (default) emits as fast as the
    /// subscriber allows — the setting that actually tests burst handling.
    #[serde(default)]
    pub delay_ms: u64,
}

/// (level, weight) — weights are relative, not percentages, and deliberately
/// shaped like real service traffic: mostly quiet, occasionally noisy, rarely
/// broken. A caller who wants a specific level distribution should reach for
/// `logstorm`, which gives exact control instead of a realistic shape.
const LEVEL_WEIGHTS: &[(&str, u32)] = &[("debug", 45), ("info", 40), ("warn", 12), ("error", 3)];

const PATHS: &[&str] = &[
    "/api/v1/users",
    "/api/v1/orders",
    "/api/v1/payments",
    "/api/v1/inventory",
    "/api/v1/search",
    "/healthz",
    "/api/v1/notifications",
];

const SERVICES: &[&str] = &[
    "auth-service",
    "order-service",
    "payment-gateway",
    "inventory-worker",
    "notification-dispatcher",
    "search-indexer",
];

/// Templates take a subset of {path, service, ms, code, id} — see `render`.
/// The point of varying which fields a message needs is that a random parser
/// or log-schema test sees genuinely heterogeneous shapes, not one shape with
/// different words substituted in.
const TEMPLATES: &[(&str, &str)] = &[
    ("debug", "cache lookup for key user:{id} took {ms}ms"),
    ("debug", "acquired connection from pool, {n} active"),
    ("debug", "parsed request body for {path} ({n} bytes)"),
    ("info", "{service} handled {path} in {ms}ms, status {code}"),
    ("info", "user {id} authenticated successfully"),
    ("info", "background job {id} completed in {ms}ms"),
    ("info", "scaled {service} to {n} replicas"),
    ("warn", "{service} responded slowly to {path}: {ms}ms"),
    ("warn", "retrying request to {service} after timeout"),
    ("warn", "queue depth for {service} reached {n}"),
    ("warn", "rate limit approaching for client {id}"),
    ("error", "{service} returned {code} for {path} after {ms}ms"),
    ("error", "database connection pool exhausted in {service}"),
    (
        "error",
        "webhook delivery to client {id} failed after {n} attempts",
    ),
];

fn weighted_level(rng: &mut impl RngExt) -> &'static str {
    let total: u32 = LEVEL_WEIGHTS.iter().map(|(_, w)| w).sum();
    let mut pick = rng.random_range(0..total);
    for (level, weight) in LEVEL_WEIGHTS {
        if pick < *weight {
            return level;
        }
        pick -= weight;
    }
    "info" // unreachable given the weights sum correctly, but a real fallback
}

fn render(template: &str, rng: &mut impl RngExt) -> String {
    template
        .replace("{path}", PATHS.choose(rng).unwrap())
        .replace("{service}", SERVICES.choose(rng).unwrap())
        .replace("{ms}", &rng.random_range(1..=4000).to_string())
        .replace(
            "{code}",
            &[200, 200, 200, 201, 400, 404, 429, 500, 503]
                .choose(rng)
                .unwrap()
                .to_string(),
        )
        .replace("{id}", &rng.random_range(1000..99999).to_string())
        .replace("{n}", &rng.random_range(1..500).to_string())
}

pub async fn random_logs(Query(p): Query<RandomParams>) -> Json<Value> {
    let mut rng = StdRng::from_rng(&mut rand::rng());

    let requested = p
        .count
        .unwrap_or_else(|| rng.random_range(DEFAULT_MIN..=DEFAULT_MAX))
        .min(MAX_COUNT);
    let run_id = p
        .run_id
        .unwrap_or_else(|| format!("run-{:08x}", rng.random::<u32>()));
    let started = std::time::Instant::now();

    // Checked once, not per line: `RUST_LOG` does not change mid-request, and
    // `logstorm` already learned this lesson the hard way — a response that
    // reports every generated line as "emitted" turns a log-level setting
    // into an apparent pipeline loss when DEBUG lines silently never reach
    // the subscriber. `count` here must equal what a log store can actually
    // find, not what this handler attempted to write.
    let on_debug = tracing::enabled!(tracing::Level::DEBUG);
    let on_info = tracing::enabled!(tracing::Level::INFO);
    let on_warn = tracing::enabled!(tracing::Level::WARN);
    let on_error = tracing::enabled!(tracing::Level::ERROR);

    let mut counts = std::collections::BTreeMap::from([
        ("debug", 0u64),
        ("info", 0u64),
        ("warn", 0u64),
        ("error", 0u64),
    ]);
    let mut suppressed = 0u64;
    let mut sample = Vec::with_capacity(5);

    for _ in 0..requested {
        let level = weighted_level(&mut rng);
        let enabled = match level {
            "debug" => on_debug,
            "warn" => on_warn,
            "error" => on_error,
            _ => on_info,
        };
        if !enabled {
            suppressed += 1;
            continue;
        }

        let candidates: Vec<&(&str, &str)> =
            TEMPLATES.iter().filter(|(l, _)| *l == level).collect();
        // Every level in LEVEL_WEIGHTS has at least one template, so this
        // unwrap reflects that invariant rather than papering over a gap.
        let (_, template) = candidates.choose(&mut rng).expect("level has templates");
        let message = render(template, &mut rng);

        *counts.get_mut(level).unwrap() += 1;
        if sample.len() < 5 {
            sample.push(json!({ "level": level.to_uppercase(), "message": message.clone() }));
        }

        match level {
            "warn" => tracing::warn!(run_id = %run_id, kind = "random", "{message}"),
            "error" => tracing::error!(run_id = %run_id, kind = "random", "{message}"),
            _ => tracing::info!(run_id = %run_id, kind = "random", "{message}"),
        }

        if p.delay_ms > 0 {
            tokio::time::sleep(Duration::from_millis(p.delay_ms)).await;
        }
    }

    let elapsed = started.elapsed();
    let emitted = counts.values().sum::<u64>();
    tracing::info!(
        run_id = %run_id,
        kind = "random",
        emitted,
        elapsed_ms = elapsed.as_millis(),
        "random-logs: complete"
    );

    Json(json!({
        "requested": requested,
        "emitted": emitted,
        "suppressed_by_log_level": suppressed,
        "run_id": run_id,
        "by_level": counts,
        "sample": sample,
        "elapsed_ms": elapsed.as_millis(),
        "verify": format!(
            "sum(count_over_time({{app=\"rust-api\"}} |= \"{run_id}\" | json | fields_kind=\"random\" [5m]))"
        )
    }))
}

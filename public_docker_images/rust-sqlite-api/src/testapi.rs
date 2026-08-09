//! Endpoints that exist to be called by other people's tools.
//!
//! This image doubles as a public API-testing target — the thing you point a
//! client, a load generator, an ingress rule, or a probe at when you need a
//! server that responds predictably and is not someone else's production
//! service. Deliberately httpbin-shaped, because that vocabulary is already
//! familiar.
//!
//! Two properties every handler here holds to:
//!
//! * **Stateless.** Nothing touches SQLite. These can be hammered without
//!   growing the volume or perturbing the telemetry counters.
//! * **Predictable.** The response says exactly what the request was, so a
//!   failing client can be diagnosed from the response alone rather than from
//!   server logs the caller cannot see.

use std::collections::BTreeMap;
use std::time::Duration;

use axum::Json;
use axum::body::Bytes;
use axum::extract::{ConnectInfo, Path, Query};
use axum::http::{HeaderMap, StatusCode, Uri};
use axum::response::IntoResponse;
use serde_json::{Value, json};
use std::net::SocketAddr;

/// Upper bound on an artificial delay. Without one, `/delay/600000` holds a
/// connection for ten minutes and looks like a hung server — and enough of
/// them exhaust the connection pool of whatever is in front of this.
const MAX_DELAY_MS: u64 = 30_000;
/// Upper bound on generated payload size, for the same reason in the other
/// direction: `/bytes/1000000000` is a memory exhaustion request.
const MAX_BYTES: usize = 10 * 1024 * 1024;

fn header_map(headers: &HeaderMap) -> BTreeMap<String, String> {
    headers
        .iter()
        .map(|(k, v)| {
            (
                k.as_str().to_string(),
                v.to_str().unwrap_or("<non-utf8>").to_string(),
            )
        })
        .collect()
}

/// Echoes the request back: method, path, query, headers, body.
///
/// The first thing to reach for when a client "isn't working" — it answers
/// what was actually sent, which is usually different from what the caller
/// believes was sent.
pub async fn echo(
    method: axum::http::Method,
    uri: Uri,
    headers: HeaderMap,
    body: Bytes,
) -> Json<Value> {
    let body_str = String::from_utf8_lossy(&body).to_string();
    // If the body parses as JSON, return it as JSON rather than as an escaped
    // string — otherwise every nested quote has to be read through a backslash.
    let parsed: Option<Value> = serde_json::from_str(&body_str).ok();

    Json(json!({
        "method": method.as_str(),
        "path": uri.path(),
        "query": uri.query(),
        "headers": header_map(&headers),
        "body": body_str,
        "json": parsed,
        "body_bytes": body.len(),
    }))
}

/// Returns whatever status code you ask for. For testing retry logic, alerting
/// rules, and ingress error pages against real codes instead of mocks.
pub async fn status(Path(code): Path<u16>) -> impl IntoResponse {
    let status = StatusCode::from_u16(code).unwrap_or(StatusCode::BAD_REQUEST);
    (
        status,
        Json(json!({
            "requested_status": code,
            "returned_status": status.as_u16(),
            "canonical_reason": status.canonical_reason(),
        })),
    )
}

/// Sleeps, then responds. For exercising client timeouts, readiness gates, and
/// latency panels with a known number.
pub async fn delay(Path(ms): Path<u64>) -> Json<Value> {
    let ms = ms.min(MAX_DELAY_MS);
    let started = std::time::Instant::now();
    tokio::time::sleep(Duration::from_millis(ms)).await;
    Json(json!({
        "requested_delay_ms": ms,
        "actual_delay_ms": started.elapsed().as_millis(),
        "capped_at_ms": MAX_DELAY_MS,
    }))
}

pub async fn uuid() -> Json<Value> {
    Json(json!({ "uuid": uuid::Uuid::new_v4().to_string() }))
}

pub async fn headers(headers: HeaderMap) -> Json<Value> {
    Json(json!({ "headers": header_map(&headers) }))
}

/// The client address as this server sees it — which behind an ingress or a
/// port-forward is usually the proxy, not the caller. That discrepancy is the
/// point: it makes X-Forwarded-For misconfiguration visible.
pub async fn ip(ConnectInfo(addr): ConnectInfo<SocketAddr>, headers: HeaderMap) -> Json<Value> {
    Json(json!({
        "peer": addr.to_string(),
        "x_forwarded_for": headers.get("x-forwarded-for").and_then(|v| v.to_str().ok()),
        "x_real_ip": headers.get("x-real-ip").and_then(|v| v.to_str().ok()),
        "note": "peer is the immediate connection. Behind a proxy it is the proxy.",
    }))
}

/// A deterministic payload of a requested size, for throughput and
/// compression testing. Deterministic rather than random so two runs are
/// comparable and a proxy's caching behaviour is observable.
pub async fn bytes(Path(n): Path<usize>) -> impl IntoResponse {
    let n = n.min(MAX_BYTES);
    let body: Vec<u8> = (0..n).map(|i| b'a' + (i % 26) as u8).collect();
    (
        [("content-type", "application/octet-stream")],
        axum::body::Body::from(body),
    )
}

#[derive(serde::Deserialize)]
pub struct SampleParams {
    #[serde(default = "one")]
    pub count: usize,
}
fn one() -> usize {
    1
}

/// A stable JSON document — for client deserialisation tests that need a
/// fixed shape they can assert against.
pub async fn sample(Query(p): Query<SampleParams>) -> Json<Value> {
    let n = p.count.clamp(1, 1000);
    let items: Vec<Value> = (0..n)
        .map(|i| {
            json!({
                "id": i,
                "name": format!("item-{i}"),
                "active": i % 2 == 0,
                "score": (i as f64) * 1.5,
                "tags": ["alpha", "beta"],
                "nested": { "level": 2, "value": null }
            })
        })
        .collect();
    Json(json!({ "count": n, "items": items }))
}

/// Build and runtime identity. The first call to make when a deployment
/// "didn't take" — it says which binary is actually answering.
pub async fn version() -> Json<Value> {
    Json(json!({
        "name": env!("CARGO_PKG_NAME"),
        "version": env!("CARGO_PKG_VERSION"),
        "arch": std::env::consts::ARCH,
        "os": std::env::consts::OS,
    }))
}

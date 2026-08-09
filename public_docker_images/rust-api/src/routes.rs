//! Router assembly and the two probes.
//!
//! Every handler here is stateless — no database, no shared connection pool.
//! The only shared thing is a request counter, threaded through as an
//! `Extension` rather than full `axum::State`, because a counter is the only
//! state this service has and a whole `AppState` type for one atomic would be
//! the wrong amount of ceremony.

use std::sync::{Arc, OnceLock};

use axum::body::Body;
use axum::extract::Extension;
use axum::http::Request;
use axum::middleware::{self, Next};
use axum::response::{IntoResponse, Response};
use axum::routing::get;
use axum::{Json, Router};
use serde_json::json;
use tower_http::trace::TraceLayer;

use crate::heartbeat::RequestCounter;
use crate::{endpoints, logstorm, randomlogs, testapi};

/// The landing page's static shell is baked into the binary — the image runs
/// with `readOnlyRootFilesystem` and often with no egress, so a file read at
/// runtime or a CDN asset would simply fail. The endpoint table inside it is
/// NOT part of this constant: it is spliced in from `endpoints::html_rows()`
/// at first request, so the page can never list a route this file does not.
const INDEX_TEMPLATE: &str = include_str!("../static/index.html");
const ENDPOINTS_MARKER: &str = "<!--ENDPOINTS-->";

fn rendered_index() -> &'static str {
    static PAGE: OnceLock<String> = OnceLock::new();
    PAGE.get_or_init(|| INDEX_TEMPLATE.replace(ENDPOINTS_MARKER, endpoints::html_rows()))
}

pub fn router(counter: Arc<RequestCounter>) -> Router {
    Router::new()
        // Landing page: what this image is and every endpoint it serves.
        .route("/", get(index))
        .route("/version", get(testapi::version))
        // The same endpoint table as JSON — generated from the identical
        // registry as the landing page, so the two cannot drift apart.
        .route("/api/endpoints", get(endpoints::list))
        // Probes
        .route("/healthz", get(healthz))
        .route("/readyz", get(healthz))
        // Log generation — the other half of what this image is for.
        .route("/debug/logstorm", axum::routing::post(logstorm::storm))
        .route(
            "/debug/random-logs",
            axum::routing::post(randomlogs::random_logs),
        )
        // Stateless API-testing surface — httpbin-shaped.
        .route(
            "/api/test/echo",
            get(testapi::echo).post(testapi::echo).put(testapi::echo),
        )
        .route("/api/test/status/{code}", get(testapi::status))
        .route("/api/test/delay/{ms}", get(testapi::delay))
        .route("/api/test/uuid", get(testapi::uuid))
        .route("/api/test/headers", get(testapi::headers))
        .route("/api/test/ip", get(testapi::ip))
        .route("/api/test/bytes/{n}", get(testapi::bytes))
        .route("/api/test/json", get(testapi::sample))
        .layer(TraceLayer::new_for_http())
        .layer(middleware::from_fn(track_requests))
        .layer(Extension(counter))
}

/// Liveness and readiness are the same check here: is the process answering
/// HTTP at all. There is no database to distinguish "up" from "up but cannot
/// reach storage" — that distinction only existed when this image had storage.
/// Both routes stay, since orchestrators expect both paths to exist.
async fn healthz() -> Json<serde_json::Value> {
    Json(json!({ "status": "ok" }))
}

async fn index() -> impl IntoResponse {
    (
        [("content-type", "text/html; charset=utf-8")],
        rendered_index(),
    )
}

async fn track_requests(
    Extension(counter): Extension<Arc<RequestCounter>>,
    req: Request<Body>,
    next: Next,
) -> Response {
    counter.increment();
    next.run(req).await
}

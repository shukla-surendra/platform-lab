//! Router assembly, probes, and the small notes CRUD the service started as.
//!
//! Handlers that touch SQLite go through `AppState::fetch`, which enforces the
//! `spawn_blocking` rule in one place — see `state.rs`.

use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::routing::get;
use axum::{Json, Router};
use serde::{Deserialize, Serialize};
use tower_http::trace::TraceLayer;

use crate::error::AppError;
use crate::{ingest, query, state::AppState, testapi};

/// The landing page is baked into the binary. The image runs with
/// readOnlyRootFilesystem and often with no egress, so a file read at runtime
/// or a CDN asset would simply fail.
const INDEX_HTML: &str = include_str!("../static/index.html");

pub fn router(state: AppState) -> Router {
    Router::new()
        // Landing page: what this image is and every endpoint it serves.
        .route("/", get(index))
        .route("/version", get(testapi::version))
        // Stateless API-testing surface — httpbin-shaped, touches no storage.
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
        // Probes
        .route("/healthz", get(healthz))
        .route("/readyz", get(readyz))
        // This service's own instrumentation, in Prometheus text format.
        // Distinct from /api/metrics, which reads back telemetry it was sent.
        .route("/metrics", get(self_metrics))
        // OTLP/HTTP ingest — the paths every OTel exporter defaults to, so a
        // collector needs only OTEL_EXPORTER_OTLP_ENDPOINT pointed here.
        .route("/v1/logs", axum::routing::post(ingest::logs))
        .route("/v1/metrics", axum::routing::post(ingest::metrics))
        .route("/v1/traces", axum::routing::post(ingest::traces))
        // Query
        // Emits a burst of log lines on demand — for proving a log pipeline
        // end to end. Writes nothing to SQLite.
        .route(
            "/debug/logstorm",
            axum::routing::post(crate::logstorm::storm),
        )
        .route("/api/summary", get(query::summary))
        .route("/api/logs", get(query::logs))
        .route("/api/metrics", get(query::metrics))
        .route("/api/traces", get(query::trace_list))
        .route("/api/traces/{trace_id}", get(query::trace_by_id))
        // Notes CRUD
        .route("/api/notes", get(list_notes).post(create_note))
        .route("/api/notes/{id}", get(get_note).delete(delete_note))
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}

/// Liveness: is the process up? Deliberately does **not** touch the database —
/// a liveness probe that fails on a locked DB gets the container killed and
/// restarted, which does nothing to unlock the DB and drops in-flight requests.
async fn index() -> impl IntoResponse {
    ([("content-type", "text/html; charset=utf-8")], INDEX_HTML)
}

async fn healthz() -> &'static str {
    "ok"
}

/// Readiness: can this instance actually serve traffic? This one *does* hit the
/// database, because a process that cannot reach its DB should be pulled out of
/// the load-balancer rotation without being restarted.
async fn readyz(State(st): State<AppState>) -> Result<&'static str, AppError> {
    st.fetch(|conn| conn.query_row("SELECT 1", [], |_| Ok(())))
        .await?;
    Ok("ready")
}

async fn self_metrics(State(st): State<AppState>) -> impl IntoResponse {
    (
        [("content-type", "text/plain; version=0.0.4; charset=utf-8")],
        st.metrics.render(),
    )
}

// ---------------------------------------------------------------------------
// Notes
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize)]
pub struct Note {
    pub id: i64,
    pub title: String,
    pub body: String,
    pub created_at: String,
}

#[derive(Debug, Deserialize)]
pub struct CreateNote {
    pub title: String,
    #[serde(default)]
    pub body: String,
}

fn row_to_note(row: &rusqlite::Row<'_>) -> rusqlite::Result<Note> {
    Ok(Note {
        id: row.get(0)?,
        title: row.get(1)?,
        body: row.get(2)?,
        created_at: row.get(3)?,
    })
}

async fn list_notes(State(st): State<AppState>) -> Result<Json<Vec<Note>>, AppError> {
    let notes = st
        .fetch(|conn| {
            let mut stmt = conn.prepare(
                "SELECT id, title, body, created_at FROM notes ORDER BY id DESC LIMIT 100",
            )?;
            stmt.query_map([], row_to_note)?.collect()
        })
        .await?;
    Ok(Json(notes))
}

async fn create_note(
    State(st): State<AppState>,
    Json(payload): Json<CreateNote>,
) -> Result<(StatusCode, Json<Note>), AppError> {
    if payload.title.trim().is_empty() {
        return Err(AppError::BadRequest("title must not be empty".into()));
    }

    let note = st
        .fetch(move |conn| {
            // RETURNING avoids a second round trip for last_insert_rowid() and
            // the server-side created_at default.
            conn.query_row(
                "INSERT INTO notes (title, body) VALUES (?1, ?2)
                 RETURNING id, title, body, created_at",
                (&payload.title, &payload.body),
                row_to_note,
            )
        })
        .await?;

    Ok((StatusCode::CREATED, Json(note)))
}

async fn get_note(State(st): State<AppState>, Path(id): Path<i64>) -> Result<Json<Note>, AppError> {
    let note = st
        .fetch(move |conn| {
            conn.query_row(
                "SELECT id, title, body, created_at FROM notes WHERE id = ?1",
                [id],
                row_to_note,
            )
        })
        .await
        .map_err(not_found_on_empty)?;
    Ok(Json(note))
}

async fn delete_note(
    State(st): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, AppError> {
    let affected = st
        .fetch(move |conn| conn.execute("DELETE FROM notes WHERE id = ?1", [id]))
        .await?;

    if affected == 0 {
        Err(AppError::NotFound)
    } else {
        Ok(StatusCode::NO_CONTENT)
    }
}

/// `query_row` reports "no rows" as an error; at the HTTP boundary that is a
/// 404, not a 500.
fn not_found_on_empty(e: AppError) -> AppError {
    match &e {
        AppError::Internal(inner)
            if matches!(
                inner.downcast_ref::<rusqlite::Error>(),
                Some(rusqlite::Error::QueryReturnedNoRows)
            ) =>
        {
            AppError::NotFound
        }
        _ => e,
    }
}

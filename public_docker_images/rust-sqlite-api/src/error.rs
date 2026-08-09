//! One error type for every handler, so `?` works everywhere and every failure
//! leaves the process as JSON rather than a bare 500 with an empty body.

use axum::Json;
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use serde_json::json;

#[derive(Debug)]
pub enum AppError {
    NotFound,
    BadRequest(String),
    /// Anything the caller cannot fix: pool exhaustion, disk errors, a panic in
    /// a blocking task. Logged in full, reported to the client as a bare 500.
    Internal(anyhow::Error),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, message) = match self {
            AppError::NotFound => (StatusCode::NOT_FOUND, "not found".to_string()),
            AppError::BadRequest(m) => (StatusCode::BAD_REQUEST, m),
            AppError::Internal(err) => {
                // The detail goes to the log, never to the response — error text
                // from a database leaks schema and paths.
                tracing::error!(error = ?err, "internal error");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "internal error".to_string(),
                )
            }
        };
        (status, Json(json!({ "error": message }))).into_response()
    }
}

// Explicit conversions rather than a blanket `impl<E: Into<anyhow::Error>>` —
// that blanket form collides with core's reflexive `impl<T> From<T> for T`.
macro_rules! internal_from {
    ($($ty:ty),* $(,)?) => {
        $(impl From<$ty> for AppError {
            fn from(err: $ty) -> Self {
                AppError::Internal(err.into())
            }
        })*
    };
}

internal_from!(
    rusqlite::Error,
    r2d2::Error,
    tokio::task::JoinError,
    anyhow::Error,
);

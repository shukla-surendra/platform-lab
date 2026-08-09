use std::sync::Arc;

use tokio::sync::mpsc;

use crate::db::Pool;
use crate::error::AppError;
use crate::metrics::Metrics;
use crate::model::Record;

/// Shared handler state. Cloned per request, so every field is cheap to clone:
/// the pool and sender are handles, and `Metrics` sits behind an `Arc`.
#[derive(Clone)]
pub struct AppState {
    pub pool: Pool,
    pub tx: mpsc::Sender<Record>,
    pub metrics: Arc<Metrics>,
}

impl AppState {
    /// Run a blocking query off the async runtime.
    ///
    /// Every read goes through here so the `spawn_blocking` discipline is
    /// enforced in one place rather than remembered at eleven call sites — the
    /// failure mode it prevents (a slow query parking a Tokio worker) is
    /// invisible until the whole server stops accepting connections.
    pub async fn fetch<T, F>(&self, f: F) -> Result<T, AppError>
    where
        F: FnOnce(&rusqlite::Connection) -> rusqlite::Result<T> + Send + 'static,
        T: Send + 'static,
    {
        let pool = self.pool.clone();
        let out = tokio::task::spawn_blocking(move || -> Result<T, AppError> {
            let conn = pool.get()?;
            Ok(f(&conn)?)
        })
        .await??;
        Ok(out)
    }
}

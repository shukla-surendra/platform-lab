//! An OTLP-compatible telemetry collector whose entire backing store is a
//! SQLite file inside the container.
//!
//! Request path:  HTTP → parse OTLP → flatten to rows → bounded queue  (no I/O)
//! Write path:    queue → batching writer → one transaction per batch  (one thread)
//! Read path:     HTTP → spawn_blocking → pooled connection → JSON
//!
//! Keeping those three apart is the whole design. See `writer.rs` for why the
//! ingest handlers never touch the database.

mod db;
mod error;
mod ingest;
mod metrics;
mod model;
mod otlp;
mod query;
mod retention;
mod routes;
mod state;
mod writer;

use std::net::SocketAddr;
use std::sync::Arc;
use std::time::Duration;

use tokio::net::TcpListener;
use tokio::signal;
use tracing_subscriber::{EnvFilter, fmt};

use crate::state::AppState;
use crate::writer::WriterConfig;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    fmt()
        .with_env_filter(EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".into()))
        .json()
        .init();

    let db_path = env_or("DATABASE_PATH", "/data/app.db");
    let bind_addr: SocketAddr = env_or("BIND_ADDR", "0.0.0.0:8080").parse()?;
    let pool_size: u32 = env_or("DB_POOL_SIZE", "8").parse()?;
    let cfg = WriterConfig {
        queue_capacity: env_or("INGEST_QUEUE_CAPACITY", "10000").parse()?,
        batch_max: env_or("INGEST_BATCH_MAX", "500").parse()?,
        flush_interval: Duration::from_millis(env_or("INGEST_FLUSH_MS", "250").parse()?),
    };
    let retention_hours: u64 = env_or("RETENTION_HOURS", "72").parse()?;

    let pool = db::init(&db_path, pool_size)?;
    let metrics = Arc::new(metrics::Metrics::default());
    tracing::info!(db_path, pool_size, retention_hours, "database ready");

    let (tx, writer_handle) = writer::spawn(pool.clone(), metrics.clone(), cfg);
    let retention_handle = retention::spawn(
        pool.clone(),
        Duration::from_secs(retention_hours * 3600),
        Duration::from_secs(env_or("RETENTION_INTERVAL_SECS", "600").parse()?),
    );

    let state = AppState { pool, tx, metrics };
    let listener = TcpListener::bind(bind_addr).await?;
    tracing::info!(addr = %listener.local_addr()?, "listening");

    axum::serve(listener, routes::router(state))
        .with_graceful_shutdown(shutdown_signal())
        .await?;

    // Shutdown order matters. `serve` returning drops the router, and with it
    // the only remaining `Sender`; that closes the channel, which is the signal
    // for the writer to flush its partial batch and exit. Awaiting it here is
    // what makes shutdown lossless — exiting immediately would discard every
    // record queued but not yet committed.
    retention_handle.abort();
    let _ = writer_handle.await;

    tracing::info!("shutdown complete");
    Ok(())
}

fn env_or(key: &str, default: &str) -> String {
    std::env::var(key).unwrap_or_else(|_| default.to_string())
}

/// Without this, PID 1 ignores SIGTERM, `docker stop` waits out its 10-second
/// grace period and then SIGKILLs — cutting in-flight requests and, worse,
/// killing the process with a full write queue.
async fn shutdown_signal() {
    let ctrl_c = async {
        signal::ctrl_c()
            .await
            .expect("failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        signal::unix::signal(signal::unix::SignalKind::terminate())
            .expect("failed to install SIGTERM handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => tracing::info!("received SIGINT, draining"),
        _ = terminate => tracing::info!("received SIGTERM, draining"),
    }
}

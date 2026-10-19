//! A public API-testing sample: a health check, a log-generation endpoint, and
//! a small set of httpbin-shaped endpoints for exercising HTTP clients.
//!
//! Deliberately stateless — no database, no persistent volume, no storage
//! layer. Every request is answered from what it carries in; nothing is
//! remembered between requests except a total-request counter used only to
//! give the heartbeat log line something that changes.

mod endpoints;
mod heartbeat;
mod logstorm;
mod randomlogs;
mod routes;
mod testapi;

use std::net::SocketAddr;
use std::sync::Arc;
use std::time::Duration;

use tokio::net::TcpListener;
use tokio::signal;
use tracing_subscriber::{EnvFilter, fmt};

use crate::heartbeat::RequestCounter;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    fmt()
        .with_env_filter(EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".into()))
        .json()
        .init();

    let bind_addr: SocketAddr = env_or("BIND_ADDR", "0.0.0.0:8080").parse()?;
    let heartbeat_secs: u64 = env_or("HEARTBEAT_SECS", "30").parse()?;

    let counter = Arc::new(RequestCounter::default());
    let heartbeat_handle = heartbeat::spawn(counter.clone(), Duration::from_secs(heartbeat_secs));

    let listener = TcpListener::bind(bind_addr).await?;
    tracing::info!(addr = %listener.local_addr()?, "listening");

    axum::serve(
        listener,
        // into_make_service_with_connect_info so /api/test/ip can report the
        // peer address; the plain make_service does not carry it.
        routes::router(counter).into_make_service_with_connect_info::<SocketAddr>(),
    )
    .with_graceful_shutdown(shutdown_signal())
    .await?;

    // Nothing to flush and nothing to drain — every handler answers from what
    // the request carried in. Aborting the heartbeat is a courtesy, not a
    // correctness requirement; the process is about to exit either way.
    heartbeat_handle.abort();

    tracing::info!("shutdown complete");
    Ok(())
}

fn env_or(key: &str, default: &str) -> String {
    std::env::var(key).unwrap_or_else(|_| default.to_string())
}

/// Without this, PID 1 ignores SIGTERM, `docker stop` waits out its 10-second
/// grace period and then SIGKILLs — cutting in-flight requests. That matters
/// here specifically because `/api/test/delay/{ms}` deliberately holds
/// connections open for up to 30s; a hard kill mid-delay is the one way this
/// service can still lose something.
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

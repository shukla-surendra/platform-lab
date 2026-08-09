//! SQLite setup: connection pool, pragmas, and schema.
//!
//! SQLite is an *embedded* database — no server process, just a file and a
//! library linked into this binary. Two consequences drive everything here:
//!
//! 1. Every call is **blocking** I/O against the local filesystem, so it must
//!    never run on a Tokio worker thread (see `state.rs::fetch` and
//!    `writer.rs`).
//! 2. It allows **many concurrent readers but exactly one writer**. WAL mode
//!    plus a busy timeout keeps that from surfacing as `SQLITE_BUSY`, and the
//!    batching writer keeps the single write lock from becoming the bottleneck.

use std::path::Path;

use anyhow::Context;
use r2d2_sqlite::SqliteConnectionManager;
use rusqlite::Connection;

pub type Pool = r2d2::Pool<SqliteConnectionManager>;

/// Open the database, apply pragmas, migrate, then hand back a ready pool.
///
/// This runs in two distinct phases, and the split is not cosmetic. SQLite
/// pragmas come in two kinds:
///
/// * **Database-level and persistent** — `journal_mode` and `auto_vacuum` are
///   written into the file header once and every later connection inherits
///   them. Setting `journal_mode` needs an exclusive lock, and SQLite returns
///   `SQLITE_BUSY` *immediately* rather than invoking the busy handler when
///   another connection is attached. So it must be set on a lone bootstrap
///   connection, before the pool exists.
/// * **Per-connection and ephemeral** — `busy_timeout`, `foreign_keys`, and
///   `synchronous` live on the connection handle and reset on every new one, so
///   they belong in the pool's init hook and must be repeated there.
///
/// Setting `journal_mode` in the pool hook instead makes all `pool_size`
/// connections race for that lock on a fresh database; the losers log
/// "database is locked" and r2d2 silently retries, so it looks like noise
/// rather than the startup stall it actually is.
pub fn init(path: &str, pool_size: u32) -> anyhow::Result<Pool> {
    if let Some(dir) = Path::new(path)
        .parent()
        .filter(|d| !d.as_os_str().is_empty())
    {
        // Name the path and the fix. The default DATABASE_PATH is /data/app.db,
        // which is correct inside the image and unwritable on a developer
        // machine — a bare "Read-only file system (os error 30)" sends people
        // looking at SQLite when the problem is one env var.
        std::fs::create_dir_all(dir).with_context(|| {
            format!(
                "cannot create database directory {}: set DATABASE_PATH to a writable location \
                 (e.g. DATABASE_PATH=./data/app.db) when running outside the container",
                dir.display()
            )
        })?;
    }

    // Phase 1 — exactly one connection, no contention possible.
    {
        let conn =
            Connection::open(path).with_context(|| format!("cannot open database file {path}"))?;
        conn.busy_timeout(std::time::Duration::from_secs(5))?;
        conn.pragma_update(None, "journal_mode", "WAL")?;
        // INCREMENTAL rather than FULL: retention frees pages constantly, and
        // full auto-vacuum would rewrite the file on every commit that frees
        // one. Must be set before any table exists to take effect.
        conn.pragma_update(None, "auto_vacuum", "INCREMENTAL")?;
        migrate(&conn)?;
    }

    // Phase 2 — the pool, whose connections inherit WAL from the file header.
    let manager = SqliteConnectionManager::file(path).with_init(|conn| {
        conn.execute_batch(
            "PRAGMA busy_timeout = 5000;   -- wait for the write lock, don't fail
             PRAGMA synchronous = NORMAL;  -- safe under WAL, far fewer fsyncs
             PRAGMA foreign_keys = ON;
             PRAGMA cache_size = -8000;    -- 8 MB page cache per connection",
        )
    });

    Ok(r2d2::Pool::builder().max_size(pool_size).build(manager)?)
}

/// Idempotent schema creation.
///
/// Index choices follow the queries in `query.rs`, not general tidiness — each
/// one below exists because a specific endpoint would otherwise scan the whole
/// table. Every index is also a write cost paid on the ingest hot path, which
/// is why there are no speculative ones.
fn migrate(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch(
        r#"
        CREATE TABLE IF NOT EXISTS notes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            title      TEXT NOT NULL,
            body       TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes (created_at);

        -- Logs -------------------------------------------------------------
        CREATE TABLE IF NOT EXISTS logs (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_unix_nano        INTEGER NOT NULL,
            severity_number     INTEGER,
            severity_text       TEXT NOT NULL DEFAULT '',
            body                TEXT NOT NULL DEFAULT '',
            service_name        TEXT NOT NULL,
            scope_name          TEXT NOT NULL DEFAULT '',
            trace_id            TEXT,
            span_id             TEXT,
            attributes          TEXT NOT NULL DEFAULT '{}',
            resource_attributes TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_logs_ts         ON logs (ts_unix_nano DESC);
        CREATE INDEX IF NOT EXISTS idx_logs_service_ts ON logs (service_name, ts_unix_nano DESC);
        CREATE INDEX IF NOT EXISTS idx_logs_sev_ts     ON logs (severity_text, ts_unix_nano DESC);
        -- Partial index: most logs carry no trace_id, so indexing the NULLs
        -- would double the index for no lookup benefit.
        CREATE INDEX IF NOT EXISTS idx_logs_trace      ON logs (trace_id)
            WHERE trace_id IS NOT NULL;

        -- Metrics ----------------------------------------------------------
        CREATE TABLE IF NOT EXISTS metrics (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_unix_nano INTEGER NOT NULL,
            name         TEXT NOT NULL,
            description  TEXT NOT NULL DEFAULT '',
            unit         TEXT NOT NULL DEFAULT '',
            kind         TEXT NOT NULL,
            value        REAL NOT NULL DEFAULT 0,
            count        INTEGER,
            buckets      TEXT,
            service_name TEXT NOT NULL,
            scope_name   TEXT NOT NULL DEFAULT '',
            attributes   TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_metrics_name_ts    ON metrics (name, ts_unix_nano DESC);
        CREATE INDEX IF NOT EXISTS idx_metrics_service_ts ON metrics (service_name, ts_unix_nano DESC);

        -- Spans ------------------------------------------------------------
        CREATE TABLE IF NOT EXISTS spans (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id        TEXT NOT NULL,
            span_id         TEXT NOT NULL,
            parent_span_id  TEXT,
            name            TEXT NOT NULL DEFAULT '',
            kind            INTEGER,
            start_unix_nano INTEGER NOT NULL,
            end_unix_nano   INTEGER NOT NULL,
            duration_nano   INTEGER NOT NULL DEFAULT 0,
            status_code     INTEGER,
            status_message  TEXT NOT NULL DEFAULT '',
            service_name    TEXT NOT NULL,
            scope_name      TEXT NOT NULL DEFAULT '',
            attributes      TEXT NOT NULL DEFAULT '{}',
            -- Makes re-delivery idempotent. OTLP exporters retry on timeout,
            -- and without this a flaky network silently duplicates spans,
            -- which corrupts every duration and count derived from them.
            UNIQUE (trace_id, span_id)
        );
        CREATE INDEX IF NOT EXISTS idx_spans_trace         ON spans (trace_id);
        CREATE INDEX IF NOT EXISTS idx_spans_service_start ON spans (service_name, start_unix_nano DESC);
        -- Partial index serving the trace-list query, which is only ever
        -- interested in root spans.
        CREATE INDEX IF NOT EXISTS idx_spans_roots         ON spans (start_unix_nano DESC)
            WHERE parent_span_id IS NULL;
        "#,
    )
}

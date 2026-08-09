//! Time-based retention.
//!
//! A telemetry store without retention is a disk-full incident on a timer —
//! ingest is unbounded and continuous, so the only question is which week it
//! happens. This task deletes rows past the horizon and is the difference
//! between a service that runs for a year and one that runs until the volume
//! fills.
//!
//! Two details that are easy to get wrong:
//!
//! * **Deletes are chunked.** One `DELETE` covering a day of telemetry holds
//!   the single write lock for its entire duration, during which ingest stalls
//!   and the queue drains into drops. Bounded chunks keep each transaction
//!   short so the writer interleaves.
//! * **Deleting does not shrink the file.** SQLite reuses freed pages but
//!   never returns them to the filesystem without a `VACUUM`. `incremental_vacuum`
//!   with `auto_vacuum=INCREMENTAL` (set in `db.rs`) gives back space without
//!   the full-rewrite stall that plain `VACUUM` causes.

use std::time::Duration;

use crate::db::Pool;
use crate::otlp::now_unix_nano;

const CHUNK: i64 = 5_000;

pub fn spawn(pool: Pool, retention: Duration, interval: Duration) -> tokio::task::JoinHandle<()> {
    tokio::spawn(async move {
        let mut ticker = tokio::time::interval(interval);
        // The first tick fires immediately; skip it so startup is not spent
        // deleting before anything has been ingested.
        ticker.tick().await;

        loop {
            ticker.tick().await;
            let pool = pool.clone();
            let cutoff = now_unix_nano().saturating_sub(retention.as_nanos() as u64) as i64;

            let result = tokio::task::spawn_blocking(move || prune(&pool, cutoff)).await;

            match result {
                Ok(Ok(n)) if n > 0 => tracing::info!(deleted = n, cutoff, "retention pass"),
                Ok(Ok(_)) => tracing::debug!("retention pass: nothing expired"),
                Ok(Err(e)) => tracing::error!(error = %e, "retention pass failed"),
                Err(e) => tracing::error!(error = %e, "retention task panicked"),
            }
        }
    })
}

fn prune(pool: &Pool, cutoff: i64) -> rusqlite::Result<usize> {
    let conn = pool
        .get()
        .map_err(|e| rusqlite::Error::InvalidParameterName(format!("pool checkout: {e}")))?;

    let mut total = 0usize;
    for (table, ts_col) in [
        ("logs", "ts_unix_nano"),
        ("metrics", "ts_unix_nano"),
        ("spans", "start_unix_nano"),
    ] {
        loop {
            // rowid-keyed subquery: LIMIT is not allowed directly on DELETE
            // unless SQLite was built with SQLITE_ENABLE_UPDATE_DELETE_LIMIT,
            // which the bundled amalgamation is not.
            let n = conn.execute(
                &format!(
                    "DELETE FROM {table} WHERE rowid IN
                     (SELECT rowid FROM {table} WHERE {ts_col} < ?1 LIMIT {CHUNK})"
                ),
                [cutoff],
            )?;
            total += n;
            if n < CHUNK as usize {
                break;
            }
        }
    }

    if total > 0 {
        // Hand freed pages back to the filesystem a slice at a time.
        conn.execute_batch("PRAGMA incremental_vacuum(200);")?;
    }
    Ok(total)
}

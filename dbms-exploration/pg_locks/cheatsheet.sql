-- Postgres lock management cheatsheet. Each block is independent: copy what you need.

-- 1. What is running right now, and for how long?
SELECT pid, usename, application_name, client_addr, state,
       wait_event_type, wait_event,
       now() - xact_start  AS xact_age,
       now() - query_start AS query_age,
       left(query, 80)     AS query
FROM pg_stat_activity
WHERE state <> 'idle' AND pid <> pg_backend_pid()
ORDER BY xact_start NULLS LAST;

-- 2. Who is blocked, and by whom?
SELECT pid, pg_blocking_pids(pid) AS blocked_by,
       now() - query_start AS waiting_for,
       left(query, 80)     AS query
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0;

-- 3. Root blockers: block someone, but aren't blocked themselves.
SELECT a.pid, a.state, now() - a.xact_start AS xact_age, left(a.query, 80) AS last_query
FROM pg_stat_activity a
WHERE a.pid IN (SELECT unnest(pg_blocking_pids(pid)) FROM pg_stat_activity)
  AND cardinality(pg_blocking_pids(a.pid)) = 0;

-- 4. Every lock in this database (granted = f are the waiters).
SELECT l.pid, l.locktype, l.relation::regclass AS tbl, l.mode, l.granted,
       left(a.query, 60) AS query
FROM pg_locks l JOIN pg_stat_activity a USING (pid)
WHERE a.datname = current_database()
ORDER BY l.granted DESC, l.pid;

-- 5. Long-open transactions (danger for locks and vacuum).
SELECT pid, state, now() - xact_start AS xact_age, left(query, 80) AS query
FROM pg_stat_activity
WHERE xact_start < now() - interval '5 minutes'
ORDER BY xact_start;

-- 6. Stop a query (gentle) / close a session (rolls back its transaction).
-- SELECT pg_cancel_backend(<pid>);
-- SELECT pg_terminate_backend(<pid>);

-- 7. Close every session idle in a transaction for > 5 minutes.
-- SELECT pid, pg_terminate_backend(pid) FROM pg_stat_activity
-- WHERE state = 'idle in transaction' AND now() - state_change > interval '5 minutes';

-- 8. Slowest queries over time (needs pg_stat_statements).
SELECT calls, round(total_exec_time) AS total_ms, round(mean_exec_time) AS mean_ms,
       left(regexp_replace(query, '\s+', ' ', 'g'), 80) AS query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
-- SELECT pg_stat_statements_reset();   -- start counting from zero

-- 9. Safety timeouts.
-- SET lock_timeout = '3s';                                        -- before a migration
-- ALTER ROLE app_user SET statement_timeout = '30s';
-- ALTER DATABASE shop SET idle_in_transaction_session_timeout = '5min';

-- 10. Logging (no restart needed).
-- ALTER SYSTEM SET log_lock_waits = on;
-- ALTER SYSTEM SET log_min_duration_statement = '1s';
-- SELECT pg_reload_conf();
-- SHOW log_directory;   -- where the log files are (if logging_collector = on)

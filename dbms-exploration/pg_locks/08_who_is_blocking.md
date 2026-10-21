# 08 — Who is running what, for how long, and who is blocking whom

Three built-in views answer everything:

| View / function | Answers |
|---|---|
| `pg_stat_activity` | every connection: its current/last query, state, how long |
| `pg_blocking_pids(pid)` | "which pids is this one waiting for?" |
| `pg_locks` | every lock held (`granted = t`) or wanted (`granted = f`) |

## 1. What's running and for how long

```sql
SELECT pid, usename, state, wait_event_type, wait_event,
       now() - xact_start  AS xact_age,     -- how long the transaction is open
       now() - query_start AS query_age,    -- how long this query is running
       left(query, 60) AS query
FROM pg_stat_activity
WHERE state <> 'idle' AND pid <> pg_backend_pid()
ORDER BY xact_start;
```

How to read `state`:

| state | meaning | worry? |
|---|---|---|
| `active` | running a query right now | if `query_age` is large |
| `idle` | connected, doing nothing, no transaction | no |
| `idle in transaction` | ran `BEGIN`, then **stopped talking** — still holding locks | **yes** |

`wait_event_type = Lock` means "stuck waiting for a lock".

## 2. Who blocks whom

```sql
SELECT pid, pg_blocking_pids(pid) AS blocked_by,
       now() - query_start AS waiting_for, left(query, 60) AS query
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0;
```

Real output while someone forgot to `COMMIT`:
```
 pid |        state        | blocked_by | in_this_state   | last_query
-----+---------------------+------------+-----------------+---------------------------------------------
 683 | idle in transaction | {}         | 00:00:02.031606 | UPDATE products SET stock = 1 WHERE id = 3;
 690 | active              | {683}      | 00:00:01.010689 | UPDATE products SET stock = 4 WHERE id = 3;
```
683 isn't running anything — its `query` is just the **last** thing it ran. It's blocking
690 only because its transaction is still open. **683 is the one to deal with** (lesson 09).

> Follow the chain to the root: the pid that appears in `blocked_by` but has `{}` itself.

## 3. Which locks exactly

```sql
SELECT l.pid, l.locktype, l.relation::regclass, l.mode, l.granted, left(a.query, 40)
FROM pg_locks l JOIN pg_stat_activity a USING (pid)
WHERE a.datname = current_database()
ORDER BY l.granted DESC;
```
`granted = f` rows are the waiters. Example in [06_ddl_pileup.md](06_ddl_pileup.md).

## 4. Slowest queries over time (not just right now)

`pg_stat_activity` only shows *now*. For history use the `pg_stat_statements` extension
(enabled in this lab):
```sql
SELECT calls, round(total_exec_time) AS total_ms, round(mean_exec_time) AS mean_ms,
       left(query, 50) AS query
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 5;
```
```
 calls | total_ms | mean_ms | query
-------+----------+---------+----------------------------------------------
     6 |     8846 |    1474 | UPDATE products SET stock = $1 WHERE id = $2
     2 |     6990 |    3495 | ALTER TABLE products ADD COLUMN color text
```
Note: time spent **waiting for a lock counts as execution time** here.

Next: [09_kill.md](09_kill.md)

# 10 — Timeouts (automatic killing) and logs

## Part 1: timeouts — let Postgres kill for you

| Setting | Kills… | Real output when it fires |
|---|---|---|
| `lock_timeout` | a statement that **waits for a lock** too long | `ERROR: canceling statement due to lock timeout` |
| `statement_timeout` | a statement that **runs** too long (waiting included) | `ERROR: canceling statement due to statement timeout` |
| `idle_in_transaction_session_timeout` | a session sitting **idle inside `BEGIN`** | `FATAL: terminating connection due to idle-in-transaction timeout` |
| `transaction_timeout` (PG 17+) | a whole transaction that's too long | |

Real run of `lock_timeout` (A holds row 1):
```
SET lock_timeout = '1s';
UPDATE products SET stock = 50 WHERE id = 1;
ERROR:  canceling statement due to lock timeout
CONTEXT:  while updating tuple (0,11) in relation "products"
Time: 1001.115 ms
```

Where to set them (narrowest first):
```sql
SET lock_timeout = '3s';                                     -- this session only
ALTER ROLE app_user SET statement_timeout = '30s';           -- every session of a user
ALTER DATABASE shop SET idle_in_transaction_session_timeout = '5min';
```
Sensible starting point for an app user: `statement_timeout 30s`,
`idle_in_transaction_session_timeout 5min`; for migrations: `lock_timeout 3s`.

## Part 2: logs — what happened while you weren't looking

Turned on in this lab's `docker-compose.yml`:

| Setting | Logs |
|---|---|
| `log_lock_waits = on` | any wait longer than `deadlock_timeout` (1 s) — who waited, who held it |
| `log_min_duration_statement = 2000` | every statement slower than 2 s, with its time |
| (always on) | deadlocks, with both queries |

**Where are the logs?**
- Docker: `docker compose logs postgres` (Postgres writes to stderr here; `logging_collector = off`)
- Linux server: usually `/var/log/postgresql/` or `$PGDATA/log/` (check `SHOW log_directory;`)
- Managed cloud (RDS, Azure, Cloud SQL): the provider's log viewer / log analytics

Real lines from this lab:

```
LOG:  process 449 still waiting for AccessExclusiveLock on relation 16385 of database 16384 after 1000.321 ms
DETAIL:  Process holding the lock: 442. Wait queue: 449, 464.
LOG:  process 464 still waiting for AccessShareLock on relation 16385 ... after 1000.061 ms
LOG:  duration: 8008.426 ms  statement: BEGIN; SELECT count(*) FROM products; SELECT pg_sleep(8); COMMIT;
LOG:  process 449 acquired AccessExclusiveLock on relation 16385 ... after 6989.615 ms
LOG:  duration: 6991.134 ms  statement: ALTER TABLE products ADD COLUMN color text;
```
→ "the ALTER (449) waited 7 s behind a report (442) and made a SELECT (464) wait too."
(`relation 16385` → name it with `SELECT 16385::regclass;`)

Deadlock in the log (more detail than the client gets):
```
ERROR:  deadlock detected
DETAIL:  Process 765 waits for ShareLock on transaction 777; blocked by process 764.
	Process 764 waits for ShareLock on transaction 778; blocked by process 765.
	Process 765: BEGIN; UPDATE products ... WHERE id = 1; ... UPDATE ... WHERE id = 2; COMMIT;
	Process 764: BEGIN; UPDATE products ... WHERE id = 2; ... UPDATE ... WHERE id = 1; COMMIT;
```

Search them:
```bash
docker compose logs postgres | grep -E "still waiting|deadlock|duration"
```

## Turning logging on in a real server

```sql
ALTER SYSTEM SET log_lock_waits = on;
ALTER SYSTEM SET log_min_duration_statement = '1s';
SELECT pg_reload_conf();          -- no restart needed for these
```
(`pg_stat_statements` needs `shared_preload_libraries` + a restart, then
`CREATE EXTENSION pg_stat_statements;`.)

That's the whole topic. Copy-paste versions of every query: [cheatsheet.sql](cheatsheet.sql).

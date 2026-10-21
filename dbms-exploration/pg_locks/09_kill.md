# 09 — Killing a query or a session

Two levels, try the gentle one first:

| Function | Story | What happens |
|---|---|---|
| `pg_cancel_backend(pid)` | tap the person on the shoulder: "stop that" | current **query** stops; connection stays; transaction becomes aborted (they must `ROLLBACK`) |
| `pg_terminate_backend(pid)` | escort them out of the building | whole **connection** closed; open transaction **rolled back**; all its locks released |

Find the pid with lesson 08's queries first.

## Cancel a long query

```sql
SELECT pg_cancel_backend(1234);
```
Real output — the killer sees `t`, the victim sees:
```
ERROR:  canceling statement due to user request
```

## Terminate a session (needed for `idle in transaction`)

Cancel does nothing to an `idle in transaction` session — it isn't running a query. You must
terminate it:
```sql
SELECT pg_terminate_backend(1234);
```
Victim sees:
```
FATAL:  terminating connection due to administrator command
server closed the connection unexpectedly
```
Its `UPDATE ... SET stock = 1` was rolled back — stock stayed `5`.

## Kill all blockers older than 5 minutes

```sql
SELECT pid, pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle in transaction'
  AND now() - state_change > interval '5 minutes';
```

## Safety notes

- You can kill your own user's sessions; killing others needs superuser or the
  `pg_signal_backend` role.
- Terminating rolls back work — a 2-hour `UPDATE` takes time to roll back too.
- Never `kill -9` the Postgres process from the OS: the whole server restarts.
- Killing fixes today. Fix the app (missing `COMMIT`, long transactions) for tomorrow, or let
  the timeouts in lesson 10 do the killing automatically.

Next: [10_timeouts_and_logs.md](10_timeouts_and_logs.md)

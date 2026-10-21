# 05 — Table locks

## Story: the shop building

Row locks are "this shelf is busy". A table lock is about the **whole shop**:
- customers walking in (`SELECT`) — any number at once
- staff restocking shelves (`UPDATE`) — many at once, each on their own shelf
- **renovation** (`ALTER TABLE`, `DROP`) — shop closed, *nobody* inside, not even browsers

**Every** SQL command takes a table lock, even `SELECT`. Most are so weak you never notice.

## See it yourself

Run a command inside a transaction, then ask Postgres what *you* are holding:
```sql
BEGIN;
UPDATE products SET stock = stock WHERE id = 1;
SELECT relation::regclass, mode FROM pg_locks
WHERE pid = pg_backend_pid() AND relation = 'products'::regclass;
ROLLBACK;
```

Real results, one per command:
```
SELECT ...                 → AccessShareLock
SELECT ... FOR UPDATE      → RowShareLock
UPDATE / DELETE / INSERT   → RowExclusiveLock
CREATE INDEX               → ShareLock
ALTER TABLE ADD COLUMN     → AccessExclusiveLock
```

## The 8 levels (weakest → strongest)

| # | Lock | Taken by | Blocks (in plain words) |
|:-:|---|---|---|
| 1 | ACCESS SHARE | `SELECT` | only #8 |
| 2 | ROW SHARE | `SELECT ... FOR UPDATE/SHARE` | #7, #8 |
| 3 | ROW EXCLUSIVE | `INSERT`, `UPDATE`, `DELETE`, `MERGE` | #5–#8 |
| 4 | SHARE UPDATE EXCLUSIVE | `VACUUM`, `ANALYZE`, `CREATE INDEX CONCURRENTLY` | #4–#8 |
| 5 | SHARE | `CREATE INDEX` (normal) | #3, #4, #6, #7, #8 → **blocks writes** |
| 6 | SHARE ROW EXCLUSIVE | `CREATE TRIGGER`, some `ALTER TABLE` | #3–#8 |
| 7 | EXCLUSIVE | `REFRESH MATERIALIZED VIEW CONCURRENTLY` | #2–#8 |
| 8 | ACCESS EXCLUSIVE | `ALTER TABLE`, `DROP`, `TRUNCATE`, `VACUUM FULL`, `LOCK TABLE` | **everything, even SELECT** |

Don't memorise all of it. Remember three lines:

```
SELECT, INSERT, UPDATE, DELETE      → don't block each other at table level (only rows)
CREATE INDEX (normal)               → blocks writes, allows reads   → use CONCURRENTLY
ALTER / DROP / TRUNCATE / VACUUM FULL → blocks EVERYTHING            → keep them short
```

## Read vs write summary

| Command | Others can still **read**? | Others can still **write**? |
|---|:-:|:-:|
| `SELECT` | ✅ | ✅ |
| `UPDATE` / `DELETE` | ✅ | ✅ other rows (same row waits) |
| `CREATE INDEX` | ✅ | ❌ |
| `CREATE INDEX CONCURRENTLY` | ✅ | ✅ (slower, can't run in a transaction) |
| `ALTER TABLE` / `DROP` / `TRUNCATE` | ❌ | ❌ |

You can also take a table lock by hand: `LOCK TABLE products IN SHARE MODE;` (rarely needed).

Next: [06_ddl_pileup.md](06_ddl_pileup.md)

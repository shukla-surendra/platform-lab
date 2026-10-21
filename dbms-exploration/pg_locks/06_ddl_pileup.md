# 06 — How one `ALTER TABLE` freezes the whole app

## Story: the queue at the door

A slow customer is browsing (long `SELECT`). The renovator (`ALTER TABLE`) arrives and waits
at the door for the shop to empty. Now new customers arrive — and they **queue behind the
renovator**, even though the shop is open and they only want to look. Locks are granted in
**arrival order** (a queue), so one waiting strong lock blocks everyone after it.

## Run it (three sessions)

```sql
-- A: a slow report
BEGIN; SELECT count(*) FROM products; SELECT pg_sleep(8); COMMIT;
-- B: a migration (1 s later)
ALTER TABLE products ADD COLUMN color text;
-- C: a normal app read (1 s later)
SELECT id FROM products WHERE id = 1;
```

## Real output — watching it happen

```
 pid | wait_event_type | query
-----+-----------------+---------------------------------------------
 442 | Timeout         | BEGIN; SELECT count(*) FROM products; ...    ← running, holds ACCESS SHARE
 449 | Lock            | ALTER TABLE products ADD COLUMN color text;  ← waiting for 442
 464 | Lock            | SELECT id FROM products WHERE id = 1;        ← waiting for 449 (!)

 pid | blocked_by
-----+-----------
 449 | {442}
 464 | {449}

 pid |        mode         | granted
-----+---------------------+---------
 442 | AccessShareLock     | t
 449 | AccessExclusiveLock | f
 464 | AccessShareLock     | f
```

C's tiny `SELECT` took **5993 ms**. In production, that's every request to that table
hanging until the report ends → connection pool fills → site down.

## How to do migrations safely

```sql
SET lock_timeout = '3s';                 -- give up instead of blocking everyone
ALTER TABLE products ADD COLUMN color text;
-- if it fails with "lock timeout", retry a bit later
```
Plus: check for long-running transactions first (lesson 08), and use
`CREATE INDEX CONCURRENTLY` for indexes.

Next: [07_deadlock.md](07_deadlock.md)

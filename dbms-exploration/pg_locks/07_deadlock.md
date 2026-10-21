# 07 — Deadlock

## Story: two people in a narrow corridor

A holds the pen and wants the notebook. B holds the notebook and wants the pen. Each waits
for the other — forever. Postgres notices this (after `deadlock_timeout`, default 1 s) and
**kills one of them** so the other can go on.

## Run it

```sql
-- A                                           -- B (at the same time)
BEGIN;                                          BEGIN;
UPDATE products ... WHERE id = 1;               UPDATE products ... WHERE id = 2;
SELECT pg_sleep(1);                             SELECT pg_sleep(1);
UPDATE products ... WHERE id = 2;  -- waits B   UPDATE products ... WHERE id = 1;  -- waits A
COMMIT;                                         COMMIT;
```

## Real output

```
A: ERROR:  deadlock detected
A: DETAIL:  Process 765 waits for ShareLock on transaction 777; blocked by process 764.
            Process 764 waits for ShareLock on transaction 778; blocked by process 765.
A: CONTEXT:  while updating tuple (0,12) in relation "products"

B: UPDATE 1
B: COMMIT         ← B survived
```

A's whole transaction is rolled back; the app must **retry** it.

> "ShareLock on transaction 777"? When you wait for a row, Postgres actually makes you wait
> for the **transaction** that holds it to finish. That's why row waits show up this way.

## How to avoid

- Always lock/update rows in the **same order** everywhere (e.g. `ORDER BY id`).
  Same order → people queue instead of crossing.
- Keep transactions short.
- In the app, catch error code `40P01` (deadlock) and retry.

Next: [08_who_is_blocking.md](08_who_is_blocking.md)

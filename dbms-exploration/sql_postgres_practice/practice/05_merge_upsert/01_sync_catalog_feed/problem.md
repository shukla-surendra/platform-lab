# 1. Sync a Catalog Price Feed

**Fixture:** `ecommerce`
**Pattern:** Basic `MERGE` upsert (update-or-insert)

## Problem

You've received a batch of catalog updates (a supplier price feed):

| name | category | price |
|---|---|---|
| Wireless Mouse | Electronics | 22.00 |
| Mechanical Keyboard | Electronics | 95.00 |
| Webcam HD | Electronics | 49.00 |

The first two products already exist (their prices should update);
"Webcam HD" is new (it should be inserted). Do this as a single `MERGE`
statement.

## Why one statement instead of "check, then decide"

Without `MERGE`, this needs application logic to check each row first,
then issue an `UPDATE` or `INSERT` per row depending on what it found —
multiple round trips, and a race window if two syncs could ever run
concurrently. `MERGE` does the check-and-branch inside the database, as
one atomic statement covering the whole batch.

## Expected output (after running, before rolling back)

```
    name             | price
----------------------+-------
 Mechanical Keyboard  | 95.00
 Webcam HD            | 49.00
 Wireless Mouse       | 22.00
```

`MERGE 3` — all three source rows produced an action (2 updates, 1 insert).

## Solution

See `solution.sql` in this folder. It's wrapped in `BEGIN; ... ROLLBACK;`
so running it doesn't permanently change your loaded fixture — drop the
`ROLLBACK` (or change it to `COMMIT`) if you want the change to stick.

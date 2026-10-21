# 04 — Locking rows on purpose: `SELECT ... FOR UPDATE`

## Story: the last bag

Only 5 bags left. Your app does: *read stock → check it's > 0 → write stock - 1*. If two
customers read "5" at the same time, both write "4" and one sale is lost. Fix: lock the row
**when you read it**, so the second customer waits until the first is done.

```sql
BEGIN;
SELECT stock FROM products WHERE id = 3 FOR UPDATE;   -- lock it now
-- app checks stock > 0 ...
UPDATE products SET stock = stock - 1 WHERE id = 3;
COMMIT;
```

## The 4 row lock modes (weakest → strongest)

| Mode | Use it when | Blocks |
|---|---|---|
| `FOR KEY SHARE` | (Postgres uses it automatically for foreign-key checks) | only deleting the row / changing its key |
| `FOR SHARE` | "nobody change this row while I'm working" | all writers, but other `FOR SHARE` can join |
| `FOR NO KEY UPDATE` | (what a normal `UPDATE` of non-key columns takes) | writers, `FOR SHARE` |
| `FOR UPDATE` | "I'm about to change/delete this row" | everyone who wants any lock on it |

None of them block a **plain `SELECT`**.

## Don't want to wait? `NOWAIT` and `SKIP LOCKED`

A holds `FOR UPDATE` on bag (id 3). B:

```sql
SELECT * FROM products WHERE id = 3 FOR UPDATE NOWAIT;
SELECT * FROM products WHERE id = 3;            -- plain read
```
```
ERROR:  could not obtain lock on row in relation "products"     ← fails instantly
Time: 0.386 ms
 id | name | price | stock
  3 | bag  |   900 |     5                                     ← plain read: fine
Time: 0.104 ms
```

**`SKIP LOCKED` = a job queue.** Two workers each grab "the next pending job":
```sql
SELECT id FROM jobs WHERE status = 'pending' ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED;
```
```
worker A gets:  1
worker B gets:  2     ← skipped the job A has locked instead of waiting for it
```

## `FOR SHARE` lets readers join, not writers

A holds `FOR SHARE` on notebook (id 2). B:
```
SELECT ... FOR SHARE    → Time: 0.919 ms        (shared + shared = OK)
UPDATE products ...     → Time: 1968.987 ms     (waited for A)
```

## Foreign keys lock too (quietly)

`INSERT INTO orders (product_id ...)` takes `FOR KEY SHARE` on the product row, to make sure
the product isn't deleted mid-insert.

```
A is renaming product 1 (UPDATE name)  → B inserts an order for product 1:  1.026 ms   (no conflict)
A is DELETING product 3                → B inserts an order for product 3:  1977.712 ms (waited)
```

Next: [05_table_locks.md](05_table_locks.md)

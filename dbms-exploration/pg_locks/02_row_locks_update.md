# 02 — Row locks: who waits when someone updates a row

## Story: two cashiers, one pen in stock

Cashier A is selling a pen (row `id = 1`) and hasn't finished yet. What happens to:
a customer just *looking* at the price, a cashier selling a *notebook*, and a cashier
selling *another pen*?

## Run it

**A** (start a sale, don't finish it):
```sql
BEGIN;
UPDATE products SET stock = stock - 1 WHERE id = 1;
-- don't commit yet
```

**B**, while A is still open:
```sql
\timing on
SELECT id, stock FROM products WHERE id = 1;          -- 1. read the same row
UPDATE products SET stock = stock - 1 WHERE id = 2;   -- 2. update a DIFFERENT row
UPDATE products SET stock = stock - 1 WHERE id = 1;   -- 3. update the SAME row  → hangs
```
Now `COMMIT;` in A — B's third statement finishes immediately.

## Real output (B)

```
 id | stock
----+-------
  1 |   100          ← sees the OLD value (A hasn't committed), instantly
Time: 0.368 ms

UPDATE 1           ← different row: no waiting
Time: 0.992 ms

UPDATE 1           ← same row: waited until A committed
Time: 2821.829 ms (00:02.822)
```

Final stock of pen: `98` — both sales counted, none lost. That's what the lock is for.

## What happened

```
A: UPDATE row 1 ──► takes EXCLUSIVE lock on row 1 ─────────────── COMMIT ─► lock released
B: SELECT row 1   ─► no lock needed, reads old version ✅
B: UPDATE row 2   ─► row 2 is free ✅
B: UPDATE row 1   ─► ⏳ waits ............................................ ✅ runs
```

## Which statements lock rows

| Statement | Row lock taken | Blocks other writers of that row? | Blocks plain SELECT? |
|---|---|:-:|:-:|
| `SELECT` | none | no | no |
| `UPDATE` | exclusive on each changed row | yes | **no** |
| `DELETE` | exclusive on each deleted row | yes | **no** |
| `INSERT` | the new row (invisible to others until commit) | only on a duplicate unique key | no |

**Edge:** two `INSERT`s with the same primary key → the second waits to see whether the first
commits (then it fails "duplicate key") or rolls back (then it succeeds).

Next: [03_no_column_locks.md](03_no_column_locks.md)

# 03 — There are no column locks

## Story: one form, two fields

A manager changes the pen's **price**. At the same moment a warehouse worker changes the
pen's **stock**. Different fields — surely they don't disturb each other?

## Run it

**A**:
```sql
BEGIN;
UPDATE products SET price = 12 WHERE id = 1;   -- touches only "price"
```

**B**:
```sql
\timing on
UPDATE products SET stock = 99 WHERE id = 1;   -- touches only "stock" → still hangs
```
Then `COMMIT;` in A.

## Real output (B)

```
UPDATE 1
Time: 1972.223 ms (00:01.972)     ← waited for A
```

## Why

Postgres never edits a row in place. An `UPDATE` writes a **whole new copy of the row**
(all columns) and marks the old one as dead. So the smallest thing it can lock is **the whole
row**. Locking levels in Postgres are only:

```
row  →  table  →  (database-wide "advisory" locks you create yourself)
```

**Column-level** in Postgres means *permissions* (`GRANT UPDATE (stock) ON products TO worker`),
not locks.

## What to do about it

If two parts of the app hammer different columns of the same hot row (e.g. a `views_count`
on a popular article), split them into **separate tables/rows** so they lock separately.

Next: [04_select_for_update.md](04_select_for_update.md)

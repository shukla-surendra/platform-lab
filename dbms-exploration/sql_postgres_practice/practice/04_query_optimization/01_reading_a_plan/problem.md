# 1. Reading a Plan and Watching an Estimate Improve

**Fixture:** `ecommerce`
**Pattern:** `EXPLAIN ANALYZE`, row-estimate accuracy

## Problem

Run `EXPLAIN ANALYZE` against a query filtering `orders` on an unindexed
column (`order_date`), on a freshly-loaded table (no `ANALYZE` run yet).
Note the estimated vs actual row count. Then run `ANALYZE orders;` and
re-run the same `EXPLAIN ANALYZE` — compare the estimate.

```sql
EXPLAIN ANALYZE SELECT * FROM orders WHERE order_date > '2026-03-01';
```

## What to look for

Before `ANALYZE`, this fixture actually produces something worth stopping
on: the planner estimates **`rows=377`** — more rows than the entire
18-row table even has — while the actual result is 7 rows. That's not a
bug; it's Postgres falling back to a generic default selectivity guess
because no real column statistics exist yet for a table this fresh. After
`ANALYZE orders;`, the estimate should land on exactly `rows=7` — matching
reality, because now the planner has an actual statistics sample to work
from.

Either way, both queries choose `Seq Scan` here (see `../PATTERN.md`'s
honest note on fixture size) — the point of this exercise is reading the
estimate-vs-actual gap and knowing `ANALYZE` is what closes it, not
forcing a different scan type.

## Expected output shape

Before `ANALYZE` (your exact numbers may vary slightly by Postgres
version, but the estimate will be far off):
```
Seq Scan on orders  (cost=0.00..24.12 rows=377 width=44) (actual ... rows=7 ...)
```

After `ANALYZE orders;`:
```
Seq Scan on orders  (cost=0.00..1.23 rows=7 width=21) (actual ... rows=7 ...)
```

## Solution

See `solution.sql` — it's the two `EXPLAIN ANALYZE` statements plus the
`ANALYZE` between them, meant to be run and compared, not just read.

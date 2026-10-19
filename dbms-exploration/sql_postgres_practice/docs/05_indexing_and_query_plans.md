# Indexing & Query Plans — Mental Model

## The one idea: an index is a second, ordered copy that points back

A table's rows aren't stored in any query-useful order (Postgres calls this
raw storage the *heap*). Without an index, "find the row where
`customer_id = 7`" means scanning every row and checking — a **sequential
scan**. An index is a separate structure (a B-tree, by default) that keeps
the indexed column(s) *sorted*, with each entry pointing back to the
matching row's physical location — so a lookup becomes a fast
sorted-search instead of "check every row," at the cost of extra storage
and slower writes (the index has to be updated on every `INSERT`/`UPDATE`/
`DELETE` too).

Same trade-off as a book: reading the index page to find "which chapter
mentions X" is faster than reading every page, but only because someone
already did the sorting work up front — and paid for it in book length.

## `EXPLAIN` vs `EXPLAIN ANALYZE`

- `EXPLAIN` — shows the planner's **estimated** plan and cost, without
  running the query. Fast, but the numbers are guesses (based on table
  statistics).
- `EXPLAIN ANALYZE` — **actually runs** the query and shows real timings
  and row counts alongside the estimates. Slower to run (it's not free —
  it executes everything, including any `INSERT`/`UPDATE` you `EXPLAIN
  ANALYZE`, which really happens), but tells you where the estimate and
  reality diverge, which is usually the actual clue when a query is slow.

## Reading a plan, the parts that matter first

```text
EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 5;

Index Scan using idx_orders_customer_id on orders
  (cost=0.15..8.17 rows=3 width=24)
  (actual time=0.021..0.024 rows=3 loops=1)
```

- **Scan type** — `Seq Scan` (read every row), `Index Scan` (use the index,
  then fetch the matching row from the heap), `Index Only Scan` (the index
  alone has every column the query needs — no heap fetch at all, the
  fastest option when it applies), `Bitmap Heap Scan` (index identifies a
  *set* of matching pages first, useful when many scattered rows match).
- **cost=A..B** — planner's estimated startup cost and total cost, in
  arbitrary units (not milliseconds) — only meaningful *relative* to other
  plans being compared, not as an absolute number.
- **rows=N** (in the cost line) — estimated row count. Compare this to
  `actual ... rows=N` — a big mismatch (planner expected 3, got 30,000)
  is the single most common root cause of "why did Postgres pick a bad
  plan," since the whole plan is chosen based on the estimate.

## Spotting "this table needs an index"

A `Seq Scan` on a large table, filtered by a `WHERE` clause on an
unindexed column, with a small `actual rows` count relative to the table's
total size, is the textbook signal: Postgres is reading everything to find
a few matching rows, and a B-tree index on that column would turn it into
a direct lookup instead.

## When an index *doesn't* help (and the planner is right to ignore it)

- **Low selectivity** — an index on a boolean `status` column with only 2
  distinct values across a million rows barely narrows anything down; the
  planner often (correctly) prefers a sequential scan over the overhead of
  an index lookup that still returns a huge fraction of the table.
- **Small tables** — for a few hundred rows, a sequential scan easily fits
  in memory and is faster than the overhead of an index traversal; the
  planner will (correctly) ignore an index that technically exists.
- **A function wraps the column** — `WHERE LOWER(email) = 'a@b.com'` can't
  use a plain index on `email`, because the *stored* values aren't
  lowercased — the index is sorted by the raw column, not by
  `LOWER(column)`. Fix: an expression index, `CREATE INDEX ON customers
  (LOWER(email))`.
- **A leading wildcard `LIKE`** — `WHERE name LIKE '%smith'` can't use a
  standard B-tree index (sorted order doesn't help when you don't know the
  *start* of the string); `WHERE name LIKE 'smith%'` can, since a sorted
  index can jump straight to the "smith..." range.

## The practical loop

Don't guess: `EXPLAIN ANALYZE` before optimizing, add the index, `EXPLAIN
ANALYZE` again, and check both that the scan type changed *and* that
`actual time` actually dropped — a changed plan that isn't actually faster
means the real bottleneck was somewhere else (or the table was small
enough that it never mattered).

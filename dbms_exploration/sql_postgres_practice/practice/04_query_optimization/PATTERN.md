# Pattern: Reading Query Plans & Diagnosing Slow Queries

## What problem does this solve?

"This query is slow" is not actionable on its own — you need to know
*why*: wrong scan type, stale statistics, a filter that can't use an
index, or (surprisingly often) nothing wrong at all, just a table too
small for an index to matter. `EXPLAIN`/`EXPLAIN ANALYZE` is how you find
out which one it actually is instead of guessing. Read
`../../docs/05_indexing_and_query_plans.md` first — this file assumes
that mental model.

## An honest note on this fixture

These fixture tables have a handful to a few dozen rows. **You will not
see a dramatic real speedup from adding an index here** — and that's
itself the lesson: the planner correctly prefers a sequential scan on a
table this small, because reading the whole (tiny) table is cheaper than
the overhead of an index lookup. The problems below are built around
things you genuinely *can* observe at this scale: reading a plan's shape,
watching a row-estimate improve after `ANALYZE`, and using
`SET enable_seqscan = off` as a diagnostic-only trick to force a plan you
want to inspect (never a production setting).

## How to recognize when this pattern applies

- "Why is this query slow" / "how do I speed this up" — always
  `EXPLAIN ANALYZE` first, never guess-and-add-an-index first.
- A `WHERE` clause wraps a column in a function (`LOWER(col)`,
  `DATE(col)`, ...) — check whether that breaks index usage.
- Estimated `rows=` and actual `rows=` diverge wildly — usually stale or
  missing statistics (`ANALYZE table_name` refreshes them).

## The general workflow

```sql
EXPLAIN ANALYZE <query>;          -- see the real plan + real timings
-- if Seq Scan on a large, selective filter: consider an index
CREATE INDEX ON table (column);
EXPLAIN ANALYZE <query>;          -- re-check: did the plan change? did it get faster?
```

Both questions in that last line matter independently — a changed plan
that isn't faster means the real bottleneck was elsewhere (or the table
was too small to matter, as in this fixture).

## Common pitfalls

- Adding an index and declaring victory without re-running
  `EXPLAIN ANALYZE` to confirm it's actually used *and* actually faster.
- Not noticing a function wrapped around the filtered column — the index
  exists but doesn't match what's actually being compared.
- Trusting stale row estimates on a table that's changed a lot since the
  last `ANALYZE` (autovacuum handles this in production over time; on a
  freshly-loaded fixture, statistics may not exist yet at all).

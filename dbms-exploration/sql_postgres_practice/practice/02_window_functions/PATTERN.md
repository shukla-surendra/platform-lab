# Pattern: Window Functions

## What problem does this solve?

Two shapes of question keep coming up that plain `GROUP BY` can't answer,
because `GROUP BY` collapses rows and these questions need to keep every
row while still comparing it against its peers:

1. **"The Nth row per group"** — most recent order per customer, top
   scorer per team, first event per session. `GROUP BY` can give you the
   *value* of the max/min, but not the *whole row* it came from, without
   an extra self-join.
2. **"Something relative to neighboring rows"** — running totals, rank,
   time-since-previous-event. There's no "previous row" concept in
   ordinary SQL without a self-join or a window function.

Read `../../docs/03_window_functions.md` first — this file assumes that
mental model (rows aren't collapsed; each row gets a computed value based
on its "peers").

## How to recognize it

- "The most recent / highest / Nth **per** X, but show me the full row" —
  not just the aggregate value.
- "Running total," "cumulative," "moving average."
- "Rank" or "percentile" within a group.
- "Time/difference since the previous/next row."

## The general template

```sql
SELECT
    *,
    ROW_NUMBER() OVER (PARTITION BY group_col ORDER BY sort_col DESC) AS rn
FROM (...)
-- then, in an outer query or CTE: WHERE rn = 1  for "top row per group"
```

```sql
SELECT
    *,
    value - LAG(value) OVER (PARTITION BY group_col ORDER BY time_col) AS delta
FROM (...);
```

```sql
SELECT
    *,
    SUM(value) OVER (PARTITION BY group_col ORDER BY time_col) AS running_total
FROM (...);
```

## Common pitfalls

- Filtering `WHERE rn = 1` in the *same* query the window function is
  computed in — window functions are evaluated after `WHERE`/`GROUP BY`/
  `HAVING` in logical order, so you can't reference the alias in the same
  query's `WHERE`. Wrap it in a subquery or CTE and filter in the outer
  query instead.
- Reaching for `RANK`/`DENSE_RANK` when you actually want exactly one row
  per group (`ROW_NUMBER`) — ties will silently give you more than one
  "rank 1" row.
- Forgetting `ORDER BY` inside `OVER(...)` for `LAG`/`LEAD`/running totals
  — without it, "previous row" and "so far" have no defined meaning and
  the result is effectively arbitrary.

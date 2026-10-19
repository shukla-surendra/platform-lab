# Window Functions — Mental Model

## The one idea: window functions don't collapse rows

`GROUP BY` collapses many rows into one summary row per group. A window
function computes a value **for every row**, looking at a set of "peer"
rows (its *window*) — but keeps every original row intact. That's the
entire distinction; everything else about window functions follows from
it.

```text
user_events (unchanged row count in either query)

GROUP BY session_id:                    Window function, PARTITION BY session_id:
session_id | COUNT(*)                   event_id | session_id | event_type   | row_num_in_session
1          | 6                          1        | 1          | login        | 1
2          | 3               vs.        2        | 1          | page_view    | 2
...                                      3        | 1          | page_view    | 3
                                         4        | 1          | add_to_cart  | 4
                                         ... (still 6 rows for session 1, not 1)
```

## The anatomy of `OVER (...)`

```sql
some_function() OVER (
    PARTITION BY session_id     -- which rows are "peers" of this row (like GROUP BY, but no collapse)
    ORDER BY event_time         -- what order to consider peers in (needed for LAG/LEAD/running totals/ranks)
)
```

- `PARTITION BY` — optional. Omit it and the whole result set is one
  window (all rows are peers of each other).
- `ORDER BY` — required for anything order-sensitive (ranking, `LAG`/`LEAD`,
  running totals). Without it, "the previous row" or "running total so far"
  has no defined meaning.

## `ROW_NUMBER` vs `RANK` vs `DENSE_RANK` — the classic mix-up

All three assign a position within `ORDER BY`, but differ on ties:

```text
priority within an order-value ranking, two orders tied at 199.00:

value  | ROW_NUMBER | RANK | DENSE_RANK
349.00 | 1          | 1    | 1
259.00 | 2          | 2    | 2
199.00 | 3          | 3    | 3   <- tie starts
199.00 | 4          | 3    | 3   <- tie: RANK/DENSE_RANK repeat, ROW_NUMBER never does
89.00  | 5          | 5    | 4   <- RANK skips to 5 (2 rows were rank 3), DENSE_RANK doesn't skip
```

- `ROW_NUMBER` — always unique 1, 2, 3, ... even for exact ties (which row
  gets which number among ties is arbitrary unless `ORDER BY` fully
  disambiguates them).
- `RANK` — ties share a rank, and the *next* rank skips ahead by the number
  of tied rows (like Olympic medal ranking: two golds means the next place
  is bronze, not silver).
- `DENSE_RANK` — ties share a rank, but the next rank is always +1, no gaps.

Use `ROW_NUMBER` when you need exactly one row per group (e.g. "the most
recent order per customer" — `ROW_NUMBER() OVER (PARTITION BY customer_id
ORDER BY order_date DESC) = 1`). Use `RANK`/`DENSE_RANK` when ties should
legitimately share a position and you care about (or don't care about) the
gap that follows.

## `LAG` / `LEAD` — looking at a neighboring row without a self-join

`LAG(col, n)` reads a value from `n` rows *before* the current row (within
its partition, in `ORDER BY` order); `LEAD` reads `n` rows *after*. Both
return `NULL` when there's no such row (start/end of partition).

This replaces what would otherwise require a self-join:

```sql
-- "seconds since the previous event in the same session"
SELECT
    session_id, event_type, event_time,
    event_time - LAG(event_time) OVER (PARTITION BY session_id ORDER BY event_time) AS gap
FROM user_events;
```

For the first event in each session, `LAG(...)` is `NULL` (no previous
row in that partition) — so `gap` is `NULL` there, correctly meaning "not
applicable," not zero.

## Running totals and moving aggregates: the frame

Adding `ORDER BY` to an aggregate function inside `OVER(...)` changes its
meaning from "the whole partition" to "the partition so far, up to and
including this row" — a **running total**, not a grand total:

```sql
SUM(unit_price * quantity) OVER (
    PARTITION BY order_id
    ORDER BY order_item_id
) AS running_order_total
```

This is controlled by the frame, whose default (when `ORDER BY` is
present) is `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` — "from
the start of the partition through the current row." Explicit frame syntax
(`ROWS BETWEEN 2 PRECEDING AND CURRENT ROW` for a 3-row moving average, for
example) exists for anything other than that default, but the default
running-total behavior is what surprises people who expected a plain `SUM`.

## Window functions vs a self-join: same answer, very different cost

Before window functions existed, "gap since previous event" or "rank
within group" required a self-join (join the table to itself on
`partition_key` matching and some `<` condition on the ordering column),
which is O(n²)-shaped work for the database. A window function computes
the same thing in a single sorted pass per partition — this is the
practical reason to reach for one, not just readability.

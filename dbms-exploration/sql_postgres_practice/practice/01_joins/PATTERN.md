# Pattern: Joins (Inner, Outer, Anti-Join)

## What problem does this solve?

Almost every real question against a normalized schema needs data that
lives in more than one table — "customers and their orders," "orders and
what was in them." A join is how you combine rows from two (or more)
tables based on a relationship between them, without denormalizing the
data first. See `../../docs/01_joins_mental_model.md` for the underlying
mechanism (filtered cross product) before diving into problems here.

## How to recognize it

- The question mentions two or more entities and a relationship between
  them ("customers **and their** orders," "products **that appear in**
  orders").
- "Which X have no Y" / "X that never did Y" — this is specifically an
  anti-join (LEFT JOIN + `WHERE right.key IS NULL`), not a plain join.
- "Total/count of Y **per** X" — join + `GROUP BY`, see
  `../../docs/02_aggregation_and_grouping.md`.

## The general template

```sql
-- Plain join: only rows that match on both sides
SELECT ...
FROM table_a a
JOIN table_b b ON b.a_id = a.id
WHERE ...;

-- Anti-join: rows in A with NO match in B
SELECT ...
FROM table_a a
LEFT JOIN table_b b ON b.a_id = a.id
WHERE b.id IS NULL;

-- Join + aggregate: summarize B's rows per A
SELECT a.name, COUNT(*), SUM(b.amount)
FROM table_a a
JOIN table_b b ON b.a_id = a.id
GROUP BY a.id, a.name;
```

## Common pitfalls

- Filtering an outer-joined table's column in `WHERE` instead of `ON` —
  silently turns a `LEFT JOIN` back into an `INNER JOIN` (see the theory
  doc's "Common pitfall" section for exactly why).
- Forgetting to `GROUP BY` every non-aggregated selected column when
  joining before aggregating — a very common source of "column must
  appear in GROUP BY" errors once a join is added to an existing
  aggregation query.
- Joining on the wrong cardinality without noticing — joining
  `orders` to `order_items` multiplies each order into one row per line
  item, so `COUNT(*)` on the joined result counts line items, not orders
  (use `COUNT(DISTINCT order_id)` if you actually want order count).

# Aggregation & GROUP BY — Mental Model

## The one idea: GROUP BY collapses rows

`GROUP BY` takes many rows and collapses every row that shares the same
grouping key into **one output row**. Aggregate functions (`COUNT`, `SUM`,
`AVG`, `MAX`, `MIN`, ...) are what you compute *from* the rows that got
collapsed together — they're the only thing that can meaningfully survive
the collapse, because they summarize many values into one.

```text
orders (before GROUP BY)              orders GROUP BY customer_id
customer_id | order_id                customer_id | COUNT(*)
1           | o1                      1            | 3
1           | o2               -->    2            | 1
1           | o3                      3            | 2
2           | o4
3           | o5
3           | o6
```

## Why you can't SELECT a column that isn't grouped or aggregated

```sql
SELECT customer_id, order_date, COUNT(*)   -- error: order_date isn't
FROM orders                                 -- in GROUP BY or wrapped in
GROUP BY customer_id;                       -- an aggregate function
```

Once rows are collapsed by `customer_id`, a customer with 3 orders has 3
different `order_date` values folded into one output row — there's no
single value left to return for that column. Postgres refuses rather than
silently picking one (some databases pick an arbitrary one, which is worse:
a silently wrong answer instead of an error). Every column in `SELECT`
must either be in `GROUP BY` (guaranteed one value per group) or wrapped in
an aggregate (explicitly summarized).

## WHERE vs HAVING — before vs after the collapse

- `WHERE` filters **rows**, before grouping happens.
- `HAVING` filters **groups**, after grouping/aggregation happens.

```sql
SELECT customer_id, COUNT(*) AS order_count
FROM orders
WHERE status = 'delivered'      -- row filter: only delivered orders count at all
GROUP BY customer_id
HAVING COUNT(*) >= 2;           -- group filter: only customers with 2+ (delivered) orders
```

You cannot write `WHERE COUNT(*) >= 2` — `COUNT(*)` doesn't exist yet at
the point `WHERE` runs; groups (and their aggregates) don't exist until
after `GROUP BY` has executed. That ordering (`WHERE` -> `GROUP BY` ->
`HAVING` -> `SELECT` -> `ORDER BY`) is the actual logical execution order
of a query, which is why `HAVING` can reference aggregates and `WHERE`
can't.

## `COUNT(*)` vs `COUNT(column)` vs `COUNT(DISTINCT column)`

- `COUNT(*)` — counts rows, full stop, `NULL`s included.
- `COUNT(column)` — counts rows where `column IS NOT NULL` (skips `NULL`s).
- `COUNT(DISTINCT column)` — counts distinct non-`NULL` values of `column`.

Against `order_items` (`fixtures/01_ecommerce`): `COUNT(*)` on an order's
items gives total line items; `COUNT(DISTINCT product_id)` gives how many
*different* products were in that order (an order with 2 units of the same
product counts as 1 distinct product, 1 or 2 rows depending on how it was
inserted).

## Grouping by more than one column

`GROUP BY customer_id, status` produces one row **per unique combination**
— a customer with orders in both `delivered` and `cancelled` status gets
two output rows, not one. This is the natural way to answer "orders per
customer, broken down by status" without losing the status breakdown.

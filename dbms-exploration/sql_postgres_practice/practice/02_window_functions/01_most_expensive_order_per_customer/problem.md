# 1. Most Expensive Order Per Customer

**Fixture:** `ecommerce`
**Pattern:** `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)`, filtered to `rn = 1`

## Problem

For each customer, find their single most expensive order (by
`SUM(quantity * unit_price)` across that order's items) — return
`customer name, order_id, total`.

## Why not just `MAX(total) GROUP BY customer_id`?

`MAX()` + `GROUP BY` gives you the highest *total*, but not which
`order_id` it belongs to — you'd need a second query (or a self-join) to
find the row that produced that max. `ROW_NUMBER()` keeps the whole row
intact while still ranking it against its peers (see
`../PATTERN.md`), so you get the full row in one pass: compute order
totals, rank them per customer, keep rank 1.

Remember: you can't filter `WHERE rn = 1` in the same query level the
window function is computed in (window functions run after `WHERE`) — wrap
the ranking in a CTE/subquery and filter in the outer query.

## A wrinkle worth noticing

Customer Carla Ruiz's highest-total order (`order_id = 4`) has
`status = 'cancelled'`. This query answers the *literal* question asked
("most expensive order," no status filter) — but "most expensive order"
in a real product question often implicitly means *completed* spend. This
is a good example of why clarifying the actual requirement before writing
the query matters: `WHERE status != 'cancelled'` before the aggregation
would give a different, also-defensible answer for Carla.

## Expected output (unfiltered by status, as asked)

```
     name      | order_id | total
----------------+----------+--------
 Alice Chen    |       15 | 288.00
 Bilal Ahmed   |        3 |  36.00
 Carla Ruiz    |        4 | 349.00   <- this one is the cancelled order
 Dmitri Ivanov |       17 | 349.00
 Emma Novak    |        8 | 138.00
 Farid Hossain |       10 |  50.00
 Grace Kim     |       11 | 238.00
 Hiro Tanaka   |       13 |  63.00
 Ines Costa    |       14 | 158.00
```

## Solution

See `solution.sql` in this folder.

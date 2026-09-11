# 3. Running Total of Spend Per Customer Over Time

**Fixture:** `ecommerce`
**Pattern:** `SUM(...) OVER (PARTITION BY ... ORDER BY ...)` — running total, not grand total

## Problem

For customer `Alice Chen` (customer_id 1), list her orders in date order
with a running cumulative total of spend alongside each one.

## Why adding `ORDER BY` inside `OVER()` changes the meaning

`SUM(total) OVER (PARTITION BY customer_id)` (no `ORDER BY`) gives the
*grand* total for that customer on every row — the same number repeated.
Adding `ORDER BY order_date` changes the default frame to "from the start
of the partition through the current row," turning it into a genuine
running total that grows as you go down the rows. See
`../../docs/03_window_functions.md`'s "Running totals and moving
aggregates" section for exactly why.

## Expected output

```
 customer_id | order_id | order_date | total  | running_total
-------------+----------+------------+--------+----------------
           1 |        1 | 2026-01-05 | 114.00 |        114.00
           1 |        2 | 2026-02-10 | 199.00 |        313.00
           1 |       15 | 2026-03-20 | 288.00 |        601.00
```

## Solution

See `solution.sql` in this folder.

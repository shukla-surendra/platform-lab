# 3. Orders With More Than One Distinct Product

**Fixture:** `ecommerce`
**Pattern:** Join + `GROUP BY` + `HAVING` + `COUNT(DISTINCT ...)`

## Problem

Find every `order_id` that contains more than one *distinct* product
(an order with 3 units of the same product doesn't count; an order with
1 unit each of two different products does).

## Why `COUNT(DISTINCT product_id)`, not `COUNT(*)`

`order_items` has one row per line item, not one row per distinct product
— a single product ordered in quantity 3 could be one row (`quantity=3`)
or three rows, depending on how the order was placed. `COUNT(*)` counts
rows (line items); `COUNT(DISTINCT product_id)` counts *distinct
products*, which is what "more than one product" actually means here. This
is exactly the `COUNT(*)` vs `COUNT(DISTINCT column)` distinction from
`../../docs/02_aggregation_and_grouping.md`.

## Why `HAVING`, not `WHERE`

The condition ("more than one distinct product") is a property of the
*group* (all of an order's line items considered together), not of any
single row — `WHERE` can't see `COUNT(DISTINCT product_id)` because that
value doesn't exist until after grouping. See `../../docs/02_aggregation_and_grouping.md`'s
`WHERE` vs `HAVING` section.

## Expected output

```
 order_id | distinct_products
----------+--------------------
        1 |                  2
        5 |                  2
        8 |                  2
       11 |                  2
       13 |                  2
       15 |                  2
```

## Solution

See `solution.sql` in this folder.

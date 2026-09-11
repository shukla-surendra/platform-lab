# 2. Top Products By Revenue

**Fixture:** `ecommerce`
**Pattern:** Join + aggregation (see `../../docs/02_aggregation_and_grouping.md`)

## Problem

For each product, compute total revenue (`quantity * unit_price`, summed
across every `order_items` row for that product). Return the top 5
products by revenue, highest first.

## Why this is a join problem, not just aggregation

Revenue lives in `order_items` (`quantity`, `unit_price`), but the
product's *name* lives in `products`. Neither table alone can answer "top
products by revenue" — you need the join first, then aggregate the joined
result.

Note `order_items.unit_price` is a snapshot of the price *at order time*,
not a live lookup into `products.price` — use `order_items.unit_price` for
revenue, not `products.price` (a real schema decision: product prices
change over time, but a past order's total shouldn't retroactively change
when a price does).

## Expected output

```
            name             | revenue
------------------------------+---------
 Standing Desk               |  698.00
 Ergonomic Chair             |  518.00
 Noise Cancelling Headphones |  398.00
 Running Shoes               |  237.00
 Mechanical Keyboard         |  178.00
```

## Solution

See `solution.sql` in this folder.

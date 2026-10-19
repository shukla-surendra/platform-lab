# 1. Customers With No Orders

**Fixture:** `ecommerce` (`make load FIXTURE=ecommerce`)
**Pattern:** Anti-join (LEFT JOIN + `IS NULL`)

## Problem

List the name of every customer who has never placed an order.

## Why this isn't just "add a WHERE clause"

There's no column anywhere that says "has no orders" — it's the *absence*
of a row in a related table. That absence only becomes visible once you
LEFT JOIN (which guarantees every customer appears at least once) and then
look for the rows where the order side came back empty.

## Approach

See `../PATTERN.md` for the general anti-join template if this isn't
immediately obvious — this problem is the textbook instance of it.

## Expected output

```
   name
------------
 Priya Shah
```

## Solution

See `solution.sql` in this folder (fixture database: `ecommerce`) — see
the repo README for how to run a solution file against a loaded fixture.

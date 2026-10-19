# 3. Forcing an Index Scan to Compare Costs

**Fixture:** `ecommerce`
**Pattern:** `SET enable_seqscan = off` as a diagnostic-only comparison trick

## Problem

`orders` already has `idx_orders_customer_id` (created in `schema.sql`).
Compare the planner's natural choice for this query against what happens
if you force it to use the index instead:

```sql
EXPLAIN SELECT * FROM orders WHERE customer_id = 5;             -- natural choice

SET enable_seqscan = off;
EXPLAIN SELECT * FROM orders WHERE customer_id = 5;              -- forced
RESET enable_seqscan;
```

## What you should see, and why it's not a bug

The **natural** plan is `Seq Scan` at cost `1.23`. The **forced** plan is
`Index Scan using idx_orders_customer_id` at cost `8.19` — higher, not
lower. The planner isn't failing to notice the index; it correctly
computed that, for an 18-row table, jumping into a separate index
structure and then fetching the matching row from the table (an extra
step an `Index Scan` requires that a `Seq Scan` doesn't) costs *more* than
just reading straight through all 18 rows once. This is the concrete,
numeric version of `../../docs/05_indexing_and_query_plans.md`'s "small
tables" pitfall — not an assertion to take on faith, but something you can
watch the cost estimates prove directly.

This is also exactly why you can't judge whether an index "worked" by
whether it merely *can* be used (problem 2) — you have to check whether
the planner's own cost comparison actually favors it, which depends on
real table size and selectivity, not just index existence.

`enable_seqscan = off` is a session-scoped setting meant purely for this
kind of side-by-side inspection — `RESET`-ing it (or ending the session)
returns to normal planning. Never leave it off in a real
application/production session.

## Expected output shape

```
-- natural:  Seq Scan on orders            (cost=0.00..1.23 ...)
-- forced:   Index Scan using idx_orders_customer_id  (cost=0.14..8.19 ...)
```

## Solution

See `solution.sql` in this folder.

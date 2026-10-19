# 2. Sync Order Statuses Without Regressing Terminal Ones

**Fixture:** `ecommerce`
**Pattern:** `MERGE` with multiple conditional `WHEN MATCHED` branches

## Problem

A shipping-provider webhook feed reports status updates for three orders:

| order_id | current status | feed says |
|---|---|---|
| 1 | delivered | shipped |
| 4 | cancelled | delivered |
| 12 | pending | shipped |

Apply the feed, but **never overwrite an order that's already
`delivered` or `cancelled`** (those are terminal — a stale/out-of-order
webhook shouldn't be able to move a delivered order back to "shipped").
Order 12 (currently `pending`) should update normally.

## Why this needs two `WHEN MATCHED` branches, not one

A plain `WHEN MATCHED THEN UPDATE` would apply the feed's status
unconditionally — the whole point here is that *most* matched rows should
update, but two specific ones (already in a terminal state) shouldn't.
`MERGE` lets you write the exception as its own branch, evaluated first:

```sql
WHEN MATCHED AND o.status NOT IN ('delivered', 'cancelled') THEN UPDATE ...
WHEN MATCHED THEN DO NOTHING
```

Branch order matters: the conditional branch has to come *before* the
unconditional catch-all, or the catch-all would fire for every matched
row regardless of status.

## Expected output

```
 order_id |  status
----------+-----------
        1 | delivered   <- unchanged (protected)
        4 | cancelled   <- unchanged (protected)
       12 | shipped     <- updated
```

`MERGE 1` — only order 12 actually had an action applied; the two
`DO NOTHING` matches don't count toward that number (see
`../../docs/06_merge_and_upsert.md`'s closing section).

## Solution

See `solution.sql` in this folder (wrapped in `BEGIN`/`ROLLBACK`, same as
problem 1).

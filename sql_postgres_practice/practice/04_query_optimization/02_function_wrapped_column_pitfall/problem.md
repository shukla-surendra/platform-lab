# 2. Why `LOWER(email) = ...` Can't Use the Email Index

**Fixture:** `ecommerce`
**Pattern:** Function-wrapped column breaks index usage

## Problem

`customers.email` has a `UNIQUE` constraint, which auto-creates a btree
index (`customers_email_key`). Compare the plans for these two,
otherwise-equivalent-looking, lookups:

```sql
EXPLAIN SELECT * FROM customers WHERE email = 'alice@example.com';
EXPLAIN SELECT * FROM customers WHERE LOWER(email) = 'alice@example.com';
```

## Why they produce different plans

The index is sorted by the **stored, raw** value of `email`. The first
query compares directly against that stored value, so the index applies.
The second wraps `email` in `LOWER(...)` before comparing — that's a
*different value* than what the index is sorted by, so Postgres can't use
it and falls back to checking `LOWER(email)` against every row (a
sequential scan), even though the exact same rows would be found by the
first query if the stored data happens to already be lowercase. See
`../../docs/05_indexing_and_query_plans.md`'s "When an index doesn't help"
section.

## The fix, if you genuinely need case-insensitive lookups

An expression index, built on the same expression the query uses:

```sql
CREATE INDEX ON customers (LOWER(email));
```

After this, `WHERE LOWER(email) = 'alice@example.com'` is *capable* of
using it (though `WHERE email = 'Alice@Example.com'` still can't — the
expression index only matches queries that wrap the column the same way).

**On this fixture, you still won't see it actually chosen** — with only
10 rows, the planner correctly judges the index lookup (cost `8.15`) more
expensive than just scanning the whole tiny table (cost `1.15`), so it
picks `Seq Scan` either way. To confirm the index is genuinely usable
(not just present), force the planner's hand with
`SET enable_seqscan = off;` (see `solution.sql`) — this is a
diagnostic-only trick, never something to leave set in production, and
it's exactly the technique problem 3 in this folder covers on its own.

## Expected output shape

```sql
-- plain email:                 Index Scan using customers_email_key
-- LOWER(email):                Seq Scan on customers, Filter: (lower(email) = ...)
-- LOWER(email), index created: still Seq Scan (table's too small for the planner to bother)
-- LOWER(email), enable_seqscan=off: Index Scan using customers_lower_idx -- proves it CAN be used
```

## Solution

See `solution.sql` in this folder.

# 3. Same Upsert, Two Ways: `MERGE` vs `ON CONFLICT`

**Fixture:** `ecommerce`
**Pattern:** Comparing `MERGE` against `INSERT ... ON CONFLICT DO UPDATE`

## Problem

Upsert two customers by email — Alice Chen (`alice@example.com`, already
exists — her country should update to `'Canada'`) and a brand-new
customer (`newuser@example.com`, should be inserted). Write it two ways:
once with `MERGE`, once with `INSERT ... ON CONFLICT`, and confirm they
produce the identical result.

## Why `ON CONFLICT` even works here

`customers.email` has a `UNIQUE` constraint (`schema.sql`) — `ON CONFLICT
(email)` needs a real unique constraint or index on the conflict target;
it can't upsert on an arbitrary join condition the way `MERGE`'s `ON`
clause can. This is the concrete version of the comparison table in
`../../docs/06_merge_and_upsert.md`.

## Expected output (both versions, identical)

```
    name    |        email         | country
------------+----------------------+---------
 Alice Chen | alice@example.com    | Canada
 Sam Novak  | newuser@example.com  | USA
```

## Solution

See `solution.sql` — both versions, each wrapped in its own
`BEGIN`/`ROLLBACK` so they don't interfere with each other when run back
to back.

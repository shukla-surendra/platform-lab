# MERGE & Upsert — Mental Model

## The problem this solves

"Sync this batch of incoming data: update rows that already exist, insert
rows that don't" is extremely common (catalog feeds, nightly syncs, CDC
pipelines) and is genuinely awkward to do safely as separate statements:

```sql
UPDATE products SET price = 22.00 WHERE name = 'Wireless Mouse';
-- then, separately, figure out which rows in the feed had no match and INSERT those
```

Two statements means two round trips and a race condition: between the
`UPDATE` and the follow-up `INSERT`, another session could insert the same
row, and now you either get a duplicate or a constraint violation you have
to handle. `MERGE` (standard SQL, Postgres 15+) and Postgres's own older
`INSERT ... ON CONFLICT` both do the check-and-branch as **one atomic
statement** — no gap where another session can race you.

## `MERGE` — the mental model

`MERGE` joins a target table to a source (a `VALUES` list, a subquery, or
another table) on some condition, then branches per matched row:

```sql
MERGE INTO products AS p
USING (VALUES
    ('Wireless Mouse', 'Electronics', 22.00),
    ('Mechanical Keyboard', 'Electronics', 95.00),
    ('Webcam HD', 'Electronics', 49.00)
) AS feed(name, category, price)
ON p.name = feed.name
WHEN MATCHED THEN
    UPDATE SET price = feed.price
WHEN NOT MATCHED THEN
    INSERT (name, category, price) VALUES (feed.name, feed.category, feed.price);
```

Read it as: for every row in `feed`, find the matching row in `products`
(by `name`) if one exists. If it matched, run the `WHEN MATCHED` action; if
it didn't, run `WHEN NOT MATCHED`. Here that's update-or-insert (the
classic "upsert"), but `MERGE` isn't limited to that — either branch can
also be `DELETE`, or `DO NOTHING`.

## Multiple `WHEN MATCHED` branches — conditional actions

Branches are evaluated **in order**, and the first one whose condition is
true (or has no condition) wins per row:

```sql
MERGE INTO orders o
USING (VALUES (1,'shipped'), (4,'delivered'), (12,'shipped')) AS feed(order_id, new_status)
ON o.order_id = feed.order_id
WHEN MATCHED AND o.status NOT IN ('delivered', 'cancelled') THEN
    UPDATE SET status = feed.new_status
WHEN MATCHED THEN
    DO NOTHING;   -- terminal-status orders are protected from a stale/out-of-order update
```

This is the real value beyond "just an upsert" — a single statement can
express "update, but only under this condition, otherwise leave it alone,"
which would otherwise need a `CASE` buried inside an `UPDATE ... WHERE` or
a second guarding query.

## `MERGE` vs `INSERT ... ON CONFLICT DO UPDATE`

Postgres had upserts before it had `MERGE` (`ON CONFLICT` since Postgres
9.5; `MERGE` since Postgres 15) — for a simple upsert, they produce
identical results:

```sql
-- ON CONFLICT needs a unique constraint/index on the conflict target
-- (customers.email is UNIQUE in this fixture's schema.sql)
INSERT INTO customers (name, email, country, signup_date) VALUES
    ('Alice Chen', 'alice@example.com', 'Canada', '2025-11-02'),
    ('Sam Novak', 'newuser@example.com', 'USA', '2026-04-01')
ON CONFLICT (email) DO UPDATE SET country = EXCLUDED.country;
```

`EXCLUDED` refers to the row that *would* have been inserted — the
`ON CONFLICT` equivalent of `MERGE`'s `feed.column`.

| | `MERGE` | `INSERT ... ON CONFLICT` |
|---|---|---|
| Match condition | Any join condition (`ON p.name = feed.name`) | Must be a real unique constraint/index — the database detects the conflict, you don't specify arbitrary join logic |
| Can `DELETE` on match | Yes | No |
| Multiple conditional branches | Yes (`WHEN MATCHED AND ...`, evaluated in order) | Only one `DO UPDATE`/`DO NOTHING`, no ordered branching |
| Standard SQL (portable to other databases) | Yes | No — Postgres-specific syntax |
| Postgres version | 15+ | 9.5+ |

Reach for `ON CONFLICT` for a plain, single-condition upsert against an
existing unique constraint (shorter, and works on any supported Postgres
version). Reach for `MERGE` when you need to match on something other than
a unique constraint, need a `DELETE` branch, need multiple conditional
branches, or want SQL that isn't Postgres-specific.

## What the row count in `MERGE n` actually means

`MERGE n` reports how many rows had an action **applied** (`UPDATE`,
`INSERT`, or `DELETE`) — rows that hit a `DO NOTHING` branch aren't
counted. A `MERGE` against 3 source rows where one hit `DO NOTHING` reports
`MERGE 2`, not `MERGE 3` — worth checking if you're relying on that count
to confirm how many rows a sync actually touched.

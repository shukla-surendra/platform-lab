# Joins — Mental Model

## The one idea that makes every join type obvious

A join is a **filtered cross product**. Conceptually, Postgres:

1. Pairs every row of the left table with every row of the right table (the cross product — if left has 10 rows and right has 12, that's 120 pairs).
2. Keeps only the pairs where the join condition (`ON ...`) is true.
3. For outer joins, adds back the rows that had *no* matching pair, filling the missing side with `NULL`.

Postgres never actually materializes the full cross product for a real join (the query planner uses hash joins, merge joins, or nested loops to get the same *result* far more cheaply — see `05_indexing_and_query_plans.md`), but thinking of it as "cross product, then filter, then maybe add back unmatched rows" is what makes every join type fall out as one rule instead of four things to memorize.

## The four join types, as that one rule

Using `customers` (left) and `orders` (right) from `fixtures/01_ecommerce`:

| Join | Keeps | Unmatched left rows | Unmatched right rows |
|---|---|---|---|
| `INNER JOIN` | only matched pairs | dropped | dropped |
| `LEFT JOIN` | matched pairs + all left rows | kept, right side `NULL` | dropped |
| `RIGHT JOIN` | matched pairs + all right rows | dropped | kept, left side `NULL` |
| `FULL JOIN` | matched pairs + all unmatched from both | kept, right side `NULL` | kept, left side `NULL` |

```text
customers          orders
c1 --- Alice        o1 (customer_id=1)
c2 --- Bilal         o2 (customer_id=1)
c3 --- Priya         (no order references c3)

INNER JOIN customers c ON o.customer_id = c.customer_id:
  Alice+o1, Alice+o2                  <- Priya never appears

LEFT JOIN (customers LEFT JOIN orders):
  Alice+o1, Alice+o2, Bilal+NULL, Priya+NULL   <- every customer appears at least once
```

## The pattern this unlocks: "find X with no Y" (anti-join)

"Which customers have never placed an order" is not a join question at
first glance — it's an *absence* question. But it becomes a join question
the moment you notice: LEFT JOIN keeps every left row, filling `NULL` on
the right for no-match rows. So "no order" = "the right side came back
NULL":

```sql
SELECT c.name
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
WHERE o.order_id IS NULL;   -- the anti-join filter
```

Filtering on `o.order_id IS NULL` (a right-side column) is what makes this
an anti-join rather than an ordinary left join — without that `WHERE`,
you'd just get every customer with their orders (and `NULL`s for the ones
without any), not a filtered list of *only* the customers without orders.
This exact shape — LEFT JOIN + `WHERE right.key IS NULL` — is the standard
way to answer any "X with no matching Y" question in SQL.

## Common pitfall: putting a right-side filter in `WHERE` on an outer join

```sql
-- Looks like "customers and their delivered orders" but actually
-- silently turns the LEFT JOIN back into an INNER JOIN:
SELECT c.name, o.order_id
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
WHERE o.status = 'delivered';
```

For a customer with zero orders, `o.status` is `NULL`, and `NULL = 'delivered'`
is `NULL` (not `TRUE`) — so `WHERE` drops that row, exactly as an `INNER JOIN`
would have. To keep the "show every customer, filter is optional" behavior,
the status condition has to move into the `ON` clause instead:

```sql
LEFT JOIN orders o ON o.customer_id = c.customer_id AND o.status = 'delivered'
```

The rule: **conditions in `ON` are applied before the outer-join padding
happens; conditions in `WHERE` are applied after** — so a `WHERE` filter on
the outer side of a join silently undoes the "keep unmatched rows" behavior
unless you're deliberately filtering out the padding (like the `IS NULL`
anti-join above, which relies on exactly this).

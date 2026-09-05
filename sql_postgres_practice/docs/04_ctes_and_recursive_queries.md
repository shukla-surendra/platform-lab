# CTEs & Recursive Queries — Mental Model

## A plain CTE is just a named subquery

```sql
WITH delivered_orders AS (
    SELECT * FROM orders WHERE status = 'delivered'
)
SELECT customer_id, COUNT(*) FROM delivered_orders GROUP BY customer_id;
```

`delivered_orders` exists only for the duration of this one query. The
value is almost entirely readability — breaking a complex query into named,
sequential steps instead of nesting subqueries inside subqueries.

**Outdated belief worth correcting**: older Postgres (pre-12) treated every
CTE as an "optimization fence" — it materialized the CTE's full result
before the outer query could push filters into it, sometimes forcing a
much more expensive plan than the equivalent subquery. Since Postgres 12,
the planner can inline a non-recursive CTE just like a subquery unless you
force materialization with `MATERIALIZED`. If you're reading older
Postgres advice that says "avoid CTEs for performance," that's the
context it's from — check `EXPLAIN` rather than assuming either way (see
`05_indexing_and_query_plans.md`).

## Recursive CTEs — the mechanism, not just the syntax

```sql
WITH RECURSIVE reports AS (
    -- 1. Anchor member: the starting row(s), runs once
    SELECT employee_id, name, manager_id, 0 AS depth
    FROM employees
    WHERE name = 'Blake Chen'

    UNION ALL

    -- 2. Recursive member: references "reports" itself, re-runs each iteration
    SELECT e.employee_id, e.name, e.manager_id, r.depth + 1
    FROM employees e
    JOIN reports r ON e.manager_id = r.employee_id
)
SELECT * FROM reports;
```

What Postgres actually does, iteration by iteration:

```text
Iteration 0 (anchor):        reports = { Blake Chen (depth 0) }

Iteration 1 (recursive member joins against iteration 0's new rows):
    finds employees whose manager_id = Blake Chen's id
    -> adds { Erin Walsh (1), Faisal Khan (1) }

Iteration 2 (recursive member joins against iteration 1's new rows):
    finds employees whose manager_id IN (Erin Walsh, Faisal Khan)
    -> adds { Jamal Reed (2), Kira Ono (2), Liam Cruz (2), Mia Torres (2) }

Iteration 3: no employee has manager_id IN (the depth-2 people) -> no new rows -> STOP
```

The recursion terminates the moment an iteration adds zero new rows — not
because of a row limit or explicit stop condition you write. This is why
the *direction* of the join matters: `e.manager_id = r.employee_id` walks
**down** the tree (a manager's reports); reversing it to
`e.employee_id = r.manager_id` would instead walk **up** (an employee's
chain of managers to the CEO) from a different anchor.

## The infinite-recursion trap

If the underlying data has a cycle (a genuine data-integrity bug — e.g.
`manager_id` pointing to someone who eventually reports back to the
original employee), the "stop when no new rows" rule never fires, because
there's always a "new" row to revisit. Postgres doesn't detect this for
you by default. Two real guards:

1. **`UNION` instead of `UNION ALL`** — deduplicates each iteration's
   output, so a cycle eventually stops producing genuinely *new* rows
   (though this can mask a real data bug rather than surfacing it).
2. **An explicit depth/path guard** — carry a depth counter (as in the
   example above) or an array of visited IDs, and add `WHERE depth < N` or
   `WHERE NOT (id = ANY(visited_path))` to the recursive member.

For tree-shaped data you control and trust (like an org chart with a
`NOT NULL ... REFERENCES employees` FK and no cycles by construction),
neither guard is strictly necessary — but it's worth knowing why they
exist before you hit a recursive CTE against data you *don't* fully trust.

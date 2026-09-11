# Pattern: Recursive CTEs (Tree/Graph Traversal)

## What problem does this solve?

Any self-referencing relationship — an org chart (`manager_id` points to
another row in the same table), a category tree, a comment thread, a
bill-of-materials — needs a query that can walk an *unknown* number of
levels deep. A plain join is fixed-depth (one `JOIN` = one level); a
recursive CTE can walk as many levels as the data actually has, stopping
itself automatically. Read `../../docs/04_ctes_and_recursive_queries.md`
first for the iteration-by-iteration mechanics — this file assumes that
mental model.

## How to recognize it

- "All reports/descendants/sub-categories of X" (arbitrary depth downward).
- "The chain from X up to the root" (arbitrary depth upward).
- "The depth/level of every node" in a tree.
- Any self-referencing foreign key (`table.parent_id REFERENCES table.id`)
  combined with a question that isn't naturally answered by one join.

## The general template

```sql
WITH RECURSIVE walk AS (
    -- Anchor: the starting point(s)
    SELECT id, parent_id, 0 AS depth
    FROM my_table
    WHERE <starting condition>

    UNION ALL

    -- Recursive step: one level further from what's already found
    SELECT t.id, t.parent_id, w.depth + 1
    FROM my_table t
    JOIN walk w ON t.parent_id = w.id     -- walking DOWN (children)
    -- or:      ON t.id = w.parent_id     -- walking UP (ancestors)
)
SELECT * FROM walk;
```

The join direction in the recursive member is the whole ballgame: `child.parent_id = current.id`
walks downward (find everyone whose parent is something already found);
`current.parent_id = ancestor.id` walks upward.

## Common pitfalls

- Getting the join direction backwards (see above) — the anchor is right
  but the traversal silently goes the wrong way, and one-level results
  can look correct by accident before breaking at depth 2+.
- Assuming acyclic data — a genuine cycle (a data bug) makes a naive
  recursive CTE with `UNION ALL` run forever. See the theory doc's
  "infinite-recursion trap" section for the two real guards.
- Forgetting you can carry more than an ID through the recursion — a depth
  counter, a running path array, or an accumulated cost are all just extra
  columns threaded through both the anchor and the recursive member.

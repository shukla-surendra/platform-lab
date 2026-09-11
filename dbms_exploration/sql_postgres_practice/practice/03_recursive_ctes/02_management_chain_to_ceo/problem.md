# 2. Management Chain Up To the CEO (Walking Up)

**Fixture:** `org_hierarchy`
**Pattern:** Recursive CTE, walking up the tree

## Problem

For Jamal Reed (a Backend Engineer, several levels down), list his full
management chain up to and including the CEO, in order from himself to
the top.

## Why this is the mirror image of problem 1

Same recursive CTE shape, opposite join direction: instead of "whose
manager is already in the set" (walking down), it's "the manager of
someone already in the set" (walking up) —
`employees.employee_id = current_level.manager_id`. See
`../PATTERN.md`'s note on join direction if this feels like the same
query as problem 1 — it's deliberately almost the same shape to make that
comparison obvious.

## Expected output

```
 depth |    name
-------+-------------
     0 | Jamal Reed
     1 | Erin Walsh
     2 | Blake Chen
     3 | Alex Morgan
```

## Solution

See `solution.sql` in this folder.

# 3. Depth of Every Employee

**Fixture:** `org_hierarchy`
**Pattern:** Recursive CTE with a multi-row anchor, full-tree traversal

## Problem

Compute the depth (0 = CEO) of every employee in the company, then show
how many employees exist at each depth.

## Why this is different from problems 1 and 2

Problems 1 and 2 anchor on a *single named employee* and walk in one
direction from just that row. This problem anchors on **every row with no
manager** (`WHERE manager_id IS NULL` — just the CEO here, but the query
doesn't hardcode a name, so it would still work correctly if the company
had multiple root-level people) and walks the *entire* tree downward at
once, computing every employee's depth in a single pass rather than one
query per employee.

## Expected output

```
 depth | count
-------+-------
     0 |     1   <- CEO
     1 |     3   <- VPs
     2 |     5   <- Managers
     3 |     9   <- Individual contributors
```

## Solution

See `solution.sql` in this folder.

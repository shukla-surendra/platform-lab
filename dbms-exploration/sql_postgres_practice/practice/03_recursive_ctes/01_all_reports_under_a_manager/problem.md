# 1. All Reports Under a Manager (Walking Down)

**Fixture:** `org_hierarchy`
**Pattern:** Recursive CTE, walking down the tree

## Problem

List every employee who reports — directly or indirectly — to Blake Chen
(VP Engineering). Not just his direct reports; everyone under him at any
depth.

## Why one join isn't enough

A single `JOIN employees e ON e.manager_id = blake.employee_id` only
finds Blake's *direct* reports (the two Engineering Managers). Their
reports (the 4 individual-contributor engineers) are two levels down —
finding them needs the join applied again to the *result* of the first
join, and again for however many levels deep the org goes. A recursive
CTE does exactly that, automatically, however deep the tree turns out to
be.

## Approach

Anchor on Blake Chen, then walk down: `employees.manager_id = <current
level's employee_id>`. See `../PATTERN.md`'s "walking DOWN" template.

## Expected output

```
    name
-------------
 Erin Walsh
 Faisal Khan
 Jamal Reed
 Kira Ono
 Liam Cruz
 Mia Torres
```

(Erin Walsh and Faisal Khan are direct reports; the other four are their
reports — depth 2 from Blake.)

## Solution

See `solution.sql` in this folder.

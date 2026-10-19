WITH RECURSIVE levels AS (
    -- Anchor: every root (no manager) -- just the CEO here, but this
    -- doesn't hardcode a name, so it generalizes to multiple roots.
    SELECT employee_id, name, manager_id, 0 AS depth
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    SELECT e.employee_id, e.name, e.manager_id, l.depth + 1
    FROM employees e
    JOIN levels l ON e.manager_id = l.employee_id
)
SELECT depth, COUNT(*)
FROM levels
GROUP BY depth
ORDER BY depth;

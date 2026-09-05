WITH RECURSIVE chain AS (
    -- Anchor: the employee we're starting from
    SELECT employee_id, name, manager_id, 0 AS depth
    FROM employees
    WHERE name = 'Jamal Reed'

    UNION ALL

    -- Recursive step: the manager of whoever's already in the chain
    SELECT e.employee_id, e.name, e.manager_id, c.depth + 1
    FROM employees e
    JOIN chain c ON e.employee_id = c.manager_id
)
SELECT depth, name
FROM chain
ORDER BY depth;

WITH RECURSIVE subtree AS (
    -- Anchor: the manager we're starting from
    SELECT employee_id, name, manager_id
    FROM employees
    WHERE name = 'Blake Chen'

    UNION ALL

    -- Recursive step: anyone whose manager is already in the subtree
    SELECT e.employee_id, e.name, e.manager_id
    FROM employees e
    JOIN subtree s ON e.manager_id = s.employee_id
)
SELECT name
FROM subtree
WHERE name != 'Blake Chen'  -- exclude the anchor itself, we only want reports
ORDER BY name;

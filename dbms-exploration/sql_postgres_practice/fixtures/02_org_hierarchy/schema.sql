-- A single self-referencing table -- the classic shape for recursive CTE
-- practice (org charts, category trees, bill-of-materials, comment threads
-- all reduce to this same "parent_id references this same table" pattern).

DROP TABLE IF EXISTS employees CASCADE;

CREATE TABLE employees (
    employee_id  SERIAL PRIMARY KEY,
    name         TEXT NOT NULL,
    title        TEXT NOT NULL,
    department   TEXT NOT NULL,
    manager_id   INTEGER REFERENCES employees(employee_id),  -- NULL only for the CEO
    salary       NUMERIC(10,2) NOT NULL,
    hire_date    DATE NOT NULL
);

CREATE INDEX idx_employees_manager_id ON employees(manager_id);

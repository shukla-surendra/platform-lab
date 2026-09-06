CREATE TABLE employees (
    employee_id   INT PRIMARY KEY,
    employee_name VARCHAR(100),
    department    VARCHAR(50),
    salary        NUMERIC(10,2),
    hire_date     DATE,
    manager_id    INT
);

INSERT INTO employees
(employee_id, employee_name, department, salary, hire_date, manager_id)
VALUES
(1,  'Alice',   'Engineering', 120000, '2020-01-15', NULL),
(2,  'Bob',     'Engineering',  95000, '2021-03-10', 1),
(3,  'Charlie', 'Engineering',  95000, '2022-07-20', 1),
(4,  'David',   'Engineering',  80000, '2023-02-05', 1),

(5,  'Emma',    'Sales',        110000, '2019-06-01', NULL),
(6,  'Frank',   'Sales',         90000, '2021-08-15', 5),
(7,  'Grace',   'Sales',         90000, '2022-01-10', 5),
(8,  'Henry',   'Sales',         75000, '2023-05-12', 5),

(9,  'Ivy',     'HR',            85000, '2020-09-20', NULL),
(10, 'Jack',    'HR',            70000, '2022-04-18', 9),
(11, 'Karen',   'HR',            65000, '2023-11-01', 9),

(12, 'Leo',     'Finance',       105000, '2019-02-14', NULL),
(13, 'Mia',     'Finance',        88000, '2021-05-25', 12),
(14, 'Noah',    'Finance',        88000, '2022-10-30', 12);
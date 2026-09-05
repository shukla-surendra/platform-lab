-- Inserted level-by-level so manager_id can reference the row just
-- inserted above it -- relies on employee_id being assigned 1..18 in
-- insertion order (true for a fresh SERIAL on an empty table).

-- Level 0: CEO
INSERT INTO employees (name, title, department, manager_id, salary, hire_date) VALUES
('Alex Morgan', 'CEO', 'Executive', NULL, 380000, '2019-01-15');

-- Level 1: VPs, report to CEO (id 1)
INSERT INTO employees (name, title, department, manager_id, salary, hire_date) VALUES
('Blake Chen',  'VP Engineering', 'Engineering', 1, 260000, '2019-06-01'),
('Casey Lopez', 'VP Sales',       'Sales',       1, 250000, '2020-02-10'),
('Drew Patel',  'VP Marketing',   'Marketing',   1, 235000, '2020-08-20');

-- Level 2: Managers, report to a VP (ids 2,3,4)
INSERT INTO employees (name, title, department, manager_id, salary, hire_date) VALUES
('Erin Walsh',   'Engineering Manager (Backend)',  'Engineering', 2, 190000, '2021-01-10'),
('Faisal Khan',  'Engineering Manager (Frontend)', 'Engineering', 2, 185000, '2021-03-05'),
('Grace Liu',    'Sales Manager (NA)',             'Sales',       3, 170000, '2021-04-15'),
('Hassan Ali',   'Sales Manager (EMEA)',           'Sales',       3, 168000, '2021-07-01'),
('Ivy Novak',    'Marketing Manager',              'Marketing',   4, 165000, '2021-09-12');

-- Level 3: Individual contributors, report to a Manager (ids 5-9)
INSERT INTO employees (name, title, department, manager_id, salary, hire_date) VALUES
('Jamal Reed',   'Backend Engineer',    'Engineering', 5, 145000, '2022-02-01'),
('Kira Ono',     'Backend Engineer',    'Engineering', 5, 148000, '2022-05-20'),
('Liam Cruz',    'Frontend Engineer',   'Engineering', 6, 140000, '2022-01-11'),
('Mia Torres',   'Frontend Engineer',   'Engineering', 6, 142000, '2022-08-30'),
('Noah Kim',     'Sales Rep (NA)',      'Sales',       7, 95000,  '2022-03-14'),
('Olga Petrov',  'Sales Rep (NA)',      'Sales',       7, 97000,  '2022-11-01'),
('Priya Nair',   'Sales Rep (EMEA)',    'Sales',       8, 92000,  '2023-01-09'),
('Quinn Baker',  'Marketing Specialist','Marketing',   9, 88000,  '2023-02-17'),
('Rosa Diaz',    'Marketing Specialist','Marketing',   9, 90000,  '2023-06-25');

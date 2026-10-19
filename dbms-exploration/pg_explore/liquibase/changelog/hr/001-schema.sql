--liquibase formatted sql

--changeset surendra:hr-001-create-schema
CREATE SCHEMA IF NOT EXISTS hr;
--rollback DROP SCHEMA IF EXISTS hr CASCADE;

--changeset surendra:hr-002-create-departments
CREATE TABLE hr.departments (
    dept_id     SERIAL PRIMARY KEY,
    dept_name   VARCHAR(100) NOT NULL UNIQUE,
    location    VARCHAR(100),
    budget      NUMERIC(14, 2)
);
--rollback DROP TABLE hr.departments;

--changeset surendra:hr-003-create-employees
CREATE TABLE hr.employees (
    emp_id      SERIAL PRIMARY KEY,
    first_name  VARCHAR(50) NOT NULL,
    last_name   VARCHAR(50) NOT NULL,
    email       VARCHAR(150) UNIQUE NOT NULL,
    phone       VARCHAR(20),
    hire_date   DATE NOT NULL,
    job_title   VARCHAR(80) NOT NULL,
    salary      NUMERIC(10, 2) NOT NULL,
    manager_id  INT REFERENCES hr.employees(emp_id),
    dept_id     INT REFERENCES hr.departments(dept_id),
    status      VARCHAR(10) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'terminated'))
);
--rollback DROP TABLE hr.employees;

--changeset surendra:hr-004-create-salary-history
CREATE TABLE hr.salary_history (
    history_id   SERIAL PRIMARY KEY,
    emp_id       INT NOT NULL REFERENCES hr.employees(emp_id),
    old_salary   NUMERIC(10, 2) NOT NULL,
    new_salary   NUMERIC(10, 2) NOT NULL,
    change_date  DATE NOT NULL,
    reason       VARCHAR(50)
);
--rollback DROP TABLE hr.salary_history;

--changeset surendra:hr-005-create-indexes
CREATE INDEX idx_hr_employees_manager_id ON hr.employees(manager_id);
CREATE INDEX idx_hr_employees_dept_id ON hr.employees(dept_id);
CREATE INDEX idx_hr_salary_history_emp_id ON hr.salary_history(emp_id);
--rollback DROP INDEX IF EXISTS idx_hr_employees_manager_id;
--rollback DROP INDEX IF EXISTS idx_hr_employees_dept_id;
--rollback DROP INDEX IF EXISTS idx_hr_salary_history_emp_id;

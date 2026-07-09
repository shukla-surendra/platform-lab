--liquibase formatted sql

--changeset surendra:edu-001-create-schema
CREATE SCHEMA IF NOT EXISTS edu;
--rollback DROP SCHEMA IF EXISTS edu CASCADE;

--changeset surendra:edu-002-create-departments
CREATE TABLE edu.departments (
    dept_id    SERIAL PRIMARY KEY,
    dept_name  VARCHAR(100) NOT NULL UNIQUE
);
--rollback DROP TABLE edu.departments;

--changeset surendra:edu-003-create-instructors
CREATE TABLE edu.instructors (
    instructor_id  SERIAL PRIMARY KEY,
    first_name     VARCHAR(50) NOT NULL,
    last_name      VARCHAR(50) NOT NULL,
    email          VARCHAR(150) UNIQUE NOT NULL,
    dept_id        INT REFERENCES edu.departments(dept_id),
    hire_date      DATE NOT NULL
);
--rollback DROP TABLE edu.instructors;

--changeset surendra:edu-004-create-students
CREATE TABLE edu.students (
    student_id       SERIAL PRIMARY KEY,
    first_name       VARCHAR(50) NOT NULL,
    last_name        VARCHAR(50) NOT NULL,
    email            VARCHAR(150) UNIQUE NOT NULL,
    dob              DATE NOT NULL,
    major            VARCHAR(100),
    enrollment_date  DATE NOT NULL,
    gpa              NUMERIC(3, 2) CHECK (gpa >= 0 AND gpa <= 4.0)
);
--rollback DROP TABLE edu.students;

--changeset surendra:edu-005-create-courses
CREATE TABLE edu.courses (
    course_id      SERIAL PRIMARY KEY,
    course_name    VARCHAR(120) NOT NULL,
    credits        INT NOT NULL,
    dept_id        INT REFERENCES edu.departments(dept_id),
    instructor_id  INT REFERENCES edu.instructors(instructor_id)
);
--rollback DROP TABLE edu.courses;

--changeset surendra:edu-006-create-enrollments
CREATE TABLE edu.enrollments (
    enrollment_id  SERIAL PRIMARY KEY,
    student_id     INT NOT NULL REFERENCES edu.students(student_id),
    course_id      INT NOT NULL REFERENCES edu.courses(course_id),
    semester       VARCHAR(20) NOT NULL,
    grade          VARCHAR(2),
    UNIQUE (student_id, course_id, semester)
);
--rollback DROP TABLE edu.enrollments;

--changeset surendra:edu-007-create-indexes
CREATE INDEX idx_edu_instructors_dept_id ON edu.instructors(dept_id);
CREATE INDEX idx_edu_courses_dept_id ON edu.courses(dept_id);
CREATE INDEX idx_edu_courses_instructor_id ON edu.courses(instructor_id);
CREATE INDEX idx_edu_enrollments_student_id ON edu.enrollments(student_id);
CREATE INDEX idx_edu_enrollments_course_id ON edu.enrollments(course_id);
--rollback DROP INDEX IF EXISTS idx_edu_instructors_dept_id;
--rollback DROP INDEX IF EXISTS idx_edu_courses_dept_id;
--rollback DROP INDEX IF EXISTS idx_edu_courses_instructor_id;
--rollback DROP INDEX IF EXISTS idx_edu_enrollments_student_id;
--rollback DROP INDEX IF EXISTS idx_edu_enrollments_course_id;

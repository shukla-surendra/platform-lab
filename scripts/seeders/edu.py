"""Seeds the edu schema: departments, instructors, students, courses, enrollments."""
import random
import sys
from datetime import date
from pathlib import Path

from faker import Faker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import get_conn  # noqa: E402

fake = Faker()
Faker.seed(19)
random.seed(19)

DEPARTMENTS = [
    "Computer Science", "Mathematics", "Physics", "Biology",
    "Chemistry", "English Literature", "History", "Economics",
]

COURSE_NAMES = {
    "Computer Science": ["Intro to Programming", "Data Structures", "Algorithms", "Operating Systems", "Databases"],
    "Mathematics": ["Calculus I", "Linear Algebra", "Discrete Math", "Probability & Statistics", "Real Analysis"],
    "Physics": ["Classical Mechanics", "Electromagnetism", "Quantum Physics", "Thermodynamics"],
    "Biology": ["Cell Biology", "Genetics", "Ecology", "Microbiology"],
    "Chemistry": ["Organic Chemistry", "Inorganic Chemistry", "Biochemistry"],
    "English Literature": ["American Literature", "Shakespearean Drama", "Modern Poetry"],
    "History": ["World History I", "World History II", "Modern European History"],
    "Economics": ["Microeconomics", "Macroeconomics", "Econometrics"],
}

NUM_STUDENTS = 200
SEMESTERS = ["Fall 2023", "Spring 2024", "Fall 2024"]
GRADES = ["A"] * 4 + ["A-"] * 3 + ["B+"] * 3 + ["B"] * 3 + ["B-"] * 2 + ["C+"] * 2 + ["C"] * 2 + ["D"] + ["F"]


def random_date(start_year, end_year):
    return fake.date_between(start_date=date(start_year, 1, 1), end_date=date(end_year, 12, 31))


def seed():
    conn = get_conn()
    with conn, conn.cursor() as cur:
        cur.execute(
            "TRUNCATE TABLE edu.enrollments, edu.courses, edu.instructors, "
            "edu.students, edu.departments RESTART IDENTITY CASCADE"
        )
        dept_ids = {}
        for name in DEPARTMENTS:
            cur.execute("INSERT INTO edu.departments (dept_name) VALUES (%s) RETURNING dept_id", (name,))
            dept_ids[name] = cur.fetchone()[0]

        instructor_ids_by_dept = {name: [] for name in DEPARTMENTS}
        for name in DEPARTMENTS:
            for _ in range(random.randint(2, 3)):
                first, last = fake.first_name(), fake.last_name()
                email = f"{first}.{last}{random.randint(1, 999)}@university.edu".lower()
                cur.execute(
                    """
                    INSERT INTO edu.instructors (first_name, last_name, email, dept_id, hire_date)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING instructor_id
                    """,
                    (first, last, email, dept_ids[name], random_date(2005, 2022)),
                )
                instructor_ids_by_dept[name].append(cur.fetchone()[0])

        course_ids = []
        for name, courses in COURSE_NAMES.items():
            for course_name in courses:
                credits = random.choice([3, 3, 4])
                instructor_id = random.choice(instructor_ids_by_dept[name])
                cur.execute(
                    """
                    INSERT INTO edu.courses (course_name, credits, dept_id, instructor_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING course_id
                    """,
                    (course_name, credits, dept_ids[name], instructor_id),
                )
                course_ids.append(cur.fetchone()[0])

        student_ids = []
        for _ in range(NUM_STUDENTS):
            first, last = fake.first_name(), fake.last_name()
            email = f"{first}.{last}{random.randint(1, 999)}@university.edu".lower()
            dob = fake.date_of_birth(minimum_age=18, maximum_age=24)
            enrollment_date = random_date(2021, 2024)
            major = random.choice(DEPARTMENTS)
            gpa = round(random.uniform(2.0, 4.0), 2)
            cur.execute(
                """
                INSERT INTO edu.students (first_name, last_name, email, dob, major, enrollment_date, gpa)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING student_id
                """,
                (first, last, email, dob, major, enrollment_date, gpa),
            )
            student_ids.append(cur.fetchone()[0])

        enrollment_count = 0
        for student_id in student_ids:
            num_courses = random.randint(3, 6)
            chosen_courses = random.sample(course_ids, num_courses)
            for course_id in chosen_courses:
                semester = random.choice(SEMESTERS)
                grade = random.choice(GRADES)
                cur.execute(
                    """
                    INSERT INTO edu.enrollments (student_id, course_id, semester, grade)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (student_id, course_id, semester) DO NOTHING
                    """,
                    (student_id, course_id, semester, grade),
                )
                enrollment_count += 1

    conn.close()
    print(f"edu: seeded {len(DEPARTMENTS)} departments, {sum(len(v) for v in instructor_ids_by_dept.values())} instructors, "
          f"{len(course_ids)} courses, {NUM_STUDENTS} students, ~{enrollment_count} enrollments.")


if __name__ == "__main__":
    seed()

"""Seeds the hr schema: departments, employees (with a real manager hierarchy), salary_history.

Deliberately injects two practice edge cases:
  - a handful of employees earn MORE than their direct manager (self-join scenario)
  - two employees share the exact same non-max salary (tie handling for window-function scenario)
"""
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import get_conn  # noqa: E402

fake = Faker()
Faker.seed(42)
random.seed(42)

DEPARTMENTS = [
    ("Engineering", "Austin, TX", 5_000_000),
    ("Sales", "Chicago, IL", 3_000_000),
    ("Marketing", "New York, NY", 2_000_000),
    ("Human Resources", "Remote", 1_000_000),
    ("Finance", "Boston, MA", 1_500_000),
    ("Customer Support", "Denver, CO", 1_200_000),
]

NUM_VPS = 5
NUM_MANAGERS = 15
NUM_ICS = 80

OVERPAID_PROBABILITY = 0.15


def random_date(start_year=2015, end_year=2024):
    return fake.date_between(start_date=date(start_year, 1, 1), end_date=date(end_year, 12, 31))


def insert_department(cur, name, location, budget):
    cur.execute(
        "INSERT INTO hr.departments (dept_name, location, budget) VALUES (%s, %s, %s) RETURNING dept_id",
        (name, location, budget),
    )
    return cur.fetchone()[0]


def insert_employee(cur, first, last, title, salary, manager_id, dept_id, hire_date):
    email = f"{first}.{last}{random.randint(1, 999)}@example.com".lower()
    phone = fake.phone_number()[:20]
    cur.execute(
        """
        INSERT INTO hr.employees
            (first_name, last_name, email, phone, hire_date, job_title, salary, manager_id, dept_id, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')
        RETURNING emp_id
        """,
        (first, last, email, phone, hire_date, title, salary, manager_id, dept_id),
    )
    return cur.fetchone()[0]


def maybe_overpaid_salary(base_min, base_max, manager_salary):
    """Returns a salary for the level, occasionally deliberately exceeding the manager's."""
    if manager_salary is not None and random.random() < OVERPAID_PROBABILITY:
        return manager_salary + random.randint(1_000, 20_000)
    salary = random.randint(base_min, base_max)
    if manager_salary is not None and salary >= manager_salary:
        salary = manager_salary - random.randint(1_000, 5_000)
    return salary


def insert_salary_history(cur, emp_id, current_salary, hire_date):
    """Backfills 0-2 raises leading up to the employee's current salary."""
    num_raises = random.randint(0, 2)
    if num_raises == 0:
        return
    salary = current_salary
    change_date = date.today()
    for _ in range(num_raises):
        old_salary = round(salary * random.uniform(0.85, 0.95), 2)
        change_date = change_date - timedelta(days=random.randint(180, 400))
        if change_date <= hire_date:
            break
        cur.execute(
            """
            INSERT INTO hr.salary_history (emp_id, old_salary, new_salary, change_date, reason)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (emp_id, old_salary, salary, change_date, random.choice(["Annual raise", "Promotion", "Market adjustment"])),
        )
        salary = old_salary


def seed():
    conn = get_conn()
    with conn, conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE hr.salary_history, hr.employees, hr.departments RESTART IDENTITY CASCADE")
        dept_ids = [insert_department(cur, *d) for d in DEPARTMENTS]

        # Level 0: CEO
        ceo_hire_date = random_date(2010, 2015)
        ceo_salary = 300_000
        ceo_id = insert_employee(
            cur, fake.first_name(), fake.last_name(), "Chief Executive Officer",
            ceo_salary, None, dept_ids[0], ceo_hire_date,
        )
        insert_salary_history(cur, ceo_id, ceo_salary, ceo_hire_date)

        # Level 1: VPs, one per department (cycling if fewer depts than VPs)
        vps = []  # (emp_id, salary, dept_id)
        for i in range(NUM_VPS):
            dept_id = dept_ids[i % len(dept_ids)]
            hire_date = random_date(2012, 2018)
            salary = maybe_overpaid_salary(180_000, 220_000, ceo_salary)
            # force a tie between the first two VPs for window-function practice
            if i == 1:
                salary = vps[0][1]
            emp_id = insert_employee(
                cur, fake.first_name(), fake.last_name(), "Vice President",
                salary, ceo_id, dept_id, hire_date,
            )
            insert_salary_history(cur, emp_id, salary, hire_date)
            vps.append((emp_id, salary, dept_id))

        # Level 2: Managers, each under a random VP (same department)
        managers = []  # (emp_id, salary, dept_id)
        for _ in range(NUM_MANAGERS):
            vp_id, vp_salary, dept_id = random.choice(vps)
            hire_date = random_date(2014, 2020)
            salary = maybe_overpaid_salary(110_000, 150_000, vp_salary)
            emp_id = insert_employee(
                cur, fake.first_name(), fake.last_name(), "Manager",
                salary, vp_id, dept_id, hire_date,
            )
            insert_salary_history(cur, emp_id, salary, hire_date)
            managers.append((emp_id, salary, dept_id))

        # Level 3: Individual contributors, each under a random manager (same department)
        ic_titles = ["Software Engineer", "Data Analyst", "Account Executive", "Support Specialist", "Recruiter", "Financial Analyst"]
        for _ in range(NUM_ICS):
            mgr_id, mgr_salary, dept_id = random.choice(managers)
            hire_date = random_date(2017, 2024)
            salary = maybe_overpaid_salary(60_000, 105_000, mgr_salary)
            emp_id = insert_employee(
                cur, fake.first_name(), fake.last_name(), random.choice(ic_titles),
                salary, mgr_id, dept_id, hire_date,
            )
            insert_salary_history(cur, emp_id, salary, hire_date)

    conn.close()
    total = 1 + NUM_VPS + NUM_MANAGERS + NUM_ICS
    print(f"hr: seeded {len(DEPARTMENTS)} departments and {total} employees.")


if __name__ == "__main__":
    seed()

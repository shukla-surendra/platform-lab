# pg_explore

A disposable Postgres sandbox for practicing SQL, Liquibase migrations, and
data modeling. Postgres runs in Docker with a persistent volume; schema is
managed by Liquibase; sample data is generated with Faker.

Three independent schemas live in one `practice` database:

| Schema      | Domain                        | Tables |
|-------------|--------------------------------|--------|
| `hr`        | Employees / org chart          | `departments`, `employees`, `salary_history` |
| `ecommerce` | Customers / orders / products  | `customers`, `categories`, `products`, `orders`, `order_items`, `payments` |
| `edu`       | Students / courses             | `departments`, `instructors`, `students`, `courses`, `enrollments` |

## Prerequisites

- Docker + Docker Compose
- Python 3.9+

## One-time setup

```bash
# 1. Start Postgres (persistent volume "pg_data", exposed on localhost:5432)
docker compose up -d postgres

# 2. Apply schema migrations (creates the hr / ecommerce / edu schemas + tables)
docker compose run --rm liquibase

# 3. Install the Python seeding dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Seed data

Each domain has its own standalone seeder. Run whichever you want to work with
(each one truncates and re-populates only its own schema, so they're safe to
re-run independently and in any order):

```bash
source .venv/bin/activate
python scripts/seeders/hr.py
python scripts/seeders/ecommerce.py
python scripts/seeders/edu.py
```

## Connect with DBeaver

| Field    | Value      |
|----------|------------|
| Host     | localhost  |
| Port     | 5432       |
| Database | practice   |
| User     | postgres   |
| Password | postgres   |

The `hr`, `ecommerce`, and `edu` schemas will show up as separate namespaces
under the `practice` database in DBeaver's schema tree.

## Project structure

```
docker-compose.yml            # postgres + liquibase services
liquibase/
  changelog/
    changelog-master.yaml     # root changelog, includes each domain's changesets
    hr/001-schema.sql         # Liquibase SQL-formatted changesets (with rollbacks)
    ecommerce/001-schema.sql
    edu/001-schema.sql
scripts/
  db.py                       # shared psycopg2 connection helper (reads PGHOST/PGPORT/etc.)
  seeders/
    hr.py                     # Faker-based seeder for the hr schema
    ecommerce.py               # Faker-based seeder for the ecommerce schema
    edu.py                    # Faker-based seeder for the edu schema
requirements.txt              # psycopg2-binary, Faker
```

## Practice scenarios baked into the seed data

The `hr` and `ecommerce` seeders deliberately shape the data so classic
interview-style SQL questions have a known-correct answer to check against:

- **Self-join ("employees who earn more than their manager")** — a handful of
  `hr.employees` rows are seeded with `salary` higher than their `manager_id`'s
  salary.
- **Second-highest salary / tie handling** — two VPs in `hr.employees` are
  seeded with the exact same salary, so a naive `ORDER BY salary DESC LIMIT 1
  OFFSET 1` gives a different (wrong) answer than `DISTINCT`/`DENSE_RANK`.
- **"Bought X but never Y" (set operations)** — in `ecommerce`, customers
  1-20 buy a Laptop and never a Mouse (the expected answer), 21-35 buy both
  (excluded), and 36-45 buy a Mouse only (excluded). Customers 46+ shop the
  full catalog at random for realistic noise.

## Resetting everything

```bash
# Wipe Postgres data entirely (drops the persistent volume)
docker compose down -v

# Then redo setup steps 1-2 above, and re-run whichever seeders you need.
```

Since each seeder truncates its own schema's tables first, you can also just
re-run a seeder at any time to get a fresh random dataset for that domain
without touching Postgres or Liquibase at all.

## Related: `sql_postgres_practice/`

`sql_postgres_practice/` (repo root) is a second, complementary Postgres
practice environment — small, hand-crafted, deterministic fixtures (so
every practice problem has a provable exact answer) plus theory notes and
pattern-organized problems (joins, window functions, recursive CTEs, query
optimization, MERGE/upsert), each solution actually executed with its real
output captured. No Liquibase, no Faker — reach for *this* repo instead
when you want realistic bulk data, schema migrations, or the `edu` domain
this repo doesn't have.

## Liquibase cheatsheet

The `liquibase` service in `docker-compose.yml` runs `update` by default. For
other commands, override the whole argument list (the same `--url` /
`--username` / `--password` flags are required every time):

```bash
# Show which changesets have/haven't been applied
docker compose run --rm liquibase \
  --changelog-file=changelog/changelog-master.yaml \
  --url=jdbc:postgresql://postgres:5432/practice \
  --username=postgres --password=postgres \
  status --verbose

# Roll back the last changeset
docker compose run --rm liquibase \
  --changelog-file=changelog/changelog-master.yaml \
  --url=jdbc:postgresql://postgres:5432/practice \
  --username=postgres --password=postgres \
  rollback-count 1
```

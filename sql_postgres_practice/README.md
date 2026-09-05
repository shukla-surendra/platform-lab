# SQL / PostgreSQL Practice

A self-contained SQL/Postgres practice environment: real Postgres in Docker,
multiple independent fixture databases (not one giant shared schema), theory
notes on *why* things work the way they do, and pattern-organized practice
problems — same shape as `rust_dsa_practice/`'s `PATTERN.md` + numbered
`problem`/`solution` pairs, applied to SQL instead of algorithms.

## Quickstart

```bash
cd sql_postgres_practice
docker compose up -d          # starts Postgres on localhost:5433
make load FIXTURE=ecommerce   # loads fixtures/01_ecommerce/*.sql
make psql FIXTURE=ecommerce   # opens a psql shell against it
```

Each fixture is its own database (not a schema within one shared database) —
so you can have `ecommerce`, `org_hierarchy`, and `event_log` all loaded at
once with zero risk of one topic's tables/data colliding with another's.

**Running a practice problem's solution** (container mounts nothing from
the host, so `psql`'s `\i` won't see repo files from inside the container —
pipe the file in from the host instead):

```bash
cat practice/01_joins/01_customers_with_no_orders/solution.sql | docker compose exec -T postgres psql -U practice -d ecommerce
```

Or `make psql FIXTURE=ecommerce` for an interactive shell and paste the
query in directly.

## Layout

```
sql_postgres_practice/
  docker-compose.yml   <- one Postgres 16 container, port 5433 (5432 is
                          commonly already taken by a local Postgres)
  Makefile             <- load/reset a fixture, open psql, list fixtures
  fixtures/
    01_ecommerce/       <- schema.sql + seed.sql: customers/products/orders
    02_org_hierarchy/   <- self-referencing employees table
    03_event_log/       <- timestamped user-events table
  docs/                 <- theory: mental models, not just syntax reference
  practice/
    01_joins/
    02_window_functions/
    03_recursive_ctes/
    04_query_optimization/
    05_merge_upsert/
      PATTERN.md         <- the reusable mental model for this category
      NN_problem_name/
        problem.md        <- which fixture, the question, expected shape
        solution.sql       <- the answer, commented with the reasoning
```

## Why multiple fixtures instead of one big schema

Real interview/take-home SQL questions rarely come from a schema you
designed yourself — you're handed someone else's tables and have to reason
about them cold. Three deliberately different shapes force that:

| Fixture | Shape | What it's good for practicing |
|---|---|---|
| `01_ecommerce` | Normalized, multi-table, one-to-many (customers → orders → order_items) | Joins, aggregation, `GROUP BY` reasoning |
| `02_org_hierarchy` | Single table, self-referencing FK (`employees.manager_id → employees.employee_id`) | Recursive CTEs, tree/graph-shaped queries |
| `03_event_log` | Wide, append-only, timestamped rows | Window functions, time-bucketing, running totals |

## Theory docs

Read these before (or alongside) the matching practice topic — `docs/`
explains the *mechanism* (what Postgres is actually doing and why), the
practice problems are where that mental model gets exercised against real
data:

- `docs/01_joins_mental_model.md`
- `docs/02_aggregation_and_grouping.md`
- `docs/03_window_functions.md`
- `docs/04_ctes_and_recursive_queries.md`
- `docs/05_indexing_and_query_plans.md`
- `docs/06_merge_and_upsert.md`

For deeper theory than this practice project covers by design (physical
storage internals, MVCC/concurrency, transaction isolation levels,
replication) — `mlops_aiops/docs/tools/postgresql/` (repo root) is a much
larger reference set, including a from-scratch `sql-tutorial-zero-to-hero.md`.
That doc explicitly isn't run against a live database; this project is —
treat them as theory-reference vs. hands-on-verified companions, not
duplicates.

# PostgreSQL

**Category:** relational database (query engine, storage engine, and — via extensions —
spatial/full-text/hybrid-NoSQL engine)

## What this section is

This section is different in kind from the other entries in `docs/tools/`: it's not built
from a running local instance verified command-by-command. It's organized, de-duplicated
technical content — mechanisms, not survey — covering PostgreSQL's join engine, query
optimizer, indexing, concurrency model, and a 40-scenario library of real query patterns.
Every SQL statement here is syntactically real PostgreSQL (mostly PostgreSQL 14+, `MERGE`
needs 15+), but none of it has been re-run against a live database as part of writing this
doc — treat it as accurate, well-established mechanism explanation, not as independently
re-confirmed the way [`../kafka/README.md`](../kafka/README.md) or
[`../redis/README.md`](../redis/README.md) are. To verify anything here directly,
`docker run --name pg-lab -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:15` gets a
real instance running in under a minute.

**Want to actually run queries against real data instead of reading
mechanism explanations?** `sql_postgres_practice/` (repo root) is the
hands-on, live-verified companion to this doc — a dockerized Postgres,
three independent fixture databases (normalized e-commerce, a
self-referencing org chart, an append-only event log), theory notes
written example-first against that real data, and pattern-organized
practice problems (joins, window functions, recursive CTEs, query
optimization) with solutions actually executed and their real output
captured — not just described.

Eight files. If you're new to SQL itself, start with
[`sql-tutorial-zero-to-hero.md`](sql-tutorial-zero-to-hero.md) — everything else here
assumes the fluency it builds. The scope past that is calibrated to what a **principal
engineer** should be able to reason about — the physical and operational mechanisms behind
the decisions other engineers ask them to weigh in on — not the full depth of a dedicated
DBA's day-to-day toolkit. Roughly ordered from "how the engine works physically" outward to
"how you run it in production":

- [`sql-tutorial-zero-to-hero.md`](sql-tutorial-zero-to-hero.md) — SQL from first
  principles, one running example throughout: `SELECT`/`WHERE`/`ORDER BY`, aggregation,
  every join type, subqueries, set operations, `NULL` handling, `INSERT`/`UPDATE`/`DELETE`,
  window functions, CTEs (including a worked recursive example), indexes, and transactions
  — every query actually run, with real output.
- **This README** — joins (types, physical execution algorithms, distributed-join
  strategies), the query optimizer and `EXPLAIN`, indexing fundamentals, window functions,
  and CTEs.
- [`storage-internals.md`](storage-internals.md) — the physical model everything else is a
  consequence of: 8KB pages, tuple headers, TOAST, the visibility/freeze maps, WAL and
  checkpoints, and the query planner's actual cost model (statistics, `n_distinct`, extended
  statistics for correlated columns).
- [`concurrency-and-locking.md`](concurrency-and-locking.md) — MVCC, transactions and
  isolation levels, the four classic anomalies (including write skew), table- vs row-level
  locking, deadlocks, advisory locks, `VACUUM`/autovacuum/bloat, and transaction ID
  wraparound.
- [`backup-recovery-and-replication.md`](backup-recovery-and-replication.md) — logical vs.
  physical backups, point-in-time recovery, streaming replication and replication slots,
  the `synchronous_commit` durability/latency dial, and HA orchestration (Patroni vs.
  repmgr vs. pgpool) — the mechanics underneath RDS Multi-AZ and Aurora failover.
- [`security-and-access-control.md`](security-and-access-control.md) — the role/privilege
  model, row-level security, `pg_hba.conf`, encryption in transit vs. at rest vs.
  column-level, and auditing.
- [`query-patterns.md`](query-patterns.md) — a working library of real query shapes:
  self-joins, gaps-and-islands, recursive CTEs, window-function traps, `LATERAL`, JSONB,
  full-text search, `MERGE`, arrays, PostGIS, and more — each with the mechanism, not just
  the syntax.
- [`production-and-scaling.md`](production-and-scaling.md) — AWS RDS vs. Aurora,
  connection pooling, parameter tuning, schema lifecycle at scale (primary-key overflow,
  partitioning, zero-downtime DDL), replication/stale reads, and zero-downtime live-table
  migration strategies.

## Joins: the logical types

A join combines rows from two (or more) tables based on a condition. PostgreSQL supports
the full standard set, plus a couple of PostgreSQL-specific extensions:

| Join | What it keeps |
|---|---|
| `INNER JOIN` | Only rows with a match on both sides |
| `LEFT JOIN` | Every row from the left table, matched columns from the right (`NULL` where no match) |
| `RIGHT JOIN` | Mirror of `LEFT JOIN` |
| `FULL OUTER JOIN` | Every row from both sides, `NULL`-padded wherever there's no match |
| `CROSS JOIN` | The full Cartesian product — every row on the left paired with every row on the right |
| Self-join | A table joined to itself, conceptually treated as two separate tables (see [`query-patterns.md`](query-patterns.md#the-managers-paycheck-self-joins)) |
| `LATERAL` join | A right-hand subquery that can reference columns from the left-hand table — effectively a per-row `FOR EACH` loop (see [`query-patterns.md`](query-patterns.md#top-n-per-group-lateral-joins)) |
| Anti-join | Not a keyword — a `LEFT JOIN ... WHERE right.key IS NULL` or `NOT EXISTS` pattern that finds rows on the left with *no* match on the right |

`JOIN ... USING (col)` is shorthand for `JOIN ... ON left.col = right.col` when the column
name is identical on both sides — it also collapses the duplicate column in the output,
which plain `ON` doesn't.

## Joins: how the engine actually executes them

The join type above is *what* you're asking for; the join **algorithm** is *how* PostgreSQL's
planner decides to physically compute it. The planner picks per-query, per-join, based on
table sizes, available indexes, and up-to-date statistics (`pg_statistic`, refreshed by
`ANALYZE`) — you don't choose the algorithm directly, but understanding the three makes
`EXPLAIN` output legible.

- **Nested Loop Join** — for every row in the outer table, scan the inner table (ideally via
  an index) for matches. Cheap when the outer side is small or the inner side has a good
  index; catastrophic (effectively O(n·m)) on two large, unindexed tables.
- **Hash Join** — build an in-memory hash table on the smaller input (keyed on the join
  column), then stream the larger input through it, probing for matches. The workhorse for
  joining two large tables with no useful index — one sequential pass of each side instead of
  repeated lookups. Needs `work_mem` to hold the hash table; spills to disk (`temp_files` in
  the logs) if it doesn't fit.
- **Merge Join** — sort both inputs on the join key (or use an existing sorted index), then
  walk both sorted streams in lockstep. Efficient when both sides are already sorted or
  cheaply sortable via an index — avoids materializing a full hash table.

Postgres also has **Parallel Hash Join** and **Parallel Merge Join**, using multiple worker
processes for large aggregations, plus **bloom filters** inside hash joins to cheaply reject
non-matching rows before doing the expensive equality check — relevant when you see
`Bloom Filter` in an `EXPLAIN` plan on a hash join over a large table.

### Distributed join strategies

Single-node join algorithms assume both tables live on the same machine. Once data is
sharded across nodes (Citus-style distributed Postgres, or any distributed SQL engine), a
join additionally has to decide *where* the join actually executes:

- **Co-located join** — both tables are sharded on the same key (e.g., both `orders` and
  `order_items` sharded by `customer_id`), so every shard already holds everything it needs
  to join locally. No network movement — the fastest possible distributed join.
- **Broadcast join** — one side is small (a dimension/lookup table). Copy the *entire* small
  table to every node holding a shard of the large table, then join locally. Cheap when one
  side is genuinely small; wasteful if both sides are large.
- **Repartition join** — neither side is co-located and neither is small enough to broadcast.
  Both tables get physically reshuffled across the network so matching keys land on the same
  node, then the join proceeds locally. The most expensive strategy — real network I/O for
  potentially the entire dataset — used only when the other two don't apply.

## Diagnosing a slow query: `EXPLAIN ANALYZE` and statistics

`EXPLAIN` shows the planner's chosen plan (and, with `ANALYZE`, actually runs the query and
reports real timings/row counts per step). A few concrete, recurring causes of a
badly-performing plan:

- **Stale statistics** — the planner's row-count estimates come from `pg_statistic`, a
  histogram populated by `ANALYZE` (autovacuum runs this automatically, but a large bulk
  load followed immediately by a query can outrun it). If the planner thinks a table has 10
  rows when it actually has 10 million, every downstream decision (join algorithm, index
  usage) is wrong.
- **Low selectivity** — an index scan isn't automatically faster than a sequential scan. If a
  `WHERE status = 'ACTIVE'` predicate matches 90% of a table, jumping between the index and
  the underlying heap for 9 million rows of random disk I/O is *slower* than reading the
  table sequentially start to finish. The planner will correctly choose `Seq Scan` here, and
  that's not a bug.
- **A function wrapped around the indexed column mutates it before comparison** —
  `WHERE DATE(created_at) = '2026-01-01'` cannot use a standard B-Tree index on
  `created_at`, because the index stores raw `TIMESTAMP` values, not `DATE`-truncated ones.
  Two fixes: rewrite as a range (`created_at >= '2026-01-01' AND created_at < '2026-01-02'`,
  the generally preferable option), or build an **expression index**
  (`CREATE INDEX ON t (DATE(created_at))`) that matches the exact expression used in the
  query. The same applies to `LOWER(col)`, `COALESCE(col, x)`, or any other function wrapped
  around an indexed column.
- **A data-type mismatch forces an implicit cast on every row** — if a column is `VARCHAR`
  but a query (often via an ORM) sends the parameter as an `INTEGER`, Postgres casts every
  row to compare, which also disables the index.
- **`OR` across different columns can defeat two separate single-column indexes** —
  `WHERE email = 'x@y.com' OR phone = '555-1234'` with separate indexes on `email` and
  `phone` sometimes makes the planner abandon both indexes for a sequential scan, rather than
  using a `BitmapOr` merge of the two index scans. Rewriting as two `SELECT`s combined with
  `UNION` forces each half to use its own index independently, then merges the results.

Two operational extensions worth enabling on any real deployment: `pg_stat_statements`
(records execution time, memory, and hit rate for every distinct query shape, stripped of
literal values — the actual source of "which queries are the problem" data) and
`auto_explain` (configured to dump the `EXPLAIN` plan into the logs automatically for any
query over a threshold, e.g. 500ms, so a slow query's plan is captured the first time it
happens, not only when someone remembers to reproduce it).

## Indexing beyond the default B-Tree

| Index type | When to use it | Why |
|---|---|---|
| B-Tree (default) | Equality and range queries on scalar columns | General-purpose, the right default |
| Partial (`CREATE INDEX ... WHERE active = true`) | A query only ever filters on a subset of rows | Skips indexing the rows nobody queries — smaller index, less write overhead |
| BRIN (Block Range Index) | Naturally-ordered, append-only data (`created_at` on a time-series table) | Stores only the min/max value per physical disk block instead of a pointer per row — often 99% smaller than a B-Tree on the same column, because it relies on physical storage order rather than indexing every value |
| Covering index (`CREATE INDEX ... INCLUDE (col)`) | A query's `SELECT` list can be satisfied entirely from the index | Enables an **index-only scan** — Postgres never touches the underlying table (the heap) at all |
| GIN (Generalized Inverted Index) | `JSONB` containment queries, full-text search (`tsvector`), array containment | Maps individual keys/values/lexemes back to row IDs — the only way to make `@>`, `?`, or `@@` queries fast on unstructured data |
| GiST (Generalized Search Tree) | Spatial data (PostGIS geometries), range-type overlap queries | Supports "nearest," "contains," and "overlaps" queries that a B-Tree's strict ordering can't express |

A B-Tree index isn't automatically the right call for every column — see the "low
selectivity" case above, and `production-and-scaling.md`'s coverage of index bloat during
bulk inserts.

## Window functions

A window function computes a value across a set of rows *related to the current row*
(the "window") without collapsing them into a single output row the way `GROUP BY` does —
every input row survives, each annotated with the window computation.

```sql
SELECT
    sales_rep_id,
    sale_month,
    revenue,
    SUM(revenue) OVER (PARTITION BY sales_rep_id ORDER BY sale_month) AS running_total
FROM monthly_sales;
```

`PARTITION BY` groups rows for the window the way `GROUP BY` groups rows for aggregation
(each partition computed independently); `ORDER BY` inside `OVER (...)` matters twice over —
it controls the order the window "sees" rows in, and it **also implicitly restricts the
default window frame to `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`**. Omit the
`ORDER BY` inside a `SUM() OVER (PARTITION BY ...)` and you get a grand total repeated on
every row, not a running total — the `ORDER BY` is what turns it into "everything so far."

`RANK()` vs `DENSE_RANK()` vs `ROW_NUMBER()` differ only in how they handle ties:
`ROW_NUMBER()` assigns a unique, arbitrary sequence even to tied rows; `RANK()` gives tied
rows the same rank and then skips the next rank number (1, 1, 3); `DENSE_RANK()` gives tied
rows the same rank with no gap (1, 1, 2).

**`ROWS BETWEEN` vs `RANGE BETWEEN`** is a real, easy-to-miss correctness bug, not a style
choice. `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW` counts literal physical rows in the
result set — if a day has zero sales (no row at all) or multiple sales (several rows), "6
rows back" silently stops meaning "6 days back." `RANGE BETWEEN INTERVAL '6 days' PRECEDING
AND CURRENT ROW` evaluates the actual logical value of the `ORDER BY` column, so a rolling
7-day average stays a true 7-day average regardless of how many rows exist on any given day.
Any "rolling N-day" calculation over data that might have gaps or multiple rows per period
needs `RANGE`, not `ROWS`.

`LAG()`/`LEAD()` read the previous/next row's value within the current partition — the
standard tool for "compare this row to the one before it" (see
[`query-patterns.md`](query-patterns.md) for streak-detection and gaps-and-islands, both
built on this).

## CTEs (`WITH` clauses)

A CTE names a subquery so it can be referenced later in the statement — mainly a
readability tool for breaking a complex query into named, sequential steps (see
[`query-patterns.md`](query-patterns.md#chaining-ctes-sessionization) for a query built
from four chained CTEs, each one step of a pipeline).

**Materialization behavior changed in PostgreSQL 12.** Before version 12, a CTE was an
optimization fence: Postgres fully executed it, materialized the entire result (in memory or
temp disk space), and only then ran the outer query against that materialized result — even
if the outer query only needed a handful of rows out of millions. From version 12 onward,
the planner inlines CTEs automatically (like a subquery), pushing outer-query filters down
into the CTE's execution. The old, non-inlined behavior can still be forced explicitly with
`WITH my_cte AS MATERIALIZED (...)` when that's genuinely what's wanted (e.g., to avoid
re-evaluating an expensive or side-effecting expression once per reference).

### Recursive CTEs

`WITH RECURSIVE` is the tool for hierarchical or graph-shaped data — an org chart, a
bill-of-materials tree, a social graph — where a fixed number of `JOIN`s can't work because
the depth isn't known in advance. Every recursive CTE has exactly three parts:

1. **The anchor member** — the starting point, runs exactly once.
2. **`UNION ALL`** — connects the anchor to the recursion (must be `UNION ALL`, not `UNION`,
   for the engine to keep iterating — `UNION` would deduplicate and potentially mask genuine
   revisits).
3. **The recursive member** — a query that joins the CTE back to itself, run repeatedly until
   it returns zero new rows.

```sql
WITH RECURSIVE org_tree AS (
    SELECT emp_id, name, manager_id, 1 AS depth
    FROM employees
    WHERE manager_id IS NULL          -- anchor: the root of the hierarchy

    UNION ALL

    SELECT e.emp_id, e.name, e.manager_id, ot.depth + 1
    FROM employees e
    INNER JOIN org_tree ot ON e.manager_id = ot.emp_id
)
SELECT * FROM org_tree ORDER BY depth, emp_id;
```

**Cycle prevention is not automatic and matters as soon as the graph isn't a strict tree.**
A bidirectional graph (user 1 connects to user 2, user 2 connects back to user 1) will loop
forever without an explicit check. The standard fix: carry an array of visited nodes forward
through each recursive step (`path_visited || next_id`), and add
`WHERE next_id != ALL(path_visited)` to the recursive member's filter — this forces the
recursion to stop extending any branch the moment it would revisit an already-seen node. See
[`query-patterns.md`](query-patterns.md#graph-traversal-with-cycle-detection) for the full
worked example, and [`query-patterns.md`](query-patterns.md#bill-of-materials-recursive-cost-rollup)
for carrying a multiplied quantity (not just a depth counter) down the tree for a cost
rollup.

# Production Partition Management — Citus/Postgres

In production, partition creation is handled **automatically** via scheduled jobs — nobody manually runs `CREATE TABLE events_2027_01 PARTITION OF events...` every month. Below are the standard approaches, roughly in order of how commonly they're used.

## 1. `pg_partman` — the most common production approach

`pg_partman` is a Postgres extension purpose-built for exactly this: auto-creating future partitions and dropping/archiving old ones on a schedule.

```sql
CREATE EXTENSION IF NOT EXISTS pg_partman;

-- Register events as a partman-managed table
SELECT partman.create_parent(
    p_parent_table => 'public.events',
    p_control      => 'created_at',
    p_type         => 'range',
    p_interval     => 'monthly',
    p_premake      => 4   -- keep 4 future partitions pre-created at all times
);
```

Then a background worker (`pg_partman_bgw`) runs on a schedule (e.g. daily) and:

- Creates new partitions ahead of time (so Jan 2027's partition exists before Jan 1, 2027 arrives)
- Optionally drops/detaches partitions older than a retention window (e.g. `p_retention => '12 months'`)

```sql
-- Enable the background worker (runs via postgresql.conf + cron-like schedule)
SELECT partman.run_maintenance_proc();
```

**Citus-specific note:** `pg_partman` works with Citus for the *parent* table's local partitioning, but the newly created child partitions still need Citus's own hooks to be distributed automatically — check `citus.partman` support in your Citus version, as this integration has evolved release to release. As of Citus 11+, Citus does auto-detect and distribute partitions created by partman under the parent, but it's worth explicitly verifying with a test partition rather than assuming.

## 2. Airflow/cron job that runs raw DDL

A scheduled DAG that runs ahead of each period boundary — gives you more control (logging, alerting on failure, easy to fold into existing DAG dependency graphs) at the cost of writing/maintaining the scheduling logic yourself instead of relying on `pg_partman`'s built-in scheduler.

```python
# Airflow task, runs monthly via cron schedule e.g. '0 0 25 * *' (25th of each month, prep next month)
CREATE_NEXT_PARTITION_SQL = """
CREATE TABLE IF NOT EXISTS events_{year}_{month:02d}
PARTITION OF events
FOR VALUES FROM ('{start_date}') TO ('{end_date}');
"""
```

## 3. Always keep a `DEFAULT` partition as a safety net

Regardless of which automation you use, keep this so a missed/late partition creation doesn't hard-fail inserts:

```sql
CREATE TABLE events_default PARTITION OF events DEFAULT;
```

Rows that don't match any existing range land here instead of erroring out — you'd then periodically check `events_default` for rows and manually move them into a properly created partition (or alert if it's non-empty, since it usually means your automation missed a beat).

## 4. Old partition lifecycle (equally important, often forgotten)

Production partitioning isn't just "create new" — it's also "retire old":

```sql
-- Detach (keeps data, removes from active partition set — fast, no data copy)
ALTER TABLE events DETACH PARTITION events_2025_01;

-- Then archive to cold storage (S3) or drop entirely
-- e.g. export via COPY, then:
DROP TABLE events_2025_01;
```

`pg_partman`'s retention settings (`p_retention`, `p_retention_keep_table`) automate this too — detach + optionally drop partitions older than N months on the same schedule as creation.

## Recommended setup

Given an AIOps/Airflow-based stack: **`pg_partman` for the create/retention mechanics** (battle-tested, handles edge cases like DST/leap years correctly) **orchestrated/monitored via an Airflow sensor DAG** that checks partman ran successfully and alerts if not — rather than reimplementing partition DDL logic manually in Airflow.

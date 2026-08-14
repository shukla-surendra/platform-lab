# Airflow in Production: Scenarios Worth Understanding Cold

Everything in [`README.md`](README.md) is Airflow working as intended. This doc is the
other half — the specific ways it breaks, surprises, or quietly costs more than expected
— each one explained by mechanism, not just named. Every scenario below was actually run
against the live 3-process lab (webserver, scheduler, Postgres) this README verifies
against, using small throwaway DAGs built and triggered for exactly this purpose, then
removed (`airflow dags delete`) once the evidence was captured — the numbers below are
real, not projected.

## Scheduling

### `catchup=True` (the global default) silently queues every missed run since `start_date`

A DAG with `start_date` set 10 days in the past, `schedule="@daily"`, and `catchup` left at
its default (`catchup_by_default=True`, verified via `airflow config get-value scheduler
catchup_by_default`):

```python
@dag(dag_id="catchup_demo", start_date=datetime.utcnow() - timedelta(days=10),
     schedule="@daily", catchup=True)
def catchup_demo():
    ...
```

Real result, within ~45 seconds of the file landing in `dags/` — **no manual trigger at
all**:

```
$ airflow dags list-runs -d catchup_demo_temp
scheduled__2026-08-12T00:00:00+00:00  success
scheduled__2026-08-11T00:00:00+00:00  success
scheduled__2026-08-10T00:00:00+00:00  success
scheduled__2026-08-09T00:00:00+00:00  success
scheduled__2026-08-08T00:00:00+00:00  success
scheduled__2026-08-07T00:00:00+00:00  success
scheduled__2026-08-06T00:00:00+00:00  success
scheduled__2026-08-05T00:00:00+00:00  success
scheduled__2026-08-04T00:00:00+00:00  success
```

**Nine DAG runs, automatically**, one per missed day between `start_date` and now. This is
the actual mechanism, working exactly as documented — but it's the single most common way
a first-time Airflow user accidentally triggers a mass-backfill: pointing `start_date` at
"whenever the underlying data started existing" (a natural instinct) rather than "whenever
this DAG should start actually running" queues a real run, with real side effects (every
downstream write, every API call, every notification a task makes), for every day in
between. **The fix, stated as a habit**: default new DAGs to `catchup=False` unless a
backfill is genuinely, deliberately intended — and when a backfill *is* intended, do it
explicitly (`airflow dags backfill`) with an explicit date range, not implicitly via
`start_date` placement.

## Concurrency

### A `Pool` genuinely throttles — five ready tasks, two slots, three sequential waves

A pool with 2 slots (`airflow pools set demo_pool 2 "..."`,), five tasks assigned to it,
each sleeping 15 seconds, all triggered simultaneously:

```
worker_3  running 17:44:47 -> success 17:45:02   ┐
worker_4  running 17:44:47 -> success 17:45:02   ┘  wave 1 (0-15s)
worker_0  running 17:45:03 -> success 17:45:18   ┐
worker_1  running 17:45:03 -> success 17:45:18   ┘  wave 2 (15-30s)
worker_2  running 17:45:19 -> success 17:45:34        wave 3 (30-45s)
```

At the 6-second mark, a state snapshot showed exactly what the pool guarantees: **two
tasks `running`, three `scheduled`** (queued, waiting on a pool slot) — never more than 2
running concurrently, confirmed directly, not just configured. Five 15-second tasks took
**45 seconds wall-clock**, not 15 — the pool traded throughput for a hard concurrency
ceiling, exactly as configured. This is the real mechanism behind rate-limiting DAGs
against a downstream system with a genuine concurrency limit (a database connection pool,
a third-party API's rate limit) — `pool` is Airflow's actual primitive for that, not
`retries`/`retry_delay`, which is a different problem (transient failure, not sustained
concurrency).

**The fix, stated as a habit**: any task that calls something with a real concurrency
ceiling downstream (a rate-limited API, a connection-pool-limited database) should be in a
`pool` sized to that ceiling — without one, Airflow's default `core.parallelism` (32,
verified via `airflow config get-value core parallelism`) is the only limit, which is
almost certainly higher than whatever's on the other end can actually absorb.

### `execution_timeout` kills a hung task — verified, not just documented

A task that sleeps 30 seconds but is given `execution_timeout=timedelta(seconds=5)`:

```
$ start_date 17:44:44.90  end_date 17:44:49.99   (== 5.09s, not 30s)
state: failed
```

Real log evidence — the task genuinely gets interrupted, not just marked failed after the
fact:

```
[timeout.py:68] ERROR - Process timed out, PID: 517
airflow.exceptions.AirflowTaskTimeout: Timeout, PID: 517
Marking task as FAILED.
```

**The fix, stated as a habit**: any task calling something that could hang indefinitely (a
network call with no client-side timeout, a query against a table that might be locked)
needs its own `execution_timeout` — without one, a single hung task doesn't just fail
slowly, it can hold a worker slot (and, if it's also holding a `pool` slot, block every
other task waiting on that pool) for as long as the underlying call is willing to hang,
which for an unbounded network call can be effectively forever.

## Data Passing

### There's no hard XCom size limit in the OSS/Postgres backend — it silently accepts megabytes

Two real pushes, same logical size class, very different actual on-disk cost — measured
directly against the Postgres metadata database, not assumed:

```sql
-- 5MB of a single repeated character
SELECT pg_column_size(value) FROM xcom WHERE task_id='push_big';
-- 60023 bytes   <- Postgres's automatic TOAST compression collapsed a highly
--                   compressible value to ~1% of its logical size

-- ~7MB of random, incompressible (base64-of-os.urandom) data
SELECT pg_column_size(value) FROM xcom WHERE task_id='push_big';
-- 6990510 bytes  <- stored essentially at full size — TOAST compression only helps
--                    when the data is actually compressible, and most real payloads
--                    (serialized objects, JSON of real data, encoded files) aren't
```

**Neither push errored, warned, or was rejected.** This is the actually-dangerous version
of the "XCom isn't for big data" advice: it's not that Airflow stops you — it's that
nothing stops you, and the cost doesn't show up as an error at push time, it shows up
later as metadata-database bloat, slower Postgres backups, and a UI that gets sluggish
rendering XCom values in the browser. **The fix, stated as a habit**: XCom is for IDs,
counts, short strings, and small structured summaries — anything that could plausibly be
"a DataFrame," "a file's contents," or "an API response body" belongs in actual storage
(S3, a database table, a shared filesystem path) with only the *reference* (a key, a path,
a row ID) passed through XCom. Airflow's own `Custom XCom Backends` feature exists
specifically to redirect large-payload XComs to object storage transparently — worth
reaching for on a real pipeline where this pattern is common, rather than relying on every
DAG author remembering the size discipline by hand.

## Failure Handling

### `on_failure_callback` only fires on the final attempt — see [`README.md`](README.md#retries-and-failure-callbacks--what-actually-fires-and-when)
  for the full mechanism, confirmed both empirically (it did not fire across two
  retryable failures in a live run) and against Airflow's own source
  (`if force_fail or not ti.is_eligible_to_retry()` in `taskinstance.py`). Repeated here
  as a pointer since it's exactly this category of "worked in testing, silently didn't
  fire in the incident that actually mattered" surprise — a callback wired up to page
  someone "on any failure" only pages once retries are fully exhausted, which for a task
  with `retries=3` and a real `retry_delay` could be many minutes after the *first* sign
  of trouble.

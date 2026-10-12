# Airflow concepts

A reference for the ideas behind the lessons in `dags/`. Written for Airflow 3.x.

## 1. What Airflow is (and is not)

Airflow is a **workflow orchestrator**. You describe a pipeline as Python code; Airflow
schedules it, runs the steps in order, retries failures, and shows the state of everything.

- It **orchestrates**: "run the Spark job, then the dbt models, then email the report."
- It is **not** the place to do heavy data processing. Trigger Spark, dbt, a warehouse query,
  or a container, and let that system do the work.
- It is **not** a streaming system. It runs batch workflows on a schedule or on events.

## 2. Core objects

| Concept | Meaning |
|---|---|
| **DAG** | Directed Acyclic Graph: tasks plus dependencies, no cycles. Defines order and schedule. |
| **Task** | One unit of work in a DAG. |
| **Operator** | A reusable template for a task: `BashOperator`, `S3CreateObjectOperator`, ... |
| **TaskFlow (`@task`)** | Turns a Python function into a task; return values pass between tasks automatically. |
| **DAG run** | One execution of a DAG for one data interval. |
| **Task instance** | One task within one DAG run. It has a state (success, failed, ...). |
| **Sensor** | A task that waits for something (a file, a partition, another DAG). |
| **Hook** | A Python client for an external system (`S3Hook`). Operators are built on hooks. |
| **Connection** | Stored credentials and settings for an external system. |
| **Variable** | A stored config value. |
| **XCom** | Small values passed between tasks. |
| **Pool** | A named limit on concurrent tasks (e.g. max 5 using one database). |
| **Provider** | A pip package that adds operators, hooks and sensors for a system (`apache-airflow-providers-amazon`). |

Operator vs task vs task instance: the operator is the template, the task is that template used in
a DAG, the task instance is that task in one specific run.

## 3. Architecture

```
            ┌────────────────────────── metadata DB (Postgres) ──────────────────────────┐
            │  DAG definitions, runs, task states, connections, variables, XComs         │
            └───────▲───────────────▲──────────────────▲──────────────────▲──────────────┘
                    │               │                  │                  │
            ┌───────┴──────┐ ┌──────┴───────┐ ┌────────┴────────┐ ┌───────┴───────┐
 dags/ ───> │ dag-processor│ │  scheduler   │ │   api-server    │ │   triggerer   │
 (files)    │ parses files │ │ decides what │ │ UI + REST API + │ │ runs deferred │
            │ stores DAGs  │ │ runs and when│ │ Execution API   │ │ (async) tasks │
            └──────────────┘ └──────┬───────┘ └────────▲────────┘ └───────────────┘
                                    │ executor                │ tasks report state
                                    ▼                         │ through the Execution API
                              ┌───────────┐                   │
                              │  workers  │───────────────────┘
                              │ run tasks │
                              └───────────┘
```

- **Scheduler:** creates DAG runs when due and decides which tasks are ready.
- **DAG processor:** repeatedly parses the files in `dags/` and stores the result in the DB.
- **Executor:** *how* tasks run. `LocalExecutor` runs them as subprocesses on the scheduler
  machine (this lab). `CeleryExecutor` sends them to a pool of workers through a queue.
  `KubernetesExecutor` starts one pod per task.
- **API server:** the web UI and REST API. In Airflow 3 it also serves the Execution API that
  running tasks use to report status and fetch connections, so workers no longer access the DB directly.
- **Triggerer:** runs deferrable operators asynchronously so they don't hold a worker slot.
- **Metadata DB:** the source of truth. Back it up in production.

## 4. How a run is scheduled

1. The dag-processor parses a file and registers the DAG.
2. When the schedule says an interval has ended, the scheduler creates a **DAG run**.
3. The scheduler finds tasks whose upstream tasks are done and queues them for the executor.
4. A worker runs the task, which reports its state; retries are scheduled if it fails.
5. When all tasks finish, the run is marked success or failed.

### Data intervals and logical date

A run covers a **data interval** and starts *after the interval ends*.

```
schedule="@daily"       run for Jan 1:  data_interval_start = Jan 1 00:00
                                        data_interval_end   = Jan 2 00:00
                                        actually starts at    Jan 2 00:00
```

Rule: **use `data_interval_start/end` (or `{{ ds }}`) to decide which data to process, never `now()`.**
That keeps backfills and re-runs correct. See [BACKFILL.md](BACKFILL.md).

### Schedule options

`"@daily"`, `"@hourly"`, a cron string (`"0 6 * * *"`), a `timedelta`, a timetable object,
an asset-based schedule (run when upstream data is updated), or `None` (manual only).

### `catchup`

`catchup=True` creates runs for every missed interval since `start_date` as soon as the DAG is
unpaused. `catchup=False` only schedules the latest interval. Prefer `False` and use a controlled
backfill when you need history.

## 5. Task states

`none` → `scheduled` → `queued` → `running` → `success`

Other states: `failed`, `up_for_retry`, `up_for_reschedule` (sensor waiting), `skipped`
(branching or short-circuit), `upstream_failed` (a parent failed), `deferred` (waiting on the triggerer).

## 6. Dependencies and trigger rules

```python
a >> b >> c                 # a, then b, then c
a >> [b, c] >> d            # fan-out then fan-in
chain(a, b, c)              # same as a >> b >> c
cross_downstream([a, b], [c, d])   # every left task feeds every right task
```

By default a task runs only when **all** upstream tasks succeeded (`all_success`). Trigger rules
change that:

| Rule | Runs when |
|---|---|
| `all_success` (default) | all parents succeeded |
| `all_done` | all parents finished, whatever the result (cleanup tasks) |
| `one_failed` | at least one parent failed (alerting) |
| `one_success` | at least one parent succeeded |
| `none_failed` | no parent failed or is `upstream_failed` (skips are fine) |
| `none_failed_min_one_success` | as above, and at least one succeeded (use after branching) |
| `all_skipped` | all parents were skipped |

## 7. Advanced task patterns

| Pattern | Use it when | Lesson |
|---|---|---|
| **Branching** (`@task.branch`) | choose one path at runtime | 03, 05 |
| **Short-circuit** | skip everything downstream if a condition is false | |
| **Task groups** | organise a big graph into collapsible boxes | 05 |
| **Dynamic task mapping** (`.expand()`) | number of parallel tasks is decided at runtime | 05 |
| **Sensors** | wait for a file/partition/other DAG; use `mode="reschedule"` or `deferrable=True` | 07 |
| **Deferrable operators** | long waits without holding a worker slot (the triggerer waits) | |
| **Retries** | `retries=2, retry_delay=...`, exponential backoff available | 03 |
| **Assets** | schedule a DAG when another DAG updates a dataset | |

## 8. Passing data between tasks

**XCom** stores small values in the metadata DB. A `@task` return value becomes an XCom automatically.

- Good for: ids, file paths, counts, small dicts.
- Bad for: DataFrames, files, large result sets. They bloat the DB and slow the UI.
- Pass a **reference** instead (an S3 key, a table name) and let each task read the data itself.

## 9. Configuration and secrets

- **Connections:** host, login, password, extras for an external system. Referenced by `conn_id`
  (`aws_default`). Create in the UI, CLI, an `AIRFLOW_CONN_<ID>` environment variable, or a secrets backend.
- **Variables:** key-value config. Avoid reading them at the top level of a DAG file (it runs on every parse).
- **Params:** values supplied when triggering a run, read as `{{ params.x }}`.
- **Secrets backends:** AWS Secrets Manager, SSM Parameter Store, Vault. Preferred in production so
  secrets never sit in the metadata DB or in Git.
- **Never** commit credentials, put them in DAG files, or in `docker-compose.yaml`.

## 10. Writing good DAGs: best practices

1. **Idempotent tasks.** Re-running an interval gives the same result with no duplicates
   (overwrite a partition, upsert, delete-then-insert in a transaction).
2. **No heavy work at the top level of the file.** The dag-processor parses files constantly; API
   calls and DB queries belong inside tasks.
3. **Deterministic DAG structure.** Don't build the graph from `now()` or from changing external data.
   For runtime-sized fan-out use dynamic task mapping.
4. **Small tasks with clear boundaries.** Easier to retry and to read in the UI.
5. **Set `retries`, `retry_delay`, `execution_timeout`,** and alerts (`on_failure_callback`).
6. **Limit concurrency:** `max_active_runs`, `max_active_tasks`, pools.
7. **Pin versions** of Airflow and providers; test in a copy of production's image.
8. **Test:** an import test that loads the `DagBag` and asserts no import errors, plus unit tests for task logic.
9. **Use `tags`, `owner` and unique `dag_id`s** (team prefix) so a shared instance stays navigable.
10. **Don't use Airflow as a data processing engine.** Delegate heavy work.

## 11. Executors compared

| Executor | Tasks run as | Scales | Good for |
|---|---|---|---|
| `LocalExecutor` | subprocesses next to the scheduler | to one machine | local dev, small setups (this lab) |
| `CeleryExecutor` | jobs on a fixed pool of worker machines (queue: Redis/RabbitMQ) | horizontally, always-on cost | steady production load |
| `KubernetesExecutor` | one pod per task | elastically, with pod start-up delay | isolation, bursty load, per-task images |

## 12. Operating Airflow

- **Debug a missing DAG:** check import errors (`airflow dags list-import-errors`), that the file is in
  the DAG folder, that the dag-processor is running, and that the DAG isn't paused.
- **Re-run work:** clear task instances in the UI, or run a backfill.
- **Logs:** per task try, in the UI; stored on disk or remote storage (S3) in production.
- **Upgrades:** run `airflow db migrate`; read the release notes; upgrade providers with the core.
- **Health:** monitor scheduler heartbeat, DAG parse time, queued task counts, metadata DB size.
  Clean old data with `airflow db clean`.

## 13. Airflow 2 vs Airflow 3

| | Airflow 2 | Airflow 3 |
|---|---|---|
| Authoring import | `from airflow import DAG`, `airflow.decorators` | `from airflow.sdk import DAG, dag, task` |
| Task to DB access | workers talk to the DB directly | tasks use the Execution API via the api-server |
| Processes | webserver, scheduler (parses DAGs) | api-server, scheduler, **separate dag-processor**, triggerer |
| Schedule arg | `schedule_interval` / `timetable` | `schedule` |
| Date naming | `execution_date` | `logical_date` and data interval |
| Backfill | CLI command running in the CLI process | scheduler-managed backfills (UI, CLI, API) |
| DAG sources | one folder | DAG bundles (local folders, git) and DAG versioning |

## 14. Where each lesson fits

| Lesson | Concepts |
|---|---|
| `01_hello_world` | DAG, TaskFlow, XCom |
| `02_schedule_and_catchup` | schedules, data interval, catchup, templates |
| `03_retries_and_branching` | retries, branching, trigger rules |
| `04_backfill_demo` | backfill, idempotency, `max_active_runs` |
| `05_complex_pipeline` | fan-out/in, task groups, mapping, branching, `cross_downstream`, cleanup tasks |
| `06_dependency_maze` | graph shape, diamonds, concurrency limits, Gantt view |
| `07_aws_s3` | connections, provider operators, sensors, hooks |

More: [BACKFILL.md](BACKFILL.md), [DEPLOYMENT.md](DEPLOYMENT.md), [AWS.md](AWS.md).

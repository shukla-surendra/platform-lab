# Airflow Lab (Docker)

Airflow 3.0.6 running locally with Docker Compose, using `LocalExecutor` + Postgres.

## Run it

```bash
open -a Docker                      # start Docker Desktop, wait until it is "running"
docker compose up airflow-init      # one-time: migrates the DB, creates the user
docker compose up -d                # start everything
```

Open http://localhost:8080, login `airflow` / `airflow`.

```bash
docker compose ps                   # what is running
docker compose logs -f airflow-scheduler
docker compose down                 # stop (keeps DB)
docker compose down -v              # stop and wipe the DB
```

Give Docker Desktop at least 4 GB RAM (Settings -> Resources).

## What each container is

| Container | Job |
|---|---|
| `postgres` | **Metadata DB**: DAG runs, task states, connections, variables, XComs. Airflow's memory. |
| `airflow-init` | Runs once: DB migration + creates the login user, then exits. |
| `airflow-apiserver` | The UI and REST API. In Airflow 3 it also serves the Execution API that running tasks call. |
| `airflow-scheduler` | Decides which tasks are due and starts them. With LocalExecutor it runs them too. |
| `airflow-dag-processor` | Parses the Python files in `dags/` and writes the result to the DB. |
| `airflow-triggerer` | Runs deferrable (async) tasks without holding a worker slot. |

Production would use `CeleryExecutor` or `KubernetesExecutor`, so tasks run on separate workers/pods instead of inside the scheduler.

## Docs

- [CONCEPTS.md](CONCEPTS.md): the ideas behind Airflow (architecture, scheduling, trigger rules, best practices)
- [BACKFILL.md](BACKFILL.md): backfills and idempotency
- [DEPLOYMENT.md](DEPLOYMENT.md): how teams deliver DAGs
- [AWS.md](AWS.md): connecting Airflow to AWS

## Lessons (in `dags/`)

1. `01_hello_world.py`: `@dag`, `@task`, passing data between tasks (XCom).
2. `02_schedule_and_catchup.py`: schedules, `data_interval_*`, `catchup`.
3. `03_retries_and_branching.py`: retries, branching, trigger rules.
4. `04_backfill_demo.py`: backfilling past dates, and writing idempotent output (one file per day in `logs/backfill_demo/`). Full explanation: [BACKFILL.md](BACKFILL.md).
5. `05_complex_pipeline.py`: a non-linear DAG: fan-out/fan-in, task groups, dynamic task mapping, branching, trigger rules, `cross_downstream`.
6. `06_dependency_maze.py`: graph shape only: 29 tasks, 7 layers, criss-cross joins, diamonds, `cross_downstream`. Use the Graph and Gantt views.
7. `07_aws_s3.py`: S3 through an Airflow connection (operator, sensor, hook). Setup in [AWS.md](AWS.md); needs an AWS account.

Do them in order: unpause the DAG in the UI, trigger it, then open the Graph and Logs tabs.
Edit a file and the change shows up in about 30 seconds, because `dags/` is mounted into the containers.

CLI inside the stack:

```bash
docker compose exec airflow-scheduler airflow dags list
docker compose exec airflow-scheduler airflow tasks test 01_hello_world total 2026-01-01
```

## How do you "deploy" things on Airflow?

> Team setup (separate DevOps and data-engineer repos, multiple DAG folders, Git): see [DEPLOYMENT.md](DEPLOYMENT.md).

A DAG is just a Python file. Deploying means getting that file into the folder the **dag-processor** reads. There is no build step and no restart.

| Where | How the files get there |
|---|---|
| **Local (this lab)** | Bind mount: `./dags` is mounted into the containers. Save the file, done. |
| **VM / bare metal** | Copy files into `$AIRFLOW_HOME/dags` (rsync, or a `git pull` cron/CI job). |
| **Kubernetes (Helm chart)** | Either **git-sync** sidecar (pulls a repo into a shared volume every N seconds) or **bake DAGs into the image** and roll out a new image. |
| **AWS MWAA** | CI uploads `dags/` and `requirements.txt` to an S3 bucket; MWAA syncs from it. |
| **GCP Cloud Composer** | CI copies files to the environment's GCS bucket. |
| **Astronomer** | `astro deploy` builds an image with your DAGs and pushes it. |

Typical CI/CD pipeline:

1. Pull request -> lint, run `python dags/x.py` (import check), run unit tests (`DagBag` has no import errors).
2. Merge to main -> publish DAGs (git-sync picks it up, or CI uploads to S3/GCS, or builds a new image).
3. Python dependencies change -> that needs a new image (or MWAA `requirements.txt` update), because DAG files alone can't install packages.

Rule of thumb: **DAG code changes = sync files. Dependency changes = new image.**

## Common interview questions

**1. What is Airflow?**
A workflow orchestrator. You define pipelines as Python code (DAGs); Airflow schedules them, runs tasks in order, retries failures, and shows everything in a UI. It orchestrates work. It is not meant to process big data itself.

**2. What is a DAG?**
Directed Acyclic Graph: tasks plus dependencies, with no cycles. The DAG defines *when and in what order*; the tasks define *what*.

**3. Operator vs Task vs Task Instance?**
- Operator: a template (`BashOperator`, `PythonOperator`).
- Task: an operator used in a DAG.
- Task instance: one task in one DAG run, with its own state (success, failed, ...).

**4. Explain the architecture.**
Scheduler, DAG processor, executor, workers, metadata DB, API server/UI (and a triggerer). The metadata DB is the source of truth; every component talks through it (in Airflow 3, tasks go through the Execution API instead of touching the DB directly).

**5. Executors: Local vs Celery vs Kubernetes?**
- Local: tasks are subprocesses on the scheduler machine. Simple, doesn't scale out.
- Celery: a fixed pool of workers fed by a queue (Redis/RabbitMQ). Scales out, always-on cost.
- Kubernetes: one pod per task. Isolation and elastic scaling, with pod start-up overhead.

**6. What is `catchup`?**
If `True`, Airflow creates a run for every missed interval since `start_date`. If `False`, it only schedules the latest. A very common production surprise: an old `start_date` with `catchup=True` launches hundreds of runs.

**7. What is `logical_date` / `data_interval`? Why does a daily run for Jan 1 start on Jan 2?**
A run covers a data interval, and it fires *after* the interval ends. The Jan 1 run processes Jan 1's data, so it starts at the end of Jan 1.

**8. What is XCom? Limits?**
Small key-value messages between tasks, stored in the metadata DB. Don't pass DataFrames or big files through it. Pass a path or URI (S3 key) instead, or use a custom XCom backend.

**9. What is idempotency and why does it matter?**
Re-running a task for the same interval must give the same result with no duplicates (use overwrite/upsert, partitioned writes, not blind appends). Retries and backfills depend on it.

**10. Sensors?**
Tasks that wait for a condition (file exists, partition lands). `mode="reschedule"` or `deferrable=True` frees the worker slot while waiting. The default `poke` mode holds it.

**11. Trigger rules?**
Control when a task runs based on upstream states. Default `all_success`; others include `all_done`, `one_failed`, `none_failed_min_one_success` (needed after branching).

**12. Connections, Variables, Secrets?**
Connections store credentials/hosts for external systems. Variables store config. Both can live in a secrets backend (Vault, AWS Secrets Manager) instead of the DB. Never hard-code secrets in DAG files.

**13. Pools, concurrency, parallelism?**
- `parallelism`: max running tasks across the whole installation.
- `max_active_runs`: concurrent runs of one DAG.
- `max_active_tasks`: concurrent tasks per DAG.
- Pool: named slot limit shared across DAGs (e.g. cap a database at 5 connections).

**14. Top-level code in DAG files: what's the problem?**
The dag-processor re-parses files constantly. API calls or DB queries at module level run on every parse and slow down or break scheduling. Keep heavy work inside tasks.

**15. A DAG is not showing in the UI. How do you debug?**
Check for import errors (UI banner, `airflow dags list-import-errors`); the file is in the right folder; the dag-processor is running; the file contains the strings `dag`/`airflow` (the safe-mode scan); the DAG isn't just paused.

**16. How do you backfill or re-run?**
Clear task instances in the UI (re-runs them), or `airflow backfill create` for a date range. This works safely only if tasks are idempotent.

**17. TaskFlow API vs classic operators?**
TaskFlow (`@task`) turns plain Python functions into tasks and handles XCom passing automatically. Classic operators are better for ready-made integrations (S3, BigQuery, ...). You can mix them.

**18. Airflow 2 vs 3, what changed?**
Separate dag-processor and API server, tasks run through the Execution API (no direct DB access), new `airflow.sdk` import path, DAG versioning, and `schedule_interval`/`execution_date` replaced by `schedule`/`logical_date`.

**19. When is Airflow the wrong tool?**
Real-time/streaming, very low-latency triggers, or doing the heavy compute inside Airflow itself. Airflow should *trigger* Spark, dbt, or warehouse jobs, not run the data processing.

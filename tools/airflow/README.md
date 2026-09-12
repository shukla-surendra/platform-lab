# Airflow

**Category:** workflow orchestrator (DAG scheduler and executor)

## What it is

Apache Airflow schedules and runs **DAGs** — Directed Acyclic Graphs of tasks, where each
task is a unit of work (usually a Python function) and the edges are dependencies ("run B
only after A succeeds"). Airflow itself doesn't do any of the actual work — it decides
*when* each task is eligible to run, *hands it to an executor* to actually execute, and
tracks the resulting state (success, failed, retrying, skipped) for every task instance,
forever, in its metadata database. That's the whole model: a scheduler plus a state
machine, not a data-processing engine — the DAG's tasks are what call out to Spark,
dbt, an API, or anything else that does the real work.

Everything below was built and verified against a real Airflow 2.10 instance (Postgres +
`LocalExecutor`) running in Docker on this machine — every DAG, every CLI command, every
retry and callback actually ran. See
[`../airflow-vs-alternatives.md`](../airflow-vs-alternatives.md) for a mechanism-level
contrast with Prefect, Dagster, and Argo Workflows, and which fits which situation.

## Running it

```bash
cd mlops_aiops/docs/tools/airflow
docker compose up -d postgres
docker compose up -d airflow-init      # runs migrations, creates the admin user, then exits
docker compose up -d airflow-webserver airflow-scheduler
```

Three real components, each a separate process even in this single-machine lab: the
**scheduler** (parses `dags/`, decides what's eligible to run, hands tasks to the
executor), the **webserver** (the UI/API — `http://localhost:8080`, `admin`/`admin`), and
Postgres (the metadata database — every DAG run, task state, and XCom value lives here,
not in memory). `LocalExecutor` runs tasks as subprocesses on the same machine as the
scheduler — real production setups more commonly use `CeleryExecutor` or
`KubernetesExecutor` to spread tasks across a worker fleet, but the DAG-authoring model
above is identical either way.

```bash
$ docker exec airflow-lab-webserver airflow dags list
dag_id                       | fileloc                                           | owners  | is_paused
=============================+===================================================+=========+==========
basic_task_dependencies      | /opt/airflow/dags/basic_task_dependencies.py      | airflow | False
retries_and_failure_handling | /opt/airflow/dags/retries_and_failure_handling.py | airflow | False
sensor_wait_for_condition    | /opt/airflow/dags/sensor_wait_for_condition.py    | airflow | False
xcom_data_passing            | /opt/airflow/dags/xcom_data_passing.py            | airflow | False
```

**A real gotcha, hit directly**: dropping a new `.py` file into `dags/` doesn't make it
appear instantly — the scheduler polls the folder on `AIRFLOW__SCHEDULER__DAG_DIR_LIST_INTERVAL`
(30 seconds in this lab's `docker-compose.yml`; 5 minutes is the real default), parsing
every file in the directory each time. A DAG missing from `airflow dags list` right after
you save it usually just means "the next poll hasn't happened yet," not a bug in the DAG.

## Defining a DAG: TaskFlow API

```python
from airflow.decorators import dag, task
from datetime import datetime

@dag(dag_id="basic_task_dependencies", start_date=datetime(2024, 1, 1),
     schedule=None, catchup=False, tags=["lab", "basics"])
def basic_task_dependencies():

    @task
    def extract():
        return {"orders": [10, 20, 30], "region": "us"}

    @task
    def transform(raw: dict):
        return {"region": raw["region"], "total": sum(raw["orders"])}

    @task
    def load(summary: dict):
        print(f"would write {summary} to a warehouse table")

    load(transform(extract()))

basic_task_dependencies()
```

The **TaskFlow API** (`@dag`/`@task`, Airflow 2.0+) infers a task's dependencies from
passing one function's return value into another — no explicit `>>` needed for that part.
It's sugar over the older, still-common pattern of instantiating `Operator` objects
directly and chaining them with `>>` — both compile down to the same underlying graph; see
[`dags/xcom_data_passing.py`](dags/xcom_data_passing.py) for the explicit form
(`PythonOperator` + manual `xcom_push`/`xcom_pull`) shown side by side with TaskFlow, so
the "magic" is visible once.

Triggered and run for real:

```
$ docker exec airflow-lab-webserver airflow dags trigger basic_task_dependencies
$ docker exec airflow-lab-webserver airflow tasks states-for-dag-run basic_task_dependencies <run_id>
task_id     state
extract     success
transform   success
load        success
notify      success
```

And the actual task log confirms real data flowed through, not just that tasks ran:

```
[transform] total for us: 60
Done. Returned value was: {'region': 'us', 'total': 60}
```

## XCom: how data actually moves between tasks

Every value TaskFlow "just returns" is stored as a real row in Airflow's metadata database
(Postgres here) — an **XCom**, keyed by DAG/task/run. `context["ti"].xcom_push(...)` and
`.xcom_pull(...)` are the literal calls TaskFlow's `return`/argument-passing sugar makes
for you (`dags/xcom_data_passing.py`, both forms verified to produce identical behavior).
This storage mechanism is exactly why XCom has a real size limit — see
[`production-scenarios.md`](production-scenarios.md) for the actual byte limit, hit
directly, and why it means XCom is for small values (IDs, counts, short strings), never
DataFrames or files.

## Sensors: waiting on a condition instead of doing work

```python
@task.sensor(poke_interval=5, timeout=60, mode="reschedule")
def wait_for_file():
    return os.path.exists(READY_FILE)
```

A sensor is a task whose job is "keep checking until this is true." `mode="reschedule"`
(used here) releases the worker slot between checks and re-queues itself — the
alternative, `mode="poke"` (the older default), holds a worker slot for the *entire* wait,
sleeping in-process between checks. For a wait that could take minutes to hours (a file
landing from an external system, another DAG finishing), `poke` mode can starve the whole
executor of worker slots; `reschedule` is the real operational choice, not a style
preference. Verified end to end in
[`dags/sensor_wait_for_condition.py`](dags/sensor_wait_for_condition.py): a task creates a
file, the sensor polls for it, a downstream task reads it back once found.

## Retries and failure callbacks — what actually fires, and when

```python
@task(retries=3, retry_delay=timedelta(seconds=5), on_failure_callback=log_failure)
def flaky_task(**context):
    if context["ti"].try_number < 3:
        raise RuntimeError("simulated failure")
    return "ok"
```

Real attempt logs from running this — three separate log files, one per try, roughly 5
seconds apart (`retry_delay`):

```
attempt=1.log: [flaky_task] this is attempt 1  ->  RuntimeError: simulated failure on attempt 1
attempt=2.log: [flaky_task] this is attempt 2  ->  RuntimeError: simulated failure on attempt 2
attempt=3.log: [flaky_task] this is attempt 3  ->  [flaky_task] succeeded on attempt 3
```

**A real, non-obvious mechanism, confirmed two ways**: `on_failure_callback` did **not**
fire after attempts 1 or 2, even though both raised an exception. Checked directly against
Airflow's own source
(`airflow/models/taskinstance.py`): the callback only runs inside the branch
`if force_fail or not ti.is_eligible_to_retry()` — a task that still has retries left
transitions to `up_for_retry`, not `failed`, and `on_failure_callback` is specifically a
*failure* callback, not a *retry* callback. It only fires once a task is truly, finally
done retrying (or `force_fail=True`). If you're relying on `on_failure_callback` to page
someone on the *first* sign of trouble, it won't — it only ever fires on the last attempt.

## Runnable DAGs

Each DAG in [`dags/`](dags/) was triggered against this exact compose setup and its real
task states/logs match what's shown above.

| DAG | Pattern | Mechanism demonstrated |
|---|---|---|
| [`basic_task_dependencies.py`](dags/basic_task_dependencies.py) | Linear ETL-shaped pipeline | TaskFlow dependency inference, explicit `>>` for non-data dependencies |
| [`xcom_data_passing.py`](dags/xcom_data_passing.py) | Passing data between tasks | Explicit `xcom_push`/`xcom_pull` vs. TaskFlow's implicit form |
| [`sensor_wait_for_condition.py`](dags/sensor_wait_for_condition.py) | Waiting on an external condition | `@task.sensor`, `mode="reschedule"` |
| [`retries_and_failure_handling.py`](dags/retries_and_failure_handling.py) | Transient-failure recovery | `retries`/`retry_delay`, `on_failure_callback` semantics |

```bash
docker exec airflow-lab-webserver airflow dags trigger basic_task_dependencies
docker exec airflow-lab-webserver airflow dags list-runs -d basic_task_dependencies
```

## When it breaks: production scenarios

[`production-scenarios.md`](production-scenarios.md) covers `catchup`-driven backfill
explosions (verified: how many DAG runs a forgotten past `start_date` actually queues), the
real XCom size limit hit directly, what a task stuck past its `execution_timeout` actually
looks like, and pool/`parallelism`-driven queuing once real concurrency limits are hit
(`core.parallelism` defaults to `32`, verified) — each run against this live instance, not
just named.

## What it's used for, and where the theory lives

This README stays hands-on and operational on purpose. Scheduling semantics
(`schedule`/`catchup`/backfill in depth), executor architecture trade-offs
(`LocalExecutor`/`CeleryExecutor`/`KubernetesExecutor`), and orchestrator design in general
are covered in:

- [`../airflow-vs-alternatives.md`](../airflow-vs-alternatives.md) — Airflow vs. Prefect,
  Dagster, and Argo Workflows, mechanism-level, with a "which to use where" framework.
- [`18_message_queues_and_event_driven_semantics.md`](../../../../fundamentals/system_design_foundation/00_prerequisite_concepts/18_message_queues_and_event_driven_semantics.md) —
  orchestration is adjacent to, but distinct from, the queueing/streaming systems covered
  there (Kafka/RabbitMQ move data continuously; Airflow schedules discrete, DAG-shaped
  units of work) — worth reading both to see the actual boundary between the two problem
  shapes.

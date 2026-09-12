"""
XCom ("cross-communication") is how tasks pass small pieces of data between each other —
under the hood, every XCom value is a row in Airflow's metadata database (Postgres here),
keyed by dag/task/run. That storage mechanism is exactly why XCom has a real size limit and
isn't meant for passing large payloads (see docs/PRODUCTION_SCENARIOS.md for the actual
byte limit, hit directly).

Two APIs shown: the TaskFlow API's implicit push/pull (used in basic_task_dependencies.py
already) and the explicit `xcom_push`/`xcom_pull` calls it's really doing underneath — worth
seeing once so the "magic" isn't actually magic.
"""
from datetime import datetime

from airflow.decorators import dag, task
from airflow.operators.python import PythonOperator


def explicit_push(**context):
    # the explicit form TaskFlow's `return` sugar-coats — context["ti"] is the TaskInstance,
    # and xcom_push is the actual underlying call.
    context["ti"].xcom_push(key="row_count", value=42)


def explicit_pull(**context):
    row_count = context["ti"].xcom_pull(task_ids="push_explicit", key="row_count")
    print(f"[explicit_pull] pulled row_count={row_count} via context['ti'].xcom_pull()")


@dag(
    dag_id="xcom_data_passing",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["lab", "xcom"],
)
def xcom_data_passing():

    push_explicit = PythonOperator(task_id="push_explicit", python_callable=explicit_push)
    pull_explicit = PythonOperator(task_id="pull_explicit", python_callable=explicit_pull)
    push_explicit >> pull_explicit

    @task
    def push_implicit():
        # TaskFlow does this exact xcom_push(key="return_value", ...) call automatically
        # whenever a @task function returns something.
        return {"status": "ok", "processed": 100}

    @task
    def pull_implicit(result: dict):
        print(f"[pull_implicit] received via TaskFlow return value: {result}")

    pull_implicit(push_implicit())


xcom_data_passing()

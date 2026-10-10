"""Lesson 3: retries, branching and trigger rules."""
import random
from datetime import datetime, timedelta

from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.sdk import dag, task


@dag(
    dag_id="03_retries_and_branching",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(seconds=10)},
    tags=["lesson"],
)
def retries_and_branching():
    @task
    def flaky():
        if random.random() < 0.6:
            raise RuntimeError("random failure -> watch the retry in the UI")
        return "ok"

    @task.branch
    def pick(value: str):
        return "happy_path" if value == "ok" else "sad_path"

    happy = EmptyOperator(task_id="happy_path")
    sad = EmptyOperator(task_id="sad_path")
    # none_failed_min_one_success: run even though one branch was skipped
    done = EmptyOperator(task_id="done", trigger_rule="none_failed_min_one_success")

    pick(flaky()) >> [happy, sad] >> done


retries_and_branching()

"""
Airflow retries a failed task automatically if `retries > 0` — but "automatically" is worth
seeing actually happen: how many attempts, how long between them, and what a callback sees
at each stage. A task that fails deterministically twice, then succeeds on the third try,
using `context["ti"].try_number` (the real, current attempt count Airflow tracks per task
instance) to decide when to stop failing.
"""
from datetime import datetime, timedelta

from airflow.decorators import dag, task


def log_failure(context):
    ti = context["task_instance"]
    print(f"[on_failure_callback] {ti.task_id} failed on try {ti.try_number} "
          f"of {ti.max_tries + 1} — would page/Slack here in a real pipeline")


@dag(
    dag_id="retries_and_failure_handling",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["lab", "retries"],
)
def retries_and_failure_handling():

    @task(
        retries=3,
        retry_delay=timedelta(seconds=5),
        on_failure_callback=log_failure,
    )
    def flaky_task(**context):
        try_number = context["ti"].try_number
        print(f"[flaky_task] this is attempt {try_number}")
        if try_number < 3:
            raise RuntimeError(f"simulated failure on attempt {try_number}")
        print("[flaky_task] succeeded on attempt 3")
        return "ok"

    flaky_task()


retries_and_failure_handling()

"""
A Sensor is a task that polls for a condition instead of doing work directly — "keep
checking until X is true, then let the DAG continue." The condition here is a file
appearing on disk (simulating "wait for an upstream system to drop a file"), but the same
shape applies to waiting on a database row, an API response, or another DAG's completion.

`mode="reschedule"` vs the (older) default `mode="poke"` is the real operational choice:
`poke` holds a worker slot for the entire wait, sleeping in-process between checks — fine
for short waits, wasteful for anything that might wait hours. `reschedule` releases the
worker slot between checks and re-queues itself, so a long wait doesn't starve other tasks
of workers. Used here since it's the one that actually matters in production.
"""
import os
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.operators.python import PythonOperator

READY_FILE = "/opt/airflow/logs/sensor_demo_ready_file.txt"


def create_the_file_after_a_delay():
    # simulates "an upstream system will eventually produce this" — in the real world this
    # task doesn't exist at all, some OTHER system creates the file/row/response the
    # sensor is waiting on.
    if os.path.exists(READY_FILE):
        os.remove(READY_FILE)
    with open(READY_FILE, "w") as f:
        f.write("ready")
    print(f"[create_file] wrote {READY_FILE}")


@dag(
    dag_id="sensor_wait_for_condition",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["lab", "sensors"],
)
def sensor_wait_for_condition():

    produce_file = PythonOperator(task_id="produce_file", python_callable=create_the_file_after_a_delay)

    @task.sensor(poke_interval=5, timeout=60, mode="reschedule")
    def wait_for_file():
        exists = os.path.exists(READY_FILE)
        print(f"[wait_for_file] checking {READY_FILE} -> exists={exists}")
        return exists

    @task
    def process_file():
        with open(READY_FILE) as f:
            content = f.read()
        print(f"[process_file] read back: {content!r}")

    produce_file >> wait_for_file() >> process_file()


sensor_wait_for_condition()

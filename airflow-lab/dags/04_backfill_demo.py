"""Lesson 4: a DAG that is safe to backfill.

Backfill = run a scheduled DAG for past intervals. Needs a schedule (so not schedule=None).

Try it:
  1. Unpause this DAG (catchup=False, so you get one run, not hundreds).
  2. Run a backfill for 2026-01-01 .. 2026-01-05 (UI trigger menu, or the CLI):
       docker compose exec airflow-scheduler airflow backfill create \
         --dag-id 04_backfill_demo --from-date 2026-01-01 --to-date 2026-01-05
  3. Look in ./logs/backfill_demo/ : one file per day.
  4. Backfill the same range again: still exactly one file per day. That is idempotency.
"""
from datetime import datetime
from pathlib import Path

from airflow.sdk import dag, task

# ./logs is mounted from the host, so you can see the output files on your laptop
OUT_DIR = Path("/opt/airflow/logs/backfill_demo")


@dag(
    dag_id="04_backfill_demo",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    max_active_runs=2,      # at most 2 intervals processed at the same time
    tags=["lesson"],
)
def backfill_demo():
    @task
    def extract(data_interval_start=None, data_interval_end=None) -> dict:
        # Always derive the data window from the run's interval, never from "now".
        # That is what makes the same code correct for today and for a backfilled day.
        print(f"extracting {data_interval_start} -> {data_interval_end}")
        return {"day": data_interval_start.strftime("%Y-%m-%d"), "rows": 100}

    @task
    def load(batch: dict) -> None:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        target = OUT_DIR / f"dt={batch['day']}.txt"
        # "w" overwrites: re-running the same day replaces the file instead of appending
        # a duplicate. This is the idempotent pattern (overwrite a partition).
        target.write_text(f"day={batch['day']} rows={batch['rows']}\n")
        print(f"wrote {target}")

    load(extract())


backfill_demo()

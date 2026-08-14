"""
The minimal real DAG: a handful of Python functions wired into a dependency graph. This is
what "DAG" (Directed Acyclic Graph) actually means in Airflow — not a scheduling concept
first, a *graph* first: which tasks must finish before which others can start.

Two ways to build a task graph, shown side by side since both appear in real codebases:
- `>>` on traditional operators — explicit, works with any Operator type.
- The TaskFlow API (`@dag`/`@task` decorators) — Airflow 2.0+, infers dependencies
  automatically from function calls, the default style for pure-Python task logic now.
"""
from datetime import datetime

from airflow.decorators import dag, task


@dag(
    dag_id="basic_task_dependencies",
    start_date=datetime(2024, 1, 1),
    schedule=None,       # only runs when triggered manually — see README.md for what
                          # schedule=None vs an actual cron string changes.
    catchup=False,
    tags=["lab", "basics"],
)
def basic_task_dependencies():

    @task
    def extract():
        raw = {"orders": [10, 20, 30], "region": "us"}
        print(f"[extract] pulled {len(raw['orders'])} orders for {raw['region']}")
        return raw

    @task
    def transform(raw: dict):
        total = sum(raw["orders"])
        print(f"[transform] total for {raw['region']}: {total}")
        return {"region": raw["region"], "total": total}

    @task
    def load(summary: dict):
        print(f"[load] would write {summary} to a warehouse table")

    @task
    def notify():
        print("[notify] pipeline finished — would send a Slack message here")

    # TaskFlow infers the extract -> transform -> load dependency just from passing the
    # return value of one task() call into the next — no explicit >> needed for this part.
    summary = load(transform(extract()))

    # notify() doesn't consume any of their outputs, so its dependency has to be stated
    # explicitly — this is the real, common case where TaskFlow alone isn't enough.
    summary >> notify()


basic_task_dependencies()

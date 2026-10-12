"""Lesson 1: the smallest useful DAG. Two tasks, one dependency."""
from datetime import datetime

from airflow.sdk import dag, task


@dag(
    dag_id="01_hello_world",
    start_date=datetime(2026, 1, 1),
    schedule=None,      # manual trigger only
    catchup=False,
    tags=["lesson"],
)
def hello_world():
    @task
    def extract() -> list[int]:
        return [1, 2, 3]

    @task
    def total(numbers: list[int]) -> None:
        print(f"sum = {sum(numbers)}")

    total(extract())    # passing the output creates the dependency (and an XCom)


hello_world()

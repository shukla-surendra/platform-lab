"""Lesson 2: schedules, logical dates and catchup.

Unpause this DAG, then flip catchup to True and see how many runs appear.
"""
from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

with DAG(
    dag_id="02_schedule_and_catchup",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,      # True would backfill every day since start_date
    tags=["lesson"],
) as dag:
    BashOperator(
        task_id="show_interval",
        bash_command="echo 'interval: {{ data_interval_start }} -> {{ data_interval_end }}'",
    )

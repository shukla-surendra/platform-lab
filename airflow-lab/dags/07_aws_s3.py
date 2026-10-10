"""Lesson 7: talk to AWS S3 from Airflow through a Connection.

Needs: an Airflow connection called `aws_default` (see AWS.md) and a bucket you can write to.
Set the bucket when you trigger the DAG (the "bucket" param), or change the default below.

Flow:  write_object (operator) -> wait_for_object (sensor) -> read_object (hook inside @task)
"""
from datetime import datetime

from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.amazon.aws.operators.s3 import S3CreateObjectOperator
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.sdk import Param, dag, task

KEY = "airflow-lab/{{ ds }}/hello.txt"   # templated: one object per run date


@dag(
    dag_id="07_aws_s3",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    params={"bucket": Param("my-airflow-lab-bucket", type="string")},
    tags=["lesson", "aws"],
)
def aws_s3():
    write_object = S3CreateObjectOperator(
        task_id="write_object",
        aws_conn_id="aws_default",
        s3_bucket="{{ params.bucket }}",
        s3_key=KEY,
        data="hello from airflow, run date {{ ds }}\n",
        replace=True,  # idempotent: re-running overwrites instead of failing
    )

    wait_for_object = S3KeySensor(
        task_id="wait_for_object",
        aws_conn_id="aws_default",
        bucket_name="{{ params.bucket }}",
        bucket_key=KEY,
        poke_interval=10,
        timeout=120,
        mode="reschedule",  # free the worker slot between checks
    )

    @task
    def read_object(bucket: str, key: str) -> str:
        body = S3Hook(aws_conn_id="aws_default").read_key(key=key, bucket_name=bucket)
        print(body)
        return body

    wait_for_object >> read_object(
        bucket="{{ params.bucket }}", key=KEY
    )
    write_object >> wait_for_object


aws_s3()

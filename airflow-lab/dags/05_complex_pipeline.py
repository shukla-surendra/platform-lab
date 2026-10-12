"""Lesson 5: a realistic, non-linear pipeline.

Shows in one DAG:
  - fan-out / fan-in            (3 extracts run in parallel, then join)
  - task groups                 (collapsible boxes in the Graph view)
  - dynamic task mapping        (one task instance per region, count decided at runtime)
  - branching + trigger rules   (full refresh vs incremental, then re-join)
  - cross_downstream            (every task on the left feeds every task on the right)
  - cleanup / alert tasks       (all_done, one_failed)

Everything is simulated with prints so it runs without any external system.
Open the Graph view and expand the groups. Then force a failure (see FAIL_SOURCE) and watch
which tasks turn red, which turn orange (upstream_failed), and which still run.
"""
from datetime import datetime, timedelta

from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.sdk import cross_downstream, dag, task, task_group

# Set to e.g. "customers" to make that extract fail and see how failure propagates.
FAIL_SOURCE = None


@dag(
    dag_id="05_complex_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(seconds=5)},
    tags=["lesson"],
)
def complex_pipeline():
    start = EmptyOperator(task_id="start")

    # ---------- 1. Ingest: three independent sources in parallel, each extract -> validate ----------
    @task_group(group_id="ingest")
    def ingest():
        results = []
        for source in ["orders", "customers", "products"]:

            @task(task_id=f"extract_{source}")
            def extract(src=source):
                if FAIL_SOURCE == src:
                    raise RuntimeError(f"simulated failure in {src}")
                print(f"extracting {src}")
                return {"source": src, "rows": 1000}

            @task(task_id=f"validate_{source}")
            def validate(batch):
                assert batch["rows"] > 0, "empty extract"
                return batch

            extracted = extract()
            start >> extracted  # every extract waits for start
            results.append(validate(extracted))
        return results

    ingested = ingest()

    # ---------- 2. Join: wait for all three, build one combined dataset ----------
    @task
    def merge(batches: list) -> dict:
        total = sum(b["rows"] for b in batches)
        print(f"merged {len(batches)} sources, {total} rows")
        return {"rows": total}

    merged = merge(ingested)

    # ---------- 3. Dynamic mapping: one task instance per region (list is built at runtime) ----------
    @task
    def list_regions() -> list[str]:
        return ["eu", "us", "apac"]  # imagine this came from a DB query; length can change per run

    @task
    def process_region(region: str, dataset: dict) -> dict:
        print(f"processing {region} from {dataset['rows']} rows")
        return {"region": region, "revenue": len(region) * 100}

    @task
    def aggregate(per_region: list) -> dict:
        # a mapped task's output arrives here as a list, one item per mapped instance
        total = sum(r["revenue"] for r in per_region)
        print(f"revenue across {len(per_region)} regions = {total}")
        return {"revenue": total}

    regional = process_region.partial(dataset=merged).expand(region=list_regions())
    aggregated = aggregate(regional)

    # ---------- 4. Branch: month-end gets a full refresh, other days an incremental load ----------
    @task.branch
    def choose_load_mode(logical_date=None) -> str:
        is_month_end = (logical_date + timedelta(days=1)).day == 1
        return "full_refresh" if is_month_end else "incremental_load"

    full_refresh = EmptyOperator(task_id="full_refresh")
    incremental_load = EmptyOperator(task_id="incremental_load")
    # One branch is always skipped, so the default all_success would skip this too.
    loaded = EmptyOperator(task_id="loaded", trigger_rule="none_failed_min_one_success")

    mode = choose_load_mode()
    aggregated >> mode >> [full_refresh, incremental_load] >> loaded

    # ---------- 5. Publish: three outputs, each needs BOTH the load and a data-quality check ----------
    @task
    def quality_check(summary: dict):
        assert summary["revenue"] > 0, "revenue must be positive"

    qc = quality_check(aggregated)

    build_report = EmptyOperator(task_id="build_report")
    update_dashboard = EmptyOperator(task_id="update_dashboard")
    notify_slack = EmptyOperator(task_id="notify_slack")

    # (loaded, qc) each feed (build_report, update_dashboard, notify_slack): 2 x 3 = 6 edges
    cross_downstream([loaded, qc], [build_report, update_dashboard, notify_slack])

    # ---------- 6. Wrap-up ----------
    # Runs if ANY upstream task failed; the end state of the run is still failed.
    alert_on_failure = EmptyOperator(task_id="alert_on_failure", trigger_rule="one_failed")

    # Runs whatever happened (success, failed, skipped): the right place for cleanup.
    cleanup = EmptyOperator(task_id="cleanup", trigger_rule="all_done")

    publish = [build_report, update_dashboard, notify_slack]
    publish >> cleanup
    publish >> alert_on_failure


complex_pipeline()

# 5. Pipelines, jobs and CI/CD

## Medallion architecture

A layering convention, not a product.

```
sources ──> BRONZE ──> SILVER ──> GOLD ──> BI / ML / apps
            raw        cleaned     business-level
            as-landed  conformed   aggregates, marts
```

| Layer | Contents | Rules |
|---|---|---|
| **Bronze** | Raw data exactly as received, plus ingestion metadata (`_ingested_at`, `_source_file`) | Append-only. Keep everything. Never fix data here. Replayable source of truth. |
| **Silver** | Deduplicated, typed, validated, conformed to a model; joins across sources | Quality rules, SCD handling, PII handling, schema contract |
| **Gold** | Aggregates, dimensional models, feature tables, serving tables | Optimised for consumers; business definitions live here |

Why: replay from bronze after a bug; isolate quality problems; give consumers stable contracts.

## Lakeflow Declarative Pipelines (formerly Delta Live Tables / DLT)

Databricks-only. You **declare** the tables and their queries; the framework works out the
dependency graph, orchestration, retries, checkpoints, and cluster management.

```python
import dlt
from pyspark.sql.functions import col

@dlt.table
def bronze_orders():
    return (spark.readStream.format("cloudFiles")
            .option("cloudFiles.format", "json").load("/Volumes/main/raw/orders"))

@dlt.table
@dlt.expect_or_drop("valid_amount", "amount > 0")
@dlt.expect("has_customer", "customer_id IS NOT NULL")
def silver_orders():
    return dlt.read_stream("bronze_orders").select("order_id", "customer_id", col("amount").cast("double"))
```

Or in SQL: `CREATE OR REFRESH STREAMING TABLE silver_orders (CONSTRAINT valid_amount EXPECT (amount > 0) ON VIOLATION DROP ROW) AS SELECT ...`

### Dataset types

| Type | Behavior |
|---|---|
| **Streaming table** | Incrementally processes new data from an append-only source |
| **Materialized view** | Result of a query, incrementally refreshed where possible |
| **View** | Temporary, within the pipeline only; not published |

### Expectations (data quality)

| Decorator | On violation |
|---|---|
| `expect` | Record the violation in metrics, keep the row |
| `expect_or_drop` | Drop the row |
| `expect_or_fail` | Fail the update |

Metrics land in the pipeline event log, so quality becomes queryable.

### CDC with `APPLY CHANGES` / `AUTO CDC`
```python
dlt.create_streaming_table("customers_silver")
dlt.apply_changes(
    target="customers_silver", source="customers_cdc", keys=["customer_id"],
    sequence_by="updated_at", apply_as_deletes=expr("op = 'D'"),
    stored_as_scd_type=2)
```
Handles ordering of out-of-order events (`sequence_by`), deletes, and SCD type 1 or 2 without hand-written `MERGE`.

### When to use it, and when not

| Use | Avoid |
|---|---|
| Standard ingestion → silver → gold with data quality | Highly custom logic that needs arbitrary side effects |
| Streaming + batch in one flow | Tight control of cluster, libraries, or table layout |
| You want lineage, quality metrics, auto-retries for free | Pipelines that must run outside Databricks |

Trade-offs: less control, a framework to learn, tables are owned by the pipeline (can't be written
by other jobs), debugging is through the event log and UI.

## Jobs / Workflows (Lakeflow Jobs)

The orchestrator built into Databricks.

- **Job** = a set of **tasks** with dependencies (a DAG). Task types: notebook, Python script/wheel, SQL, dbt, pipeline, JAR, run another job, condition (if/else), for-each loop.
- **Triggers:** cron schedule, **file arrival**, **table update**, continuous, manual/API.
- **Parameters:** job-level and task-level; pass values between tasks with **task values** (`dbutils.jobs.taskValues`).
- **Retries, timeouts, alerts** per task; **repair run** re-runs only the failed tasks and their downstream.
- **Compute:** a job cluster (created per run), a shared job cluster across tasks (cheaper), or serverless.
- **Permissions:** run-as identity (use a **service principal** for production), per-job ACLs.

### Databricks Jobs vs Airflow

| | Databricks Jobs | Airflow |
|---|---|---|
| Scope | Databricks workloads, tight integration | Anything, any system |
| Setup | None | You operate it (or MWAA/Composer) |
| Features | Repair runs, task values, UC lineage | Huge operator library, sensors, mature scheduling semantics |
| Typical choice | All-Databricks stack | Many systems, existing Airflow estate. Airflow can trigger Databricks jobs (`DatabricksRunNowOperator`) |

## Databricks Asset Bundles (DABs)

Infrastructure-as-code for Databricks resources. A bundle is a Git repo with a `databricks.yml`
describing jobs, pipelines, and targets (dev/stage/prod).

```yaml
bundle:
  name: orders_etl

targets:
  dev:
    mode: development
    default: true
    workspace: { host: https://<dev-workspace> }
  prod:
    mode: production
    workspace: { host: https://<prod-workspace> }
    run_as: { service_principal_name: <sp-app-id> }

resources:
  jobs:
    orders_job:
      name: orders_${bundle.target}
      tasks:
        - task_key: ingest
          notebook_task: { notebook_path: ./src/ingest.py }
```

```bash
databricks bundle validate
databricks bundle deploy -t dev
databricks bundle run orders_job -t dev
databricks bundle deploy -t prod       # from CI
```

`mode: development` prefixes resource names with the user, pauses schedules and isolates your copy.

## CI/CD flow

```
feature branch ─> PR ─> CI: lint, unit tests (local Spark), bundle validate
                          │
                  merge to main ─> deploy to STAGING (bundle deploy -t stage) ─> integration tests on small data
                          │
                  release/tag ─> deploy to PROD (bundle deploy -t prod) as a service principal
```

- **Code in Git, deployed by CI**, never by editing notebooks in prod.
- **Unit tests:** put logic in plain Python functions that take and return DataFrames; test them with a local Spark session (this lab's `common.py` is that).
- **Integration tests:** run the job in a staging workspace/catalog on a sample.
- **Environment separation:** separate workspaces or catalogs per environment (`dev`, `stage`, `prod`) and identical code parameterised by catalog name.
- **Secrets:** secret scopes or a cloud secret manager; never in code.
- **Terraform** (Databricks provider) provisions the platform (workspaces, UC metastore, clusters policies, groups); bundles deploy the *workloads*.

## Notebook vs package

| Notebooks | Python packages (wheels) |
|---|---|
| Fast to explore | Testable, reusable, reviewable |
| Hard to unit test, hidden state | Version-pinned, installable on jobs |
| Fine for orchestration glue | Put business logic here |

Production rule of thumb: thin notebooks or scripts that call a tested library.

## Error handling and idempotency

- Jobs will be retried and re-run, so **every task must be idempotent**: overwrite a partition (`replaceWhere`), `MERGE` on a key, or write with a `txnVersion`/`txnAppId` for exactly-once batch writes.
- Dynamic partition overwrite and `replaceWhere` make "reload a day" safe:
  `df.write.format("delta").mode("overwrite").option("replaceWhere", "dt = '2026-01-01'").saveAsTable(...)`
- Handle bad records: `badRecordsPath`, `PERMISSIVE` mode with `_corrupt_record`, Auto Loader `_rescued_data`, or quarantine tables for rows failing validation.
- Alert on failure *and* on silence (a job that didn't run, or loaded zero rows).

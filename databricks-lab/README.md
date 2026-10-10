# Databricks and data-engineering lab

Concepts, runnable lessons and hard interview questions for Databricks and modern data engineering.

**How it's split:**
- **`docs/`**: the concepts, written as references.
- **`lessons/`**: small runnable lessons, one idea each. They run **locally** on open-source Spark +
  Delta Lake (the same engine and file format Databricks uses), so you don't need an account.
- **`databricks_only/`**: examples for features that exist only on Databricks (Auto Loader, Lakeflow
  pipelines, Asset Bundles, Unity Catalog). Reference code, not runnable locally.

## Setup

Needs Java 17+ and [uv](https://docs.astral.sh/uv/).

```bash
cd databricks-lab
uv sync                                          # first run downloads PySpark (about 400 MB)
uv run python lessons/01_delta_basics/lesson.py
```

The first Spark run also downloads the Delta Lake jar, so it needs internet once. Tables and
checkpoints go in `.data/` (git-ignored); each lesson wipes and recreates its own folder.

## Learning path

| # | Lesson | Idea |
|---|---|---|
| 1 | [`01_delta_basics`](lessons/01_delta_basics) | A Delta table is Parquet files + a JSON transaction log |
| 2 | [`02_time_travel_and_merge`](lessons/02_time_travel_and_merge) | Versions, `MERGE`, time travel, `RESTORE` |
| 3 | [`03_schema_enforcement_evolution`](lessons/03_schema_enforcement_evolution) | Enforcement, `mergeSchema`, `CHECK` constraints |
| 4 | [`04_small_files_optimize_vacuum`](lessons/04_small_files_optimize_vacuum) | Small files, `OPTIMIZE`, `VACUUM`, Z-ORDER |
| 5 | [`05_medallion_pipeline`](lessons/05_medallion_pipeline) | Bronze/silver/gold, quarantine, idempotent reloads |
| 6 | [`06_streaming_and_checkpoints`](lessons/06_streaming_and_checkpoints) | Checkpoints, `availableNow`, watermarks |
| 7 | [`07_scd2_and_cdc`](lessons/07_scd2_and_cdc) | SCD Type 2, applying CDC in sequence order |
| 8 | [`08_skew_joins_and_aqe`](lessons/08_skew_joins_and_aqe) | Join strategies, skew, salting, AQE |

Each lesson folder has a short `README.md` (idea, what to watch for, an exercise) and `lesson.py`.

## Concept docs

| Doc | Covers |
|---|---|
| [01 Platform concepts](docs/01-platform-concepts.md) | Architecture, compute types, workspace objects, managed vs external tables, product map |
| [02 Delta Lake](docs/02-delta-lake.md) | Transaction log, ACID, time travel, MERGE, CDF, deletion vectors, layout and maintenance |
| [03 Spark internals and performance](docs/03-spark-internals-and-performance.md) | Execution model, shuffles, joins, AQE, skew, memory, UDFs, tuning checklist |
| [04 Ingestion and streaming](docs/04-ingestion-and-streaming.md) | Auto Loader, Structured Streaming, checkpoints, watermarks, `foreachBatch` |
| [05 Pipelines, jobs and CI/CD](docs/05-pipelines-jobs-and-cicd.md) | Medallion, Lakeflow pipelines, Jobs, Asset Bundles, testing, idempotency |
| [06 Unity Catalog and governance](docs/06-unity-catalog-governance.md) | Object model, privileges, masks, lineage, Delta Sharing, security |
| [07 Data engineering patterns](docs/07-data-engineering-patterns.md) | Load strategies, dedup, SCD, CDC, late data, modelling, data quality, testing |
| [08 Cost, operations, troubleshooting](docs/08-cost-operations-and-troubleshooting.md) | Cost levers, compute choice, monitoring, failure playbook |
| [09 Delta packages and ecosystem](docs/09-delta-packages-and-ecosystem.md) | Where Delta lives (JARs vs pip), versions, configuration layers, who builds it, the protocol and other implementations, Delta vs Unity Catalog |
| [**Interview questions**](docs/INTERVIEW.md) | 50 hard questions with answers, plus a rapid-fire table |

Suggested order: read docs 01 and 02 → do lessons 1–4 → doc 03 → lessons 5–8 → docs 04–07 → interview questions.

## What runs locally vs only on Databricks

| Topic | Local lessons | Databricks only |
|---|---|---|
| Delta Lake (MERGE, time travel, OPTIMIZE, VACUUM, schema) | yes | same, plus predictive optimization |
| Structured Streaming | yes | same, plus Auto Loader (`cloudFiles`) |
| Spark SQL/DataFrame performance, AQE, skew | yes | plus Photon |
| Medallion, SCD2, CDC patterns | yes (hand-written MERGE) | plus Lakeflow `APPLY CHANGES` |
| Governance (catalog, grants, masks, lineage) | not yet: open-source Unity Catalog can run locally (Java server + Spark connector) but has fewer features; no lesson here yet | full Unity Catalog |
| Jobs, Asset Bundles, serverless, system tables | no | yes |

## Notes

- Lessons print what they do. Read the output with the code open.
- Some Delta features (liquid clustering, deletion vectors, column mapping) depend on the Delta and
  Databricks Runtime versions. Check the current docs for exact availability.
- Product names change (Delta Live Tables became Lakeflow Declarative Pipelines; Workflows became
  Lakeflow Jobs). The concepts underneath stay the same.

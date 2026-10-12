# 1. Databricks platform concepts

## What Databricks is

A managed **data and AI platform** built around Apache Spark, Delta Lake and a governance layer
(Unity Catalog). It runs in *your* cloud account (AWS, Azure or GCP): you pay the cloud for the
machines and Databricks for the software (billed in DBUs, Databricks Units).

The pitch is the **lakehouse**: data warehouse features (ACID tables, SQL, governance, BI speed) on
cheap open-format files in object storage, in place of a separate lake plus warehouse.

## Architecture: control plane vs data plane

```
┌──────────── Databricks control plane (Databricks' account) ────────────┐
│  web UI, REST API, notebooks, job scheduler, cluster manager,          │
│  Unity Catalog metadata, query history                                 │
└──────────────────────────────┬─────────────────────────────────────────┘
                               │ launches / manages (secure channel)
┌──────────────────────────────▼─────────────────────────────────────────┐
│  Data plane (YOUR cloud account, your VPC/VNet)                         │
│  clusters (driver + workers), SQL warehouses, your data in S3/ADLS/GCS  │
└─────────────────────────────────────────────────────────────────────────┘
```

- **Classic compute:** VMs in your account. You pick sizes. Slower to start (minutes).
- **Serverless compute:** VMs in Databricks' account, started in seconds, no sizing. Your data
  still sits in your storage.
- Data never has to leave your account for classic compute. This is the usual security answer.

## Compute

| Type | For | Notes |
|---|---|---|
| **All-purpose cluster** | interactive notebooks, development | Shared, kept running, costs more per DBU. |
| **Job cluster** | scheduled production jobs | Created for the run, terminated after. Cheaper. Default for production. |
| **SQL warehouse** | SQL, BI tools, dashboards | Photon-powered; Classic, Pro, or Serverless. Scales by clusters. |
| **Serverless notebooks / jobs** | no cluster management | Instant start, usage-billed. |
| **Cluster pools** | cut start-up time | Idle pre-warmed instances. Less relevant with serverless. |

Cluster settings that matter: **Databricks Runtime (DBR)** version (a tested bundle of Spark, Delta
and libraries; LTS releases get long support), **autoscaling** (min/max workers), **auto-termination**,
**access mode** (single user vs shared), instance type, **spot instances** for workers (never for the
driver), **Photon**.

**Photon** is a vectorised C++ engine that runs Spark SQL/DataFrame operations faster. It helps scans,
joins, aggregations and Delta writes; it does nothing for Python UDFs.

## Workspace objects

- **Notebooks** (Python, SQL, Scala, R). Magics: `%sql`, `%python`, `%run`, `%pip`.
- **Repos / Git folders:** Git integration. Production code should live in Git, not in notebooks edited in the UI.
- **Workflows / Jobs:** scheduling and orchestration (see doc 5).
- **Dashboards, Genie** (natural-language querying), **SQL editor and alerts**.
- **Secrets:** secret scopes read in code with `dbutils.secrets.get(scope, key)`; values are redacted in output.
- **DBFS:** the legacy workspace file layer (`dbfs:/`). Don't store production data in the DBFS root.
  Use Unity Catalog **volumes** and external locations.
- **dbutils:** helpers for files (`dbutils.fs`), secrets, widgets, notebook calls.

## Unity Catalog in one picture

```
metastore (one per region, shared by many workspaces)
 └─ catalog                     e.g. prod, dev
     └─ schema (database)       e.g. sales
         ├─ table / view / materialized view
         ├─ volume              files (non-tabular data)
         ├─ function
         └─ model               registered ML model
```

Three-level name: `catalog.schema.table`. Details in [doc 6](06-unity-catalog-governance.md).

## Managed vs external tables

| | Managed | External |
|---|---|---|
| Storage location | Chosen by Unity Catalog (managed location) | Your path (an *external location*) |
| `DROP TABLE` | Deletes metadata **and** data (data retained ~7 days, recoverable with `UNDROP`) | Deletes metadata only; files stay |
| Maintenance | Can be automated (predictive optimization) | You manage it |
| Use when | Default for new tables | Data is shared with other engines, or must stay at a fixed path |

## Delta Lake, in one paragraph

Parquet files plus a transaction log give you ACID transactions, time travel, schema enforcement,
and efficient upserts. Everything on Databricks is Delta by default. See [doc 2](02-delta-lake.md).

## The ecosystem, by name

| Product | What it is |
|---|---|
| **Delta Lake** | Open table format (storage layer). |
| **Unity Catalog** | Governance: catalog, permissions, lineage, audit. |
| **Auto Loader** | Incremental file ingestion (`cloudFiles`). |
| **Lakeflow Declarative Pipelines** (formerly Delta Live Tables) | Declarative ETL with expectations. |
| **Lakeflow Jobs** (Workflows) | Orchestration. |
| **Databricks SQL** | Warehouses, editor, dashboards, alerts. |
| **MLflow** | Experiment tracking, model registry, serving. |
| **Mosaic AI** | Model serving, vector search, agents. |
| **Delta Sharing** | Open protocol to share data across orgs and platforms. |
| **Databricks Asset Bundles (DABs)** | Infrastructure-as-code for jobs, pipelines, and notebooks. |
| **Lakehouse Federation** | Query external databases without copying data. |
| **Photon** | Native vectorised engine. |

Product names change often; check current docs for exact naming.

## Databricks vs alternatives (short)

| | Databricks | Snowflake | Plain Spark (EMR, etc.) |
|---|---|---|---|
| Strength | Spark + ML + open formats + governance | SQL warehouse, simple operations | Full control, lower software cost |
| Storage | Open (Delta/Parquet) in your bucket | Proprietary (Iceberg support growing) | Whatever you choose |
| You manage | Compute config (less with serverless) | Almost nothing | Everything |

Local lessons here run on **open-source Spark + Delta Lake**, which is the same engine and file
format, minus Unity Catalog, Photon, Auto Loader, Lakeflow and the managed platform. Those
Databricks-only parts are covered in `docs/` and `databricks_only/`.

# 4. Mapping the concepts to what you've used

> Product details change quickly. Names and capabilities below reflect general
> knowledge of these products; check current docs before relying on a specific
> API or limit. The *concepts* on page 3 are stable.

## Concept map

| Concept | This repo's mini store | SageMaker Feature Store | Databricks (Feature Engineering in Unity Catalog) | Feast |
|---|---|---|---|---|
| Entity / join key | `entity_key` | **Record identifier** feature | Table **primary key** | `Entity` |
| Feature collection | `FeatureView` | **Feature Group** | **Feature table** (a Delta / UC table with a PK) | `FeatureView` |
| Event time | `event_ts` | Required **EventTime** feature | `timestamp_lookup_key` on time-series tables | `timestamp_field` |
| Offline store | DataFrame | S3 (Parquet) + Glue catalog, queried via Athena | The Delta table itself | Pluggable: file, BigQuery, Snowflake, Redshift… |
| Online store | dict | SageMaker online store (managed, low-latency) | Online tables / a published online store | Pluggable: SQLite, Redis, DynamoDB, … |
| Point-in-time join | `get_historical_features` | Dataset builder (`create_dataset`) or your own Athena query | `create_training_set` with `FeatureLookup`s | `get_historical_features` |
| Materialization | `materialize` | Automatic: ingest writes online + offline | Publish to online store / sync online tables | `feast materialize` (you run it) |
| Registry | `views` dict | Feature group metadata in the service | Unity Catalog (+ lineage) | Registry file/SQL DB |
| Transformation | `compute` fn | **Yours** (you call `PutRecord`/ingest) | **Yours** (Spark/SQL/DLT), lookups are declarative | **Yours** (Feast doesn't compute) |

## Where each one is "thick" vs "thin"

**SageMaker Feature Store** — thick on *storage*: you get a managed online store
and an S3/Glue offline store that stay in sync on ingestion. Thin on
*computation*: features come from your own Glue/Spark/Flink jobs, and the
offline store is append-only history, so "latest value" queries need a
dedupe/`row_number()` step. If you ingested into a feature group and queried
via Athena, you touched the offline half; the online half only matters if you
call `GetRecord` from an endpoint.

**Databricks** — thin as a "store", thick on *integration*. A feature table is a
governed table; the win is that **the trained model is logged with its
feature lookups**, so at serving time the platform fetches the same features
by key automatically (and lineage shows model → features → source tables).
If you were already in the lakehouse, it can honestly feel like "a table with a
primary key" — because mostly that's what it is.

**Feast** — thin and explicit: an *abstraction layer* (registry + retrieval
API + materialization) over stores you already run. It intentionally doesn't
transform data. Good for learning because everything is visible; see the
working notebook in [`mlops/projects/feast-demo`](../../mlops/projects/feast-demo)
and Feast applied to a real model in
[`mlops/projects/fraud-detection-xgboost`](../../mlops/projects/fraud-detection-xgboost)
(`feast_features.py`, `train_with_feast.py`).

**Others** — *Tecton* (managed; owns transformations incl. streaming, strongest
on real-time), *Hopsworks* (full platform, transformation + store),
*Vertex AI Feature Store* (GCP, BigQuery-backed), Snowflake / BigQuery
"feature" tables with as-of joins (plain warehouse, no separate product).

## How to relate your past use to the pain points

When you used SageMaker/Databricks feature stores, ask which of these you
actually exercised:

| Pain point | Did your use exercise it? |
|---|---|
| Skew | Only if train and serve computed features separately. One notebook → no. |
| Leakage / as-of join | Only if you built training sets with timestamps. Did you use `create_dataset` / `create_training_set`, or read the whole table? |
| Reuse | Only if a second model or team consumed the same feature group. |
| Online serving | Only if an endpoint read features by key at request time. |

If the answer was "no" to all four, you correctly perceived that the feature
store wasn't buying you anything in that project.

## Try it yourself

1. Run the three demos in [`../demos`](../demos) — the problems, then the tiny store.
2. Run [`mlops/projects/feast-demo`](../../mlops/projects/feast-demo) and locate each concept
   from page 3 in `feature_definitions.py` and the notebook.
3. Open your SageMaker/Databricks code and label each line with the concept it implements.

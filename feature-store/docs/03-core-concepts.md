# 3. Core concepts

Vocabulary is where most of the confusion lives, because every product renames
the same handful of ideas. This page pins them down once; page 4 maps the
names to SageMaker / Databricks / Feast. Code for every concept is in
[`demos/mini_feature_store.py`](../demos/mini_feature_store.py).

## Entity
The thing features describe, identified by a **join key**: `customer_id`,
`driver_id`, `(user_id, merchant_id)`. Every feature belongs to an entity.
A prediction request says "score entity X".

## Feature view / feature group / feature table
A named collection of features **for one entity from one source**, e.g.
`customer_txn_stats` = {`avg_amount_30d`, `txn_count_30d`} keyed by
`customer_id`. This is the unit you register, compute, backfill and reuse.
(Feast: *FeatureView*. SageMaker: *Feature Group*. Databricks: *feature
table*.)

## Two timestamps (the concept that makes everything else work)
- **Event time** — when the feature value became *true in the world* (the
  transaction time, the snapshot time). Used for point-in-time joins.
- **Ingestion / created time** — when the value was *written to the store*.
  Used to reason about late-arriving data and to reproduce "what did we know
  when we trained this model".

Confusing the two is the classic source of subtle leakage. SageMaker requires
an explicit `EventTime` feature; Feast has `timestamp_field` plus a created
timestamp; Databricks uses a `timestamp_lookup_key` for time-series tables.

## Offline store
Append-only **history** of feature values, each row carrying its event time.
Optimised for big scans and joins (Parquet on S3, Delta table, BigQuery,
Snowflake). Its job: answer *"what was the value for entity X at time t?"* for
millions of `(X, t)` pairs. Feeds **training sets** and **batch scoring**.

## Online store
Only the **latest** value per entity, in a low-latency key-value system
(DynamoDB, Redis, SageMaker's online store, Databricks online tables).
Its job: answer *"what is the value for entity X right now?"* in single-digit
milliseconds. Feeds **real-time inference**.

## Point-in-time (as-of) join
For each row `(entity, t)` in your labels, pick the **most recent** feature row
with `event_ts <= t` (optionally no older than a TTL). Worked example:

```
labels                          feature history for customer 7
(customer, t)      label        event_ts        avg_amount_30d
(7, Mar 10)        1            Mar 01          40
                                Mar 08          52   ← chosen for Mar 10 ✔
                                Mar 12          80   ← after t: must NOT be used
```

Demo 2 shows what happens if you pick 80 (or "latest") instead: AUC 0.98 vs
0.62. In pandas it's `pd.merge_asof(labels, features, on=..., by=entity,
direction="backward")`; every feature store implements this as its core read.

## Materialization
The job that copies the **latest** offline values into the **online** store
(`feast materialize`, SageMaker's dual write on `PutRecord`, Databricks
publishing to online tables). It's the reason the offline and online worlds
stay consistent: same values, two layouts. Freshness of the online store is
bounded by how often this runs (or by streaming ingestion).

## TTL (time to live)
"A feature value older than X is treated as missing." Without it, an entity
that went quiet six months ago is still served its stale `avg_amount_30d` as if
it were current. Applied in **both** the as-of join (tolerance) and the online
lookup — demo 3 shows the two paths agreeing.

## Registry
The metadata catalog: feature names, types, owners, descriptions, sources,
which models consume them, lineage. Boring, and for many organizations the
*actual* payoff.

## Feature service / training-set spec
A named bundle of features a *particular model* consumes
(`fraud_model_v3 = customer_txn_stats:* + merchant_risk:score`). Lets you
version "the feature set model X was trained on" and fetch exactly that at
serving time.

## Batch vs streaming vs on-demand features
| Kind | Computed | Example | Notes |
|---|---|---|---|
| **Batch** | On a schedule from the warehouse | `avg_amount_30d` refreshed nightly | Simplest; freshness = schedule |
| **Streaming** | Continuously from an event stream (Kafka/Kinesis + Flink/Spark) | `txns_last_10_min` | Freshest; hardest to keep identical to the training backfill |
| **On-demand** | At request time from request data | `amount / avg_amount_30d` | Combines a stored feature with a live input; must share code with training |

## The single most important principle: transform once
The transformation runs **once**; its output is written to **both** stores.
That's what removes skew. Products that only *store* features (Feast, SageMaker
FS) leave the transformation to you — the guarantee then depends on you
feeding the store from one pipeline. Products that also *own* the transformation
(Tecton, Databricks with feature functions, Hopsworks pipelines) can enforce it.

Next: [SageMaker vs Databricks vs Feast →](04-sagemaker-databricks-feast.md)

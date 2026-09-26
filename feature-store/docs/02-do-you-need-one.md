# 2. Do you actually need one? (the skeptic's page)

Your instinct that it "looks very unnecessary" is **often correct**. Feature
stores are one of the most over-adopted pieces of ML infrastructure. Here is
why the feeling exists and when it's wrong.

## A "feature store" is four things stapled together

| Component | What it does | You can build it with |
|---|---|---|
| **1. Registry / catalog** | Names, owners, schemas, lineage of features | A table + a wiki (or a data catalog) |
| **2. Offline store + point-in-time join** | Historical feature values, "as of" reads for training | A warehouse/lake table with an event-time column + `merge_asof`/`ASOF JOIN` |
| **3. Online store + sync** | Latest value per key, ms lookups; a job that keeps it fresh | Redis/DynamoDB + a scheduled job |
| **4. Transformation orchestration** | Compute features once (batch/stream), backfill | Spark/dbt/Flink + Airflow |

Vendors bundle all four behind one API. **You may need only one or two of
them** — and if so, you don't need "a feature store", you need a
timestamped table or a KV cache. The mini implementation in
[`demos/mini_feature_store.py`](../demos/mini_feature_store.py) is ~100 lines
because the *concepts* are small; the products are large because of scale,
durability, access control, streaming, and UI.

## Why it felt unnecessary in SageMaker and Databricks

Most tutorials and first uses have this shape: one table, one model, batch
scoring, one person. In that world:

- **No skew** — the same notebook computes features for train and predict.
- **No reuse problem** — you are the only consumer.
- **No online path** — nothing needs a 10 ms lookup.
- **Leakage** — real, but you can do the as-of join once by hand.

So what you experienced was the *API surface* (create a feature group, ingest,
query) **without the pain it prevents**. It looked like a table with extra
steps — because in that setup it *is* a table with extra steps. That isn't a
gap in your understanding; it's a mismatch between the demo and the problem.

Databricks makes this especially visible: a feature table there is a
Delta/Unity Catalog table with a primary key (and optionally a timestamp key).
There is very little "store" beyond the table — the value is the
lookup/point-in-time wiring and lineage on top of a table you'd have had anyway.

## Decision guide

**You probably do NOT need one if…**

- Scoring is **batch** (nightly/hourly, in the warehouse or a Spark job) and
  training and scoring can run the *same SQL/code path*.
- One model (or a couple) owned by one team.
- Features are simple columns from existing tables with little time-dependence.
- You have no online inference, or online inference only needs features already
  in the request.

→ Use a well-named, timestamped table plus one shared function/dbt model for
the feature logic. Add an as-of join helper. That's it.

**You probably DO want one when several of these hold…**

- **Online inference** with features that need aggregation over history
  (`txns_last_hour`, `avg_amount_30d`) — the serving-path re-implementation
  risk is real.
- **Many models sharing features** across teams (fraud, credit risk, marketing,
  recommendations all want `customer_activity_*`).
- **Time-dependent features at scale**, where leakage is a live risk and
  hand-rolled as-of joins keep getting written wrong.
- **Streaming features** (window aggregates over an event stream) that must be
  identical in the training backfill and the live path.
- **Governance needs**: who owns this feature, which models use it, what data
  does it derive from (lineage / audit).

## What it costs you

A feature store is not free even when the product is managed:

- **Another system to operate**: schemas, permissions, quotas, versioning.
- **Two storage systems to keep consistent** (offline + online), and
  freshness/latency SLOs on the sync between them.
- **Ingestion pipelines** you still write — the store doesn't compute features
  for you (Feast, SageMaker FS) or only partly does (Tecton/Databricks with
  their transformation layers).
- **Backfills and schema evolution** — changing a feature's definition means
  recomputing history and coordinating with every consumer model.
- **Lock-in to its data model** (entity + timestamp + features).
- **Cost**: online store capacity is always-on; SageMaker online store bills
  per read/write/storage, Redis/Dynamo-backed stores bill for provisioned
  capacity, etc.

## A useful test

Ask: **"If I deleted the feature store and used a plain table + one shared
function, what specific failure would I risk?"** If you can't name a concrete
skew, leakage, reuse, or latency problem you'd hit — you don't need it yet.
"Best practice" is not a reason. Being able to name the failure is.

Next: [Core concepts →](03-core-concepts.md)

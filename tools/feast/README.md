# Feast

**Category:** feature store

## What it is

Open-source feature store for machine learning. Originally built at Gojek,
now a Linux Foundation (LF AI & Data) project. Feast doesn't compute
features for you — it manages the definitions, storage, and retrieval of
features that some other pipeline already computed, so training and
serving can both pull the *same* feature values without re-implementing
the logic twice.

## What it's used for

The problem Feast exists to solve: a model is trained offline against a
big historical table, but served online against whatever the latest
values are for one entity at a time. Left alone, teams end up with two
separate implementations of "what is average_daily_trips" — one in the
training pipeline, one in the serving code — and those two
implementations drift apart over time (**training/serving skew**). Feast
gives both paths one shared definition.

Core concepts, all defined once in Python and registered with
`feast apply`:

- **Entity** — the thing features are attached to (e.g. `driver`, keyed on
  `driver_id`). The join key used to look features up.
- **FeatureView** — a named set of columns, sourced from some batch/stream
  source, that count as features for a given entity.
- **FeatureService** — a named bundle of features a specific model version
  requests as a unit, instead of spelling out individual feature names at
  every call site.
- **Offline store** — where historical feature values live for training
  (Parquet files locally; BigQuery/Snowflake/Redshift/Spark in production).
  Retrieval here is `get_historical_features()`, and it does a
  **point-in-time correct join**: for each `(entity_id, timestamp)` in your
  training set, it returns feature values as they were *at that exact
  timestamp* — not the latest values — which is what prevents label
  leakage when your labeled examples span different points in time.
- **Online store** — a low-latency key-value store for serving (SQLite
  locally; Redis/DynamoDB/Datastore in production). Retrieval here is
  `get_online_features()` — a point lookup by entity ID, no timestamp
  involved, the way a live prediction request works.
- **Registry** — metadata about everything above (a file locally; a
  SQL-backed registry for team/production use), so feature definitions are
  a shared, discoverable asset rather than scattered feature-engineering
  code.
- **Materialization** — the step (`materialize` / `materialize_incremental`)
  that copies the latest values per entity from the offline store into the
  online store. Nothing is servable online until this has run.

Newer Feast versions (0.6x) also add: **on-demand feature views** (transform
request-time inputs into features at lookup time), **push sources**
(stream fresh values directly into the online and/or offline store instead
of waiting on a batch job), and **label views** (managing mutable
human-provided labels, e.g. from an annotation UI, with conflict
resolution). The demo notebook in this repo sticks to the core
entity/feature-view/feature-service loop; these show up in `feast init`'s
full generated scaffold if you want to go further.

## Does it need a server?

Not for the core workflow. `FeatureStore` is a Python client — `apply`,
`get_historical_features`, `materialize`, and `get_online_features` all
run in-process against local files (registry) and a local online store
(SQLite), exactly like the demo notebook in this repo. Nothing to deploy
to use Feast from a notebook or a batch job.

Verified directly against the `feast-demo` project's `local` provider
(Feast 0.65.0) rather than assumed — each piece is a plain file or an
in-process library, no server involved:

- **Registry** (`feature_repo/data/registry.db`) — a flat binary file, not
  a database at all. It's Feast's serialized metadata (protobuf)
  describing entities/feature views/services; the client reads/writes it
  directly.
- **Online store** (`feature_repo/data/online_store.db`) — a real,
  literal **SQLite** database (`file` reports `SQLite 3.x database...`).
  One table per feature view, schema `entity_key BLOB, feature_name TEXT,
  value BLOB, event_ts, created_ts`, primary key on `(entity_key,
  feature_name)`, indexed on `entity_key` — a plain key-value point-lookup
  table, opened directly by the Python client.
- **Offline store** — `store.config.offline_store.type` resolves to
  **`dask`**, not plain pandas or DuckDB. `get_historical_features()`'s
  point-in-time join runs as in-process Dask DataFrame operations over the
  Parquet `FileSource`, no Dask cluster/scheduler required for this local
  default.

Two things become servers once you're past local development:

- **Feature server** — Feast can run its online-store lookups behind a
  REST/gRPC service (`feast serve`), so a separate application (not
  running Python/Feast itself) can fetch online features over the network
  at inference time. Deployable on Kubernetes/EKS via the community-
  maintained **Feast Operator** if the model-serving side isn't Python.
- **Registry server** — for a team sharing one registry instead of each
  person applying against their own local file, Feast can run a registry
  service (or you point everyone at a shared SQL-backed registry) so
  `feast apply` and reads go through one consistent source of truth.

## Alternatives

| Tool | Angle |
|---|---|
| **Tecton** | Managed, enterprise feature platform (started by Feast's original creators) — streaming feature pipelines, SLAs, governance built in |
| **Databricks Feature Store** (Unity Catalog) | Databricks-native — feature tables are just Delta tables with lineage back to the model via MLflow; zero extra infra if you're fully on Databricks, not portable off it |
| **AWS SageMaker Feature Store** | AWS-native, integrates with the rest of the SageMaker training/serving stack |
| **Vertex AI Feature Store** | GCP-native equivalent |
| **Hopsworks Feature Store** | Open-source, more opinionated end-to-end platform (also includes model registry, serving) |

Feast's niche is being open-source and platform-agnostic — it runs the
same way on a laptop, on Kubernetes, or against any of several cloud
offline/online store backends, rather than being tied to one cloud or one
platform's model-serving stack.

## Relationship with MLflow

Complementary, similar to the [Evidently/MLflow
relationship](../evidently/README.md#relationship-with-mlflow) already
documented in this repo: [MLflow](../mlflow/README.md) tracks experiments,
versions models, and serves them; Feast manages the features that go
*into* those models. A typical pipeline: pull training data via
`store.get_historical_features()`, train the model, log it with
`mlflow.log_model()`, then at serving time call
`store.get_online_features()` to build the input vector for that same
model. Neither tool does the other's job — MLflow has no concept of a
point-in-time join, and Feast has no experiment tracking or model
registry.

## Relationship with Evidently

Also complementary, and worth being explicit about because it's easy to
conflate "feature store" with "feature monitoring": Feast stores and
serves feature *values*; it does not compute drift statistics, run
tests, or compare distributions. If you want to know whether the features
Feast is serving have drifted from what a model was trained on, that's
still [Evidently](../evidently/README.md)'s job — Feast would typically be
the thing supplying both the `reference_data` (via a historical retrieval
against the training-time entity set) and `current_data` (via the latest
materialized online values, or a fresh historical pull) that Evidently
then compares. See
[`drift-detection-concepts.md`](../evidently/drift-detection-concepts.md)
for how that comparison actually works.

## Usage

Full runnable example, executed and verified:
[`projects/feast-demo/feast_quickstart.ipynb`](../../../projects/feast-demo/feast_quickstart.ipynb)
(setup notes in that project's
[README](../../../projects/feast-demo/README.md)). It walks through, in
order: `feast apply`, `get_historical_features` for training, training a
small model, `materialize_incremental`, `get_online_features` for serving,
and requesting a bundle of features via a `FeatureService`.

The feature definitions themselves live in
[`projects/feast-demo/feature_repo/feature_definitions.py`](../../../projects/feast-demo/feature_repo/feature_definitions.py)
— trimmed down from `feast init`'s full generated scaffold (which also
demonstrates on-demand feature views, push sources, and label views) to
just `Entity` + `FeatureView` + `FeatureService`, the part of the API most
real usage actually looks like.

**A second, real (not generic-tutorial) usage**:
[`projects/fraud-detection-xgboost/`](../../../projects/fraud-detection-xgboost/README.md)
uses Feast for leakage-safe, trailing per-IP "velocity" features (prior
transaction count/average amount/fraud count) — `ip_address` standing in
for a recurring entity in a dataset with no persistent customer ID. Trained
via `get_historical_features()`'s point-in-time join, served via
`get_online_features()`, and registered as a separate MLflow model so it's
directly A/B-comparable against the same project's non-Feast baseline. It
also surfaced a genuine, honestly-reported null result — see that
project's `FAQ.md` "Tier 2B" for why a row-count-based (not calendar-time)
train/test split caused the added features to measure as useless despite
being computed and served correctly.

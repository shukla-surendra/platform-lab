"""Feature definitions for the local lab. Concept map is in ../README.md.

  entities         customer, merchant
  feature views    customer_stats, merchant_stats        (batch, Postgres source -> Redis)
                   customer_stats_fresh                  (same data, PushSource -> push to online/offline)
  on-demand view   amount_vs_avg                         (stored feature + live request value)
  feature services model_a, model_b                      (what each model consumes)
"""
from datetime import timedelta

import pandas as pd
from feast import Entity, FeatureService, FeatureView, Field, PushSource, RequestSource, ValueType
from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import PostgreSQLSource
from feast.on_demand_feature_view import on_demand_feature_view
from feast.types import Float64, Int64

# ---- entities: the keys features are looked up by ----------------------------------
customer = Entity(name="customer", join_keys=["customer_id"], value_type=ValueType.INT64)
merchant = Entity(name="merchant", join_keys=["merchant_id"], value_type=ValueType.INT64)

# ---- sources: tables in the OFFLINE store (Postgres) --------------------------------
# event_timestamp = when the value was true; created = when it was written (ingestion time)
customer_source = PostgreSQLSource(
    name="customer_stats_source",
    query="SELECT * FROM customer_stats",
    timestamp_field="event_timestamp",
    created_timestamp_column="created",
)
merchant_source = PostgreSQLSource(
    name="merchant_stats_source",
    query="SELECT * FROM merchant_stats",
    timestamp_field="event_timestamp",
    created_timestamp_column="created",
)

# ---- feature views -------------------------------------------------------------------
customer_stats = FeatureView(
    name="customer_stats",
    entities=[customer],
    ttl=timedelta(days=14),  # a value older than this is treated as missing
    schema=[
        Field(name="avg_amount_30d", dtype=Float64),
        Field(name="txn_count_30d", dtype=Int64),
    ],
    online=True,
    source=customer_source,
    tags={"owner": "risk-team", "shared": "true"},
)

merchant_stats = FeatureView(
    name="merchant_stats",
    entities=[merchant],
    ttl=timedelta(days=14),
    schema=[
        Field(name="merch_avg_30d", dtype=Float64),
        Field(name="merch_txn_30d", dtype=Int64),
    ],
    online=True,
    source=merchant_source,
    tags={"owner": "risk-team", "shared": "true"},
)

# ---- push source: lets a stream/app write fresh values without a batch job -------------
customer_push = PushSource(name="customer_stats_push", batch_source=customer_source)

customer_stats_fresh = FeatureView(
    name="customer_stats_fresh",
    entities=[customer],
    ttl=timedelta(days=14),
    schema=[
        Field(name="avg_amount_30d", dtype=Float64),
        Field(name="txn_count_30d", dtype=Int64),
    ],
    online=True,
    source=customer_push,
    tags={"owner": "risk-team", "purpose": "push-demo"},
)

# ---- on-demand feature: needs the live request, so it cannot be precomputed ------------
txn_request = RequestSource(name="txn_request", schema=[Field(name="amount", dtype=Float64)])


@on_demand_feature_view(
    sources=[customer_stats, txn_request],
    schema=[Field(name="amount_vs_avg", dtype=Float64)],
)
def amount_vs_avg(inputs: pd.DataFrame) -> pd.DataFrame:
    """One function used for training AND serving, so it cannot skew."""
    out = pd.DataFrame()
    out["amount_vs_avg"] = inputs["amount"] / inputs["avg_amount_30d"]
    return out


# ---- feature services: each model declares exactly what it consumes ---------------------
model_a = FeatureService(name="model_a", features=[customer_stats, merchant_stats])
model_b = FeatureService(name="model_b", features=[customer_stats[["avg_amount_30d"]], amount_vs_avg])

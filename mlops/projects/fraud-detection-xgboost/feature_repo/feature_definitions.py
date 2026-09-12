"""Feast feature definitions for the IP-reuse "velocity" features.

Why IP address as the entity, not a customer/account ID: this dataset has
no persistent customer/account identifier at all (see ../README.md's
"About the dataset"). IP address is the only column that legitimately
recurs across transactions -- most of the 56,965 distinct IPs across
57,394 rows appear once, a few are reused many times (verified directly
against the raw file) -- which is exactly the shape Feast is built for: a
recurring entity whose features evolve over time, looked up point-in-time
-correctly for training and by latest value for serving. See
docs/tools/feast/README.md for the general concepts this trims down from.
"""

from datetime import timedelta

from feast import Entity, FeatureService, FeatureView, Field, FileSource
from feast.types import Float32, Int64
from feast.value_type import ValueType

ip = Entity(name="ip", join_keys=["ip_address"], value_type=ValueType.STRING)

ip_velocity_source = FileSource(
    name="ip_velocity_stats_source",
    path="data/ip_velocity_stats.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created",
)

ip_velocity_stats_fv = FeatureView(
    name="ip_velocity_stats",
    entities=[ip],
    # Generous TTL: this is a static historical dump, not a live stream --
    # there's no "expiry" concept for it, same reasoning as feast-demo's
    # driver_hourly_stats view.
    ttl=timedelta(days=3650),
    schema=[
        Field(name="ip_prior_txn_count", dtype=Int64),
        Field(name="ip_prior_avg_amount", dtype=Float32),
        Field(name="ip_prior_fraud_count", dtype=Int64),
    ],
    online=True,
    source=ip_velocity_source,
    tags={"team": "fraud_detection"},
)

fraud_ip_velocity_v1 = FeatureService(
    name="fraud_ip_velocity_v1",
    features=[ip_velocity_stats_fv],
)

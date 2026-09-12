"""
Focused Feast feature definitions for the demo notebook.

Trimmed down from `feast init`'s generated scaffold (which also shows off
on-demand feature views, push sources, feature service versioning, and
label views) to just the core loop most real usage looks like: an entity,
a batch source, a feature view, and a feature service grouping them for a
model version. See docs/tools/feast/README.md for the other concepts.
"""

from datetime import timedelta

from feast import Entity, FeatureService, FeatureView, Field, FileSource
from feast.types import Float32, Int64
from feast.value_type import ValueType

driver = Entity(name="driver", join_keys=["driver_id"], value_type=ValueType.INT64)

driver_stats_source = FileSource(
    name="driver_hourly_stats_source",
    path="data/driver_stats.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created",
)

driver_stats_fv = FeatureView(
    name="driver_hourly_stats",
    entities=[driver],
    ttl=timedelta(days=3650),  # generous TTL so the bundled sample data stays servable
    schema=[
        Field(name="conv_rate", dtype=Float32),
        Field(name="acc_rate", dtype=Float32),
        Field(name="avg_daily_trips", dtype=Int64),
    ],
    online=True,
    source=driver_stats_source,
    tags={"team": "driver_performance"},
)

driver_activity_v1 = FeatureService(
    name="driver_activity_v1",
    features=[driver_stats_fv],
)

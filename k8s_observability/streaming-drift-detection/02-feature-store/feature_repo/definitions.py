"""Feast repo definitions for streaming-drift-detection.

One entity (the event producer), one feature view backed by a PushSource —
so the same feature definition serves both paths this pipeline needs:

  - offline (FileSource `amount_source`, backfilled from the seed parquet at
    build time) — what 03-drift-engine's batch mode reads as its reference
    window, and what a real training job would read for point-in-time-correct
    historical features.
  - online (the PushSource itself) — 03-drift-engine's streaming mode calls
    the feature server's /push endpoint per Kafka event it consumes from
    01-ingestion, and reads back via get_online_features for its sliding
    window. Same transformation, same schema, both paths — this is the
    train/serve consistency Feast exists to guarantee.
"""

from datetime import timedelta

from feast import Entity, FeatureView, Field, FileSource, PushSource
from feast.types import Float32, String

producer = Entity(name="producer_id", join_keys=["producer_id"])

amount_source = FileSource(
    name="amount_source",
    path="data/amount_stats.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created",
)

amount_push_source = PushSource(
    name="amount_push_source",
    batch_source=amount_source,
)

producer_amount_stats = FeatureView(
    name="producer_amount_stats",
    entities=[producer],
    ttl=timedelta(days=1),
    schema=[
        Field(name="amount", dtype=Float32),
        Field(name="category", dtype=String),
    ],
    online=True,
    source=amount_push_source,
)

"""Generates the tiny offline-store seed Feast needs at `feast apply` /
materialize time. Not committed as a binary — regenerated at image build
time instead (see ../Dockerfile), same reasoning as this project's other
stages: nothing binary checked into git that a script can produce instead.
"""

import os
from datetime import datetime, timedelta

import pandas as pd

os.makedirs("data", exist_ok=True)

now = datetime.utcnow()
rows = []
for i in range(1000):
    rows.append(
        {
            "producer_id": f"producer-{i % 100}",
            "amount": 50.0,
            "category": "a",
            "event_timestamp": now - timedelta(minutes=1000 - i),
            "created": now,
        }
    )

pd.DataFrame(rows).to_parquet("data/amount_stats.parquet")
print("wrote data/amount_stats.parquet")

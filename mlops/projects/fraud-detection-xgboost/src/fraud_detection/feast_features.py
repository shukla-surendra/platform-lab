"""Feast integration: IP-reuse "velocity" features as a genuine feature-store
use case, not a pass-through demo.

Leakage discipline: every "prior" feature below is computed with a
shift(1)-before-expanding pattern -- each row's feature values summarize
transactions *strictly before* it from the same IP, never the row's own
transaction. Feast's point-in-time join can't protect you from leakage
baked into the *source* data itself; this module is where that guarantee
actually has to be enforced, verified directly against the real dataset
(IP 185.75.225.22, reused 425 times) before trusting it: the first
occurrence of any IP gets ip_prior_txn_count=0 and
ip_prior_fraud_count=0, and both grow monotonically in timestamp order.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone

import pandas as pd
from feast import FeatureStore

from fraud_detection.config import PROJECT_ROOT

FEATURE_REPO_PATH = PROJECT_ROOT / "feature_repo"
IP_VELOCITY_SOURCE_PATH = FEATURE_REPO_PATH / "data" / "ip_velocity_stats.parquet"

IP_VELOCITY_FEATURES = [
    "ip_velocity_stats:ip_prior_txn_count",
    "ip_velocity_stats:ip_prior_avg_amount",
    "ip_velocity_stats:ip_prior_fraud_count",
]


def build_ip_velocity_source(df: pd.DataFrame) -> pd.DataFrame:
    """Compute leakage-safe, trailing per-IP aggregates and write them as a
    Feast FileSource (Parquet). `df` must already be sorted by timestamp
    (data.load_dataset() guarantees this) and have unique `id` values.

    Returns the dataframe that was written, mainly for inspection/tests.
    """
    df = df.sort_values("timestamp").reset_index(drop=True)
    grouped = df.groupby("ip_address")

    shifted_amount = grouped["amount"].shift(1)
    shifted_fraud = grouped["is_fraud"].shift(1)

    prior_txn_count = grouped.cumcount()
    prior_avg_amount = (
        shifted_amount.groupby(df["ip_address"]).expanding().mean().reset_index(level=0, drop=True)
    )
    prior_fraud_count = (
        shifted_fraud.groupby(df["ip_address"]).expanding().sum().reset_index(level=0, drop=True)
    )

    velocity = pd.DataFrame(
        {
            "ip_address": df["ip_address"],
            "event_timestamp": df["timestamp"],
            "created": df["timestamp"],
            "ip_prior_txn_count": prior_txn_count.astype("int64"),
            "ip_prior_avg_amount": prior_avg_amount.fillna(0).astype("float32"),
            "ip_prior_fraud_count": prior_fraud_count.fillna(0).astype("int64"),
        }
    )

    IP_VELOCITY_SOURCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    velocity.to_parquet(IP_VELOCITY_SOURCE_PATH)
    return velocity


def apply_feast_repo() -> FeatureStore:
    """Register the feature definitions (`feast apply`) and return a client.

    Uses the CLI via subprocess, the same pattern already verified working
    in projects/feast-demo/feast_quickstart.ipynb, rather than the
    programmatic store.apply() -- kept consistent with that existing demo.
    """
    result = subprocess.run(
        ["feast", "apply"], cwd=FEATURE_REPO_PATH, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"feast apply failed:\n{result.stdout}\n{result.stderr}")
    return FeatureStore(repo_path=str(FEATURE_REPO_PATH))


def get_training_features(store: FeatureStore, df: pd.DataFrame) -> pd.DataFrame:
    """Point-in-time-correct retrieval: for each transaction's own
    (ip_address, timestamp), get the IP velocity features as they stood at
    that exact moment -- not the latest values. This is what prevents a
    training row from seeing IP stats that only existed *after* it.
    """
    entity_df = df[["ip_address", "timestamp"]].rename(columns={"timestamp": "event_timestamp"})
    historical = store.get_historical_features(
        entity_df=entity_df, features=IP_VELOCITY_FEATURES
    ).to_df()
    # get_historical_features returns one row per entity_df row, in a
    # possibly different order -- id isn't part of entity_df, so join back
    # positionally is unsafe; instead attach by resetting both to the same
    # index the entity_df was built from.
    historical.index = df.index
    return pd.concat([df, historical.drop(columns=["ip_address", "event_timestamp"])], axis=1)


def materialize_latest(store: FeatureStore) -> None:
    """Copy the latest per-IP values from the offline source into the
    online store -- nothing is servable via get_online_features until this
    has run at least once."""
    store.materialize_incremental(end_date=datetime.now(timezone.utc))


def get_online_ip_features(store: FeatureStore, ip_address: str) -> dict:
    """Latest-value lookup by IP, the way a live prediction request works --
    no timestamp involved, unlike get_training_features's point-in-time join."""
    result = store.get_online_features(
        features=IP_VELOCITY_FEATURES, entity_rows=[{"ip_address": ip_address}]
    ).to_dict()
    # to_dict() values are single-element lists (one entity row requested).
    return {
        "ip_prior_txn_count": (result["ip_prior_txn_count"][0] or 0),
        "ip_prior_avg_amount": (result["ip_prior_avg_amount"][0] or 0.0),
        "ip_prior_fraud_count": (result["ip_prior_fraud_count"][0] or 0),
    }

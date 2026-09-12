"""Unit tests for the IP-velocity feature computation -- the leakage-safety
guarantee (Tier 2/8 of FAQ.md) is exactly what these assert, on tiny
synthetic data, no Feast repo/apply/materialize involved."""

import pandas as pd
import pytest

from fraud_detection.feast_features import build_ip_velocity_source


@pytest.fixture(autouse=True)
def _isolate_source_path(tmp_path, monkeypatch):
    """Every test in this file writes to a throwaway path, never the real
    feature_repo/data/ip_velocity_stats.parquet a real run might depend on."""
    monkeypatch.setattr(
        "fraud_detection.feast_features.IP_VELOCITY_SOURCE_PATH",
        tmp_path / "ip_velocity_stats.parquet",
    )


def test_first_occurrence_of_an_ip_has_zero_prior_stats():
    df = pd.DataFrame(
        {
            "ip_address": ["1.1.1.1", "2.2.2.2", "1.1.1.1"],
            "timestamp": pd.to_datetime(
                ["2026-01-01 00:00", "2026-01-01 00:01", "2026-01-01 00:02"]
            ),
            "amount": [100.0, 50.0, 200.0],
            "is_fraud": [1, 0, 0],
        }
    )

    velocity = build_ip_velocity_source(df)
    first_ip1 = velocity[velocity["ip_address"] == "1.1.1.1"].iloc[0]
    assert first_ip1["ip_prior_txn_count"] == 0
    assert first_ip1["ip_prior_avg_amount"] == 0
    assert first_ip1["ip_prior_fraud_count"] == 0


def test_second_occurrence_sees_only_the_prior_transaction_not_its_own():
    df = pd.DataFrame(
        {
            "ip_address": ["1.1.1.1", "1.1.1.1"],
            "timestamp": pd.to_datetime(["2026-01-01 00:00", "2026-01-01 00:02"]),
            "amount": [100.0, 200.0],
            "is_fraud": [1, 0],
        }
    )

    velocity = build_ip_velocity_source(df)
    second = velocity[velocity["ip_address"] == "1.1.1.1"].iloc[1]

    # Must reflect the FIRST transaction (amount=100, is_fraud=1) only --
    # never the second row's own amount=200/is_fraud=0.
    assert second["ip_prior_txn_count"] == 1
    assert second["ip_prior_avg_amount"] == 100.0
    assert second["ip_prior_fraud_count"] == 1


def test_prior_txn_count_is_monotonically_increasing_per_ip():
    n = 5
    df = pd.DataFrame(
        {
            "ip_address": ["9.9.9.9"] * n,
            "timestamp": pd.date_range("2026-01-01", periods=n, freq="min"),
            "amount": [10.0 * i for i in range(n)],
            "is_fraud": [0] * n,
        }
    )

    velocity = build_ip_velocity_source(df)
    counts = velocity.sort_values("event_timestamp")["ip_prior_txn_count"].tolist()
    assert counts == list(range(n))

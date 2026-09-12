"""Unit tests for feature engineering -- pure in-memory data, no download."""

import pandas as pd

from fraud_detection.features import build_feature_matrix, temporal_train_test_split


def _sample_df(n: int = 10) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": range(n),
            "transaction_id": [f"t{i}" for i in range(n)],
            "amount": [100.0 + i for i in range(n)],
            "time_value": list(range(n)),
            **{f"v{i}": [0.1 * j for j in range(n)] for i in range(1, 29)},
            "is_fraud": [1 if i % 5 == 0 else 0 for i in range(n)],
            "fraud_probability": [0.9 if i % 5 == 0 else 0.1 for i in range(n)],
            "risk_level": ["HIGH" if i % 5 == 0 else "LOW" for i in range(n)],
            "confidence": [90.0] * n,
            "recommendation": ["BLOCK" if i % 5 == 0 else "ALLOW" for i in range(n)],
            "timestamp": pd.date_range("2026-01-01", periods=n, freq="h"),
            "test_date": [None] * n,
            "ip_address": ["1.2.3.4"] * n,
        }
    )


def test_build_feature_matrix_drops_leakage_and_id_columns():
    df = _sample_df()
    X, y = build_feature_matrix(df)

    leaked = {"fraud_probability", "risk_level", "confidence", "recommendation"}
    identifiers = {"id", "transaction_id", "ip_address", "test_date", "timestamp"}
    assert not leaked & set(X.columns)
    assert not identifiers & set(X.columns)
    assert "is_fraud" not in X.columns
    assert list(y) == list(df["is_fraud"])


def test_build_feature_matrix_keeps_v_columns_and_amount():
    df = _sample_df()
    X, _ = build_feature_matrix(df)

    assert "amount" in X.columns
    assert "time_value" in X.columns
    assert all(f"v{i}" in X.columns for i in range(1, 29))


def test_temporal_train_test_split_is_chronological_and_disjoint():
    df = _sample_df(n=10)
    train_df, test_df = temporal_train_test_split(df, train_frac=0.7)

    assert len(train_df) == 7
    assert len(test_df) == 3
    assert train_df["timestamp"].max() < test_df["timestamp"].min()

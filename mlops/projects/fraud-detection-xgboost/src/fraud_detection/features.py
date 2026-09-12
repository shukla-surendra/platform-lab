"""Turn the raw dataset into a leakage-free feature matrix, and a
chronological (not random) train/test split."""

from __future__ import annotations

import pandas as pd

from fraud_detection.config import (
    ID_COLUMNS,
    LEAKAGE_COLUMNS,
    TARGET_COLUMN,
    TIMESTAMP_COLUMN,
)


def build_feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Split a raw dataframe into features (X) and label (y).

    Drops LEAKAGE_COLUMNS (the source system's own fraud-probability/
    risk_level/confidence/recommendation outputs -- these are downstream of
    is_fraud, not independent signal a real-world model would have at
    prediction time) plus ID_COLUMNS and the timestamp (identifiers, not
    features).
    """
    drop_cols = [
        c
        for c in (*ID_COLUMNS, *LEAKAGE_COLUMNS, TIMESTAMP_COLUMN, TARGET_COLUMN)
        if c in df.columns
    ]
    X = df.drop(columns=drop_cols)
    y = df[TARGET_COLUMN]
    return X, y


def temporal_train_test_split(
    df: pd.DataFrame, train_frac: float = 0.7
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split chronologically by position, not randomly.

    `df` must already be sorted by timestamp (load_dataset() guarantees
    this). A random split would let "future" transactions leak into
    training and would understate real drift between the reference period
    and current traffic -- exactly the distinction monitor.py's reference
    vs. current split relies on.
    """
    split_idx = int(len(df) * train_frac)
    return df.iloc[:split_idx].copy(), df.iloc[split_idx:].copy()

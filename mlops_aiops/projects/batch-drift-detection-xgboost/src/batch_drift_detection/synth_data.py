"""Synthetic data generation: one fixed base dataset, split into a
`reference` set (what the model trains on) and a `holdout` pool (never
seen during training -- later drawn from by generate_drift.py to build
"new" batches, clean or drifted, the same way a real pipeline would
receive fresh production data it never trained on).

Kept in its own module, not inlined in train.py, because generate_drift.py
needs the exact same holdout pool train.py set aside -- persisting it once
here (make_or_load_split) is what makes "train now, generate drifted
batches later, in a separate run" actually work, rather than each script
regenerating its own random split and silently drifting apart from the
model's real training data.
"""

from __future__ import annotations

import pandas as pd
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

from batch_drift_detection.config import (
    CLASS_SEP,
    DATA_DIR,
    FEATURE_NAMES,
    HOLDOUT_FRACTION,
    HOLDOUT_PATH,
    N_FEATURES,
    N_INFORMATIVE,
    N_SAMPLES,
    RANDOM_SEED,
    TARGET_COLUMN,
)


def _make_base_dataset() -> pd.DataFrame:
    X, y = make_classification(
        n_samples=N_SAMPLES,
        n_features=N_FEATURES,
        n_informative=N_INFORMATIVE,
        n_classes=2,
        class_sep=CLASS_SEP,
        random_state=RANDOM_SEED,
    )
    df = pd.DataFrame(X, columns=FEATURE_NAMES)
    df[TARGET_COLUMN] = y
    return df


def make_or_load_split(force: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (reference_df, holdout_df).

    On first call, generates the base dataset and splits it; the holdout
    half is persisted to HOLDOUT_PATH so later, separate runs of
    generate_drift.py draw from the exact same pool instead of a fresh
    random sample. The reference half is NOT persisted here -- train.py
    persists it only after attaching the model's own predictions
    (REFERENCE_PATH), since an unscored reference set isn't useful to
    monitor.py on its own.
    """
    if HOLDOUT_PATH.exists() and not force:
        holdout_df = pd.read_parquet(HOLDOUT_PATH)
        # Reference isn't persisted pre-scoring, so it's regenerated with the
        # same seed/split -- deterministic, so this reproduces byte-identical
        # rows to what produced the persisted holdout.
        base_df = _make_base_dataset()
        reference_df, _ = train_test_split(
            base_df, test_size=HOLDOUT_FRACTION, random_state=RANDOM_SEED, stratify=base_df[TARGET_COLUMN]
        )
        return reference_df.reset_index(drop=True), holdout_df

    base_df = _make_base_dataset()
    reference_df, holdout_df = train_test_split(
        base_df, test_size=HOLDOUT_FRACTION, random_state=RANDOM_SEED, stratify=base_df[TARGET_COLUMN]
    )
    reference_df = reference_df.reset_index(drop=True)
    holdout_df = holdout_df.reset_index(drop=True)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    holdout_df.to_parquet(HOLDOUT_PATH)

    return reference_df, holdout_df

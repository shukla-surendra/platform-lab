import numpy as np
import pandas as pd

from batch_drift_detection.config import TARGET_COLUMN
from batch_drift_detection.generate_drift import inject_concept_drift, inject_data_drift, sample_batch
from batch_drift_detection.synth_data import make_or_load_split


def test_inject_data_drift_shifts_feature_leaves_rest_untouched():
    _, holdout_df = make_or_load_split()
    batch = sample_batch(holdout_df, n=200, seed=1)
    drifted = inject_data_drift(batch, feature="feature_0", scale=1.8, shift=3.0)

    assert not np.allclose(drifted["feature_0"], batch["feature_0"])
    other_cols = [c for c in batch.columns if c != "feature_0"]
    pd.testing.assert_frame_equal(drifted[other_cols], batch[other_cols])


def test_inject_concept_drift_flips_target_for_slice_leaves_features():
    _, holdout_df = make_or_load_split()
    batch = sample_batch(holdout_df, n=200, seed=1)
    drifted = inject_concept_drift(batch, slice_feature="feature_1")

    feature_cols = [c for c in batch.columns if c != TARGET_COLUMN]
    pd.testing.assert_frame_equal(drifted[feature_cols], batch[feature_cols])
    assert not drifted[TARGET_COLUMN].equals(batch[TARGET_COLUMN])

    median = batch["feature_1"].median()
    above_median = batch["feature_1"] > median
    assert (drifted.loc[above_median, TARGET_COLUMN] == 1 - batch.loc[above_median, TARGET_COLUMN]).all()
    assert (drifted.loc[~above_median, TARGET_COLUMN] == batch.loc[~above_median, TARGET_COLUMN]).all()

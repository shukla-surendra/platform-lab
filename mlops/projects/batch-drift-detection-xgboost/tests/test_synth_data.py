from batch_drift_detection.config import FEATURE_NAMES, N_SAMPLES, TARGET_COLUMN
from batch_drift_detection.synth_data import make_or_load_split


def test_split_shapes_and_columns():
    reference_df, holdout_df = make_or_load_split(force=True)

    assert len(reference_df) + len(holdout_df) == N_SAMPLES
    for df in (reference_df, holdout_df):
        for col in [*FEATURE_NAMES, TARGET_COLUMN]:
            assert col in df.columns
    assert set(reference_df[TARGET_COLUMN].unique()) <= {0, 1}


def test_split_is_deterministic():
    reference_df, holdout_df = make_or_load_split(force=True)
    reference_df2, holdout_df2 = make_or_load_split()  # force=False, loads persisted holdout

    assert holdout_df.equals(holdout_df2)
    assert reference_df.equals(reference_df2)

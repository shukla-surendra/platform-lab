"""Smoke test for the training loop -- runs the real (small, synthetic)
pipeline end to end. No mocking of the data itself needed, unlike
fraud-detection-xgboost's tests (that project downloads a real external
dataset; this one's "dataset" is make_classification, already synthetic
and network-free). Only MLflow's tracking URI is redirected, so test runs
don't write into this project's real mlflow.db.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from batch_drift_detection.config import FEATURE_NAMES, MODEL_PATH, PREDICTION_COLUMN, REFERENCE_PATH


@pytest.fixture()
def tmp_mlflow_uri(tmp_path):
    return f"sqlite:///{tmp_path / 'mlflow.db'}"


def test_train_runs_end_to_end(tmp_mlflow_uri):
    with patch("batch_drift_detection.train.MLFLOW_TRACKING_URI", tmp_mlflow_uri):
        from batch_drift_detection.train import train

        model = train()

    assert MODEL_PATH.exists()
    assert REFERENCE_PATH.exists()

    reference_df = pd.read_parquet(REFERENCE_PATH)
    assert PREDICTION_COLUMN in reference_df.columns
    assert set(reference_df[PREDICTION_COLUMN].unique()) <= {0, 1}

    preds = model.predict_proba(reference_df[FEATURE_NAMES])[:, 1]
    assert ((preds >= 0) & (preds <= 1)).all()

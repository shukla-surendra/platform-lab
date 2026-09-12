"""Smoke test for the training loop -- tiny synthetic data, no network call,
no dependency on the real (imbalanced, 21MB) dataset."""

from unittest.mock import patch

import mlflow
import numpy as np
import pandas as pd
import pytest


def _synthetic_df(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    is_fraud = (rng.random(n) < 0.1).astype(int)
    df = pd.DataFrame(
        {
            "id": range(n),
            "transaction_id": [f"t{i}" for i in range(n)],
            "amount": rng.uniform(1, 500, n),
            "time_value": range(n),
            **{f"v{i}": rng.normal(0, 1, n) for i in range(1, 29)},
            "is_fraud": is_fraud,
            "fraud_probability": is_fraud * 90.0,
            "risk_level": np.where(is_fraud, "HIGH", "LOW"),
            "confidence": 80.0,
            "recommendation": np.where(is_fraud, "BLOCK", "ALLOW"),
            "timestamp": pd.date_range("2026-01-01", periods=n, freq="h"),
            "test_date": None,
            "ip_address": "1.2.3.4",
        }
    )
    return df


@pytest.fixture()
def tmp_mlflow_uri(tmp_path):
    return f"sqlite:///{tmp_path / 'mlflow.db'}"


def test_train_runs_end_to_end_on_synthetic_data(tmp_mlflow_uri):
    with (
        patch("fraud_detection.train.load_dataset", return_value=_synthetic_df()),
        patch("fraud_detection.train.MLFLOW_TRACKING_URI", tmp_mlflow_uri),
    ):
        from fraud_detection.train import train

        run, model, (X_test, y_test) = train(train_frac=0.7)

        # run.info is a snapshot taken at start_run() and is never refreshed
        # on the returned object, so it always reads "RUNNING" here even
        # though the run has genuinely finished by this point (verified via
        # a real run: MLflow's own log output shows the model registered
        # successfully) -- mlflow.get_run() re-fetches from the tracking
        # store and reflects the real, current status.
        assert mlflow.get_run(run.info.run_id).info.status == "FINISHED"
        assert len(X_test) == 60
        preds = model.predict_proba(X_test)[:, 1]
        assert len(preds) == len(y_test)
        assert ((preds >= 0) & (preds <= 1)).all()

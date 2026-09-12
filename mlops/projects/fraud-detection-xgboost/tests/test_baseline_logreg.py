"""Unit tests for the ColumnTransformer-based preprocessing pipeline --
pure in-memory data, no MLflow run, no download."""

import numpy as np
import pandas as pd

from fraud_detection.train_baseline_logreg import build_pipeline


def test_log1p_applied_to_amount_only():
    X = pd.DataFrame(
        {
            "amount": [1.0, 10.0, 100.0],
            "v1": [5.0, 5.0, 5.0],
            "v2": [-3.0, -3.0, -3.0],
        }
    )
    pipeline = build_pipeline(list(X.columns))
    transformed = pipeline.named_steps["preprocess"].fit_transform(X)

    # v1/v2 are constant -> StandardScaler maps them to 0 everywhere.
    # amount is log1p'd *then* scaled -- not constant, so its column must
    # have nonzero variance, unlike the untouched-shape v1/v2 columns.
    assert np.allclose(transformed[:, 1], 0.0)  # v1 (scale_rest)
    assert np.allclose(transformed[:, 2], 0.0)  # v2 (scale_rest)
    assert not np.allclose(transformed[:, 0], transformed[0, 0])  # amount varies


def test_pipeline_predict_proba_runs_on_tiny_synthetic_data():
    rng = np.random.default_rng(0)
    n = 60
    X = pd.DataFrame(
        {
            "amount": rng.uniform(1, 5000, n),
            "time_value": range(n),
            **{f"v{i}": rng.normal(0, 1, n) for i in range(1, 5)},
        }
    )
    y = pd.Series((rng.random(n) < 0.2).astype(int))

    pipeline = build_pipeline(list(X.columns))
    pipeline.fit(X, y)
    proba = pipeline.predict_proba(X)[:, 1]

    assert len(proba) == n
    assert ((proba >= 0) & (proba <= 1)).all()

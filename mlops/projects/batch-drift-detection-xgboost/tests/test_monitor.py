"""End-to-end proof that this project's own code reproduces the same
phenomenon ../../evidently-monitoring-demo/drift_types_with_evidently.ipynb
demonstrates: DataDriftPreset catches the data-drift batch but not the
concept-drift one; ClassificationPreset shows the opposite pattern.
"""

from unittest.mock import patch

import pytest

from batch_drift_detection.config import MODEL_PATH
from batch_drift_detection.generate_drift import inject_concept_drift, inject_data_drift, sample_batch
from batch_drift_detection.synth_data import make_or_load_split


@pytest.fixture()
def tmp_mlflow_uri(tmp_path):
    return f"sqlite:///{tmp_path / 'mlflow.db'}"


def _ensure_trained(tmp_mlflow_uri):
    if not MODEL_PATH.exists():
        with patch("batch_drift_detection.train.MLFLOW_TRACKING_URI", tmp_mlflow_uri):
            from batch_drift_detection.train import train

            train()


def test_data_drift_batch_flags_drift_without_collapsing_accuracy(tmp_mlflow_uri, tmp_path):
    _ensure_trained(tmp_mlflow_uri)
    _, holdout_df = make_or_load_split()
    batch = inject_data_drift(sample_batch(holdout_df, n=500, seed=11))

    with (
        patch("batch_drift_detection.monitor.MLFLOW_TRACKING_URI", tmp_mlflow_uri),
        patch("batch_drift_detection.monitor.REPORTS_DIR", tmp_path),
    ):
        from batch_drift_detection.monitor import run_monitor

        summary = run_monitor(batch, name="test_data_drift")

    assert summary["n_drifted_columns"] >= 1
    assert abs(summary["reference_accuracy"] - summary["current_accuracy"]) < 0.15


def test_concept_drift_batch_collapses_accuracy_without_flagging_drift(tmp_mlflow_uri, tmp_path):
    _ensure_trained(tmp_mlflow_uri)
    _, holdout_df = make_or_load_split()
    batch = inject_concept_drift(sample_batch(holdout_df, n=500, seed=12))

    with (
        patch("batch_drift_detection.monitor.MLFLOW_TRACKING_URI", tmp_mlflow_uri),
        patch("batch_drift_detection.monitor.REPORTS_DIR", tmp_path),
    ):
        from batch_drift_detection.monitor import run_monitor

        summary = run_monitor(batch, name="test_concept_drift")

    assert summary["n_drifted_columns"] == 0
    assert summary["current_accuracy"] < summary["reference_accuracy"] - 0.2

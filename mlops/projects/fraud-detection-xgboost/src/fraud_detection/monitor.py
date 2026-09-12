"""Drift monitoring: compare the training-period reference data against the
held-out "current" period using Evidently, and log the result to MLflow.

Reference = the training split, current = the test split -- both already
chronologically separated by features.temporal_train_test_split, so this is
a genuine "did the world change since training" comparison, not an
arbitrary random resample.

If EVIDENTLY_SERVER_URL is set (e.g. pointing at the k8n_mlops/evidently_stack
Helm release), the report is also pushed there via RemoteWorkspace -- see
mlops_aiops/docs/tools/evidently/README.md and k8n_mlops/README.md for that
piece. Unset, this only logs locally to MLflow -- no server required.
"""

from __future__ import annotations

import os

import mlflow
from evidently import DataDefinition, Dataset, Report
from evidently.presets import DataDriftPreset
from evidently.ui.workspace import RemoteWorkspace

from fraud_detection.config import (
    MLFLOW_EXPERIMENT_NAME,
    MLFLOW_TRACKING_URI,
    PROJECT_ROOT,
)
from fraud_detection.data import load_dataset
from fraud_detection.features import build_feature_matrix, temporal_train_test_split


def run_drift_report(train_frac: float = 0.7):
    df = load_dataset()
    train_df, test_df = temporal_train_test_split(df, train_frac=train_frac)

    X_train, _ = build_feature_matrix(train_df)
    X_test, _ = build_feature_matrix(test_df)

    reference = Dataset.from_pandas(X_train, data_definition=DataDefinition())
    current = Dataset.from_pandas(X_test, data_definition=DataDefinition())

    report = Report([DataDriftPreset()])
    snapshot = report.run(current, reference)

    report_path = PROJECT_ROOT / "evidently_report.html"
    snapshot.save_html(str(report_path))

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
    with mlflow.start_run(run_name="drift-check"):
        mlflow.log_artifact(str(report_path))

    server_url = os.environ.get("EVIDENTLY_SERVER_URL")
    if server_url:
        workspace = RemoteWorkspace(server_url)
        project = workspace.create_project("fraud-detection-xgboost")
        workspace.add_run(project.id, snapshot, include_data=False)
        print(f"Pushed drift report to {server_url} (project {project.id})")
    else:
        print(f"EVIDENTLY_SERVER_URL not set -- report saved locally to {report_path}")

    return snapshot


if __name__ == "__main__":
    run_drift_report()

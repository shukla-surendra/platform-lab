"""Run Evidently against a current batch vs. the persisted reference —
the "use Evidently to detect data drift and concept drift, both" step.

Every batch generate_drift.py produces (clean/data/concept) keeps the
`target` column, so this always runs BOTH checks in one report, the same
way evidently_xgboost_monitoring.ipynb does when ground truth happens to
already be available:

  - DataDriftPreset  -- covariate/feature drift. Flags the shifted feature
    on a `data`-kind batch; stays quiet on a `concept`-kind batch, since
    concept drift never touches any feature value.
  - ClassificationPreset -- reference vs. current accuracy (and the full
    confusion-matrix/precision/recall suite in the saved HTML). Roughly
    unchanged on a `data`-kind batch (the model still does fine on shifted-
    but-not-relabeled inputs unless the shift pushes far outside the
    training range); collapses on a `concept`-kind batch, since the
    labeling rule itself changed underneath the model's now-outdated
    predictions.

Uses evidently.legacy.* deliberately, not the newer top-level
evidently.Report/presets API — ClassificationPreset + ColumnMapping is the
combination already proven working in
../../evidently-monitoring-demo/drift_types_with_evidently.ipynb; the new
API's preset surface doesn't have a verified equivalent in this repo yet.
Requires NLTK_DISABLE_IMPORT_SECURITY=1 (see this project's README) for the
same NLTK-false-positive reason documented in
../../../docs/tools/evidently/README.md.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import mlflow
import pandas as pd

from evidently.legacy.metric_preset import ClassificationPreset, DataDriftPreset
from evidently.legacy.pipeline.column_mapping import ColumnMapping
from evidently.legacy.report import Report

from batch_drift_detection.config import (
    FEATURE_NAMES,
    MLFLOW_EXPERIMENT_NAME,
    MLFLOW_TRACKING_URI,
    PREDICTION_COLUMN,
    REFERENCE_PATH,
    REPORTS_DIR,
    TARGET_COLUMN,
)
from batch_drift_detection.predict import predict as score_batch


def _find_result(metrics: list[dict], required_keys: list[str]) -> dict:
    """First metric['result'] dict containing all required_keys — a scan
    rather than a hardcoded index, since DataDriftPreset expands into a
    variable number of sub-metrics ahead of ClassificationPreset's own
    entries in the combined metrics list, and only the *shape* of each
    preset's own result dict (not its position) is what's actually been
    verified against a real run.
    """
    for metric in metrics:
        result = metric.get("result", {})
        if all(key in result for key in required_keys):
            return result
    raise KeyError(f"no metric result containing all of {required_keys} in: {[m.get('metric') for m in metrics]}")


def run_monitor(batch_df: pd.DataFrame, name: str) -> dict:
    if not REFERENCE_PATH.exists():
        raise FileNotFoundError(f"No scored reference at {REFERENCE_PATH} -- run `train.py` first.")
    reference_df = pd.read_parquet(REFERENCE_PATH)

    if PREDICTION_COLUMN not in batch_df.columns:
        batch_df = score_batch(batch_df)

    column_mapping = ColumnMapping(
        target=TARGET_COLUMN,
        prediction=PREDICTION_COLUMN,
        numerical_features=FEATURE_NAMES,
    )

    report = Report(metrics=[DataDriftPreset(), ClassificationPreset()])
    report.run(reference_data=reference_df, current_data=batch_df, column_mapping=column_mapping)

    result = report.as_dict()
    drift_result = _find_result(result["metrics"], ["dataset_drift", "number_of_drifted_columns"])
    quality_result = _find_result(result["metrics"], ["reference", "current"])

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"{name}.html"
    report.save_html(str(report_path))

    summary = {
        "name": name,
        "dataset_drift": drift_result["dataset_drift"],
        "n_drifted_columns": drift_result["number_of_drifted_columns"],
        "share_drifted_columns": drift_result["share_of_drifted_columns"],
        "reference_accuracy": quality_result["reference"]["accuracy"],
        "current_accuracy": quality_result["current"]["accuracy"],
        "report_path": str(report_path),
    }

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
    with mlflow.start_run(run_name=f"monitor-{name}"):
        mlflow.log_metric("dataset_drift_detected", int(summary["dataset_drift"]))
        mlflow.log_metric("n_drifted_columns", summary["n_drifted_columns"])
        mlflow.log_metric("reference_accuracy", summary["reference_accuracy"])
        mlflow.log_metric("current_accuracy", summary["current_accuracy"])
        mlflow.log_artifact(str(report_path))

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path, required=True, help="Parquet file from generate_drift.py (or any batch with the same feature/target columns)")
    args = parser.parse_args()

    batch_df = pd.read_parquet(args.batch)
    summary = run_monitor(batch_df, name=args.batch.stem)

    print(f"=== {summary['name']} ===")
    print(f"Data drift detected:      {summary['dataset_drift']}")
    print(f"Drifted columns:          {summary['n_drifted_columns']} ({summary['share_drifted_columns']:.0%})")
    print(f"Accuracy  reference -> current:  {summary['reference_accuracy']:.3f} -> {summary['current_accuracy']:.3f}")
    print(f"Report saved to {summary['report_path']}")


if __name__ == "__main__":
    main()

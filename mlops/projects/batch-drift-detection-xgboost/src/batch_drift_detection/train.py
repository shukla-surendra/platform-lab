"""Train the XGBoost classifier on the reference (synthetic) dataset and
persist everything later stages need:

  - models/xgb_model.json         -- the trained model, XGBoost's own
                                      native format (not pickle -- avoids
                                      the sklearn/xgboost version-pinning
                                      fragility pickle has across upgrades)
  - data/reference_scored.parquet -- the reference features + true target +
                                      the model's own prediction on them.
                                      monitor.py needs this exact artifact
                                      as Evidently's `reference_data`: both
                                      DataDriftPreset (features/prediction)
                                      and ClassificationPreset (target vs.
                                      prediction) compare against it.

Run once. predict.py / generate_drift.py / monitor.py in later, separate
runs all just load these two files rather than retraining anything.
"""

from __future__ import annotations

import mlflow
from sklearn.metrics import accuracy_score, roc_auc_score
from xgboost import XGBClassifier

from batch_drift_detection.config import (
    FEATURE_NAMES,
    MLFLOW_EXPERIMENT_NAME,
    MLFLOW_TRACKING_URI,
    MODEL_PATH,
    MODELS_DIR,
    PREDICTION_COLUMN,
    REFERENCE_PATH,
    TARGET_COLUMN,
)
from batch_drift_detection.synth_data import make_or_load_split


def train() -> XGBClassifier:
    reference_df, holdout_df = make_or_load_split()

    model = XGBClassifier(n_estimators=150, max_depth=4, eval_metric="logloss", random_state=42)
    model.fit(reference_df[FEATURE_NAMES], reference_df[TARGET_COLUMN])

    reference_df = reference_df.copy()
    reference_df[PREDICTION_COLUMN] = model.predict(reference_df[FEATURE_NAMES])

    # Sanity-check generalization on the untouched, never-trained-on holdout
    # pool -- NOT the final word on model quality (predict.py/monitor.py are
    # the actual pipeline stages for that), just confirms the model learned
    # something real before anything downstream depends on it.
    holdout_pred = model.predict(holdout_df[FEATURE_NAMES])
    holdout_proba = model.predict_proba(holdout_df[FEATURE_NAMES])[:, 1]
    holdout_accuracy = accuracy_score(holdout_df[TARGET_COLUMN], holdout_pred)
    holdout_roc_auc = roc_auc_score(holdout_df[TARGET_COLUMN], holdout_proba)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model.save_model(str(MODEL_PATH))
    reference_df.to_parquet(REFERENCE_PATH)

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
    with mlflow.start_run(run_name="train"):
        mlflow.log_params(
            {
                "n_estimators": model.n_estimators,
                "max_depth": model.max_depth,
                "n_features": len(FEATURE_NAMES),
            }
        )
        mlflow.log_metric("holdout_accuracy", holdout_accuracy)
        mlflow.log_metric("holdout_roc_auc", holdout_roc_auc)
        mlflow.log_artifact(str(MODEL_PATH))

    print(f"Trained on {len(reference_df)} reference rows, {len(FEATURE_NAMES)} features.")
    print(f"Holdout sanity check -- accuracy: {holdout_accuracy:.3f}, ROC-AUC: {holdout_roc_auc:.3f}")
    print(f"Model saved to {MODEL_PATH}")
    print(f"Scored reference saved to {REFERENCE_PATH}")

    return model


if __name__ == "__main__":
    train()

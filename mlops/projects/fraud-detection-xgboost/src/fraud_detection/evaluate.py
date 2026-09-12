"""Evaluate the currently-registered model against a fresh split of the data.

Distinct from train.py's own held-out evaluation: this loads whatever model
is actually registered in MLflow right now (not necessarily the one you just
trained) and scores it -- the "is what's deployed still good?" question, as
opposed to "how good was the model I just trained?".
"""

from __future__ import annotations

import mlflow
import mlflow.xgboost
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)

from fraud_detection.config import (
    MLFLOW_TRACKING_URI,
    REGISTERED_MODEL_NAME,
)
from fraud_detection.data import load_dataset
from fraud_detection.features import build_feature_matrix, temporal_train_test_split


def evaluate(model_stage: str = "latest", train_frac: float = 0.7) -> dict:
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    model_uri = f"models:/{REGISTERED_MODEL_NAME}/{model_stage}"
    model = mlflow.xgboost.load_model(model_uri)

    df = load_dataset()
    _, test_df = temporal_train_test_split(df, train_frac=train_frac)
    X_test, y_test = build_feature_matrix(test_df)

    y_pred_proba = model.predict(X_test)
    y_pred = (y_pred_proba >= 0.5).astype(int)

    results = {
        "pr_auc": average_precision_score(y_test, y_pred_proba),
        "roc_auc": roc_auc_score(y_test, y_pred_proba),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(y_test, y_pred, output_dict=True),
    }
    return results


if __name__ == "__main__":
    import json

    print(json.dumps(evaluate(), indent=2, default=str))

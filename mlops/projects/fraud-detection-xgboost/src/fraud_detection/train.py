"""Train an XGBoost fraud classifier and log everything to MLflow."""

from __future__ import annotations

import mlflow
import mlflow.xgboost
import xgboost as xgb
from sklearn.metrics import average_precision_score, roc_auc_score

from fraud_detection.config import (
    MLFLOW_EXPERIMENT_NAME,
    MLFLOW_TRACKING_URI,
    RANDOM_SEED,
    REGISTERED_MODEL_NAME,
)
from fraud_detection.data import load_dataset
from fraud_detection.features import build_feature_matrix, temporal_train_test_split


def train(train_frac: float = 0.7):
    df = load_dataset()
    train_df, test_df = temporal_train_test_split(df, train_frac=train_frac)

    X_train, y_train = build_feature_matrix(train_df)
    X_test, y_test = build_feature_matrix(test_df)

    # ~0.17% fraud rate: scale_pos_weight tells XGBoost to weight the
    # minority class by roughly its imbalance ratio -- the standard fix for
    # a model that would otherwise trivially minimize loss by predicting
    # "not fraud" for everything. See README.md's "Why PR-AUC, not accuracy"
    # for the matching evaluation-side fix.
    scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)

    params = {
        "objective": "binary:logistic",
        "eval_metric": "aucpr",
        "scale_pos_weight": float(scale_pos_weight),
        "max_depth": 5,
        "learning_rate": 0.1,
        "n_estimators": 200,
        "random_state": RANDOM_SEED,
    }

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    with mlflow.start_run() as run:
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train)

        y_pred_proba = model.predict_proba(X_test)[:, 1]
        metrics = {
            "pr_auc": average_precision_score(y_test, y_pred_proba),
            "roc_auc": roc_auc_score(y_test, y_pred_proba),
            "train_rows": len(X_train),
            "test_rows": len(X_test),
            "train_fraud_rate": float(y_train.mean()),
            "test_fraud_rate": float(y_test.mean()),
        }

        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        mlflow.xgboost.log_model(
            model,
            artifact_path="model",
            registered_model_name=REGISTERED_MODEL_NAME,
        )

        print(f"Run ID: {run.info.run_id}")
        print(f"PR-AUC: {metrics['pr_auc']:.4f}  ROC-AUC: {metrics['roc_auc']:.4f}")
        return run, model, (X_test, y_test)


if __name__ == "__main__":
    train()

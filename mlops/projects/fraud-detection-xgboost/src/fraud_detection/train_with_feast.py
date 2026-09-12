"""Train an XGBoost fraud classifier augmented with Feast-served IP velocity
features, registered as a separate MLflow model from train.py's baseline so
the two are directly comparable.

This is deliberately a second, parallel model rather than a change to
train.py's existing one: train.py's numbers are already measured and
documented (see ../README.md and ../FAQ.md); this module exists to give an
honest "baseline vs. +feature-store" comparison instead of silently
overwriting previously-reported results.
"""

from __future__ import annotations

import mlflow
import mlflow.xgboost
import xgboost as xgb
from sklearn.metrics import average_precision_score, roc_auc_score

from fraud_detection.config import (
    MLFLOW_EXPERIMENT_NAME,
    MLFLOW_TRACKING_URI,
    RANDOM_SEED,
)
from fraud_detection.data import load_dataset
from fraud_detection.feast_features import (
    apply_feast_repo,
    build_ip_velocity_source,
    get_training_features,
    materialize_latest,
)
from fraud_detection.features import build_feature_matrix, temporal_train_test_split

REGISTERED_MODEL_NAME_FEAST = "fraud-xgboost-feast"


def train_with_feast(train_frac: float = 0.7):
    df = load_dataset()

    # Computed once over the *full* chronological history, then split --
    # test-period rows legitimately get to see accumulated IP stats from
    # earlier test-period rows AND all training-period rows for that IP,
    # exactly as a real deployed system would have accumulated them by then.
    build_ip_velocity_source(df)
    store = apply_feast_repo()

    train_df, test_df = temporal_train_test_split(df, train_frac=train_frac)

    train_df = get_training_features(store, train_df)
    test_df = get_training_features(store, test_df)

    X_train, y_train = build_feature_matrix(train_df)
    X_test, y_test = build_feature_matrix(test_df)

    materialize_latest(store)

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

    with mlflow.start_run(run_name="xgboost-with-feast") as run:
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train)

        y_pred_proba = model.predict_proba(X_test)[:, 1]
        metrics = {
            "pr_auc": average_precision_score(y_test, y_pred_proba),
            "roc_auc": roc_auc_score(y_test, y_pred_proba),
            "train_rows": len(X_train),
            "test_rows": len(X_test),
        }

        mlflow.log_params({**params, "feature_source": "feast+raw"})
        mlflow.log_metrics(metrics)
        mlflow.xgboost.log_model(
            model,
            artifact_path="model",
            registered_model_name=REGISTERED_MODEL_NAME_FEAST,
        )

        print(f"Run ID: {run.info.run_id}")
        print(f"PR-AUC: {metrics['pr_auc']:.4f}  ROC-AUC: {metrics['roc_auc']:.4f}")
        return run, model, (X_test, y_test)


if __name__ == "__main__":
    train_with_feast()

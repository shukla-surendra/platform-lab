"""A logistic regression baseline, to actually measure the "why XGBoost"
claim in README.md/FAQ.md instead of just asserting it.

This is the one place in the project where sklearn's ColumnTransformer
earns its keep. XGBoost's tree splits are invariant to any monotonic
per-feature transform (verified directly: training on raw `amount` vs.
`log1p(amount)` produced byte-identical predictions, max diff 0.0) -- so
scaling/log-transforming would be theatre there. Logistic regression is
not invariant to feature scale or skew, and `amount` is badly skewed
(skew ~74, range $0.02-$659,035). ColumnTransformer lets `amount` get a
log1p+scale treatment while every other numeric column just gets scaled,
in one persisted Pipeline -- so serve.py/evaluate.py never need to
hand-reimplement this preprocessing (the training/serving skew concern
from FAQ.md's Tier 8).
"""

from __future__ import annotations

import mlflow
import mlflow.sklearn
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from fraud_detection.config import MLFLOW_EXPERIMENT_NAME, MLFLOW_TRACKING_URI
from fraud_detection.data import load_dataset
from fraud_detection.features import build_feature_matrix, temporal_train_test_split

REGISTERED_MODEL_NAME_LOGREG = "fraud-logreg-baseline"


def build_pipeline(feature_columns: list[str]) -> Pipeline:
    other_columns = [c for c in feature_columns if c != "amount"]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "log_amount",
                Pipeline(
                    [
                        ("log1p", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
                        ("scale", StandardScaler()),
                    ]
                ),
                ["amount"],
            ),
            ("scale_rest", StandardScaler(), other_columns),
        ]
    )
    return Pipeline(
        [
            ("preprocess", preprocessor),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )


def train_baseline_logreg(train_frac: float = 0.7):
    df = load_dataset()
    train_df, test_df = temporal_train_test_split(df, train_frac=train_frac)

    X_train, y_train = build_feature_matrix(train_df)
    X_test, y_test = build_feature_matrix(test_df)

    pipeline = build_pipeline(list(X_train.columns))

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    with mlflow.start_run(run_name="logreg-baseline") as run:
        pipeline.fit(X_train, y_train)

        y_pred_proba = pipeline.predict_proba(X_test)[:, 1]
        metrics = {
            "pr_auc": average_precision_score(y_test, y_pred_proba),
            "roc_auc": roc_auc_score(y_test, y_pred_proba),
            "train_rows": len(X_train),
            "test_rows": len(X_test),
        }

        mlflow.log_params({"model": "LogisticRegression", "class_weight": "balanced"})
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(
            pipeline,
            artifact_path="model",
            registered_model_name=REGISTERED_MODEL_NAME_LOGREG,
        )

        print(f"Run ID: {run.info.run_id}")
        print(f"PR-AUC: {metrics['pr_auc']:.4f}  ROC-AUC: {metrics['roc_auc']:.4f}")
        return run, pipeline, (X_test, y_test)


if __name__ == "__main__":
    train_baseline_logreg()

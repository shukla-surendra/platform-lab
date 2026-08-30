"""
Real Ray job: distributed hyperparameter search for a breast-cancer classifier.

Trains 8 RandomForestClassifier configs in parallel as Ray tasks (real dataset,
real 5-fold cross-validation), picks the best by mean CV accuracy, retrains it on
the full training set, evaluates on a held-out test set, and saves the model to
disk so `serve_model.py` can load and serve real predictions from it.

Run this via the Ray Jobs API (not `python train_job.py` directly) so the driver
logs actually show up in the dashboard:

    ray job submit --address=http://127.0.0.1:8265 --working-dir . -- python train_job.py
"""

import json
import time
from pathlib import Path

import joblib
import ray
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, train_test_split

ray.init()

# Absolute path, not `Path(__file__).parent` — when this job runs via the Jobs
# API with --working-dir, __file__ points into a sandboxed temp copy, not this
# repo checkout, so a relative artifact path would land somewhere ephemeral.
# Built from Path.home() rather than hardcoded so it doesn't bake in a username.
ARTIFACT_PATH = (
    Path.home() / "projects/2026/platform-lab/k8s_explorer/kuberay-demo/model.joblib"
)

CONFIGS = [
    {"n_estimators": 100, "max_depth": 3},
    {"n_estimators": 100, "max_depth": 5},
    {"n_estimators": 100, "max_depth": 7},
    {"n_estimators": 200, "max_depth": 3},
    {"n_estimators": 200, "max_depth": 5},
    {"n_estimators": 200, "max_depth": 7},
    {"n_estimators": 300, "max_depth": 5},
    {"n_estimators": 300, "max_depth": 7},
]


@ray.remote
def evaluate_config(X_train, y_train, config):
    model = RandomForestClassifier(random_state=42, **config)
    scores = cross_val_score(model, X_train, y_train, cv=5)
    return config, float(scores.mean())


def main():
    data = load_breast_cancer()
    X_train, X_test, y_train, y_test = train_test_split(
        data.data, data.target, test_size=0.2, random_state=42
    )

    print(f"dataset: {data.data.shape[0]} samples, {data.data.shape[1]} features")
    print(f"train/test split: {len(X_train)}/{len(X_test)}")
    print(f"searching {len(CONFIGS)} configs across the Ray cluster...")

    X_train_ref = ray.put(X_train)
    y_train_ref = ray.put(y_train)

    t0 = time.perf_counter()
    futures = [
        evaluate_config.remote(X_train_ref, y_train_ref, c) for c in CONFIGS
    ]
    results = ray.get(futures)
    elapsed = time.perf_counter() - t0

    for config, score in sorted(results, key=lambda r: -r[1]):
        print(f"  cv_accuracy={score:.4f}  config={config}")

    best_config, best_cv_score = max(results, key=lambda r: r[1])
    print(f"\nbest config: {best_config} (cv_accuracy={best_cv_score:.4f})")
    print(f"search took {elapsed:.2f}s across {len(ray.nodes())} node(s)")

    final_model = RandomForestClassifier(random_state=42, **best_config)
    final_model.fit(X_train, y_train)
    test_accuracy = final_model.score(X_test, y_test)
    print(f"held-out test accuracy: {test_accuracy:.4f}")

    joblib.dump(
        {
            "model": final_model,
            "feature_names": list(data.feature_names),
            "target_names": list(data.target_names),
            "config": best_config,
            "cv_accuracy": best_cv_score,
            "test_accuracy": test_accuracy,
        },
        ARTIFACT_PATH,
    )
    print(f"saved model to {ARTIFACT_PATH}")

    print(
        "RESULT_JSON="
        + json.dumps(
            {
                "best_config": best_config,
                "cv_accuracy": best_cv_score,
                "test_accuracy": test_accuracy,
                "artifact_path": str(ARTIFACT_PATH),
            }
        )
    )


if __name__ == "__main__":
    main()

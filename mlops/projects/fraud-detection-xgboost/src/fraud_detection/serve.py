"""Minimal FastAPI inference service around the registered MLflow model.

Run with: uv run uvicorn fraud_detection.serve:app --reload
"""

from __future__ import annotations

import mlflow
import mlflow.xgboost
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

from fraud_detection.config import MLFLOW_TRACKING_URI, REGISTERED_MODEL_NAME
from fraud_detection.feast_features import FEATURE_REPO_PATH, get_online_ip_features
from fraud_detection.train_with_feast import REGISTERED_MODEL_NAME_FEAST

app = FastAPI(title="fraud-detection-xgboost")

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
_model = None
_feast_model = None
_feast_store = None


def get_model():
    global _model
    if _model is None:
        _model = mlflow.xgboost.load_model(f"models:/{REGISTERED_MODEL_NAME}/latest")
    return _model


def get_feast_model():
    global _feast_model
    if _feast_model is None:
        _feast_model = mlflow.xgboost.load_model(f"models:/{REGISTERED_MODEL_NAME_FEAST}/latest")
    return _feast_model


def get_feast_store():
    # Feast has already been `apply`'d by train_with_feast.py -- this just
    # opens a client against the existing repo, no re-registration here.
    global _feast_store
    if _feast_store is None:
        from feast import FeatureStore

        _feast_store = FeatureStore(repo_path=str(FEATURE_REPO_PATH))
    return _feast_store


class Transaction(BaseModel):
    amount: float
    time_value: float
    v1: float
    v2: float
    v3: float
    v4: float
    v5: float
    v6: float
    v7: float
    v8: float
    v9: float
    v10: float
    v11: float
    v12: float
    v13: float
    v14: float
    v15: float
    v16: float
    v17: float
    v18: float
    v19: float
    v20: float
    v21: float
    v22: float
    v23: float
    v24: float
    v25: float
    v26: float
    v27: float
    v28: float


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def predict(transaction: Transaction):
    model = get_model()
    X = pd.DataFrame([transaction.model_dump()])
    fraud_probability = float(model.predict(X)[0])
    return {
        "fraud_probability": fraud_probability,
        "is_fraud": fraud_probability >= 0.5,
    }


class TransactionWithIp(Transaction):
    ip_address: str


@app.post("/predict_feast")
def predict_feast(transaction: TransactionWithIp):
    """Same model family as /predict, but augmented with Feast-served IP
    velocity features -- a live get_online_features() lookup by ip_address,
    the latest-value counterpart to train_with_feast.py's point-in-time
    join. Separate endpoint (not a change to /predict's existing, already-
    tested contract) since it depends on a different registered model and
    on Feast having been materialized at least once."""
    model = get_feast_model()
    store = get_feast_store()

    row = transaction.model_dump()
    ip_address = row.pop("ip_address")
    row.update(get_online_ip_features(store, ip_address))

    X = pd.DataFrame([row])
    fraud_probability = float(model.predict(X)[0])
    return {
        "fraud_probability": fraud_probability,
        "is_fraud": fraud_probability >= 0.5,
        "ip_velocity_features": get_online_ip_features(store, ip_address),
    }

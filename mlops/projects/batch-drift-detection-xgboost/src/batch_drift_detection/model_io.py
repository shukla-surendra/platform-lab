"""Load the persisted XGBoost model -- shared by predict.py and monitor.py
so neither has to duplicate the load call or drift out of sync on how the
model is instantiated before `.load_model()` is called.
"""

from __future__ import annotations

from xgboost import XGBClassifier

from batch_drift_detection.config import MODEL_PATH


def load_model() -> XGBClassifier:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"No trained model at {MODEL_PATH} -- run `train.py` first.")
    model = XGBClassifier()
    model.load_model(str(MODEL_PATH))
    return model

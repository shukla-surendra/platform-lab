"""Shared paths and constants for the batch drift-detection pipeline."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"

REFERENCE_PATH = DATA_DIR / "reference_scored.parquet"
HOLDOUT_PATH = DATA_DIR / "holdout.parquet"
MODEL_PATH = MODELS_DIR / "xgb_model.json"

TARGET_COLUMN = "target"
PREDICTION_COLUMN = "prediction"

# make_classification params -- fixed here (not left as CLI args with
# defaults duplicated in three scripts) so train.py, generate_drift.py, and
# any future script all agree on the same feature space without importing
# each other.
N_SAMPLES = 8000
N_FEATURES = 8
N_INFORMATIVE = 5
CLASS_SEP = 1.2
FEATURE_NAMES = [f"feature_{i}" for i in range(N_FEATURES)]

RANDOM_SEED = 42
HOLDOUT_FRACTION = 0.4  # reserved as the pool later batches (clean + drifted) sample from

MLFLOW_TRACKING_URI = f"sqlite:///{PROJECT_ROOT / 'mlflow.db'}"
MLFLOW_EXPERIMENT_NAME = "batch-drift-detection-xgboost"

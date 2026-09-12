"""Shared paths and constants for the fraud-detection pipeline."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_PATH = DATA_DIR / "banking_fraud_raw.csv"

# Zenodo record 20030065 -- "A Production-Collected Online Banking Fraud
# Detection Dataset from a Live Cloud-Based Deep Learning System", CC-BY 4.0.
# URL and schema verified directly (curled the file and read its header)
# rather than assumed from the abstract -- see README.md's "About the
# dataset" section for what that check actually found.
ZENODO_RECORD_ID = "20030065"
ZENODO_FILE_URL = (
    "https://zenodo.org/records/20030065/files/"
    "fraud_tests_export_20260501_080333.csv?download=1"
)

TARGET_COLUMN = "is_fraud"
TIMESTAMP_COLUMN = "timestamp"

# These are OUTPUTS of the live system that produced this dataset (its own
# fraud-probability score, risk tier, confidence, and recommended action) --
# not legitimate model inputs. Verified directly from the raw file: risk_level
# is near-perfectly correlated with is_fraud, so training on it would be
# leakage, not signal. See README.md's "Leakage columns" section.
LEAKAGE_COLUMNS = ["fraud_probability", "risk_level", "confidence", "recommendation"]

# Identifiers/metadata, not predictive features.
ID_COLUMNS = ["id", "transaction_id", "ip_address", "test_date"]

MLFLOW_TRACKING_URI = f"sqlite:///{PROJECT_ROOT / 'mlflow.db'}"
MLFLOW_EXPERIMENT_NAME = "fraud-detection-xgboost"
REGISTERED_MODEL_NAME = "fraud-xgboost"

RANDOM_SEED = 42

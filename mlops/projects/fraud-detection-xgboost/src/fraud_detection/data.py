"""Download and load the banking fraud dataset.

data/ is git-ignored -- this module is the only place the raw dataset ever
touches disk, and it's never committed. Deleting data/ and re-running
load_dataset() reproduces it from scratch from Zenodo.
"""

from __future__ import annotations

import logging

import pandas as pd
import requests

from fraud_detection.config import DATA_DIR, RAW_DATA_PATH, ZENODO_FILE_URL

logger = logging.getLogger(__name__)


def download_dataset(force: bool = False) -> None:
    """Fetch the raw CSV from Zenodo into data/, if not already cached."""
    if RAW_DATA_PATH.exists() and not force:
        logger.info("Using cached dataset at %s", RAW_DATA_PATH)
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading dataset from %s", ZENODO_FILE_URL)
    response = requests.get(ZENODO_FILE_URL, timeout=60)
    response.raise_for_status()
    RAW_DATA_PATH.write_bytes(response.content)
    logger.info("Saved %d bytes to %s", len(response.content), RAW_DATA_PATH)


def load_dataset(force_download: bool = False) -> pd.DataFrame:
    """Load the dataset, sorted chronologically by timestamp.

    Sorting here (rather than leaving callers to remember it) is what makes
    features.temporal_train_test_split's chronological split correct.
    """
    download_dataset(force=force_download)
    df = pd.read_csv(RAW_DATA_PATH, parse_dates=["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)

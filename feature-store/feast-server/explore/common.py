"""Shared helpers for the explore scripts (run inside the compose network)."""
import warnings

import pandas as pd
from feast import FeatureStore
from sqlalchemy import create_engine

warnings.filterwarnings("ignore")

REPO = "/app/feature_repo"
PG_URL = "postgresql+psycopg://feast:feast@postgres:5432/feast"
FEATURE_SERVER = "http://feature-server:6566"

store = FeatureStore(repo_path=REPO)
engine = create_engine(PG_URL)


def sql(query: str) -> pd.DataFrame:
    """Run SQL against the offline store (Postgres)."""
    return pd.read_sql(query, engine)


def banner(title: str) -> None:
    print(f"\n=== {title} ===")

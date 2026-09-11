"""Shared connection helper for the practice Postgres instance."""
import os

import psycopg2

DB_CONFIG = dict(
    host=os.environ.get("PGHOST", "localhost"),
    port=os.environ.get("PGPORT", "5432"),
    dbname=os.environ.get("PGDATABASE", "practice"),
    user=os.environ.get("PGUSER", "postgres"),
    password=os.environ.get("PGPASSWORD", "postgres"),
)


def get_conn():
    return psycopg2.connect(**DB_CONFIG)

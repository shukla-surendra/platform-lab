"""Connection helper for the pgvector-backed documents table."""

from __future__ import annotations

import psycopg2
from pgvector.psycopg2 import register_vector

import config


def get_connection():
    conn = psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )
    register_vector(conn)
    return conn

"""Configuration for the local pgvector RAG project, loaded from .env / env vars."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("PGVECTOR_HOST", "localhost")
DB_PORT = int(os.getenv("PGVECTOR_PORT", "5433"))
DB_NAME = os.getenv("PGVECTOR_DB", "rag")
DB_USER = os.getenv("PGVECTOR_USER", "rag")
DB_PASSWORD = os.getenv("PGVECTOR_PASSWORD", "rag")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "qwen3-embedding:0.6b")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://127.0.0.1:11434/api/embed")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "200"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "40"))
TOP_K = int(os.getenv("TOP_K", "4"))

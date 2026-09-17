"""Configuration for the local LangGraph + Ollama agent, loaded from .env / env vars."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:latest")
MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.2"))

CHECKPOINT_DB = str(BASE_DIR / os.getenv("CHECKPOINT_DB", "agent_memory.sqlite"))
NOTES_FILE = BASE_DIR / os.getenv("NOTES_FILE", "notes.json")
KNOWLEDGE_DIR = BASE_DIR / os.getenv("KNOWLEDGE_DIR", "knowledge")

RECURSION_LIMIT = int(os.getenv("RECURSION_LIMIT", "25"))

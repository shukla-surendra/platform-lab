"""Configuration for the local SRE agent, loaded from .env / env vars."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

# Ollama's OpenAI-compatible endpoint. Any Ollama-served model with tool-calling support works.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:latest")
MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.2"))

STATE_FILE = BASE_DIR / os.getenv("STATE_FILE", "infra_state.json")
SESSION_DB = str(BASE_DIR / os.getenv("SESSION_DB", "sre_sessions.sqlite"))

MAX_TURNS = int(os.getenv("MAX_TURNS", "20"))

# Safety gate for mutating tools (reboot_instance, scale_ecs_service). Starts False (dry-run) on
# every process; the CLI's --apply flag flips this in-process before running the agent. Tools read
# this at call time, not at import time, so the CLI can set it after `import config`.
APPLY_CHANGES = False

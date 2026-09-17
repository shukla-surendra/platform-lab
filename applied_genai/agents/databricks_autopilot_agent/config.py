"""Configuration for the local Databricks pipeline autopilot agent, loaded from .env / env vars."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:latest")
MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.1"))

STATE_FILE = BASE_DIR / os.getenv("STATE_FILE", "pipeline_state.json")
AUDIT_LOG_FILE = BASE_DIR / os.getenv("AUDIT_LOG_FILE", "audit_log.jsonl")

EVENTS_DIR = BASE_DIR / "events"
INBOX_DIR = EVENTS_DIR / "inbox"
PROCESSED_DIR = EVENTS_DIR / "processed"
FAILED_DIR = EVENTS_DIR / "failed"

POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "1.0"))

# A job whose last N runs include this many (or more) failures gets escalated regardless of what
# the category handler decided — the cross-cutting "this keeps happening" override.
RECURRENCE_WINDOW = int(os.getenv("RECURRENCE_WINDOW", "5"))
RECURRENCE_THRESHOLD = int(os.getenv("RECURRENCE_THRESHOLD", "3"))

MAX_AUTO_RETRIES = int(os.getenv("MAX_AUTO_RETRIES", "2"))

# Safety gate for mutating tools (resize_cluster, retry_job). Starts False (dry-run) on every
# process; the CLI's --apply flag flips this in-process before the daemon starts. Tools read this
# at call time, not at import time.
APPLY_CHANGES = False

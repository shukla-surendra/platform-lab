"""Configuration for the deep research agent, loaded from .env / env vars."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# Deep agents lean hard on multi-step tool calling (planning, delegating, editing files), so use
# a model that's good at it. Subagents can run on a cheaper model.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
SUBAGENT_MODEL = os.getenv("SUBAGENT_MODEL", OPENAI_MODEL)

# The corpus the agent researches: defaults to the whole platform-lab repo. Tools are read-only
# and can't escape this directory.
NOTES_ROOT = Path(os.getenv("NOTES_ROOT", BASE_DIR.parents[2])).resolve()
OUTPUT_DIR = BASE_DIR / os.getenv("OUTPUT_DIR", "output")

# Tracing is on only when both keys are present, so the agent also runs with no Langfuse at all.
# LANGFUSE_BASE_URL is read by the SDK itself (defaults to Langfuse Cloud EU).
LANGFUSE_ENABLED = bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))

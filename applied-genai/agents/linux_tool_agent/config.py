"""Configuration for the Local Ops Agent, loaded from .env / env vars."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# OPENAI_API_KEY itself isn't read here -- langchain_openai's ChatOpenAI picks it up
# straight from the environment (which load_dotenv() above already populated from
# .env), so it never needs to appear in this file or get passed around explicitly.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.2"))

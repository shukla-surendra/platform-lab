"""Configuration for the A2A protocol demo, loaded from .env / env vars."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:latest")

WEATHER_AGENT_HOST = os.getenv("WEATHER_AGENT_HOST", "127.0.0.1")
WEATHER_AGENT_PORT = int(os.getenv("WEATHER_AGENT_PORT", "9102"))
WEATHER_AGENT_URL = f"http://{WEATHER_AGENT_HOST}:{WEATHER_AGENT_PORT}"

COORDINATOR_AGENT_HOST = os.getenv("COORDINATOR_AGENT_HOST", "127.0.0.1")
COORDINATOR_AGENT_PORT = int(os.getenv("COORDINATOR_AGENT_PORT", "9101"))
COORDINATOR_AGENT_URL = f"http://{COORDINATOR_AGENT_HOST}:{COORDINATOR_AGENT_PORT}"

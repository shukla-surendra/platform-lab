"""Configuration for the local LangGraph + Ollama K8s on-call agent, loaded from .env / env vars."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.1"))

CHECKPOINT_DB = str(BASE_DIR / os.getenv("CHECKPOINT_DB", "agent_memory.sqlite"))
RECURSION_LIMIT = int(os.getenv("RECURSION_LIMIT", "25"))

# The only namespace mutating tools are allowed to touch. Read-only tools (list/describe/logs)
# aren't restricted to it, but restart_deployment refuses anything outside this namespace - the
# same "scope the blast radius" principle as k8s_explorer/admission-webhook-demo's
# namespaceSelector, applied here to keep a demo agent from ever touching real cluster workloads.
DEMO_NAMESPACE = os.getenv("DEMO_NAMESPACE", "checkout")

"""Central configuration, loaded from .env / environment variables. Every value has a working
default so the project runs with zero configuration once Ollama is up.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

# --- LLM provider -----------------------------------------------------------------------------
# "ollama" (default, no API key) or "claude" (needs ANTHROPIC_API_KEY). Swapping is one env var;
# every node in graph.py asks llm.py for a model rather than importing a provider directly.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:latest")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "qwen3-embedding:0.6b")
# Ollama's default context window (4096) is too small for diagnose's prompt (live context +
# several retrieved knowledge passages) -- see llm.py's get_chat_model().
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "16384"))

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.1"))

# --- World state / storage ---------------------------------------------------------------------
STATE_FILE = BASE_DIR / os.getenv("STATE_FILE", "world_state.json")
AUDIT_LOG_FILE = BASE_DIR / os.getenv("AUDIT_LOG_FILE", "audit_log.jsonl")
SESSION_DB = BASE_DIR / os.getenv("SESSION_DB", "agent_sessions.sqlite")

# --- RAG ------------------------------------------------------------------------------------
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
FAISS_INDEX_DIR = BASE_DIR / os.getenv("FAISS_INDEX_DIR", "faiss_index")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "4"))

# --- MCP servers ------------------------------------------------------------------------------
# "stdio" (default, local dev): mcp_client.py spawns both servers as subprocesses -- no ports, no
# network config, and APPLY_CHANGES travels in the subprocess's environment per run (see below).
# "http" (docker-compose / production simulation): both servers are already-running network
# services (containers); mcp_client.py connects to them by URL instead of spawning anything, and
# APPLY_CHANGES becomes a property of the running ops-server container, not of a client flag --
# see mcp_client.py's build_client() and the README's "Docker / production simulation" section.
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio").lower()

OPS_SERVER_SCRIPT = str(BASE_DIR / "mcp_servers" / "ops_server.py")
KNOWLEDGE_SERVER_SCRIPT = str(BASE_DIR / "mcp_servers" / "knowledge_server.py")

OPS_SERVER_HOST = os.getenv("OPS_SERVER_HOST", "0.0.0.0")
OPS_SERVER_PORT = int(os.getenv("OPS_SERVER_PORT", "8001"))
KNOWLEDGE_SERVER_HOST = os.getenv("KNOWLEDGE_SERVER_HOST", "0.0.0.0")
KNOWLEDGE_SERVER_PORT = int(os.getenv("KNOWLEDGE_SERVER_PORT", "8002"))

# Defaults assume `docker compose port` mappings or same-host testing; docker-compose.yml
# overrides these to the in-network service names (http://ops-server:8001/mcp, etc).
OPS_SERVER_URL = os.getenv("OPS_SERVER_URL", f"http://localhost:{OPS_SERVER_PORT}/mcp")
KNOWLEDGE_SERVER_URL = os.getenv("KNOWLEDGE_SERVER_URL", f"http://localhost:{KNOWLEDGE_SERVER_PORT}/mcp")

# --- Automode -----------------------------------------------------------------------------------
EVENTS_DIR = BASE_DIR / "events"
INBOX_DIR = EVENTS_DIR / "inbox"
PROCESSED_DIR = EVENTS_DIR / "processed"
FAILED_DIR = EVENTS_DIR / "failed"
POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "1.0"))

# --- Decision thresholds -----------------------------------------------------------------------
# diagnose's confidence must clear this bar for decide() to auto-remediate instead of escalating.
AUTO_REMEDIATE_CONFIDENCE = float(os.getenv("AUTO_REMEDIATE_CONFIDENCE", "0.7"))

# --- Safety gate for mutating tools ------------------------------------------------------------
# The ops MCP server is a *separate process*, spawned fresh per run, so this can't be a plain
# in-process flag like a single-process project would use -- it's passed to the subprocess as an
# environment variable (see mcp_client.py) and the server reads it once at import time.
APPLY_CHANGES = os.getenv("APPLY_CHANGES", "false").lower() == "true"

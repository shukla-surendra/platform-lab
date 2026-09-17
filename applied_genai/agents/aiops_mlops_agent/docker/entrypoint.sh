#!/bin/sh
# Entrypoint for the agent/cli services: wait for both MCP servers and Ollama to actually be
# accepting connections (not just "container started"), then exec whatever command was passed.
set -e

python docker/wait_for.py \
    "ops-server:${OPS_SERVER_PORT:-8001}" \
    "knowledge-server:${KNOWLEDGE_SERVER_PORT:-8002}" \
    "ollama:11434"

exec "$@"

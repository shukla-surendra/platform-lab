#!/bin/sh
# Build the FAISS index exactly once per volume -- only if it doesn't exist yet. Needs Ollama
# reachable for embeddings, which is why knowledge-server depends on ollama-pull completing.
set -e

if [ ! -f "$FAISS_INDEX_DIR/index.faiss" ]; then
    echo "No FAISS index at $FAISS_INDEX_DIR -- building from knowledge_base/." >&2
    python rag/ingest.py
fi

exec python mcp_servers/knowledge_server.py

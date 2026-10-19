"""MCP server exposing the RAG knowledge base (runbooks, postmortems, model cards, pipeline
docs) as a single search tool. Separate process from ops_server.py -- retrieval and mutation are
different concerns and there's no reason for the ops server to also carry FAISS/numpy as a
dependency.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from fastmcp import FastMCP  # noqa: E402
from rag import store  # noqa: E402
from rag.embeddings import embed_one  # noqa: E402

mcp = FastMCP("Knowledge Base")

_index = None
_chunks = None


def _get_index():
    global _index, _chunks
    if _index is None:
        _index, _chunks = store.load()
    return _index, _chunks


@mcp.tool()
def search_knowledge_base(query: str, k: int = config.RETRIEVAL_K) -> list[dict]:
    """Search runbooks, postmortems, model cards, and pipeline docs for passages relevant to a
    query (e.g. an incident summary or 'model drift rollback runbook'). Returns the top-k chunks
    with their source file and similarity score."""
    index, chunks = _get_index()
    vector = embed_one(query)
    return store.query(index, chunks, vector, k)


if __name__ == "__main__":
    if config.MCP_TRANSPORT == "http":
        mcp.run(transport="http", host=config.KNOWLEDGE_SERVER_HOST, port=config.KNOWLEDGE_SERVER_PORT)
    else:
        mcp.run()

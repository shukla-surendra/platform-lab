"""Embedding model wrapper -- calls Ollama's /api/embed endpoint (local qwen3-embedding model).

Same pattern as ../rag_pgvector_local/embeddings.py: Ollama is the only runtime dependency for turning
text into vectors, so this project needs no separate PyTorch/HuggingFace stack.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import config


def embed(texts: list[str]) -> list[list[float]]:
    payload = {"model": config.EMBEDDING_MODEL, "input": texts}
    request = urllib.request.Request(
        config.OLLAMA_EMBED_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach Ollama at {config.OLLAMA_EMBED_URL}. Make sure `ollama serve` is running "
            f"and `ollama pull {config.EMBEDDING_MODEL}` has completed."
        ) from exc
    return body["embeddings"]


def embed_one(text: str) -> list[float]:
    return embed([text])[0]

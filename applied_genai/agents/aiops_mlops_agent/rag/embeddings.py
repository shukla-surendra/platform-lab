"""Embedding provider, following the same LLM_PROVIDER switch as `llm.py`: Ollama's local
`/api/embed` endpoint by default (no API key), or Claude-compatible workflow via a sentence
embedding fallback isn't applicable here since Anthropic has no embeddings endpoint -- so on
`LLM_PROVIDER=claude`, embeddings still use Ollama (chat model and embedding model are
independent choices; only the reasoning calls move to Claude).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import config


def embed(texts: list[str]) -> list[list[float]]:
    payload = {"model": config.OLLAMA_EMBED_MODEL, "input": texts}
    request = urllib.request.Request(
        f"{config.OLLAMA_BASE_URL}/api/embed",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach Ollama at {config.OLLAMA_BASE_URL}. Make sure `ollama serve` is "
            f"running and `ollama pull {config.OLLAMA_EMBED_MODEL}` has completed."
        ) from exc
    return body["embeddings"]


def embed_one(text: str) -> list[float]:
    return embed([text])[0]

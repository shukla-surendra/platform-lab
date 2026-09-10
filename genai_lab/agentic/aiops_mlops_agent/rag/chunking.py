"""Word-based sliding-window chunking. Simple on purpose -- the knowledge base here is short,
structured markdown (runbooks, postmortems), not long unstructured prose, so a fixed-size window
with overlap is enough; no need for a semantic/recursive splitter."""

from __future__ import annotations

import config


def chunk_text(text: str, chunk_size: int = config.CHUNK_SIZE, overlap: int = config.CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    step = max(1, chunk_size - overlap)
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_size])
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(words):
            break
    return chunks

"""Fixed-size, word-based chunking with overlap.

See docs/RAG_Knowledge_Base_Starter/08_Interview_Questions.md (Q57) in the repo root for why chunk size is
the highest-leverage tuning knob in a RAG pipeline, and how this compares to sentence- or semantic-based
chunking.
"""

from __future__ import annotations


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return []

    step = max(chunk_size - overlap, 1)
    chunks: list[str] = []
    start = 0
    while start < len(words):
        chunk_words = words[start : start + chunk_size]
        chunks.append(" ".join(chunk_words))
        if start + chunk_size >= len(words):
            break
        start += step
    return chunks

#!/usr/bin/env python3
"""Build the FAISS index from every markdown file under knowledge_base/. Re-run any time the
knowledge base changes; it fully rebuilds rather than updating incrementally.

    python rag/ingest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from rag import store  # noqa: E402
from rag.chunking import chunk_text  # noqa: E402
from rag.embeddings import embed  # noqa: E402


def main() -> None:
    files = sorted(config.KNOWLEDGE_BASE_DIR.rglob("*.md"))
    if not files:
        raise SystemExit(f"No markdown files found under {config.KNOWLEDGE_BASE_DIR}")

    chunks: list[dict] = []
    for path in files:
        source = str(path.relative_to(config.KNOWLEDGE_BASE_DIR))
        for i, text in enumerate(chunk_text(path.read_text())):
            chunks.append({"source": source, "chunk_index": i, "text": text})

    print(f"Chunked {len(files)} documents into {len(chunks)} chunks. Embedding...")
    vectors = embed([c["text"] for c in chunks])
    store.build(chunks, vectors)
    print(f"Index built -> {config.FAISS_INDEX_DIR}")


if __name__ == "__main__":
    main()

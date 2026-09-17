#!/usr/bin/env python3
"""Similarity search against the pgvector `documents` table.

`<=>` is pgvector's cosine-distance operator; embeddings are stored normalized
(see embeddings.py), so `1 - distance` below gives cosine similarity in [0, 1].
"""

from __future__ import annotations

import sys

import config
from db import get_connection
from embeddings import embed_one


def search(query: str, top_k: int | None = None) -> list[dict]:
    top_k = top_k or config.TOP_K
    query_vector = embed_one(query)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT source, chunk_index, content, 1 - (embedding <=> %s::vector) AS similarity
        FROM documents
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (query_vector, query_vector, top_k),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {"source": source, "chunk_index": chunk_index, "content": content, "similarity": similarity}
        for source, chunk_index, content, similarity in rows
    ]


def main() -> int:
    query = " ".join(sys.argv[1:]).strip() or "What is a vector database?"
    results = search(query)
    if not results:
        print("No documents indexed yet. Run ingest.py first.")
        return 1

    for result in results:
        print(f"[{result['similarity']:.3f}] {result['source']}#{result['chunk_index']}")
        snippet = result["content"][:200].replace("\n", " ")
        print(f"{snippet}...")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

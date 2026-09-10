#!/usr/bin/env python3
"""Similarity search against the Qdrant collection (retrieval only, no LLM)."""

from __future__ import annotations

import sys

import config
from embeddings import embed_one
from store import QdrantVectorStore, get_client


def search(query: str, top_k: int | None = None) -> list[dict]:
    top_k = top_k or config.TOP_K
    client = get_client()
    if not client.collection_exists(config.COLLECTION_NAME):
        raise RuntimeError(
            f"Collection '{config.COLLECTION_NAME}' does not exist yet. Run ingest.py first."
        )
    store = QdrantVectorStore(client=client, collection_name=config.COLLECTION_NAME, dim=config.EMBEDDING_DIM)
    query_vector = embed_one(query)
    return store.search(query_vector, top_k)


def main() -> int:
    query = " ".join(sys.argv[1:]).strip() or "What is a vector database?"
    try:
        results = search(query)
    except RuntimeError as exc:
        print(exc)
        return 1

    if not results:
        print("No documents indexed yet. Run ingest.py first.")
        return 1

    for result in results:
        print(f"[{result['similarity']:.3f}] {result['source']}#{result['chunk_index']} (id={result['id']})")
        snippet = result["text"][:200].replace("\n", " ")
        print(f"{snippet}...")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Walks through the full vector DB lifecycle against a scratch Qdrant collection, step by step:

    CREATE -> INSERT -> READ (get + search) -> UPDATE -> DELETE -> STATS

Uses the local Ollama qwen embedding model for every vector, same as ingest.py/search.py. Runs against
its own scratch collection (`demo_lifecycle`) so it never touches whatever ingest.py has built in
`documents`.

Unlike faiss_vector_db's lifecycle_demo.py, there's no explicit PERSIST/LOAD step here: Qdrant writes
every op straight to its own storage (the `qdrant_data` Docker volume), so the data is already durable —
that's the main thing you get "for free" from a real vector DB server versus an in-process library.

Usage:
  python lifecycle_demo.py
"""

from __future__ import annotations

from embeddings import embed
from store import QdrantVectorStore, get_client

DEMO_COLLECTION = "demo_lifecycle"

SENTENCES = [
    "A vector database stores embeddings and supports nearest-neighbor search.",
    "Qdrant is a dedicated vector database server with a REST and gRPC API.",
    "Cosine similarity measures the angle between two vectors, ignoring magnitude.",
    "Ollama runs open-weight language and embedding models locally.",
]


def step(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> int:
    client = get_client()

    # 1. CREATE — (re)create a fresh, empty collection of the right dimension.
    step("CREATE")
    vectors = embed(SENTENCES)
    dim = len(vectors[0])
    store = QdrantVectorStore.create_collection(client, DEMO_COLLECTION, dim, recreate=True)
    print(f"Created empty collection '{DEMO_COLLECTION}'. dim={dim}")

    # 2. INSERT — embed and add the initial records; Qdrant assigns/stores payload natively.
    step("INSERT")
    payloads = [{"source": "demo", "chunk_index": i, "text": text} for i, text in enumerate(SENTENCES)]
    ids = store.add(vectors, payloads)
    print(f"Inserted {len(ids)} records with ids {ids}")

    # 3. READ — fetch a record by id, then run a similarity search.
    step("READ (get by id)")
    record = store.get(ids[0])
    print(f"get({ids[0]}) -> {record['text']!r}")

    step("READ (search)")
    query_vector = embed(["How do I find similar text using vector math?"])[0]
    for result in store.search(query_vector, top_k=2):
        print(f"[{result['similarity']:.3f}] id={result['id']} {result['text']!r}")

    # 4. UPDATE — Qdrant supports a true in-place update: upsert under the same id.
    step("UPDATE")
    updated_text = "Qdrant stores the vector and its JSON payload together -- no separate sidecar needed."
    new_vector = embed([updated_text])[0]
    store.update(ids[1], new_vector, {"source": "demo", "chunk_index": 1, "text": updated_text})
    print(f"update({ids[1]}) -> {store.get(ids[1])['text']!r}")

    # 5. DELETE — remove a record by id; it disappears from both the collection and future searches.
    step("DELETE")
    removed = store.delete([ids[-1]])
    print(f"Deleted {removed} record(s). get({ids[-1]}) -> {store.get(ids[-1])}")

    # 6. STATS — inspect collection size/dimension/metric/status.
    step("STATS")
    print(store.stats())

    step("Cleanup")
    client.delete_collection(DEMO_COLLECTION)
    print(f"Dropped scratch collection '{DEMO_COLLECTION}'.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

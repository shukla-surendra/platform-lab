#!/usr/bin/env python3
"""Walks through the full vector DB lifecycle against a scratch FAISS index, step by step:

    CREATE -> INSERT -> READ (get + search) -> UPDATE -> DELETE -> STATS -> PERSIST -> LOAD -> READ again

Uses the local Ollama qwen embedding model for every vector, same as ingest.py/search.py. Runs against
its own scratch index under data/demo_* so it never touches whatever ingest.py has built in
data/index.faiss.

Usage:
  python lifecycle_demo.py
"""

from __future__ import annotations

import config
from embeddings import embed
from store import FaissVectorStore

DEMO_INDEX_PATH = config.DATA_DIR / "demo_index.faiss"
DEMO_METADATA_PATH = config.DATA_DIR / "demo_metadata.json"

SENTENCES = [
    "A vector database stores embeddings and supports nearest-neighbor search.",
    "FAISS is a library for efficient similarity search, not a standalone server.",
    "Cosine similarity measures the angle between two vectors, ignoring magnitude.",
    "Ollama runs open-weight language and embedding models locally.",
]


def step(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> int:
    # 1. CREATE — build a fresh, empty index of the right dimension.
    step("CREATE")
    vectors = embed(SENTENCES)
    dim = len(vectors[0])
    store = FaissVectorStore.create(dim)
    print(f"Created empty index. dim={dim}")

    # 2. INSERT — embed and add the initial records.
    step("INSERT")
    metadatas = [{"source": "demo", "chunk_index": i, "text": text} for i, text in enumerate(SENTENCES)]
    ids = store.add(vectors, metadatas)
    print(f"Inserted {len(ids)} records with ids {ids}")

    # 3. READ — fetch a record by id, then run a similarity search.
    step("READ (get by id)")
    record = store.get(ids[0])
    print(f"get({ids[0]}) -> {record['text']!r}")

    step("READ (search)")
    query_vector = embed(["How do I find similar text using vector math?"])[0]
    for result in store.search(query_vector, top_k=2):
        print(f"[{result['similarity']:.3f}] id={result['id']} {result['text']!r}")

    # 4. UPDATE — FAISS has no in-place update, so this is remove + re-add under the same id.
    step("UPDATE")
    updated_text = "FAISS stores only vectors and ids -- your app is responsible for the text payload."
    new_vector = embed([updated_text])[0]
    store.update(ids[1], new_vector, {"source": "demo", "chunk_index": 1, "text": updated_text})
    print(f"update({ids[1]}) -> {store.get(ids[1])['text']!r}")

    # 5. DELETE — remove a record by id; it disappears from both the index and future searches.
    step("DELETE")
    removed = store.delete([ids[-1]])
    print(f"Deleted {removed} record(s). get({ids[-1]}) -> {store.get(ids[-1])}")

    # 6. STATS — inspect index size/dimension/metric.
    step("STATS")
    print(store.stats())

    # 7. PERSIST — write the index + metadata sidecar to disk.
    step("PERSIST")
    store.save(DEMO_INDEX_PATH, DEMO_METADATA_PATH)
    print(f"Saved to {DEMO_INDEX_PATH} and {DEMO_METADATA_PATH}")

    # 8. LOAD — read it back into a brand-new instance, proving nothing was lost.
    step("LOAD")
    reloaded = FaissVectorStore.load(DEMO_INDEX_PATH, DEMO_METADATA_PATH)
    print(f"Reloaded store stats: {reloaded.stats()}")

    step("READ again (after reload)")
    for result in reloaded.search(query_vector, top_k=3):
        print(f"[{result['similarity']:.3f}] id={result['id']} {result['text']!r}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

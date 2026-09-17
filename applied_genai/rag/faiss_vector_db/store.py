"""FaissVectorStore -- the full vector DB lifecycle around a FAISS index.

FAISS itself only knows about `(id, vector)` pairs; it has no concept of a document's original text or
metadata (see docs/RAG_Knowledge_Base_Starter/04_Vector_Databases.md, "What is stored alongside the
vector"). This class pairs a FAISS index with a JSON sidecar file that holds the `id -> {source, text,
...}` payload, and exposes the operations that make up a vector DB's lifecycle:

    CREATE  -> FaissVectorStore.create()
    INSERT  -> add()
    READ    -> get(), search()
    UPDATE  -> update()
    DELETE  -> delete(), delete_by_source()
    PERSIST -> save()
    LOAD    -> FaissVectorStore.load()
    STATS   -> stats()

Index choice: IndexFlatIP (exact inner-product search) wrapped in IndexIDMap2, so callers can assign their
own stable integer ids (needed for update/delete-by-id) and FAISS still supports exact `reconstruct()` and
physical `remove_ids()`. Vectors are L2-normalized before insertion, which turns inner product into cosine
similarity -- see normalize().  This trades some speed for exactness and simplicity; docs/
Similarity_Search_Methods/10_FAISS_Index_Types.md covers the approximate alternatives (IVF, HNSW, PQ) you'd
reach for once a Flat index stops scaling.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np


def normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


class FaissVectorStore:
    def __init__(self, dim: int, index: faiss.Index, records: dict[int, dict[str, Any]], next_id: int):
        self.dim = dim
        self.index = index
        self.records = records
        self.next_id = next_id

    # -- CREATE --------------------------------------------------------

    @classmethod
    def create(cls, dim: int) -> "FaissVectorStore":
        index = faiss.IndexIDMap2(faiss.IndexFlatIP(dim))
        return cls(dim=dim, index=index, records={}, next_id=0)

    # -- INSERT ----------------------------------------------------------

    def add(self, vectors: list[list[float]], metadatas: list[dict[str, Any]]) -> list[int]:
        if len(vectors) != len(metadatas):
            raise ValueError("vectors and metadatas must be the same length")
        if not vectors:
            return []

        matrix = normalize(np.array(vectors, dtype="float32"))
        ids = list(range(self.next_id, self.next_id + len(vectors)))
        self.index.add_with_ids(matrix, np.array(ids, dtype="int64"))
        for record_id, metadata in zip(ids, metadatas):
            self.records[record_id] = metadata
        self.next_id += len(vectors)
        return ids

    # -- READ --------------------------------------------------------------

    def get(self, record_id: int) -> dict[str, Any] | None:
        if record_id not in self.records:
            return None
        vector = self.index.reconstruct(record_id)
        return {"id": record_id, "vector": vector.tolist(), **self.records[record_id]}

    def search(self, query_vector: list[float], top_k: int) -> list[dict[str, Any]]:
        if self.index.ntotal == 0:
            return []
        query = normalize(np.array([query_vector], dtype="float32"))
        scores, ids = self.index.search(query, min(top_k, self.index.ntotal))
        results = []
        for score, record_id in zip(scores[0], ids[0]):
            if record_id == -1:
                continue
            results.append({"id": int(record_id), "similarity": float(score), **self.records[int(record_id)]})
        return results

    # -- UPDATE --------------------------------------------------------------

    def update(self, record_id: int, vector: list[float], metadata: dict[str, Any]) -> bool:
        if record_id not in self.records:
            return False
        self.index.remove_ids(np.array([record_id], dtype="int64"))
        matrix = normalize(np.array([vector], dtype="float32"))
        self.index.add_with_ids(matrix, np.array([record_id], dtype="int64"))
        self.records[record_id] = metadata
        return True

    # -- DELETE --------------------------------------------------------------

    def delete(self, ids: list[int]) -> int:
        existing = [record_id for record_id in ids if record_id in self.records]
        if not existing:
            return 0
        self.index.remove_ids(np.array(existing, dtype="int64"))
        for record_id in existing:
            del self.records[record_id]
        return len(existing)

    def delete_by_source(self, source: str) -> int:
        ids = [record_id for record_id, meta in self.records.items() if meta.get("source") == source]
        return self.delete(ids)

    # -- STATS -----------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        return {
            "ntotal": self.index.ntotal,
            "dimension": self.dim,
            "metric": "cosine (via normalized inner product)",
            "records": len(self.records),
            "next_id": self.next_id,
        }

    def __len__(self) -> int:
        return self.index.ntotal

    # -- PERSIST / LOAD --------------------------------------------------

    def save(self, index_path: Path, metadata_path: Path) -> None:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(index_path))
        payload = {
            "dim": self.dim,
            "next_id": self.next_id,
            "records": {str(record_id): meta for record_id, meta in self.records.items()},
        }
        metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, index_path: Path, metadata_path: Path) -> "FaissVectorStore":
        if not index_path.exists() or not metadata_path.exists():
            raise FileNotFoundError(
                f"No saved index at {index_path} / {metadata_path}. Run ingest.py or lifecycle_demo.py first."
            )
        index = faiss.read_index(str(index_path))
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        records = {int(record_id): meta for record_id, meta in payload["records"].items()}
        return cls(dim=payload["dim"], index=index, records=records, next_id=payload["next_id"])

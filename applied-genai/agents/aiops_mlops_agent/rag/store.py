"""A tiny FAISS-backed vector store: one flat inner-product index (vectors are L2-normalized, so
inner product == cosine similarity) plus a parallel JSON file of chunk metadata. No metadata
filtering, no incremental updates -- `ingest.py` rebuilds the whole index from scratch, which is
fine at this knowledge base's size (a few dozen documents)."""

from __future__ import annotations

import json

import faiss
import numpy as np

import config

_INDEX_FILE = config.FAISS_INDEX_DIR / "index.faiss"
_META_FILE = config.FAISS_INDEX_DIR / "chunks.json"


def _normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def build(chunks: list[dict], vectors: list[list[float]]) -> None:
    config.FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    array = _normalize(np.array(vectors, dtype="float32"))
    index = faiss.IndexFlatIP(array.shape[1])
    index.add(array)
    faiss.write_index(index, str(_INDEX_FILE))
    _META_FILE.write_text(json.dumps(chunks, indent=2))


def load() -> tuple["faiss.Index", list[dict]]:
    if not _INDEX_FILE.exists():
        raise FileNotFoundError(
            f"No index at {_INDEX_FILE} -- run `python rag/ingest.py` first."
        )
    index = faiss.read_index(str(_INDEX_FILE))
    chunks = json.loads(_META_FILE.read_text())
    return index, chunks


def query(index: "faiss.Index", chunks: list[dict], vector: list[float], k: int) -> list[dict]:
    array = _normalize(np.array([vector], dtype="float32"))
    scores, indices = index.search(array, min(k, index.ntotal))
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        results.append({**chunks[idx], "score": round(float(score), 4)})
    return results

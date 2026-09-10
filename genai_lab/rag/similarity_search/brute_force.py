"""Exact nearest-neighbor search: compare the query against every stored vector.

This is the "flat index" / ground truth every approximate method in this project is benchmarked
against. O(n * dim) per query — accurate, but doesn't scale to large n.
"""

import numpy as np

from metrics import dot_product


class BruteForceIndex:
    """Exact top-K search over unit-normalized vectors using dot product (= cosine similarity)."""

    def __init__(self, vectors: np.ndarray):
        self.vectors = vectors

    def search(self, query: np.ndarray, k: int = 10) -> np.ndarray:
        scores = dot_product(query, self.vectors)
        # argpartition avoids a full O(n log n) sort when we only need the top k
        top_k = np.argpartition(-scores, k)[:k]
        return top_k[np.argsort(-scores[top_k])]

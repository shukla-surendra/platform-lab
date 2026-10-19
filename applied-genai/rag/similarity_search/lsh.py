"""Random-projection Locality-Sensitive Hashing (LSH), implemented from scratch.

Idea: project every vector onto `n_planes` random hyperplanes and keep only the sign of each
projection. Vectors that are close in cosine similarity land on the same side of most planes and
therefore collide into the same hash bucket. A query only needs to be compared against the
(small) bucket it falls into, instead of the whole dataset.

This is approximate — nearby vectors can still land in different buckets — which is the
recall/speed trade-off explored in ../docs/Similarity_Search_Methods/03_Hashing_Based_Methods.md.
"""

import warnings
from collections import defaultdict

import numpy as np

from metrics import dot_product

warnings.filterwarnings("ignore", message=".*encountered in matmul")


class LSHIndex:
    def __init__(self, vectors: np.ndarray, n_planes: int = 12, seed: int = 42):
        self.vectors = vectors
        rng = np.random.default_rng(seed)
        dim = vectors.shape[1]
        self.planes = rng.normal(size=(dim, n_planes)).astype(np.float32)

        self.buckets: dict[tuple, list[int]] = defaultdict(list)
        hashes = self._hash(vectors)
        for i, h in enumerate(hashes):
            self.buckets[h].append(i)

    def _hash(self, vectors: np.ndarray) -> list[tuple]:
        projections = vectors @ self.planes
        signs = (projections > 0).astype(np.int8)
        return [tuple(row) for row in signs]

    def search(self, query: np.ndarray, k: int = 10) -> np.ndarray:
        bucket_key = self._hash(query.reshape(1, -1))[0]
        candidates = self.buckets.get(bucket_key, [])

        if len(candidates) < k:
            # Bucket came up short (common with unlucky splits) — fall back to brute force so
            # the caller always gets k results. A production LSH uses multiple hash tables
            # instead of this fallback; see the doc above for that "multi-probe" approach.
            candidates = list(range(len(self.vectors)))

        candidate_vectors = self.vectors[candidates]
        scores = dot_product(query, candidate_vectors)
        k = min(k, len(candidates))
        top_k_local = np.argpartition(-scores, k - 1)[:k] if k > 0 else np.array([], dtype=int)
        top_k_local = top_k_local[np.argsort(-scores[top_k_local])]
        return np.array(candidates)[top_k_local]

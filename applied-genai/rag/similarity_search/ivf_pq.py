"""Inverted-file + Product Quantization (IVF-PQ), via FAISS.

Two ideas stacked together:
  - IVF (inverted file): k-means-cluster the dataset into `n_clusters` cells, then at query time
    only search the `n_probe` cells nearest the query instead of the whole dataset.
  - PQ (product quantization): split each vector into subvectors and quantize each subvector
    independently against a small codebook, shrinking storage (and speeding up distance
    computation) at the cost of some accuracy.

This is the combination most vector databases reach for at very large scale (hundreds of millions
of vectors) where even HNSW's memory footprint gets expensive. See
../docs/Similarity_Search_Methods/05_Quantization_and_Compression.md for the compression math.
"""

import faiss
import numpy as np


class IVFPQIndex:
    def __init__(
        self,
        vectors: np.ndarray,
        n_clusters: int = 100,
        n_subquantizers: int = 32,
        bits_per_code: int = 8,
        n_probe: int = 8,
    ):
        # n_subquantizers must evenly divide dim (each subvector gets dim / n_subquantizers
        # dimensions) — the default pairs with this project's default dim=128 (4 dims/subvector).
        dim = vectors.shape[1]
        quantizer = faiss.IndexFlatIP(dim)
        self.index = faiss.IndexIVFPQ(
            quantizer, dim, n_clusters, n_subquantizers, bits_per_code, faiss.METRIC_INNER_PRODUCT
        )
        self.index.train(vectors)
        self.index.add(vectors)
        self.index.nprobe = n_probe

    def search(self, query: np.ndarray, k: int = 10) -> np.ndarray:
        _, indices = self.index.search(query.reshape(1, -1), k)
        return indices[0]

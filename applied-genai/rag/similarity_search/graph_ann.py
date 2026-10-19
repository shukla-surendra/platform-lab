"""Graph-based ANN search: HNSW (Hierarchical Navigable Small World), via hnswlib.

HNSW builds a multi-layer graph where each vector is a node, linked to a handful of its nearest
neighbors. A query starts at a sparse top layer and greedily walks toward the query point, then
drops down a layer and repeats — like a skip list over a proximity graph. This is what pgvector,
FAISS, Milvus, Qdrant, and Weaviate all use as their default (or best) ANN index. See
../docs/Similarity_Search_Methods/04_Graph_Based_Methods.md for the construction/search algorithm
and the ef_construction/ef_search/M parameters tuned below.
"""

import hnswlib
import numpy as np


class HNSWIndex:
    def __init__(
        self,
        vectors: np.ndarray,
        M: int = 16,
        ef_construction: int = 200,
        ef_search: int = 50,
    ):
        dim = vectors.shape[1]
        self.index = hnswlib.Index(space="cosine", dim=dim)
        self.index.init_index(max_elements=len(vectors), M=M, ef_construction=ef_construction)
        self.index.add_items(vectors, np.arange(len(vectors)))
        self.index.set_ef(ef_search)

    def search(self, query: np.ndarray, k: int = 10) -> np.ndarray:
        labels, _ = self.index.knn_query(query.reshape(1, -1), k=k)
        return labels[0]

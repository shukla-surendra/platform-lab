"""Synthetic embedding-like datasets for exercising similarity-search methods.

Real embedding models (e.g. the Ollama models used in ../rag_pgvector_local) produce vectors
with the same statistical shape we synthesize here: roughly unit-norm, clustered by semantic
topic. Using synthetic data keeps this project dependency-free (no model download, no network
call) while still exercising every algorithm at a realistic scale.
"""

import numpy as np


def make_dataset(n_vectors: int = 20_000, dim: int = 128, n_clusters: int = 50, seed: int = 0):
    """Generate `n_vectors` unit-normalized vectors arranged in `n_clusters` gaussian blobs.

    Clustering mimics real embeddings, where semantically related items sit near each other —
    this is what makes tree/graph/hash-based indexes faster than brute force in practice.
    Returns (vectors, cluster_ids, centers) as float32 arrays, ready for cosine/dot-product search.
    """
    rng = np.random.default_rng(seed)
    centers = rng.normal(size=(n_clusters, dim))
    centers /= np.linalg.norm(centers, axis=1, keepdims=True)

    cluster_ids = rng.integers(0, n_clusters, size=n_vectors)
    noise = rng.normal(scale=0.15, size=(n_vectors, dim))
    vectors = centers[cluster_ids] + noise
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors.astype(np.float32), cluster_ids, centers.astype(np.float32)


def make_queries(centers: np.ndarray, n_queries: int = 200, seed: int = 1):
    """Generate query vectors from the *same* cluster distribution as `make_dataset`.

    Mirrors how ANN benchmarks (SIFT/GIST/ANN-Benchmarks) construct query sets: held-out samples
    from the indexed distribution, not unrelated random noise. A query unrelated to every indexed
    vector is an unrealistic worst case — real queries (e.g. "what is cosine similarity?" against
    a corpus that discusses it) land near at least one cluster, which is what lets graph/hash/
    quantization-based indexes exploit structure instead of degrading to brute force.
    """
    rng = np.random.default_rng(seed)
    n_clusters, dim = centers.shape
    query_cluster_ids = rng.integers(0, n_clusters, size=n_queries)
    noise = rng.normal(scale=0.15, size=(n_queries, dim))
    queries = centers[query_cluster_ids] + noise
    queries /= np.linalg.norm(queries, axis=1, keepdims=True)
    return queries.astype(np.float32)

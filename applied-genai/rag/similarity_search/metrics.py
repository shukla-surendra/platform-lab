"""The three similarity/distance metrics used throughout this project, from scratch.

See ../docs/Similarity_Search_Methods/01_Vector_Based_Methods_for_Similarity_Search.md for the
math and when to prefer each one.
"""

import warnings

import numpy as np

# Apple's Accelerate BLAS raises spurious "divide by zero"/"overflow" RuntimeWarnings on float32
# matmul even when the result contains no NaN/Inf (numpy/numpy#21150). Harmless on this platform,
# so silence just this message rather than let it drown out real warnings elsewhere.
warnings.filterwarnings("ignore", message=".*encountered in matmul")


def cosine_similarity(query: np.ndarray, vectors: np.ndarray) -> np.ndarray:
    """1.0 = identical direction, 0.0 = orthogonal, -1.0 = opposite. Higher is more similar."""
    query_norm = query / np.linalg.norm(query)
    vectors_norm = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors_norm @ query_norm


def euclidean_distance(query: np.ndarray, vectors: np.ndarray) -> np.ndarray:
    """Straight-line distance. Lower is more similar."""
    return np.linalg.norm(vectors - query, axis=1)


def dot_product(query: np.ndarray, vectors: np.ndarray) -> np.ndarray:
    """Cheapest metric; equivalent to cosine similarity when all vectors are unit-normalized."""
    return vectors @ query

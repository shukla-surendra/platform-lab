"""Tree-based exact/approximate search: KD-Tree and Ball-Tree, via scikit-learn.

Both recursively partition space so a query only has to descend and backtrack through a fraction
of the tree instead of scanning every vector. KD-Tree splits on axis-aligned hyperplanes and
degrades toward brute force as dimensionality grows past a few dozen; Ball-Tree splits on nested
hyperspheres and holds up somewhat better in higher dimensions. See
../docs/Similarity_Search_Methods/02_Tree_Based_Methods.md for why both struggle on real (100+
dim) embeddings — this project uses them mainly as a benchmark data point illustrating that
struggle.
"""

import numpy as np
from sklearn.neighbors import BallTree, KDTree


class TreeIndex:
    def __init__(self, vectors: np.ndarray, kind: str = "kd"):
        if kind not in ("kd", "ball"):
            raise ValueError("kind must be 'kd' or 'ball'")
        self.kind = kind
        tree_cls = KDTree if kind == "kd" else BallTree
        # vectors are unit-normalized, so Euclidean order matches cosine/dot order
        self.tree = tree_cls(vectors, metric="euclidean")

    def search(self, query: np.ndarray, k: int = 10) -> np.ndarray:
        _, indices = self.tree.query(query.reshape(1, -1), k=k)
        return indices[0]

# Cosine Similarity and Inner Product

Cosine similarity measures the angle between two vectors, ignoring their magnitude:

    cosine(a, b) = (a . b) / (||a|| * ||b||)

If both `a` and `b` are first normalized to unit length (`||a|| = ||b|| = 1`), the denominator becomes 1
and cosine similarity reduces to the plain dot product (inner product) `a . b`.

That's why this project normalizes every vector before adding it to the FAISS index and calls
`IndexFlatIP` (inner product) rather than `IndexFlatL2` (Euclidean distance): normalize once at insert
time, and every subsequent inner-product search is already a cosine similarity search, which is cheaper
per query than dividing by norms on every comparison.

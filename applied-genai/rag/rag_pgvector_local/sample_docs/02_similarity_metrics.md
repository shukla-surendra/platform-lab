# Similarity Metrics

The three most common ways to compare two vectors are cosine similarity, Euclidean distance, and dot
product.

Cosine similarity measures the angle between two vectors, ignoring their magnitude: `(A · B) / (||A|| *
||B||)`. A score of 1.0 means identical direction, 0.0 means unrelated, and -1.0 means opposite. It is the
default choice for text embeddings, because embedding magnitude usually reflects text length rather than
meaning.

Euclidean distance measures straight-line distance between two points: `sqrt(sum((a_i - b_i)^2))`. Smaller
distance means more similar. It is sensitive to vector magnitude, which makes it a better fit than cosine
similarity when magnitude itself is meaningful.

Dot product multiplies corresponding elements of two vectors and sums the result. When vectors are
pre-normalized to unit length, dot product and cosine similarity produce the same ranking — this is exactly
why this project normalizes embeddings before storing them, then uses pgvector's cosine-distance operator
`<=>` for search.

# HNSW

Hierarchical Navigable Small World (HNSW) is one of the most popular
Approximate Nearest Neighbor algorithms.

Idea: Instead of comparing every vector, HNSW builds a graph where
nearby vectors are connected. Searching follows graph edges, making
retrieval extremely fast while maintaining high recall.

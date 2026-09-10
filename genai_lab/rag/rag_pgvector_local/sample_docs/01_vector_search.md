# Vector Search

Vector search retrieves items by meaning instead of exact keyword matches. Text, images, or code are first
converted into embeddings — dense numerical vectors where semantically similar items end up close together
in the vector space. A query is embedded the same way, and the search returns the stored vectors nearest to
the query vector.

Comparing a query against every stored vector one by one (brute-force search) is accurate but slow once a
collection reaches millions of vectors. Approximate Nearest Neighbor (ANN) algorithms such as HNSW trade a
small amount of accuracy for much faster search, which is why they power virtually every production vector
database.

Vector search is the retrieval half of Retrieval-Augmented Generation (RAG): it finds the most relevant
chunks of text before an LLM ever sees the question.

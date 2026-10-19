# Embeddings

## What is an Embedding?

An embedding is a dense numerical vector that represents the meaning of
an object (text, image, audio, code, etc.).

Example:

Text:

    I love Python

Embedding:

    [0.13, -0.42, 0.91, ...]

The numbers themselves have no human meaning. Their position relative to
other vectors captures semantic relationships.

## Why do we need embeddings?

Computers cannot understand language directly.

Without embeddings: - "car" != "automobile" - "AI" != "Artificial
Intelligence"

With embeddings: These concepts are mapped close together.

## Properties

-   Fixed-length vectors
-   Capture semantic meaning
-   Enable mathematical comparison
-   Support multilingual understanding (depending on model)

## Applications

-   Semantic search
-   RAG
-   Recommendations
-   Clustering
-   Duplicate detection
-   Classification

## Impact of Embedding Dimensionality

Common sizes: 384 (MiniLM), 768 (BERT-base / E5-base), 1024 (BGE-large),
1536 (OpenAI text-embedding-3-small), 3072 (OpenAI text-embedding-3-large).

Bigger is not free — it trades quality for cost along several axes:

Benefits of higher dimensions:

-   More capacity to capture fine-grained semantic nuance
-   Can separate concepts that a smaller model would collapse together
-   Usually (not always) improves retrieval accuracy, with diminishing
    returns past a point

Costs of higher dimensions:

-   **Storage**: memory/disk scales linearly. 1M vectors at 1536 dims
    (float32) ≈ 6 GB; at 384 dims ≈ 1.5 GB. Multiply by index overhead
    (HNSW graphs typically add 1.5-3x).
-   **Search latency**: distance computation (cosine/dot/Euclidean) is
    O(dimensions), so ANN search and reranking both slow down.
-   **Index build time**: building HNSW/IVF indexes takes longer as
    dimensionality grows.
-   **Network/IO cost**: larger payloads to transfer per query, more
    relevant for hosted vector DBs billed on storage + bandwidth.
-   **Curse of dimensionality**: beyond a point, distances between
    points become less discriminative, which can hurt nearest-neighbor
    quality rather than help it.

Mitigations:

-   **Matryoshka embeddings** (e.g. OpenAI text-embedding-3, Nomic):
    truncate the vector to a smaller prefix (e.g. 3072 → 512) with
    graceful quality degradation, instead of retraining a smaller model.
-   **Dimensionality reduction**: PCA or product quantization (PQ) to
    compress stored vectors while approximating original distances.
-   **Quantization**: store as int8/binary instead of float32 to cut
    storage and speed up search, at some accuracy cost.

Rule of thumb: pick the smallest dimension that meets your accuracy bar
for the target domain — benchmark on your own data (e.g. via MTEB-style
eval) rather than assuming bigger always wins.

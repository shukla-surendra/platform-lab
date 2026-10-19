# Vector Databases

Purpose: Store millions or billions of embeddings efficiently.

Responsibilities: - Store vectors - Build ANN indexes - Execute
nearest-neighbor search - Filter by metadata - Return Top-K matches

Examples: - Databricks Vector Search - FAISS - Milvus - Pinecone -
Weaviate - Qdrant

## What is stored alongside the vector

Embeddings are one-way: there is no model that reliably reconstructs
the original text from just a vector. So the vector DB does not store
the vector alone — each record is `(vector, original_text, metadata)`,
often called the "payload" or "document".

Indexing:

    Text → Embedding Model → Vector
    Store record: { vector, text: "...", metadata: {...} }

Query:

    Query text → Embedding Model → Query Vector
    Nearest-neighbor search → returns matching records
    Each result already includes { text, metadata, score } — no decoding needed

Practical implication: when you query Pinecone/Weaviate/Qdrant/pgvector,
the Top-K results come back with the source text attached (e.g. in a
`metadata.text` field). You read that field directly to build the LLM
prompt — you never convert a vector back into text.

If a system stores vectors with no payload (rare), it keeps a separate
`id → text` lookup table and joins on the IDs returned by the search,
rather than decoding the vector itself.

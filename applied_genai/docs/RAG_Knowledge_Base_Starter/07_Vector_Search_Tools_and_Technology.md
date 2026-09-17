# Vector Search: Tools and Technology

The concepts in the previous pages — embeddings, similarity search, HNSW, RAG — map to a concrete stack of
tools. This page is a reference map of that stack, roughly in pipeline order.

## 1. Embedding models

Turn text (or images/audio/code) into vectors.

| Type | Examples |
|---|---|
| Hosted API | OpenAI `text-embedding-3-*`, Cohere Embed, Voyage AI, Google `text-embedding-004` |
| Open-source / self-hosted | Sentence-Transformers, BAAI BGE, E5, Nomic Embed, Jina Embeddings |

Self-hosted models run locally via the `sentence-transformers` library, or served at scale through
Hugging Face's `text-embeddings-inference`.

## 2. Indexing algorithms (Approximate Nearest Neighbor)

How a database avoids comparing a query vector against every stored vector one by one.

| Algorithm | Idea | Used by |
|---|---|---|
| **HNSW** (see [HNSW](05_HNSW.md)) | Graph of nearby vectors; search follows edges | Qdrant, Weaviate, pgvector, FAISS (default in most modern vector DBs) |
| **IVF** (Inverted File Index) | Clusters vectors, searches only nearby clusters | FAISS, Milvus |
| **Product Quantization (PQ)** | Compresses vectors to shrink memory footprint; often paired with IVF (IVF-PQ) | FAISS, Milvus |
| **DiskANN** | Disk-based ANN index for billion-scale data without holding everything in RAM | Milvus, Azure Cosmos DB |

## 3. Vector databases and libraries

Store vectors and run the ANN search, usually alongside metadata filtering.

| Category | Examples |
|---|---|
| Dedicated vector databases | Pinecone (managed), Weaviate, Qdrant, Milvus/Zilliz, Chroma (popular for local/prototype RAG) |
| Vector search bolted onto an existing database | `pgvector` (Postgres), Redis (vector fields), Elasticsearch/OpenSearch (k-NN plugin), MongoDB Atlas Vector Search |
| Libraries (no server) | FAISS (Meta — the reference ANN library most others build on or benchmark against), Annoy (Spotify), ScaNN (Google) |

## 4. Similarity metrics

Covered in depth in [Similarity Search](03_Similarity_Search.md) and its
[extended version](Similarity_Search_Explanation.md) — summarized here:

| Metric | Notes |
|---|---|
| Cosine similarity | Most common default |
| Dot product | Cheaper to compute; correct once vectors are pre-normalized |
| Euclidean (L2) distance | Straight-line distance; smaller = more similar |

## 5. Orchestration layers

Glue embeddings, the vector store, and the LLM into a retrieval pipeline — chunking, embedding, storing,
retrieving top-K, and feeding the result to an LLM (see [RAG Architecture](06_RAG_Architecture.md)).

- **LangChain** / **LlamaIndex** — retrievers, chunking/splitting utilities, and vector-store integrations
  for most of the databases above.
- **Hand-rolled** — the same pipeline built directly against a vector database's SDK, useful when the
  built-in chunking/retrieval abstractions add more overhead than they save.

## Picking a starting point

| Situation | Reach for |
|---|---|
| Prototyping locally, no infra to stand up | Chroma or FAISS |
| Already running Postgres | `pgvector` |
| Need managed hosting / scale-out without ops work | Pinecone or Weaviate Cloud |
| Billion-vector scale | Milvus or a DiskANN-based system |

## Where this fits with agents

A RAG pipeline is commonly wired into an agent as one **tool** — "search the knowledge base" — the same way
this repo's `task_store.py` sits behind a task-management tool (see
[Chapter 4 — Tools & Agents](../04-tools-and-agents.md)). The vector database plays the role `task_store.py`
plays for tasks: the agent never talks to it directly, only through the tool boundary.

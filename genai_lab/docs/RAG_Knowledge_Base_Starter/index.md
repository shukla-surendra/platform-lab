# RAG Knowledge Base Starter

A short set of standalone notes on the concepts behind **Retrieval-Augmented Generation (RAG)**: how text
gets turned into vectors, how those vectors are searched and stored, and how the pieces combine into a RAG
pipeline. Unlike the numbered [agentic development tutorial](../index.md), these pages are independent
reference notes rather than a sequential, code-backed course — read them in order for a linear introduction,
or jump straight to whichever concept you need.

| # | Page | Covers |
|---|------|--------|
| 0 | [Mathematics Foundations](Mathematics_Foundations_for_Similarity_Search.md) | Vectors, norms, dot product, cosine/Euclidean/Manhattan distance, curse of dimensionality, glossary — from first principles |
| 1 | [Embeddings](01_Embeddings.md) | What an embedding is, and why it captures meaning as a vector |
| 2 | [Why Embedding Models Are Needed](02_Why_Embedding_Models_Are_Needed.md) | Why embeddings must be learned, not hand-assigned |
| 3 | [Similarity Search](03_Similarity_Search.md) | The query → embed → nearest-neighbor → top-K pipeline |
| — | [Similarity Search, in depth](Similarity_Search_Explanation.md) | A longer walkthrough with worked examples and a keyword-vs-similarity comparison |
| 4 | [Vector Databases](04_Vector_Databases.md) | What a vector database is responsible for, and common options |
| 5 | [HNSW](05_HNSW.md) | The graph-based ANN algorithm most vector databases use under the hood |
| 6 | [RAG Architecture](06_RAG_Architecture.md) | How chunking, embedding, retrieval, and generation fit together end to end |
| — | [Chunking Strategies, In Depth](Chunking_Strategies_In_Depth.md) | Fixed-size, recursive, semantic, structure-aware, parent-document, contextual, and late chunking — trade-offs, code, and how to choose a chunk size empirically |
| 7 | [Vector Search: Tools and Technology](07_Vector_Search_Tools_and_Technology.md) | A reference map of embedding models, ANN algorithms, vector databases, and orchestration layers |
| 8 | [Interview Questions (101, with Answers)](08_Interview_Questions.md) | Senior/staff-level Q&A on embeddings, similarity metrics, ANN algorithms, vector DB design, and RAG — with example code |

Azure AI Search (Microsoft's managed search service — Index/Indexer/Skillset,
why skillsets exist, and a full step-by-step PDF-from-Blob-Storage setup)
outgrew a single chapter here and now has its own folder:
[`Azure_AI_Search/`](../Azure_AI_Search/index.md).

## How this relates to the agent tutorial

The [main tutorial](../index.md) covers agents that call **tools** ([Chapter 4](../04-tools-and-agents.md))
and reach external systems over **MCP** ([Chapter 11](../11-mcp-agentic-capabilities.md)). A RAG pipeline is
commonly wired into an agent as exactly one such tool — "search the knowledge base" — with the vector
database sitting behind it the same way `task_store.py` sits behind this repo's task tools. These notes are
the background you'd want before building that tool.

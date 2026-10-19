# Similarity Search Methods

A deep dive into *how* similarity search actually works under the hood: the algorithm families
behind every vector database and ANN library, the math and trade-offs behind each one, and a
runnable benchmark comparing them head to head.

This complements the [RAG Knowledge Base](../RAG_Knowledge_Base_Starter/index.md), which
introduces similarity search, embeddings, and HNSW at a conceptual level as background for
building a RAG pipeline. These pages assume that background and go one level deeper — into the
full landscape of indexing strategies (not just HNSW), their internal mechanics, and how to
actually choose between them. The runnable code behind every algorithm discussed here lives in
[`../../similarity_search/`](../../similarity_search/README.md) — read the docs for the "why,"
run the code for the "how it actually behaves."

| # | Page | Covers |
|---|------|--------|
| 1 | [Vector-Based Methods for Similarity Search](01_Vector_Based_Methods_for_Similarity_Search.md) | The full taxonomy — flat/exact, tree-based, hashing-based, graph-based, and quantization-based methods — with the math, pseudocode, and complexity behind each |
| 2 | [Tree-Based Methods](02_Tree_Based_Methods.md) | KD-Tree, Ball-Tree, VP-Tree — how they partition space, and why they lose to brute force in high dimensions |
| 3 | [Hashing-Based Methods](03_Hashing_Based_Methods.md) | Locality-Sensitive Hashing (LSH) — random projection, MinHash, multi-probe |
| 4 | [Graph-Based Methods](04_Graph_Based_Methods.md) | HNSW and Navigable Small World graphs — the construction and search algorithm behind most production vector databases |
| 5 | [Quantization and Compression](05_Quantization_and_Compression.md) | Scalar quantization, Product Quantization (PQ), OPQ, and IVF — trading recall for memory and speed |
| 6 | [Choosing an Algorithm and Benchmarking It](06_Choosing_and_Benchmarking.md) | A decision guide by dataset size/dimensionality/recall target, plus how to measure recall@k, QPS, and latency yourself |
| 7 | [Tools, Libraries, and Interview Questions](07_Tools_Libraries_and_Interview_Questions.md) | FAISS, hnswlib, Annoy, ScaNN, pgvector, Milvus, Qdrant, Weaviate compared; Q&A for interview prep |
| 8 | [Databricks Vector Search](08_Databricks_Vector_Search.md) | A concrete platform case study — index types, the L2/cosine-equivalence formula, hybrid search + RRF, endpoint sizing — mapped back onto the general concepts above, with claims verified in a companion notebook |
| 9 | [Additional Methods, Re-Ranking, and the Full Taxonomy](09_Additional_Methods_Reranking_and_Taxonomy.md) | ScaNN, DiskANN/Vamana, cross-encoder re-ranking, the full metrics list (Manhattan/Jaccard/Hamming/Pearson), a system-to-algorithm reference table, and a suggested learning order |
| 10 | [FAISS Index Types](10_FAISS_Index_Types.md) | FAISS is a toolbox, not one algorithm — which index class (`Flat`, `HNSW`, `IVFFlat`, `IVFPQ`) to pick, why IVF+PQ combine but HNSW+IVF don't, and a dataset-size decision table |

## How this maps to the code

| Method | Doc | Code |
|---|---|---|
| Brute force (flat, exact) | [01](01_Vector_Based_Methods_for_Similarity_Search.md#4-flat-brute-force-search) | [`brute_force.py`](../../similarity_search/brute_force.py) |
| KD-Tree / Ball-Tree | [02](02_Tree_Based_Methods.md) | [`tree_methods.py`](../../similarity_search/tree_methods.py) |
| Random-projection LSH | [03](03_Hashing_Based_Methods.md) | [`lsh.py`](../../similarity_search/lsh.py) |
| HNSW | [04](04_Graph_Based_Methods.md) | [`graph_ann.py`](../../similarity_search/graph_ann.py) |
| IVF + Product Quantization | [05](05_Quantization_and_Compression.md) | [`ivf_pq.py`](../../similarity_search/ivf_pq.py) |
| Recall@k / latency benchmarking | [06](06_Choosing_and_Benchmarking.md) | [`benchmark.py`](../../similarity_search/benchmark.py) |
| Databricks similarity score / RRF fusion, verified | [08](08_Databricks_Vector_Search.md) | [`databricks_vector_search.ipynb`](../../similarity_search/databricks_vector_search.ipynb) |

## Prerequisites

Comfort with vectors, dot product, cosine similarity, and Euclidean distance at the level of the
RAG Knowledge Base's
[Mathematics Foundations](../RAG_Knowledge_Base_Starter/Mathematics_Foundations_for_Similarity_Search.md)
page. No prior ANN-algorithm knowledge assumed.

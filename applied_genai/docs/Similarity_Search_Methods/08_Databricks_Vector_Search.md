# Databricks Vector Search

A managed vector database built into the Databricks platform (recently renamed **AI Search**).
Everything on this page is documented by Databricks at
[docs.databricks.com/aws/en/ai-search/ai-search](https://docs.databricks.com/aws/en/ai-search/ai-search),
[databricks.com/blog/what-is-vector-database](https://www.databricks.com/blog/what-is-vector-database),
and [databricks.com/blog/vector-search](https://www.databricks.com/blog/vector-search) — this page
maps that platform-specific terminology back onto the algorithm-level concepts covered elsewhere in
this doc set. The companion notebook,
[`../../similarity_search/databricks_vector_search.ipynb`](../../similarity_search/databricks_vector_search.ipynb),
verifies two of the concrete claims below (the L2/cosine ranking equivalence, and Reciprocal Rank
Fusion) by implementing them against this project's own vectors — this environment has no
Databricks workspace to query, so that notebook grounds the concepts in code that actually runs,
rather than untested API examples.

## Architecture, in this project's terms

Same three stages as every method in
[01_Vector_Based_Methods_for_Similarity_Search.md](01_Vector_Based_Methods_for_Similarity_Search.md):
embed → index → query. What Databricks adds is everything *around* that: managed embedding
computation, automatic sync from Delta tables, Unity Catalog governance, and a serverless query
endpoint — not a new search algorithm. The ANN algorithm underneath is documented as **HNSW**, the
same algorithm in [`graph_ann.py`](../../similarity_search/graph_ann.py) and
[04_Graph_Based_Methods.md](04_Graph_Based_Methods.md).

## The similarity score formula

Databricks documents the index as using **L2 (Euclidean) distance** internally, converted to a
score via:

```
similarity_score = 1 / (1 + distance²)
```

with the documented claim that *when vectors are normalized, L2-distance ranking is identical to
cosine-similarity ranking* — you get cosine semantics from an L2-native index for free, as long as
you normalize embeddings before indexing. This is exactly the normalization fact covered generally
in [01_Vector_Based_Methods_for_Similarity_Search.md §3](01_Vector_Based_Methods_for_Similarity_Search.md#3-similarity-metrics-revisited)
(where dot product on normalized vectors equals cosine similarity) — Databricks made a different
but equivalent choice (L2 instead of dot product), which the companion notebook confirms produces
an identical top-10 ranking to cosine similarity across 20 test queries on this project's synthetic
data.

## Index types

| Index type | Who computes embeddings | Sync |
|---|---|---|
| **Delta Sync Index (Databricks-managed)** | Platform, via a specified model serving endpoint | Automatic, on source Delta table change |
| **Delta Sync Index (self-managed)** | You, pre-computed into a Delta table column | Automatic |
| **Direct Vector Access Index** | You, via API calls | Manual — you push updates yourself |
| **Full-text search (storage-optimized, Beta)** | N/A — keyword-only | N/A |

The first three all sit on the same underlying HNSW index; they differ only in *who produces
embeddings* and *how index freshness is maintained* — the "Direct Vector Access" pattern is
architecturally the same problem this project's `HNSWIndex(vectors)` (rebuild on change) solves by
hand, just with a managed API instead of re-running a script.

## Hybrid search: BM25 + vector, fused with RRF

Databricks combines dense vector search with sparse keyword search (**Okapi BM25** — good for
exact terms like product codes and IDs that embeddings tend to blur together), merging the two
rankings with **Reciprocal Rank Fusion (RRF)**, `rrf_param=60`:

```
RRF_score(doc) = Σ over each ranked list of  1 / (60 + rank_in_that_list)
```

A document that ranks well in *either* signal contributes meaningfully; a document ranking well in
*both* accumulates both contributions and rises to the top — without requiring BM25 scores and
cosine similarities to be on a comparable numeric scale, since RRF only uses rank *position*. The
companion notebook implements this exact formula and demonstrates the effect on a toy example.

## Endpoint sizing = the same recall/memory trade-off, packaged differently

| | Standard endpoint | Storage-optimized endpoint |
|---|---|---|
| Capacity | ~320M vectors @ 768 dims | > 1B vectors |
| Indexing speed | baseline | 10–20x faster |
| Query latency | lower | +~250ms |

This is the same trade-off covered generally in
[05_Quantization_and_Compression.md](05_Quantization_and_Compression.md) and
[06_Choosing_and_Benchmarking.md](06_Choosing_and_Benchmarking.md): past a certain scale, keeping
every vector's full-precision HNSW graph in memory stops being affordable, and the system has to
compress or restructure. Databricks exposes that trade-off as an endpoint-sizing choice (standard
vs. storage-optimized); this project's [`ivf_pq.py`](../../similarity_search/ivf_pq.py) exposes the
same trade-off as index parameters (`n_subquantizers`, `n_probe`) you tune yourself with FAISS.

## Documented limits worth knowing

- 50 indexes per endpoint, 500 endpoints per workspace
- Max embedding dimension: 4096
- Max results: 10,000 for ANN queries, 200 for hybrid/full-text queries
- Max row size: 100KB (Delta Sync indexes)
- Encrypted at rest (AES-256) and in transit (TLS 1.2+); row/column-level permissions are not
  supported natively — access control is implemented at the application layer

## How this maps back to the rest of this doc set

| Databricks concept | General concept | Where it's covered here |
|---|---|---|
| HNSW-backed index | Graph-based ANN | [04_Graph_Based_Methods.md](04_Graph_Based_Methods.md) |
| `similarity_score = 1/(1+distance²)` on normalized vectors | Cosine similarity via dot product on normalized vectors | [01 §3](01_Vector_Based_Methods_for_Similarity_Search.md#3-similarity-metrics-revisited) |
| Storage-optimized endpoint | Quantization / compression for memory-constrained scale | [05_Quantization_and_Compression.md](05_Quantization_and_Compression.md) |
| Hybrid search + RRF | Combining keyword and vector retrieval | [09_Additional_Methods_Reranking_and_Taxonomy.md](09_Additional_Methods_Reranking_and_Taxonomy.md#hybrid-search) |
| Delta Sync / Direct Vector Access | Index freshness / rebuild strategy | This page, above |

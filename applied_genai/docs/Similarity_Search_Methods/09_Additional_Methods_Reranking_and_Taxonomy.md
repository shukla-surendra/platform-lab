# Additional Methods, Re-Ranking, and the Full Taxonomy

The other pages in this doc set go deep on the five families this project actually implements and
benchmarks (flat, tree, hash, graph, quantization — see
[01_Vector_Based_Methods_for_Similarity_Search.md](01_Vector_Based_Methods_for_Similarity_Search.md)).
This page rounds out the picture with the algorithms and techniques that show up constantly in
practice and in interviews but aren't implemented in this project's code: ScaNN, DiskANN, and
cross-encoder re-ranking — plus a full taxonomy tree, a system-to-algorithm reference table, and a
suggested learning order tying every page in this doc set together.

## Two More ANN Algorithms Worth Knowing

### ScaNN (Google)

Google's ANN library, optimized for both CPU and TPU. Combines three ideas already covered
individually on other pages into one pipeline:

1. **Tree/cluster partitioning** — like IVF (see [01 §9](01_Vector_Based_Methods_for_Similarity_Search.md#9-hybrid-methods-ivf-anything)), narrow the search to a subset of the dataset first.
2. **Anisotropic quantization** — a refinement of Product Quantization (see
   [05_Quantization_and_Compression.md](05_Quantization_and_Compression.md)) that weights
   quantization error by how much it would actually distort the final similarity ranking, rather
   than treating all reconstruction error as equally bad — this is ScaNN's key research
   contribution over plain PQ.
3. **Re-ranking** — a final exact-distance pass over a small shortlist of candidates (see
   [Re-Ranking](#re-ranking-with-cross-encoders) below) to recover precision lost to quantization.

ScaNN doesn't introduce a fundamentally new search primitive — it's a well-tuned composition of
techniques this doc set already covers individually, which is exactly why understanding IVF, PQ,
and re-ranking generally transfers directly to understanding what ScaNN (or any similarly-composed
production system) is doing.

### DiskANN / Vamana (Microsoft)

A graph-based method (same family as HNSW — see
[04_Graph_Based_Methods.md](04_Graph_Based_Methods.md)) purpose-built for datasets too large to
fit in RAM. The underlying graph construction algorithm is called **Vamana**; DiskANN is the
system built around it that keeps most vectors on **SSD** rather than in memory, using the SSD's
much higher random-read throughput (compared to spinning disk) to make graph traversal against
disk-resident data practical. Where HNSW assumes the whole graph and all vectors fit in RAM, and
IVF-PQ compresses vectors to make more of them *fit* in RAM, DiskANN instead accepts that not
everything can be memory-resident and re-architects the graph traversal around that constraint —
the right tool once a dataset is too large for either of the other two strategies to keep in
memory even after compression. Milvus supports DiskANN as an index option; it's also the algorithm
family behind Microsoft's own large-scale internal vector search systems.

## Re-Ranking with Cross-Encoders

Every method in this doc set so far is a **bi-encoder** approach: the query and every document are
embedded *independently*, and similarity is a cheap function (dot product, cosine, L2) of the two
resulting vectors. That independence is exactly what makes ANN search possible — document
embeddings can be precomputed and indexed once, long before any query arrives.

A **cross-encoder** instead takes the query and a *specific* candidate document together as joint
input to a (usually transformer-based) model, which directly outputs a relevance score. This is
much more accurate — the model can attend to interactions between query and document tokens that
two independently-computed vectors can never capture — but it's also far more expensive: it can't
be precomputed, and it must run once per (query, candidate) pair.

```
ANN search (bi-encoder, cheap, approximate)
        │
Top 50-100 candidates
        │
        ▼
Cross-encoder re-ranking (expensive, precise)
        │
Top 10 final results
```

The standard production pattern — used in RAG pipelines, enterprise search, and recommendation
systems alike — is exactly this two-stage funnel: use a cheap ANN index (any method from
[01_Vector_Based_Methods_for_Similarity_Search.md](01_Vector_Based_Methods_for_Similarity_Search.md))
to cut millions of candidates down to a shortlist of 50–100, then run the expensive cross-encoder
only on that shortlist. This is not implemented in this project's code (no cross-encoder model is
bundled here — see [`../../rag_pgvector_local`](../../rag_pgvector_local/README.md) for a project
that does call a real model, for embeddings), but it's essential context for evaluating recall@k
numbers honestly: an ANN index's job is to get the right answer *into* the shortlist, not
necessarily to rank it first — re-ranking is what fixes ordering within that shortlist.

## Hybrid Search

Covered concretely for one specific platform in
[08_Databricks_Vector_Search.md](08_Databricks_Vector_Search.md#hybrid-search-bm25-vector-fused-with-rrf),
generalized here: **hybrid search** combines keyword-based retrieval (BM25 or similar) with
vector/embedding-based retrieval, on the reasoning that they fail in complementary ways — keyword
search misses synonyms and paraphrases but nails exact identifiers (product codes, part numbers,
acronyms) that embeddings tend to blur together; vector search does the reverse. The two ranked
lists are typically merged with **Reciprocal Rank Fusion (RRF)**, which combines rankings using
only rank position (not raw scores), making it robust to the two rankers producing scores on
totally different, incomparable scales.

## Additional Similarity Metrics

[01_Vector_Based_Methods_for_Similarity_Search.md §3](01_Vector_Based_Methods_for_Similarity_Search.md#3-similarity-metrics-revisited)
and [`metrics.py`](../../similarity_search/metrics.py) cover the three metrics this project
actually implements and uses (cosine, Euclidean, dot product) — the ones relevant to dense
embedding vectors. A few more come up constantly in broader similarity-search contexts:

| Metric | Best for | Notes |
|---|---|---|
| Manhattan (L1) distance | Sparse, high-cardinality features | Sum of absolute per-dimension differences; less sensitive to outlier dimensions than Euclidean |
| Jaccard similarity | Sets, document overlap | `\|A ∩ B\| / \|A ∪ B\|` — what MinHash (see [03_Hashing_Based_Methods.md](03_Hashing_Based_Methods.md#minhash-different-data-same-idea)) is built to approximate at scale |
| Hamming distance | Binary vectors, hashed codes | Counts differing bits — the natural metric once vectors have been reduced to binary sign codes, as in the LSH bucket keys in [`lsh.py`](../../similarity_search/lsh.py) |
| Pearson correlation | Statistical/tabular data | Measures linear relationship between two variables' *fluctuations*, not raw magnitude — common in recommender systems comparing user rating patterns rather than embeddings |

None of these four are implemented in this project — they apply to sets, binary codes, or
statistical data rather than the dense unit-norm embedding vectors this project's code operates on
— but they're worth recognizing by name, especially Jaccard and Hamming, which pair naturally with
the hashing-based methods already covered in [03_Hashing_Based_Methods.md](03_Hashing_Based_Methods.md).

## System-to-Algorithm Reference

Expands on the tool tables in
[07_Tools_Libraries_and_Interview_Questions.md](07_Tools_Libraries_and_Interview_Questions.md)
with a couple more systems and their typical underlying index:

| System | Typical indexing/search method |
|---|---|
| FAISS | Toolbox — you pick one index class (Flat, HNSW, IVFFlat, or IVFPQ) per collection, see [10](10_FAISS_Index_Types.md) |
| Milvus | HNSW, IVF, DiskANN — configurable per collection, same "pick one" model as FAISS |
| Qdrant | HNSW |
| Weaviate | HNSW |
| pgvector | HNSW (also supports IVFFlat) |
| Pinecone | Proprietary ANN (graph/quantization techniques, implementation not public) |
| Chroma | HNSW (via an underlying library, typically hnswlib) |
| Elasticsearch | HNSW (via Lucene's vector search support) |
| OpenSearch | HNSW |
| Databricks Vector Search | Managed HNSW (see [08](08_Databricks_Vector_Search.md)) |
| ScaNN | Tree/cluster partitioning + anisotropic PQ + re-ranking |
| DiskANN | Vamana graph, SSD-resident |

The pattern worth internalizing: **HNSW is the default nearly everywhere.** Almost every name in
this table reduces, underneath, to "HNSW, plus a governance/persistence/scaling layer" — which is
exactly the point made in [08_Databricks_Vector_Search.md](08_Databricks_Vector_Search.md) about
Databricks specifically, and generalizes to the rest of the list.

## The Full Taxonomy

```
Similarity Search
│
├── Exact Search
│   ├── Brute force / flat            → 01 §4, brute_force.py
│   └── k-NN (brute force + top-k)    → same as above, k is just the result-count parameter
│
├── Approximate Nearest Neighbor (ANN)
│   │
│   ├── Tree-based                    → 02_Tree_Based_Methods.md
│   │   ├── KD-Tree                   → tree_methods.py
│   │   ├── Ball-Tree                 → tree_methods.py
│   │   └── VP-Tree / Cover Tree      → 02, "VP-Tree" section
│   │
│   ├── Hash-based                    → 03_Hashing_Based_Methods.md
│   │   ├── Random-projection LSH     → lsh.py
│   │   └── MinHash (set similarity)  → 03, "MinHash" section
│   │
│   ├── Graph-based                   → 04_Graph_Based_Methods.md
│   │   ├── NSW                       → 04, "Navigable Small World" section
│   │   ├── HNSW                      → graph_ann.py
│   │   └── DiskANN / Vamana          → this page, "DiskANN / Vamana" section
│   │
│   └── Cluster / quantization-based  → 05_Quantization_and_Compression.md
│       ├── IVF-Flat                  → 05, "IVF" section
│       ├── Product Quantization (PQ) → 05, "Product Quantization" section
│       ├── IVF-PQ                    → ivf_pq.py
│       └── ScaNN                     → this page, "ScaNN" section
│
└── Hybrid Retrieval
    ├── BM25 + Vector Search (RRF)    → this page, "Hybrid Search"; 08 for a concrete example
    └── Re-ranking (cross-encoders)   → this page, "Re-Ranking with Cross-Encoders"
```

## Suggested Learning Order

If you're working through this doc set for the first time (or studying for an interview — see
[07's Q&A](07_Tools_Libraries_and_Interview_Questions.md#interview-questions)), this order builds
each concept on the last:

1. **Similarity metrics** — cosine, dot product, Euclidean ([01 §3](01_Vector_Based_Methods_for_Similarity_Search.md#3-similarity-metrics-revisited))
2. **Exact search** — brute force, k-NN ([01 §4](01_Vector_Based_Methods_for_Similarity_Search.md#4-flat-brute-force-search))
3. **ANN concepts and trade-offs** — why approximate, recall@k, the decision guide ([06](06_Choosing_and_Benchmarking.md))
4. **HNSW** — the most widely used graph-based ANN index ([04](04_Graph_Based_Methods.md))
5. **IVF and Product Quantization** — the memory/recall trade-off at scale ([05](05_Quantization_and_Compression.md))
6. **Hybrid search** — BM25 + vectors, RRF fusion ([this page](#hybrid-search); [08](08_Databricks_Vector_Search.md) for a worked platform example)
7. **Re-ranking with cross-encoders** — the precision pass on top of everything above ([this page](#re-ranking-with-cross-encoders))

By the end of that path you've covered what the vast majority of production vector search systems
in [the table above](#system-to-algorithm-reference) actually do under the hood.

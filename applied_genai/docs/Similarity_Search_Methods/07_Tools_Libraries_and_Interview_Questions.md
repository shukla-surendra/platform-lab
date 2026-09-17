# Tools, Libraries, and Interview Questions

## Libraries Used in This Project

| Library | What it provides | Used for |
|---|---|---|
| [`scikit-learn`](https://scikit-learn.org/) | `KDTree`, `BallTree` | [`tree_methods.py`](../../similarity_search/tree_methods.py) |
| [`hnswlib`](https://github.com/nmslib/hnswlib) | HNSW, C++ core with Python bindings | [`graph_ann.py`](../../similarity_search/graph_ann.py) |
| [`faiss`](https://github.com/facebookresearch/faiss) | Flat, IVF, PQ, and HNSW indexes; the industry-standard ANN toolkit | [`ivf_pq.py`](../../similarity_search/ivf_pq.py) |
| `numpy` | Brute force, LSH — both implemented from scratch | [`brute_force.py`](../../similarity_search/brute_force.py), [`lsh.py`](../../similarity_search/lsh.py) |

## Standalone ANN Libraries

| Library | Algorithms | Notes |
|---|---|---|
| **FAISS** (Meta) | Flat, IVF, PQ, HNSW — pick one index class per collection, see [10_FAISS_Index_Types.md](10_FAISS_Index_Types.md) | The most complete single toolkit; GPU support; no persistence/server built in — you wire it into your own service |
| **hnswlib** | HNSW only | Minimal, fast, easy to embed; what this project uses for HNSW |
| **Annoy** (Spotify) | Random-projection forest (similar family to LSH/tree-based) | Read-only after build, memory-mapped — good fit for static datasets rebuilt periodically |
| **ScaNN** (Google) | Anisotropic vector quantization + a proprietary partitioning scheme | State-of-the-art recall/speed in Google's own benchmarks; less common outside GCP-adjacent stacks |

## Vector Databases

Libraries like FAISS give you an index; a **vector database** wraps one (or several) of these
indexes with persistence, metadata filtering, CRUD, replication, and a query API — the difference
between "an algorithm" and "a system you can build a product on."

| Database | Default/primary index | Notes |
|---|---|---|
| **pgvector** | HNSW (also supports IVFFlat) | Runs inside Postgres — see [`../../rag_pgvector_local`](../../rag_pgvector_local/README.md) for this repo's own local, Docker-based example |
| **Qdrant** | HNSW | Rust-based, filterable payloads, popular for self-hosted RAG |
| **Weaviate** | HNSW | Built-in modules for calling out to embedding models directly |
| **Milvus** | Configurable — HNSW, IVF-PQ, and others | Designed for very large scale, distributed deployments |
| **Pinecone** | Proprietary (managed service) | No self-hosting; trades control for zero ops |

See the RAG Knowledge Base's
[Vector Search: Tools and Technology](../RAG_Knowledge_Base_Starter/07_Vector_Search_Tools_and_Technology.md)
page for a broader map that also covers embedding models and orchestration layers, not just the
ANN/database layer this page focuses on.

## Interview Questions

**Q: What's the difference between exact and approximate nearest-neighbor search, and why does
almost every production system use the approximate kind?**
A: Exact (kNN) search guarantees the true top-k but costs O(n·d) per query; approximate (ANN)
search trades a small, measurable amount of recall for large speedups (often orders of magnitude),
which is necessary once n reaches the millions-to-billions scale typical of real embedding
collections.

**Q: Why do KD-Trees perform worse than brute force on 128-dimensional embeddings?**
A: KD-Tree search relies on pruning branches whose splitting hyperplane is provably farther from
the query than the current best answer. As dimensionality grows, a query point ends up close to
many hyperplanes simultaneously (distances concentrate — the "curse of dimensionality"), so that
pruning test rarely succeeds, and the algorithm ends up visiting nearly every branch anyway, with
extra traversal overhead on top of what a flat scan would cost.

**Q: Explain how HNSW achieves logarithmic search time.**
A: HNSW builds a hierarchy of proximity graphs, sparse at the top layer and dense at the bottom
(every vector). Search starts at the sparse top layer and greedily walks toward the query, then
drops down a layer and repeats. The sparse upper layers let a query cover large distances in a few
hops before refining in the dense lower layers — analogous to a skip list built over a navigable
small-world graph.

**Q: What do `ef_construction`, `ef_search`, and `M` control in HNSW, and which one can you tune
without rebuilding the index?**
A: `M` is the max edges per node per layer (build-time, more memory/better recall); `ef_construction`
is the candidate list size used while building the graph (build-time, better graph quality);
`ef_search` is the candidate list size used at query time — the only one of the three that's a
runtime knob, letting you trade recall for latency per query without rebuilding.

**Q: What is Product Quantization, and why is it faster than computing exact distances, not just
smaller in memory?**
A: PQ splits each vector into subvectors and replaces each with the index of its nearest centroid
in a small, pre-trained codebook. At search time, using asymmetric distance computation, the
distance from the query to each codebook centroid is computed once per subvector position (a small
lookup table); each stored vector's approximate distance to the query is then just a sum of
lookup-table values, avoiding floating-point distance computation against full vectors entirely —
speed comes from replacing math with table lookups, memory savings from storing codes instead of
floats.

**Q: What's the difference between IVF-Flat and IVF-PQ?**
A: Both partition the dataset into cells via k-means and only search the `n_probe` cells nearest
the query at search time. IVF-Flat stores full-precision vectors within each cell (higher recall,
more memory); IVF-PQ additionally compresses each cell's vectors with Product Quantization (much
less memory, more recall lost to quantization error).

**Q: A recall@10 benchmark shows Method A at 0.95 recall / 2ms latency and Method B at 0.99 recall
/ 8ms latency. How do you decide which to ship?**
A: There's no universally correct answer — it depends on the application's tolerance for missed
results versus latency budget. For a user-facing autocomplete, 2ms might be the binding constraint
and 0.95 recall is plenty. For a legal-document RAG system where missing the one relevant precedent
is costly, the 4x latency cost for 0.99 recall may be clearly worth it. The right answer comes from
the product requirement, not the benchmark table alone — this is the "Pareto frontier" framing in
[06_Choosing_and_Benchmarking.md](06_Choosing_and_Benchmarking.md).

**Q: Why is cosine similarity typically implemented as a dot product in ANN libraries (FAISS's
`METRIC_INNER_PRODUCT`, pgvector's `<#>`)?**
A: Cosine similarity is `(A·B) / (‖A‖‖B‖)`. If every vector is pre-normalized to unit length at
insert time, `‖A‖ = ‖B‖ = 1`, so the formula reduces exactly to `A·B` — a plain dot product, which
is cheaper to compute at query time than recomputing norms for every comparison.

**Q: When would you choose LSH over HNSW despite HNSW's better recall/latency profile?**
A: When you need an index with no training/build-graph step and minimal implementation complexity
(LSH is a few dozen lines over numpy, see [`lsh.py`](../../similarity_search/lsh.py)), when the
dataset changes so frequently that HNSW's graph-maintenance cost is unattractive, or when you want
buckets that shard trivially across machines (each bucket is independent, unlike a graph that spans
the whole dataset).

**Q: Your ANN index is returning good recall in offline benchmarks but users report missing
"obvious" results in production. What's the likely mismatch, and how would you diagnose it?**
A: The most common cause is a mismatch between the benchmark's query distribution and real user
queries — see [`data.py`](../../similarity_search/data.py)'s docstring on this exact pitfall:
benchmarking with queries unrelated to the indexed data (or drawn from a different distribution
than production traffic) produces recall numbers that don't reflect real-world behavior. Diagnose
by re-running the benchmark using actual logged production queries (or a representative sample) as
the query set, not synthetic or held-out-training-set queries.

# Vector-Based Methods for Similarity Search

## Table of Contents

1. What "Vector-Based" Means
2. The Core Problem: Nearest Neighbor Search
3. Similarity Metrics, Revisited
4. Flat / Brute-Force Search
5. Tree-Based Methods (Overview)
6. Hashing-Based Methods (Overview)
7. Graph-Based Methods (Overview)
8. Quantization-Based Methods (Overview)
9. Hybrid Methods: IVF + Anything
10. Comparison Table
11. Complexity Cheat Sheet
12. Choosing a Family
13. Key Takeaways

------------------------------------------------------------------------

# 1. What "Vector-Based" Means

Every method in this document operates on the same representation: an item (text, image, audio,
product, user) reduced to a fixed-length **vector** — a point in a high-dimensional space —
usually produced by an embedding model. "Vector-based similarity search" is the umbrella term for
*any* algorithm that finds nearest neighbors in that space, as opposed to:

- **Keyword-based search** (inverted indexes, BM25) — matches tokens, not meaning.
- **Rule-based matching** — hand-written filters and heuristics.

Within vector-based search, the methods differ only in *how they avoid comparing the query against
every single stored vector*. That's the entire design problem this document is about: brute force
is always correct, but O(n) per query doesn't scale — everything else is a strategy for trading a
little accuracy for a lot of speed.

------------------------------------------------------------------------

# 2. The Core Problem: Nearest Neighbor Search

Given a query vector `q` and a set of `n` stored vectors, return the `k` vectors most similar to
`q` — this is **k-Nearest Neighbor (k-NN) search**.

```
Query vector q
      │
      ▼
 ┌─────────────────────────────┐
 │  n stored vectors (index)   │
 └─────────────────────────────┘
      │
      ▼
Top-K most similar vectors
```

Two flavors:

| | Exact (kNN) | Approximate (ANN) |
|---|---|---|
| Guarantee | Always the true top-k | Usually the true top-k (measured as **recall@k**) |
| Speed at scale | Degrades linearly with n | Sub-linear, often near-constant with tuning |
| Used when | n is small, or correctness is non-negotiable | n is large (the common case for embeddings) |

Almost every production vector database defaults to ANN, because at the scale embeddings are
actually used (thousands to billions of vectors), exact search is too slow — see
[§11 Complexity Cheat Sheet](#11-complexity-cheat-sheet).

------------------------------------------------------------------------

# 3. Similarity Metrics, Revisited

Every method below needs a way to score "how close." The three in practical use (see
[`metrics.py`](../../similarity_search/metrics.py) for from-scratch implementations):

| Metric | Formula | Range | Notes |
|---|---|---|---|
| Cosine similarity | `(A·B) / (‖A‖‖B‖)` | [-1, 1], higher = more similar | Ignores magnitude, compares direction only |
| Euclidean (L2) distance | `‖A - B‖` | [0, ∞), lower = more similar | Straight-line distance |
| Dot product | `A·B` | (-∞, ∞), higher = more similar | Cheapest to compute; equals cosine similarity when both vectors are unit-normalized |

Most embedding models output (or are trained expecting) unit-normalized vectors, which is why
dot product and cosine similarity are used almost interchangeably in ANN libraries — FAISS's
`METRIC_INNER_PRODUCT` and pgvector's `<#>` operator are both just dot product, correct for
normalized vectors and much cheaper than computing a norm at query time.

------------------------------------------------------------------------

# 4. Flat / Brute-Force Search

The baseline every other method is measured against.

```python
def brute_force_search(query, vectors, k):
    scores = vectors @ query          # dot product against every stored vector
    return top_k_indices(scores, k)   # sort, take the best k
```

- **Complexity:** O(n · d) per query (n vectors, d dimensions), O(1) build time, O(n · d) memory.
- **Recall:** 1.0, always — this *is* the ground truth.
- **When to use it:** small n (thousands, not millions), or whenever you need a correctness
  baseline to measure an ANN method's recall against — which is exactly how
  [`benchmark.py`](../../similarity_search/benchmark.py) uses
  [`brute_force.py`](../../similarity_search/brute_force.py) in this project.

Modern hardware (SIMD, GPUs, BLAS-optimized matrix multiply) makes brute force viable further than
intuition suggests — FAISS's `IndexFlatIP` can score millions of 128-dim vectors against a query
in single-digit milliseconds on a GPU. The moment it stops being viable is dataset-and-latency
dependent, not a fixed n — benchmark before reaching for an ANN index.

------------------------------------------------------------------------

# 5. Tree-Based Methods (Overview)

**Idea:** recursively partition the vector space into regions (a binary tree), so a query only
has to descend and backtrack through a fraction of the tree instead of scanning every vector.

```
              all vectors
              /         \
        split on        split on
        dim/plane A     dim/plane A
        /      \          /      \
      ...      ...      ...      ...
```

- **KD-Tree** splits on axis-aligned hyperplanes (one dimension at a time).
- **Ball-Tree** splits on nested hyperspheres — no axis alignment, so it holds up somewhat better
  in higher dimensions.

**The catch:** both degrade toward brute force as dimensionality grows, because in high dimensions
almost every region ends up adjacent to almost every other region ("curse of dimensionality" — see
[02_Tree_Based_Methods.md](02_Tree_Based_Methods.md) for why, with numbers from this project's own
benchmark showing KD-Tree/Ball-Tree *losing* to brute force at `dim=128`). Tree-based methods are
the right choice at low dimensionality (roughly single digits to a few dozen), not for typical
128–4096-dim text/image embeddings.

Code: [`tree_methods.py`](../../similarity_search/tree_methods.py). Full write-up:
[02_Tree_Based_Methods.md](02_Tree_Based_Methods.md).

------------------------------------------------------------------------

# 6. Hashing-Based Methods (Overview)

**Idea:** hash each vector such that similar vectors are *likely* to collide into the same bucket
("Locality-Sensitive Hashing" — the opposite goal of a cryptographic hash, which wants collisions
to be as unlikely as possible). At query time, hash the query and only compare it against whatever
landed in the same bucket.

```
Vector ──► random hyperplanes ──► sign per plane ──► bucket key
                                                          │
                                          bucket: [v_12, v_87, v_301, ...]
```

The most common variant, **random-projection LSH**, projects each vector onto `n_planes` random
hyperplanes and keeps only the sign of each projection as a bit — vectors on the same side of most
planes are likely near each other in cosine similarity. More planes → finer buckets → higher
precision but a higher chance the true neighbor lands in a *different* bucket than the query
(lower recall). Production LSH implementations use multiple independent hash tables to recover
that lost recall (a neighbor only needs to collide in *one* table).

- **Complexity:** O(d · n_planes) to hash a query, then linear scan of a (small) bucket.
- **When to use it:** very high-dimensional data, or when you want a simple, dependency-free
  approximate index — LSH is easy to implement from scratch (see
  [`lsh.py`](../../similarity_search/lsh.py), ~40 lines of numpy) and doesn't require a training
  step, unlike quantization methods.

Full write-up: [03_Hashing_Based_Methods.md](03_Hashing_Based_Methods.md).

------------------------------------------------------------------------

# 7. Graph-Based Methods (Overview)

**Idea:** build a graph where each vector is a node, connected to a handful of its approximate
nearest neighbors. Search greedily walks the graph toward the query — like following "closer,
closer, closer" signposts instead of checking every location.

**HNSW (Hierarchical Navigable Small World)** — the dominant algorithm in this family, and the
default (or top-performing) index in nearly every modern vector database — stacks multiple graph
layers, sparse at the top and dense at the bottom:

```
Layer 2 (sparse)     ●───────────────●
                      │               │
Layer 1               ●───●───●───●───●
                      │   │   │   │   │
Layer 0 (dense, all)  ●─●─●─●─●─●─●─●─●─●─●
```

A query enters at the top (sparse) layer, greedily walks to the locally closest node, drops down a
layer, and repeats — like a skip list built over a proximity graph. By the time it reaches layer 0
it has narrowed to a small neighborhood, where it does a final, cheap local search.

- **Complexity:** O(log n) search (empirically, near-constant with good tuning), O(n log n) build.
- **Recall:** typically 0.9–0.99+ with reasonable tuning (`M`, `ef_construction`, `ef_search`) — by
  far the best recall-per-millisecond of any approximate method, at the cost of memory (the graph
  itself, plus every full vector, must fit in memory).
- **Used by:** pgvector (`USING hnsw`), Qdrant, Weaviate, Milvus, and as an index type in FAISS.

Code: [`graph_ann.py`](../../similarity_search/graph_ann.py) (via `hnswlib`). Full write-up:
[04_Graph_Based_Methods.md](04_Graph_Based_Methods.md). See also the RAG Knowledge Base's
[HNSW page](../RAG_Knowledge_Base_Starter/05_HNSW.md) for a gentler first pass.

------------------------------------------------------------------------

# 8. Quantization-Based Methods (Overview)

**Idea:** instead of indexing full-precision vectors, *compress* them — trading some accuracy for
dramatically less memory and faster distance computation.

**Product Quantization (PQ)** splits each vector into `m` subvectors, and quantizes each
subvector independently against a small codebook (learned via k-means) of `2^bits` centroids. A
128-dim `float32` vector (512 bytes) with `m=32, bits=8` compresses to 32 bytes — a 16x reduction
— by storing, per subvector, only the index of its nearest codebook centroid.

```
Original vector (128 floats)
[■■■■|■■■■|■■■■| ... |■■■■]     32 subvectors of 4 dims each
   │     │     │            │
   ▼     ▼     ▼            ▼
  code   code  code   ...   code    → 32 byte codes instead of 512 bytes
  (nearest centroid id per subvector, from a trained codebook)
```

This is lossy — distances computed from quantized codes only approximate the true distance — so PQ
alone trades meaningfully more recall than HNSW for its memory savings. It's the right tool when
the dataset is too large to fit un-compressed in memory (hundreds of millions to billions of
vectors), not a default for smaller collections.

Code: [`ivf_pq.py`](../../similarity_search/ivf_pq.py) (via FAISS). Full write-up:
[05_Quantization_and_Compression.md](05_Quantization_and_Compression.md).

------------------------------------------------------------------------

# 9. Hybrid Methods: IVF + Anything

**IVF (Inverted File Index)** isn't a standalone method — it's a *partitioning* layer combined
with something else. It k-means-clusters the dataset into `n_clusters` cells at build time; at
query time it only searches the `n_probe` cells nearest the query instead of every vector.

```
Dataset ──k-means──► [cell 0] [cell 1] [cell 2] ... [cell n_clusters]
                          │
Query ──find nearest n_probe cells──┘
                          │
                 search only within those cells
```

- **IVF-Flat**: cells contain full-precision vectors — exact search within the probed cells, still
  approximate overall (because non-probed cells are never searched). Higher recall, more memory.
- **IVF-PQ**: cells contain *compressed* (PQ) vectors — the combination FAISS ships as
  `IndexIVFPQ`, and what most vector databases mean by "IVF" in practice. This is the method in
  [`ivf_pq.py`](../../similarity_search/ivf_pq.py).

IVF's `n_probe` is the single knob that trades recall for speed most directly: `n_probe = n_clusters`
degrades to a full scan (plus quantization loss, if using PQ); `n_probe = 1` is the fastest and
least accurate.

------------------------------------------------------------------------

# 10. Comparison Table

| Family | Exact? | Build time | Query time | Memory | Recall (typical) | Needs training |
|---|---|---|---|---|---|---|
| Flat / brute force | ✅ | O(1) | O(n·d) | O(n·d) | 1.0 | No |
| KD-Tree / Ball-Tree | ✅ | O(n log n) | O(log n) low-dim, → O(n) high-dim | O(n·d) | 1.0 | No |
| LSH (random projection) | ❌ | O(n · planes) | O(bucket size) | O(n·d) + hash tables | 0.7–0.95 | No |
| HNSW (graph) | ❌ | O(n log n) | ~O(log n) | O(n·d) + graph edges | 0.9–0.99+ | No |
| IVF-Flat | ❌ | O(n) + k-means | O((n/n_clusters)·n_probe) | O(n·d) | 0.85–0.99 | Yes (k-means) |
| IVF-PQ | ❌ | O(n) + k-means + PQ training | O((n/n_clusters)·n_probe), cheap distance | O(n · m) — much less than O(n·d) | 0.5–0.95 (tunable via `m`) | Yes (k-means + PQ codebooks) |

These are the actual numbers this project's benchmark produces at `n=20,000, dim=128, k=10` (see
[06_Choosing_and_Benchmarking.md](06_Choosing_and_Benchmarking.md) for the full run and how to
reproduce it):

```
| method                   |   build_s |   avg_query_ms |   recall@k |
|--------------------------|-----------|----------------|------------|
| Brute force (flat)       |     0.000 |          0.176 |      1.000 |
| KD-Tree                  |     0.024 |          1.344 |      1.000 |
| Ball-Tree                |     0.026 |          1.171 |      1.000 |
| LSH (random projection)  |     0.021 |          1.234 |      0.801 |
| HNSW (graph)             |     0.362 |          0.046 |      0.983 |
| IVF-PQ (quantized)       |     1.033 |          0.027 |      0.656 |
```

Notice KD-Tree and Ball-Tree are both *exact* but *slower than brute force* at 128 dimensions —
the tree structure isn't pruning enough branches to pay for its own overhead. This is the curse of
dimensionality in action, not a bug (see [02_Tree_Based_Methods.md](02_Tree_Based_Methods.md)).

------------------------------------------------------------------------

# 11. Complexity Cheat Sheet

For n vectors of dimension d, returning the top k:

| Method | Query time | Space |
|---|---|---|
| Brute force | O(n·d) | O(n·d) |
| KD-Tree / Ball-Tree (low-dim) | O(d·log n) | O(n·d) |
| KD-Tree / Ball-Tree (high-dim) | → O(n·d) (degenerates) | O(n·d) |
| LSH | O(d·planes + bucket size) | O(n·d) |
| HNSW | O(d·M·log n) empirically | O(n·d + n·M) |
| IVF-PQ | O(d·n_clusters + (n/n_clusters)·n_probe·m) | O(n·m) |

------------------------------------------------------------------------

# 12. Choosing a Family

```
                     Is n small (≤ ~10K–100K) or is recall=1.0 required?
                                    │
                     ┌──────yes─────┴──────no──────┐
                     ▼                              ▼
              Flat / brute force           Is d small (≤ ~20)?
                                                    │
                                    ┌──────yes───────┴──────no──────┐
                                    ▼                                ▼
                             KD-Tree / Ball-Tree          Does the whole index
                                                           need to fit in RAM
                                                           at billion-vector scale?
                                                                    │
                                                    ┌──────yes───────┴──────no──────┐
                                                    ▼                                ▼
                                              IVF-PQ (compressed)              HNSW (best recall/speed,
                                              or IVF-Flat if recall            more memory)
                                              matters more than memory
```

In practice: **default to HNSW** for embeddings (this is what pgvector, Qdrant, Weaviate, and
Milvus all default to, for good reason), reach for **IVF-PQ** only once memory becomes the binding
constraint, and use **flat/brute-force** for anything small enough that "just compute it" is
simpler and fast enough — don't add an ANN index you don't need. See
[06_Choosing_and_Benchmarking.md](06_Choosing_and_Benchmarking.md) for a fuller decision guide and
how to validate the choice with your own data instead of these generic defaults.

------------------------------------------------------------------------

# 13. Key Takeaways

- "Vector-based similarity search" is the umbrella term for the entire field covered on this page
  — it is not one algorithm, but a family of strategies for avoiding an O(n) scan.
- **Flat/brute-force** is exact and simple, and remains the right choice up to a surprisingly large
  n on modern hardware — always benchmark before reaching for an ANN index.
- **Tree-based** methods (KD-Tree, Ball-Tree) win only at low dimensionality; they lose to brute
  force on typical embedding dimensions due to the curse of dimensionality.
- **Hashing-based** methods (LSH) are simple, training-free, and tunable, at moderate recall.
- **Graph-based** methods (HNSW) offer the best recall-per-millisecond of the approximate methods
  and are the default choice in most production vector databases.
- **Quantization-based** methods (PQ, IVF-PQ) trade the most recall for the smallest memory
  footprint, and are the right tool once billion-scale memory becomes the binding constraint.
- Every method here can be run, benchmarked, and compared directly using the code in
  [`../../similarity_search/`](../../similarity_search/README.md).

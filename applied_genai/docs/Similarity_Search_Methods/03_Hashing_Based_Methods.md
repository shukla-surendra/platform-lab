# Hashing-Based Methods (LSH)

Code: [`lsh.py`](../../similarity_search/lsh.py) · Part of the taxonomy in
[01_Vector_Based_Methods_for_Similarity_Search.md](01_Vector_Based_Methods_for_Similarity_Search.md#6-hashing-based-methods-overview)

## The Idea, Precisely

A normal hash function is designed to make collisions *rare*, even for near-identical inputs —
that's what makes it useful for hash tables and checksums. **Locality-Sensitive Hashing (LSH)**
does the opposite on purpose: it's designed so that similar inputs collide *often*, and dissimilar
inputs rarely do. That single property turns "find the nearest neighbors" into "hash the query,
then only check whatever landed in the same bucket."

## Random-Projection LSH (for Cosine Similarity)

The variant implemented in [`lsh.py`](../../similarity_search/lsh.py). The intuition: a random
hyperplane through the origin splits space in two. Two vectors that are close together (small
angle between them) are unlikely to fall on opposite sides of a *random* hyperplane; two vectors
that are far apart (large angle) are more likely to.

**Build:**

1. Generate `n_planes` random hyperplanes (as random vectors — the plane is everything
   orthogonal to it, we never construct it explicitly).
2. For every stored vector, compute its **sign vector**: for each plane, is the vector on the
   positive or negative side (sign of the dot product)? This gives an `n_planes`-bit code.
3. Group vectors by identical sign vector — each unique code is a bucket.

```python
projections = vectors @ random_planes      # (n_vectors, n_planes)
sign_bits   = (projections > 0)            # bucket key per vector
```

**Search:** hash the query the same way, look up its bucket, and brute-force search only within
that bucket (typically a small fraction of the whole dataset).

```
Query ──► same random planes ──► sign vector "101101..." ──► bucket lookup
                                                                    │
                                             candidates: [v_12, v_87, v_301, ...]
                                                                    │
                                              brute-force rank just these
```

## The Precision/Recall Knob: `n_planes`

- **More planes** → more, smaller buckets → less brute-force work per query, but more chances a
  true near neighbor lands in a *different* bucket than the query (lower recall).
- **Fewer planes** → fewer, larger buckets → higher recall (buckets closer to a full scan), but
  less speedup.

This project's [`lsh.py`](../../similarity_search/lsh.py) defaults to `n_planes=12`; the benchmark
shows recall ≈ 0.80 at that setting and `dim=128` — reasonable, not HNSW-level. Try the trade-off
directly:

```bash
python -c "
from data import make_dataset, make_queries
from lsh import LSHIndex
from brute_force import BruteForceIndex

vectors, _, centers = make_dataset()
queries = make_queries(centers)
brute = BruteForceIndex(vectors)
gt = [brute.search(q, 10) for q in queries]

for n_planes in [6, 12, 18, 24]:
    idx = LSHIndex(vectors, n_planes=n_planes)
    results = [idx.search(q, 10) for q in queries]
    hits = sum(len(set(r) & set(g)) for r, g in zip(results, gt))
    print(n_planes, hits / sum(len(g) for g in gt))
"
```

## Multi-Probe LSH (Not Implemented Here, Worth Knowing)

The fallback in this project's `LSHIndex.search()` — when a bucket comes up short of `k`
candidates, it falls back to a full brute-force scan — is a simplification. Production LSH
implementations instead use **multiple independent hash tables** (different random planes per
table): a candidate only needs to collide with the query in *any one* table to be considered, which
recovers much of the recall lost to unlucky bucket splits without ever falling back to a full scan.
This is the "multi-probe" approach; `n_planes` and `n_tables` become two independent knobs instead
of one.

## MinHash (Different Data, Same Idea)

Worth knowing about even though it doesn't apply to dense embedding vectors: **MinHash** is an LSH
variant for *set similarity* (Jaccard similarity) rather than vector cosine similarity — used for
near-duplicate detection on sets of shingled tokens (e.g. deduplicating web pages or detecting
plagiarism). Same core idea (hash such that similar inputs collide more), different similarity
function and different hash construction.

## When to Reach for LSH

- You want an approximate index with **no training step** (unlike IVF/PQ, which require k-means)
  and a small, dependency-free implementation.
- Very high-dimensional or sparse data, where graph-based methods (HNSW) become expensive to build.
- Moderate recall requirements — if you need recall above ~0.9, HNSW is usually a better default
  (see [04_Graph_Based_Methods.md](04_Graph_Based_Methods.md)) unless you specifically need LSH's
  simplicity or its ability to work as a pure hash lookup (no graph traversal, embarrassingly
  parallel, easy to shard by bucket).

# Quantization and Compression (PQ, IVF-PQ)

Code: [`ivf_pq.py`](../../similarity_search/ivf_pq.py) · Part of the taxonomy in
[01_Vector_Based_Methods_for_Similarity_Search.md](01_Vector_Based_Methods_for_Similarity_Search.md#8-quantization-based-methods-overview)
and [§9 Hybrid Methods](01_Vector_Based_Methods_for_Similarity_Search.md#9-hybrid-methods-ivf-anything)

## The Problem Quantization Solves

HNSW gets great recall and latency, but pays for it in memory: every full-precision vector, plus
graph edges, must fit in RAM. At billion-vector scale (or on constrained hardware), that stops
being affordable. Quantization methods trade some accuracy for a much smaller memory footprint —
often 8–32x smaller — by storing a *compressed approximation* of each vector instead of the vector
itself.

## Scalar Quantization (the Simple Version)

Before Product Quantization, the simplest form: instead of a 32-bit float per dimension, store an
8-bit integer per dimension, linearly mapped from the observed min/max range of that dimension
across the dataset. 4x compression, small accuracy loss, trivial to implement — but it compresses
each *dimension* independently and doesn't exploit any correlation between dimensions, which is
where Product Quantization does better.

## Product Quantization (PQ)

**Build:**

1. Split every `d`-dimensional vector into `m` **subvectors** of `d/m` dimensions each.
2. For each of the `m` subvector positions, run k-means independently across the whole dataset to
   learn a **codebook** of `2^bits` centroids (typically `bits=8` → 256 centroids).
3. Replace each vector with `m` codes — the index of the nearest centroid in each subvector's
   codebook. A 128-dim `float32` vector (512 bytes) with `m=32, bits=8` becomes 32 bytes: a 16x
   reduction.

```
Original: [ 0.12, -0.87, 0.45, 0.03 | 0.91, -0.22, ... ]   (128 floats = 512 bytes)
             \__ subvector 1 __/      \__ subvector 2 __/  ... (32 subvectors of 4 dims)
                    │                        │
             nearest centroid          nearest centroid
             in codebook 1             in codebook 2
                    │                        │
                  code=17                 code=203         ... (32 bytes total)
```

**Search (asymmetric distance computation, the trick that makes PQ fast, not just small):**
compute the distance from the *un-quantized* query subvector to every centroid in each subvector's
codebook once per query (a small lookup table), then approximate each stored vector's distance to
the query as the sum of precomputed lookup-table values for its stored codes — no floating-point
distance computation against the original vectors at all, just table lookups and additions.

## The `m` Knob: Compression vs. Recall

More subvectors (`m`) means each subvector covers fewer dimensions, so the codebook quantizes it
more precisely — better recall, less compression (more bytes per vector), slower training.
Fewer subvectors means more compression but coarser quantization per subvector, and more recall
lost. This project's benchmark tuning found exactly this trade-off on synthetic data
(`dim=128, nlist=100, nprobe=8`):

| `n_subquantizers` (m) | dims per subvector | recall@10 |
|---|---|---|
| 8 | 16 | 0.21 |
| 16 | 8 | 0.40 |
| 32 (this project's default) | 4 | 0.66 |
| 64 | 2 | 0.89 |

`m` must evenly divide the vector dimension — [`ivf_pq.py`](../../similarity_search/ivf_pq.py)
defaults to `n_subquantizers=32` paired with this project's default `dim=128` (4 dims/subvector).
Raise it toward `64` for higher recall at the cost of memory (see the table above), or lower it for
maximum compression when recall matters less than footprint.

## IVF: The Partitioning Layer PQ Is Usually Combined With

Product Quantization alone still requires computing an approximate distance against *every* stored
vector's codes — cheap per-comparison, but still O(n). **IVF (Inverted File Index)** adds a
partitioning step on top: k-means-cluster the dataset into `n_clusters` cells at build time, then
at query time only search the `n_probe` cells whose centroid is nearest the query.

```
Build:  dataset ──k-means (n_clusters cells)──► [cell 0][cell 1]...[cell n_clusters]
                                                    each cell's vectors stored as PQ codes

Query:  find the n_probe nearest cell centroids ──► search only within those cells
```

`n_probe` trades recall for speed independently of `m`: `n_probe = n_clusters` searches everything
(slow, but recovers the recall IVF's partitioning would otherwise cost you — leaving only PQ's
compression loss); `n_probe = 1` is fastest and least accurate. In this project's tuning, `n_probe`
mattered far less than `m` — the PQ compression was the dominant source of recall loss, not the IVF
partitioning (confirmed by testing `IndexIVFFlat`, uncompressed IVF, which held recall ≈ 0.997 at
`n_probe=8` on the same data — see [`ivf_pq.py`](../../similarity_search/ivf_pq.py)'s docstring).
This won't generalize to every dataset; always tune both knobs against your own data (see
[06_Choosing_and_Benchmarking.md](06_Choosing_and_Benchmarking.md)).

## OPQ (Optimized Product Quantization)

A refinement worth knowing about: PQ's subvector split (dimensions 1–4, 5–8, ...) is arbitrary and
may cut across correlated dimensions, hurting quantization quality. **OPQ** learns a rotation of
the vector space *before* splitting into subvectors, chosen to minimize the quantization error PQ
will introduce — same compression ratio, meaningfully better recall, at the cost of an extra
training step and a matrix multiply at query time. FAISS exposes this as `OPQ` + `IndexIVFPQ`
composed together.

## When to Reach for Quantization

- Dataset large enough that full-precision vectors (plus an HNSW graph) won't fit in available
  memory — hundreds of millions to billions of vectors is the regime where this actually bites.
- You can tolerate meaningfully lower recall than HNSW in exchange for the memory savings, and can
  tune `m`/`bits`/`n_probe` against your own recall target (this project's numbers above show how
  much that tuning matters — the default `m=8` FAISS example configs use is far too aggressive for
  128-dim data).
- Often combined with HNSW rather than instead of it in production systems: HNSW graph over
  PQ-compressed vectors (FAISS's `IndexHNSWPQ`) gets HNSW's search efficiency with PQ's memory
  savings, at the cost of implementation complexity this project doesn't cover.

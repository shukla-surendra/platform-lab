# FAISS Index Types: A Toolbox, Not One Algorithm

FAISS shows up throughout this doc set — it's what
[`ivf_pq.py`](../../similarity_search/ivf_pq.py) uses, and it's listed in every tool comparison in
[07_Tools_Libraries_and_Interview_Questions.md](07_Tools_Libraries_and_Interview_Questions.md) as
supporting "Flat, IVF, PQ, HNSW." That phrasing can read as "FAISS uses all of them at once" —
**it doesn't.** FAISS is a library of several independent index *classes*; for any given collection
of vectors, you pick one (or a combination of genuinely compatible ones) and build that specific
index. This page is the dedicated write-up of what that choice actually looks like.

## The Mental Model

Think of FAISS as a toolbox, not a single algorithm:

```
                FAISS
                  │
      ┌───────────┼────────────┐
      │           │            │
    Flat        HNSW          IVF
 (exact)    (graph-based)       │
                            ┌───┴───┐
                        IVFFlat   IVFPQ / IVFSQ
                       (exact per   (compressed per
                        probed cell) probed cell)
```

| FAISS class | Family (full write-up) | Accuracy | Speed | Memory |
|---|---|---|---|---|
| `IndexFlatL2` / `IndexFlatIP` | Exact / brute force ([01 §4](01_Vector_Based_Methods_for_Similarity_Search.md#4-flat-brute-force-search)) | 100% | Slow | High |
| `IndexHNSWFlat` | Graph-based ([04](04_Graph_Based_Methods.md)) | Very high (typically 95–99%+) | Very fast | High (graph edges + full vectors) |
| `IndexIVFFlat` | Cluster-based, uncompressed ([01 §9](01_Vector_Based_Methods_for_Similarity_Search.md#9-hybrid-methods-ivf-anything)) | Depends on `nprobe` | Fast | Medium |
| `IndexIVFPQ` | Cluster-based + compressed ([05](05_Quantization_and_Compression.md)) | Lower, tunable via `m`/`nprobe` | Very fast | Low |
| `IndexIVFScalarQuantizer` (IVF+SQ) | Cluster-based + scalar-quantized ([05](05_Quantization_and_Compression.md#scalar-quantization-the-simple-version)) | Between IVFFlat and IVFPQ | Fast | Low-medium |

This project's [`ivf_pq.py`](../../similarity_search/ivf_pq.py) builds exactly one of these
(`IndexIVFPQ`) — it never constructs `IndexHNSWFlat` or a plain `IndexFlatL2` alongside it in the
same index. [`benchmark.py`](../../similarity_search/benchmark.py) builds several *separate*
indexes over the *same* dataset purely to compare them side by side — that's a benchmarking
harness, not how you'd deploy multiple FAISS indexes together in production.

## Why IVF and PQ *Do* Combine

They solve different problems. IVF answers *"which vectors should I even compare against?"*
(partitioning); PQ answers *"how do I store each candidate using less memory?"* (compression).

```
100,000,000 vectors
        │
   IVF: find nearest 10 of 1,000 clusters
        │
   ~1,000,000 candidate vectors
        │
   PQ: each candidate stored as a compact code, not a full vector
        │
   Score cheaply, return top-k
```

The two techniques stack because they operate at *different stages* of the same query — IVF
narrows the candidate set first, PQ makes scoring that (still large) candidate set cheap — not
because they're the same kind of trade-off applied twice.

## Why HNSW and IVF *Don't* Combine in Standard FAISS

They're alternative strategies for the same job — deciding which vectors to compare a query
against — not complementary stages. You pick one or the other as your top-level index, not both.
(FAISS does support pairing a graph index as an IVF *quantizer* in specialized configurations, but
that's an advanced composition, not something to reach for by default — the standard choice is
genuinely one of Flat, HNSW, IVFFlat, or IVFPQ.)

## Choosing a FAISS Index by Dataset Size

| Dataset size | Recommended FAISS index |
|---|---|
| ≤ 10K | `IndexFlatL2` / `IndexFlatIP` |
| ≤ 100K | Flat, or `IndexHNSWFlat` if latency matters |
| ~1M | `IndexHNSWFlat` or `IndexIVFFlat` |
| ~10M | `IndexHNSWFlat` or `IndexIVFPQ` |
| 100M+ | `IndexIVFPQ` |
| Billion+ | `IndexIVFPQ`, or a disk-resident approach outside core FAISS ([DiskANN](09_Additional_Methods_Reranking_and_Taxonomy.md#diskann-vamana-microsoft)) |

This is the same decision guide as
[06_Choosing_and_Benchmarking.md](06_Choosing_and_Benchmarking.md), narrowed to FAISS's specific
class names — the underlying trade-off (exact vs. graph vs. cluster vs. cluster+compression) is
identical; FAISS just gives each point on that trade-off curve a concrete class to instantiate.

## Summary

- FAISS is a **toolbox of index classes**, not one combined algorithm — you build one index type
  per collection.
- **IVF + PQ combine** because they act at different stages (partition, then compress).
- **HNSW + IVF don't combine** in the standard case because they're alternative top-level
  strategies for the same decision.
- Every accuracy/speed/memory trade-off in the table above is the same one covered generally
  throughout this doc set — this page is specifically about which FAISS *class name* corresponds
  to which point on that trade-off curve.

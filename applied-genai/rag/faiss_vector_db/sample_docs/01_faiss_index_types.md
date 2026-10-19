# FAISS Index Types

FAISS is a library, not a server: it gives you an in-process data structure for storing vectors and
running nearest-neighbor search over them, plus tools to save/load that structure to disk.

- **IndexFlatL2 / IndexFlatIP** — brute-force exact search (Euclidean distance / inner product). No
  training step, no approximation, O(n) per query. Good baseline for small-to-medium corpora.
- **IndexIVFFlat** — partitions vectors into clusters (`nlist` centroids via k-means); a query only
  scans the nearest few clusters (`nprobe`). Requires a `train()` step on representative vectors before
  the first `add()`. Approximate, but far faster than Flat at scale.
- **IndexHNSWFlat** — builds a multi-layer navigable small-world graph. No training step needed. Very
  fast, high-recall approximate search; the main cost is memory (the graph itself) and slower inserts
  than Flat.
- **IndexIVFPQ** — adds product quantization on top of IVF, compressing each vector into a short code.
  Much smaller memory footprint at some recall cost — the standard choice once a corpus is too large to
  keep as full-precision float32 vectors in RAM.
- **IndexIDMap / IndexIDMap2** — a wrapper that lets you assign your own 64-bit ids to vectors instead of
  relying on FAISS's implicit 0..n-1 insertion order. `IndexIDMap2` additionally supports `remove_ids`,
  which is what makes delete-by-id and update-by-id possible.

This project uses `IndexIDMap2(IndexFlatIP(dim))`: exact search, cosine similarity via normalized inner
product, and stable ids so records can be updated and deleted individually — see `store.py`.

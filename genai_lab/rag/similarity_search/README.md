# Similarity Search

A from-scratch, runnable tour of the algorithms that power similarity search: brute-force (exact),
tree-based, hashing-based (LSH), graph-based (HNSW), and quantization-based (IVF-PQ). Each method
is a small, readable implementation you can step through, plus a benchmark script that builds all
of them over the same synthetic dataset and compares build time, query latency, and recall@k.

This is a standalone project — it has its own `requirements.txt` and no external services (no
Docker, no Ollama, no network calls). It pairs with
[`../docs/Similarity_Search_Methods/`](../docs/Similarity_Search_Methods/index.md) — read those
docs for the "why" (the math, the algorithms, when to choose what), this project is the "how" (code
you can run and measure). It also complements
[`../rag_pgvector_local`](../rag_pgvector_local/README.md), which shows one specific ANN index
(pgvector's HNSW) wired into a real RAG pipeline with real embeddings; this project instead
compares *five* index types side by side over synthetic vectors, so the algorithmic differences
aren't muddied by network/DB overhead.

## Why synthetic data?

Real embedding models produce vectors with a specific statistical shape: roughly unit-norm, and
clustered — semantically related items sit near each other in the vector space. `data.py`
synthesizes exactly that shape (Gaussian blobs around random unit-norm cluster centers), which is
enough to make every algorithm here behave the way it would over real embeddings, without a model
download or GPU. Queries are drawn from the *same* cluster distribution as the indexed vectors
(mirroring how ANN-Benchmarks/SIFT/GIST construct query sets) — a query that isn't semantically
related to anything in the index is an unrealistic worst case that makes every ANN method look
artificially bad.

## Files

| File | Role |
|---|---|
| `data.py` | Synthetic clustered unit-norm vectors (`make_dataset`) and matching queries (`make_queries`) |
| `metrics.py` | Cosine similarity, Euclidean distance, dot product — implemented from scratch over numpy |
| `brute_force.py` | Exact nearest-neighbor search (the ground truth every other method is scored against) |
| `tree_methods.py` | KD-Tree and Ball-Tree (`scikit-learn`) |
| `lsh.py` | Random-projection Locality-Sensitive Hashing, implemented from scratch |
| `graph_ann.py` | HNSW (Hierarchical Navigable Small World), via `hnswlib` |
| `ivf_pq.py` | Inverted-File + Product Quantization, via `faiss` |
| `benchmark.py` | Builds every index over the same dataset; reports build time, query latency, recall@k |
| `explore.ipynb` | Interactive notebook: visualize the dataset, step through each method, plot recall-vs-latency |
| `databricks_vector_search.ipynb` | Verifies two Databricks Vector Search claims (L2/cosine ranking equivalence, RRF hybrid fusion) against this project's own vectors — see [`../docs/Similarity_Search_Methods/08_Databricks_Vector_Search.md`](../docs/Similarity_Search_Methods/08_Databricks_Vector_Search.md) |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the benchmark

```bash
python benchmark.py                       # 20,000 vectors, dim=128, k=10 (defaults)
python benchmark.py --n 100000 --dim 256  # larger dataset
```

### With `make`

```bash
make install
make benchmark
```

### Example output

```
Dataset: 20000 vectors, dim=128, k=10

| method                   |   build_s |   avg_query_ms |   recall@k |
|--------------------------|-----------|----------------|------------|
| Brute force (flat)       |     0.000 |          0.176 |      1.000 |
| KD-Tree                  |     0.024 |          1.344 |      1.000 |
| Ball-Tree                |     0.026 |          1.171 |      1.000 |
| LSH (random projection)  |     0.021 |          1.234 |      0.801 |
| HNSW (graph)             |     0.362 |          0.046 |      0.983 |
| IVF-PQ (quantized)       |     1.033 |          0.027 |      0.656 |
```

(Numbers vary by machine and by the `--n`/`--dim` you pass — the *shape* of the result is the
point, not the exact decimals.) Read the results as:

- **KD-Tree / Ball-Tree** are *exact* (recall 1.0) but at `dim=128` are actually **slower** than
  brute force — a direct demonstration of the curse of dimensionality (see
  [`02_Tree_Based_Methods.md`](../docs/Similarity_Search_Methods/02_Tree_Based_Methods.md)). They
  win only at low dimensions (try `--dim 8`).
- **LSH** is fast and approximate; recall depends on `n_planes` (`lsh.py`) — more planes means
  finer buckets, higher precision, but more buckets to miss the right one entirely.
- **HNSW** gets both the best recall of the approximate methods *and* the lowest latency — this is
  why it's the default ANN index in pgvector, Qdrant, Weaviate, and Milvus.
- **IVF-PQ** is the fastest and most memory-compact by construction (each vector is stored as a
  handful of quantization codes, not 128 floats), at the cost of the most recall lost to lossy
  compression. Raising `n_subquantizers` in `ivf_pq.py` recovers recall at the cost of memory —
  that dial is the whole point of the algorithm.

## Exploring interactively (Jupyter Lab)

```bash
make install-notebook
make lab             # opens explore.ipynb at http://localhost:8891
make lab-databricks  # opens databricks_vector_search.ipynb at http://localhost:8891
```

Select the **Similarity Search (local)** kernel if it isn't already active.

`explore.ipynb` covers: a 2D PCA plot of the synthetic clusters, stepping through each index type
on a single query with its actual top-k neighbors and scores, and a recall-vs-latency scatter plot
across all five methods. `databricks_vector_search.ipynb` implements and verifies two specific
Databricks Vector Search claims (the L2/cosine ranking-equivalence formula, and Reciprocal Rank
Fusion for hybrid search) against this project's own data.

## Documentation

Full write-ups of every method, the math behind the metrics, tool/library comparisons, and a
benchmarking/evaluation guide live in
[`../docs/Similarity_Search_Methods/`](../docs/Similarity_Search_Methods/index.md), including the
dedicated deep dive
[**Vector-Based Methods for Similarity Search**](../docs/Similarity_Search_Methods/01_Vector_Based_Methods_for_Similarity_Search.md).
Build and preview the whole repo's docs site locally with `make docs` from the repo root.

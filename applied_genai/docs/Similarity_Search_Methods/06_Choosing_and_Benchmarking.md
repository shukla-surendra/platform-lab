# Choosing an Algorithm, and Benchmarking It Yourself

Code: [`benchmark.py`](../../similarity_search/benchmark.py)

## The Only Rule That Actually Matters

Every table in this doc set is directional, not a substitute for measuring on *your* data, at
*your* scale, with *your* recall requirement. Dimensionality, cluster structure, and query
distribution all change which method wins — this project's own IVF-PQ tuning
([05_Quantization_and_Compression.md](05_Quantization_and_Compression.md)) needed `n_subquantizers=64`
to hit 0.89 recall on *this* synthetic data; a different dataset could need a completely different
setting. Use the decision guide below to pick a starting point, then benchmark to confirm it.

## Decision Guide

| Question | If yes | If no |
|---|---|---|
| Is n small (≤ ~10K–100K vectors), or is recall=1.0 non-negotiable? | **Brute force** — simplest correct answer, don't add an index you don't need | keep going |
| Is dimensionality low (≤ ~20)? | **KD-Tree / Ball-Tree** | keep going |
| Must the whole index fit in memory at hundreds of millions to billions of vectors? | **IVF-PQ** (tune `m`/`n_probe` against your recall target) | **HNSW** — best recall/latency of the approximate methods, the right default for most embedding search |
| Want a dependency-free, training-free approximate index, and can tolerate ~0.8 recall? | **LSH** | reconsider HNSW/IVF-PQ above |

This mirrors the flowchart in
[01_Vector_Based_Methods_for_Similarity_Search.md §12](01_Vector_Based_Methods_for_Similarity_Search.md#12-choosing-a-family) —
this page is the "now go measure it" companion to that decision tree.

## The Three Numbers That Matter

| Metric | What it measures | How `benchmark.py` computes it |
|---|---|---|
| **Build time** | Cost of constructing the index (one-time, amortized over all future queries) | Wall-clock time around index construction |
| **Query latency** | Cost per search (`avg_query_ms`) — what your users/downstream LLM actually wait on | Wall-clock time around all queries, divided by query count |
| **Recall@k** | Fraction of the *true* top-k (from brute force) that the approximate method actually found | `\|approx_results ∩ ground_truth\| / k`, averaged across queries |

Recall@k is *not* the same as precision or accuracy in the classification sense — it specifically
answers "of the k best matches, how many did we actually retrieve?" A method that returns 10
results, 8 of which are in the true top-10, has recall@10 = 0.8, regardless of what order they came
back in. (Order-sensitive variants like NDCG exist but aren't used in this project — for retrieval
into an LLM prompt, "is the true best match in the returned set at all" is usually what matters.)

## Running the Benchmark

```bash
cd similarity_search
python benchmark.py                        # defaults: n=20000, dim=128, k=10
python benchmark.py --n 100000 --dim 384    # larger, closer to a real embedding model's output size
python benchmark.py --dim 8                 # watch KD-Tree/Ball-Tree actually win, at low dimensionality
```

Each run: generates a fresh synthetic dataset ([`data.py`](../../similarity_search/data.py)),
builds a brute-force index to compute ground truth, then builds and times every other method
against it. See [`explore.ipynb`](../../similarity_search/explore.ipynb) for the same comparison
as an interactive recall-vs-latency scatter plot instead of a table.

## Reading a Recall-vs-Latency Trade-off

The scatter plot in `explore.ipynb`'s last cell plots every method as one point: x-axis latency
(log scale), y-axis recall. The shape to look for is a **Pareto frontier** — methods that are both
faster *and* more accurate than another method strictly dominate it and should always be preferred;
methods on the frontier represent genuine trade-offs (faster-but-less-accurate vs.
slower-but-more-accurate) where the right choice depends on your application's tolerance for either.
In this project's runs, HNSW dominates LSH outright (faster *and* higher recall) — LSH's only
remaining argument is implementation simplicity and no training step, not speed or accuracy.

## Real Benchmarks Beyond This Project

For production decisions at real scale, this project's synthetic-data benchmark is a starting
point for building intuition, not a substitute for:

- **[ANN-Benchmarks](https://ann-benchmarks.com/)** — the standard, continuously-updated
  comparison of ANN libraries across real datasets (SIFT, GIST, GloVe), reporting recall/QPS
  Pareto curves per algorithm and per library implementation.
- Benchmarking directly on **your own embeddings**, from the actual model you're using in
  production — cluster structure and dimensionality both meaningfully change which method wins,
  and a synthetic Gaussian-blob dataset (like this project's) is a simplification of what a real
  fine-tuned or domain-specific embedding model produces.

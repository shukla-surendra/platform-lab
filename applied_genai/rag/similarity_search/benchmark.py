"""Build every index in this project over the same synthetic dataset and compare them on:

  - build time      how long constructing the index takes
  - query latency   mean time per query, in milliseconds
  - recall@k        fraction of the brute-force top-k this method actually finds

Run: python benchmark.py [--n 20000] [--dim 128] [--k 10]
"""

import argparse
import time

import numpy as np
from tabulate import tabulate

from brute_force import BruteForceIndex
from data import make_dataset, make_queries
from graph_ann import HNSWIndex
from ivf_pq import IVFPQIndex
from lsh import LSHIndex
from tree_methods import TreeIndex


def recall_at_k(approx_results: list[np.ndarray], ground_truth: list[np.ndarray]) -> float:
    hits = sum(len(set(a) & set(g)) for a, g in zip(approx_results, ground_truth))
    total = sum(len(g) for g in ground_truth)
    return hits / total


def bench(name: str, build_fn, search_fn, queries: np.ndarray, k: int, ground_truth):
    start = time.perf_counter()
    index = build_fn()
    build_time = time.perf_counter() - start

    start = time.perf_counter()
    results = [search_fn(index, q, k) for q in queries]
    query_time_ms = (time.perf_counter() - start) * 1000 / len(queries)

    recall = recall_at_k(results, ground_truth) if ground_truth is not None else 1.0
    return {
        "method": name,
        "build_s": round(build_time, 3),
        "avg_query_ms": round(query_time_ms, 3),
        "recall@k": round(recall, 3),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20_000)
    parser.add_argument("--dim", type=int, default=128)
    parser.add_argument("--k", type=int, default=10)
    args = parser.parse_args()

    print(f"Dataset: {args.n} vectors, dim={args.dim}, k={args.k}\n")
    vectors, _, centers = make_dataset(n_vectors=args.n, dim=args.dim)
    queries = make_queries(centers)

    brute = BruteForceIndex(vectors)
    ground_truth = [brute.search(q, args.k) for q in queries]

    rows = []
    rows.append(
        bench(
            "Brute force (flat)",
            lambda: brute,
            lambda idx, q, k: idx.search(q, k),
            queries,
            args.k,
            ground_truth,
        )
    )
    rows.append(
        bench(
            "KD-Tree",
            lambda: TreeIndex(vectors, kind="kd"),
            lambda idx, q, k: idx.search(q, k),
            queries,
            args.k,
            ground_truth,
        )
    )
    rows.append(
        bench(
            "Ball-Tree",
            lambda: TreeIndex(vectors, kind="ball"),
            lambda idx, q, k: idx.search(q, k),
            queries,
            args.k,
            ground_truth,
        )
    )
    rows.append(
        bench(
            "LSH (random projection)",
            lambda: LSHIndex(vectors),
            lambda idx, q, k: idx.search(q, k),
            queries,
            args.k,
            ground_truth,
        )
    )
    rows.append(
        bench(
            "HNSW (graph)",
            lambda: HNSWIndex(vectors),
            lambda idx, q, k: idx.search(q, k),
            queries,
            args.k,
            ground_truth,
        )
    )
    rows.append(
        bench(
            "IVF-PQ (quantized)",
            lambda: IVFPQIndex(vectors),
            lambda idx, q, k: idx.search(q, k),
            queries,
            args.k,
            ground_truth,
        )
    )

    print(tabulate(rows, headers="keys", tablefmt="github"))


if __name__ == "__main__":
    main()

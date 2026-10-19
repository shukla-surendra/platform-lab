# Graph-Based Methods (HNSW)

Code: [`graph_ann.py`](../../similarity_search/graph_ann.py) · Part of the taxonomy in
[01_Vector_Based_Methods_for_Similarity_Search.md](01_Vector_Based_Methods_for_Similarity_Search.md#7-graph-based-methods-overview)
· See also the gentler introduction in the RAG Knowledge Base's
[HNSW page](../RAG_Knowledge_Base_Starter/05_HNSW.md)

## Why a Graph?

Instead of partitioning space (trees) or hashing into buckets (LSH), graph-based methods build a
**proximity graph**: each vector is a node, connected by edges to a small number of its (approximate)
nearest neighbors. Searching means walking the graph greedily toward the query — no partitioning,
no hashing, just "which of my current node's neighbors is closer to the query? Move there. Repeat."

## Navigable Small World (NSW) — the Building Block

A **Navigable Small World** graph is built incrementally: insert vectors one at a time, and for
each new vector, connect it to the `M` nearest vectors already in the graph (found by greedy search
from an entry point). This produces a graph with the "small world" property — most nodes aren't
neighbors of one another, but any node can reach any other in a small number of hops, because early-
inserted nodes end up acting as long-range hubs.

**Search:** start at a fixed entry point, greedily move to whichever neighbor is closest to the
query, and stop when no neighbor is closer than the current node. This is fast but has a known
failure mode: it can get stuck in a **local minimum** — a node that's closer to the query than all
of its immediate neighbors, but not the true global nearest neighbor.

## HNSW — NSW, Layered

**Hierarchical Navigable Small World** fixes NSW's local-minimum problem by stacking multiple NSW
graphs on top of each other, like a skip list:

```
Layer 2 (sparsest — long jumps)      ●───────────────●
                                      │               │
Layer 1                              ●───●───●───●───●
                                      │   │   │   │   │
Layer 0 (densest — every vector)     ●─●─●─●─●─●─●─●─●─●─●
```

Each vector is randomly assigned a maximum layer (exponentially decaying probability, so most
vectors only exist at layer 0, and very few exist all the way up at the top). **Search:**

1. Start at the top layer's fixed entry point.
2. Greedily walk that layer until no neighbor is closer to the query.
3. Drop down one layer, using the current position as the new starting point, and repeat.
4. At layer 0, do a wider local search (controlled by `ef_search`, see below) and return the top-k.

The upper, sparse layers act as an express lane — a query can jump across large distances in a few
hops before ever touching the dense layer-0 graph, which is exactly what makes HNSW avoid the
local-minima problem plain NSW has: getting stuck at a coarse layer just means dropping down and
refining, not failing.

## The Three Parameters That Matter

Set in [`graph_ann.py`](../../similarity_search/graph_ann.py):

| Parameter | What it controls | Trade-off |
|---|---|---|
| `M` | Max edges per node per layer | Higher → better recall, more memory, slower build |
| `ef_construction` | Candidate list size while *building* the graph | Higher → better graph quality (higher eventual recall), slower build |
| `ef_search` | Candidate list size while *searching* | Higher → better recall, slower query. The only one of the three you can change without rebuilding the index |

`ef_search` is the parameter you'll actually tune in production — it's a runtime knob (this
project's `HNSWIndex` sets it via `set_ef()`), so you can trade recall for latency per-query or
per-deployment without touching the index itself. `M` and `ef_construction` are baked in at build
time and require a rebuild to change.

## Why HNSW Wins in Practice

This project's benchmark shows HNSW getting both the best recall of the four approximate methods
*and* the lowest query latency simultaneously:

```
| method                   |   avg_query_ms |   recall@k |
|--------------------------|----------------|------------|
| LSH (random projection)  |          1.234 |      0.801 |
| HNSW (graph)             |          0.046 |      0.983 |
| IVF-PQ (quantized)       |          0.027 |      0.656 |
```

That's why HNSW is the default (or best-performing) ANN index in essentially every production
vector database: **pgvector** (`CREATE INDEX ... USING hnsw`, the index used in
[`../../rag_pgvector_local`](../../rag_pgvector_local/README.md)), **Qdrant**, **Weaviate**,
**Milvus**, and as an index type in **FAISS**. The cost is memory — the full-precision vectors
*and* the graph edges must fit in RAM — which is exactly the gap quantization-based methods (next
page) exist to close.

## When to Reach for HNSW

- The default choice for embedding search at moderate-to-large scale (up to tens or low hundreds
  of millions of vectors, depending on available RAM) where recall matters and memory isn't the
  binding constraint.
- Not ideal when the whole index genuinely can't fit in memory — that's IVF-PQ's territory, see
  [05_Quantization_and_Compression.md](05_Quantization_and_Compression.md).

# Tree-Based Methods

Code: [`tree_methods.py`](../../similarity_search/tree_methods.py) · Part of the taxonomy in
[01_Vector_Based_Methods_for_Similarity_Search.md](01_Vector_Based_Methods_for_Similarity_Search.md#5-tree-based-methods-overview)

## KD-Tree

Recursively splits the dataset on one dimension at a time, alternating dimensions (or picking the
dimension with highest variance) at each level, always splitting at the median so the tree stays
balanced.

```
Build (2D example, splitting alternately on x then y):

              split x=5
              /        \
        split y=3    split y=7
        /     \        /     \
      ...     ...    ...     ...
```

**Search:** descend the tree toward the query's region (O(log n) to reach a leaf), then
**backtrack** — at each ancestor node, check whether the splitting hyperplane is closer to the
query than the current best answer; if so, the other branch might contain a closer point and must
be explored too.

That backtracking step is where KD-Trees fall apart in high dimensions: with `d` dimensions, the
splitting hyperplane is only `d-1` dimensional relative to the full space, and as `d` grows, a
query point ends up close to *many* hyperplanes simultaneously — the "prune this branch, it can't
contain anything closer" test almost never succeeds, so the algorithm ends up backtracking into
nearly every branch. Above roughly a few dozen dimensions, a KD-Tree effectively degenerates into
a full scan, but with extra tree-traversal overhead on top — worse than brute force, not just
equal to it.

This project's own benchmark demonstrates exactly that at `dim=128`:

```
| method              |   build_s |   avg_query_ms |   recall@k |
|----------------------|-----------|----------------|------------|
| Brute force (flat)   |     0.000 |          0.176 |      1.000 |
| KD-Tree              |     0.024 |          1.344 |      1.000 |
```

Try it yourself at low dimensionality, where KD-Trees are actually supposed to win:

```bash
python benchmark.py --dim 8
```

## Ball-Tree

Same recursive-partition idea, but instead of axis-aligned hyperplane splits, each node is a
**hypersphere** ("ball") containing a subset of the points, and children are nested balls.

```
        ( outer ball, radius r )
        /                      \
  ( ball A )              ( ball B )
   /     \                  /     \
 leaf   leaf              leaf   leaf
```

**Search** uses the triangle inequality to prune: if the query is farther from a ball's center
than `ball_radius + current_best_distance`, nothing inside that ball can be closer than the
current best answer, so the whole subtree is skipped without visiting it.

Because balls aren't tied to coordinate axes, Ball-Trees hold up somewhat better than KD-Trees as
dimensionality grows, but suffer the same fundamental problem: in high dimensions, distances
between points concentrate (nearly everything is nearly equidistant from the query), so the
pruning test rarely fires. This project's benchmark shows Ball-Tree essentially tied with KD-Tree
at `dim=128` — both correct, both slower than brute force.

## VP-Tree (Vantage-Point Tree)

Worth knowing about even without a from-scratch implementation here: a VP-Tree picks a random
"vantage point" at each node and splits the remaining points into "closer than the median
distance" vs. "farther than the median distance" from that point. It only needs a valid distance
*metric* (triangle inequality), not a coordinate space — useful for non-Euclidean similarity
functions where KD-Tree/Ball-Tree don't apply at all (e.g. edit distance on strings). Same curse-
of-dimensionality ceiling applies.

## When Tree-Based Methods Are the Right Call

- Low-dimensional data: geographic coordinates (2D/3D), small hand-engineered feature vectors
  (roughly ≤ 20 dimensions) — not typical text/image embeddings (128–4096 dimensions).
- Exact search is required and n is large enough that brute force is genuinely too slow, but d is
  small enough that the tree actually prunes effectively.
- `scikit-learn`'s `KDTree`/`BallTree` (used in [`tree_methods.py`](../../similarity_search/tree_methods.py))
  are a reasonable default for this regime — no extra dependency beyond `scikit-learn`, which most
  ML codebases already have.

For typical embedding dimensionality, skip straight to hashing-based (LSH), graph-based (HNSW), or
quantization-based (IVF-PQ) methods — see
[01_Vector_Based_Methods_for_Similarity_Search.md](01_Vector_Based_Methods_for_Similarity_Search.md#12-choosing-a-family).

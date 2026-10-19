# Interview Questions: Vector Search, Similarity Search, and RAG

101 senior/staff-level interview questions on embeddings, similarity metrics, ANN algorithms, vector
database system design, and RAG architecture/evaluation — each with an answer, and example code where code
clarifies the answer better than prose alone. Grouped by topic, same order as the
[question-only version](07_Vector_Search_Tools_and_Technology.md) referenced from the
[overview](index.md).

## Embeddings & Representation Learning

**1. Why do embeddings from two different model families live in incompatible vector spaces?**
Each model is trained with its own objective, data, and loss geometry, so there's no guarantee two models
place "dog" and "puppy" the same relative distance apart, or even in comparable coordinate systems. Mixing
them in one index means distances are meaningless across the boundary — a OpenAI-embedded query will not
reliably retrieve a BGE-embedded document even if they're semantically related. Always embed queries and
the corpus with the *same* model and version.

**2. Explain contrastive learning (InfoNCE) for embedding models.**
Training pulls embeddings of a query and its known-relevant document ("positive") closer together while
pushing embeddings of unrelated documents ("negatives," often from the same batch) apart:

```python
import torch
import torch.nn.functional as F

def info_nce_loss(query_emb, pos_emb, neg_embs, temperature=0.05):
    # query_emb: (d,), pos_emb: (d,), neg_embs: (N, d)
    candidates = torch.cat([pos_emb.unsqueeze(0), neg_embs], dim=0)  # (N+1, d)
    sims = F.cosine_similarity(query_emb.unsqueeze(0), candidates) / temperature
    labels = torch.zeros(1, dtype=torch.long)  # positive is index 0
    return F.cross_entropy(sims.unsqueeze(0), labels)
```

**3. What is anisotropy, and why does it hurt cosine similarity for raw BERT `[CLS]` embeddings?**
Untuned transformer embeddings tend to occupy a narrow cone in vector space rather than spreading
uniformly, so almost every pair of vectors has high cosine similarity regardless of actual semantic
relatedness — the signal is drowned in a shared "average direction." Contrastive fine-tuning (or
whitening/normalization post-processing) spreads the embeddings out and restores cosine similarity as a
meaningful signal, which is why raw BERT is a poor retrieval embedding but SBERT (fine-tuned BERT) works
well.

**4. How does embedding dimensionality trade off retrieval quality, index size, and latency?**
Higher dimensionality generally captures more nuance up to a point of diminishing returns, but memory and
distance-computation cost scale linearly with it, and ANN recall at fixed `ef`/`nprobe` tends to degrade
slightly as dimensionality rises (curse of dimensionality). 384-dim is a good default for latency/cost
-sensitive, high-QPS systems; 1536-dim buys marginal quality for cases where accuracy matters more than
infra cost (e.g., legal/medical search).

**5. What is Matryoshka Representation Learning, and how does truncation work?**
MRL trains an embedding model so that *prefixes* of the full vector (e.g., the first 256 of 1536 dims) are
themselves valid, usable embeddings — importance is front-loaded into earlier dimensions during training.
That lets you truncate post-hoc for a smaller index without retraining:

```python
full_embedding = model.encode("some text")          # shape (1536,)
compact_embedding = full_embedding[:256]             # still usable, lower recall than full
compact_embedding = compact_embedding / np.linalg.norm(compact_embedding)  # re-normalize after truncation
```

**6. Why do bi-encoders scale for retrieval while cross-encoders don't?**
A bi-encoder embeds the query and each document independently, so document embeddings can be precomputed
once and searched with ANN in sublinear time. A cross-encoder concatenates the query and document and runs
them through the model *together*, producing a much more accurate relevance score but requiring a full
forward pass per query-document pair — no precomputation possible. That's why the standard pattern is
bi-encoder for first-pass retrieval (top-1000 → top-100), cross-encoder for re-ranking the shortlist.

**7. How would you fine-tune an embedding model with limited labeled pairs?**
Use parameter-efficient fine-tuning (LoRA) on a pretrained bi-encoder, generate synthetic positive pairs
via LLM paraphrasing or query generation from documents when labels are scarce, mine hard negatives from
the base model's own top-K retrieval mistakes, and evaluate on a held-out set with recall@k before and
after to confirm the fine-tune actually helps your domain rather than overfitting to a small labeled set.

**8. Symmetric vs. asymmetric semantic search, and why do `"query: "` / `"passage: "` prefixes exist?**
Symmetric search compares texts of similar length/nature (duplicate question detection); asymmetric search
compares a short query against long documents, which is a different distribution the model must learn to
bridge. Models like E5 use different prefixes per side so the model learns distinct representations for
"things people ask" vs. "things that get retrieved," improving asymmetric retrieval accuracy over using
one shared encoding function for both roles.

**9. How does hard-negative mining improve embedding quality?**
Random negatives are usually trivially dissimilar, so the model learns very little from them past the
first few epochs. Hard negatives — documents that are lexically or superficially similar to the positive
but not actually relevant — force the model to learn finer-grained semantic distinctions. Mining them
typically means running the current model's retrieval, taking high-scoring wrong answers, and feeding those
back in as negatives (an iterative loop).

**10. Why can semantically opposite sentences end up close in embedding space?**
Many embedding models are trained primarily on topical/contextual similarity ("this text co-occurs with
that text") rather than fine-grained sentiment or logical polarity, so "I love this movie" and "I hate this
movie" share topic, subject, and grammatical structure and can embed close together even though their
meaning is opposite. This is a known weakness — sentiment-sensitive tasks often need a specialized model or
an additional classifier layer, not raw embedding similarity.

**11. What is embedding drift, and how would you detect it needs full re-indexing?**
Drift happens when the model version changes (even a minor update) or the underlying data distribution
shifts, silently invalidating the geometric assumptions your index was built under. Detect it by tracking
retrieval quality metrics (recall@k on a fixed eval set) over time, monitoring the centroid/variance of
newly ingested embeddings against the original corpus's distribution, and treating any embedding model
version bump as a hard requirement to re-embed the whole corpus, not just new documents.

**12. How do multilingual embedding models achieve cross-lingual retrieval?**
They're trained on parallel/translated corpora so that a sentence and its translation are pushed to nearby
points regardless of source language, effectively building one shared semantic space across languages. This
breaks down for low-resource languages with little parallel training data — the model has seen too few
examples to learn a reliable mapping, so retrieval quality for those languages lags well behind
high-resource ones (English, Chinese, Spanish).

**13. Impact of tokenization/truncation limits on long documents, and how ColBERT addresses it.**
Most bi-encoders truncate input at a fixed token limit (e.g., 512) and compress the whole thing into one
vector, discarding information beyond the limit and blending everything before it into a single mean/pooled
representation — losing fine-grained detail. ColBERT instead keeps a vector *per token* and computes
similarity as a sum of per-token maximum similarities ("late interaction"), preserving much more
fine-grained matching at the cost of much larger storage (one vector per token instead of one per
document).

**14. Dense vs. sparse vs. learned-sparse (SPLADE) embeddings — when does sparse win?**
Dense embeddings are compact, fixed-length vectors capturing latent semantics; sparse embeddings (classic
TF-IDF/BM25) are high-dimensional but mostly zero, directly tied to vocabulary terms; learned-sparse
(SPLADE) uses a neural model to *predict* term-weight expansions, combining sparse's exact-term precision
with some semantic generalization. Sparse (and SPLADE) tend to win on queries with rare, exact tokens —
product SKUs, legal citations, error codes — where dense embeddings tend to over-generalize past the exact
term that actually matters.

**15. How would you evaluate a new embedding model beyond public benchmarks like MTEB?**
MTEB scores are aggregate and task-general; they don't guarantee performance on your corpus's vocabulary,
document length distribution, or query style. Build a small labeled eval set from your own data (even
50-200 query→relevant-doc pairs), measure recall@k/NDCG with the candidate model vs. your current one, and
run an online A/B test on a query sample before a full rollout — offline gains don't always survive contact
with real user queries.

## Similarity Metrics & the Math Underneath

**16. Derive why cosine similarity and dot product are equivalent for L2-normalized vectors.**
Cosine similarity is `(A · B) / (‖A‖ ‖B‖)`. If both vectors are normalized so `‖A‖ = ‖B‖ = 1`, the
denominator becomes 1, leaving just `A · B` — the dot product. This is why many vector databases only
implement dot product internally and get cosine similarity "for free" by normalizing vectors at insert
time.

```python
import numpy as np

def cosine_sim(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

a_norm = a / np.linalg.norm(a)
b_norm = b / np.linalg.norm(b)
assert np.isclose(cosine_sim(a, b), np.dot(a_norm, b_norm))
```

**17. When is Euclidean distance a better choice than cosine similarity?**
Euclidean distance accounts for vector *magnitude*, not just direction — useful when magnitude itself
carries meaning (e.g., embeddings where norm correlates with confidence, popularity, or intensity). Cosine
similarity, which normalizes magnitude away, is generally preferred for text embeddings where direction
alone encodes semantic meaning and magnitude is often an artifact of text length rather than signal.

**18. Geometric interpretation of the curse of dimensionality for nearest-neighbor search.**
As dimensionality grows, the volume of a high-dimensional space grows exponentially, so any fixed number of
data points becomes exponentially sparser — most of a hypersphere's volume concentrates near its surface
rather than its center, and the ratio between the nearest and farthest neighbor distances shrinks toward 1.
Practically, "nearest" and "far" stop being meaningfully different, which is why brute-force
distance-threshold search breaks down and graph/cluster-based ANN algorithms (which don't rely on absolute
distance thresholds) become necessary.

**19. Why does concentration of measure make distances look similar in high dimensions?**
For many common distributions, as dimensionality increases, the variance of pairwise distances shrinks
relative to their mean — nearly all points end up roughly equidistant from a given query. ANN algorithms
cope not by fixing this (it's a property of the data, not a bug in the algorithm) but by relying on *local*
structure (graph neighborhoods in HNSW, cluster membership in IVF) rather than global distance thresholds,
since local relative ordering remains meaningful even when absolute distances compress.

**20. What is Mahalanobis distance, and when would you prefer it?**
Mahalanobis distance accounts for the covariance structure of the data, effectively rescaling and
de-correlating dimensions before measuring distance — two points that differ mostly along a
low-variance/highly-correlated axis are considered "closer" than raw Euclidean distance would suggest.
Prefer it when embedding dimensions have very different scales or are correlated (e.g., combining raw
numeric features with embeddings), which is rare for pure text embeddings but common in tabular/feature-store
similarity search.

**21. How does vector normalization affect which ANN algorithms and indexes remain valid?**
Once vectors are normalized to unit length, cosine similarity, dot product, and (monotonically) Euclidean
distance all produce the *same ranking* of nearest neighbors — `‖a-b‖² = 2 - 2(a·b)` for unit vectors — so
an index built for Euclidean distance (like standard HNSW/FAISS L2 index) can be used for cosine similarity
simply by normalizing vectors before insertion and query. This is a common trick to use an L2-only index for
a cosine-similarity use case without reimplementing distance functions.

**22. Why is maximum inner product search (MIPS) not just cosine similarity with a different name?**
MIPS explicitly does *not* normalize vectors — it optimizes for raw dot product, where vector magnitude
matters (common in recommendation systems where norm can encode item popularity or user engagement
strength). Because MIPS breaks the triangle inequality assumptions many ANN algorithms rely on, it requires
specialized techniques (e.g., transforming MIPS into an equivalent nearest-neighbor problem in an augmented
space) rather than dropping straight into a cosine-similarity ANN index.

**23. Effect of unnormalized vector magnitude on dot-product retrieval (popularity bias).**
If item embeddings aren't normalized and their norm correlates with, say, how frequently an item was
interacted with during training, dot-product retrieval will systematically favor high-norm (popular) items
regardless of true relevance to the query — a hidden popularity bias baked into the geometry. Normalizing
vectors before indexing (switching to cosine similarity) removes this bias, at the cost of losing whatever
signal the magnitude legitimately carried.

**24. How would you detect and fix a "hubness" problem?**
Hubness shows up as a small subset of vectors appearing disproportionately often in other points' top-K
nearest-neighbor lists, regardless of query — detectable by measuring the k-occurrence distribution across
your corpus and flagging heavy right-skew. Mitigations include local/mutual scaling (rescaling distances
based on each point's own neighborhood density), re-ranking with a secondary, less hub-prone metric, or
removing/down-weighting known hub items directly.

**25. Why is exact k-NN sometimes still the right choice, and where does it stop scaling?**
Brute-force search guarantees perfect recall with zero index-build time or approximation error — fine for
corpora up to roughly a few hundred thousand vectors on modern hardware with vectorized distance
computation (e.g., matrix multiply on GPU). Past roughly 1M+ vectors, or when query latency budgets are in
the tens of milliseconds, linear scan's O(n) cost per query becomes the bottleneck and an ANN index
becomes necessary.

## ANN Algorithms: HNSW, IVF, PQ, DiskANN, LSH

**26. How does HNSW's layered graph achieve near-logarithmic search?**
HNSW builds multiple graph layers, where higher layers contain exponentially fewer nodes and longer-range
edges. Search starts at the sparse top layer, greedily moves toward the query, then drops down a layer and
repeats with finer-grained edges — like a skip list, this gets you close to the answer in
O(log n)-ish hops before doing detailed search in the dense bottom layer. `M` controls how many neighbor
edges each node keeps (higher = better recall, more memory); `efConstruction` controls how thorough the
search is *while building* the graph (higher = better graph quality, slower to build).

```python
import hnswlib

index = hnswlib.Index(space='cosine', dim=384)
index.init_index(max_elements=1_000_000, M=16, ef_construction=200)
index.add_items(embeddings, ids)
index.set_ef(64)  # runtime search parameter, see Q27
labels, distances = index.knn_query(query_embedding, k=10)
```

**27. Why does increasing `ef_search` trade recall for latency?**
`ef_search` controls how many candidate nodes HNSW keeps in its exploration frontier at query time — a
larger frontier explores more of the graph before settling on the top-K result, increasing the odds the
true nearest neighbors are found (higher recall) at the cost of visiting more nodes (higher latency). Tune
it by binary-searching for the smallest `ef_search` that meets your recall target on a held-out
ground-truth set, then re-check periodically as the index grows.

**28. Why is deletion hard for graph-based ANN indexes?**
Removing a node from an HNSW graph can disconnect its neighbors from the rest of the graph if that node was
a critical bridge, since edges were built assuming that node's presence — naive deletion silently degrades
recall over time as the graph accumulates "dead" connectivity gaps. Most implementations handle this with
soft deletes (mark as deleted, filter from results, exclude from future edge-building) and periodic full
rebuilds rather than true in-place structural deletion.

**29. IVF-Flat vs. IVF-PQ: what's approximated, and the trade-off?**
Both cluster vectors into `nlist` buckets via k-means and only search buckets near the query (controlled by
`nprobe`) — that's the approximation both share, trading exhaustive search for speed. IVF-Flat then stores
and compares *full-precision* vectors within the probed buckets (exact distance, less compression); IVF-PQ
additionally compresses each vector into a small set of quantized codes, trading further recall for a much
smaller memory footprint (often 8-32x smaller) at the cost of only approximate in-bucket distances.

**30. How does Product Quantization compress a vector?**
PQ splits each vector into `m` subvectors, runs k-means separately on each subvector's slice across the
whole dataset to learn a small codebook (e.g., 256 centroids per subspace), then represents the original
vector as `m` small integer codes (one per subspace) pointing to its nearest centroid in each. Splitting
into subvectors before quantizing lets you represent an exponentially large number of possible combined
vectors (256^m) from a codebook of only `256*m` total centroids — far more expressive than quantizing the
whole vector at once.

```python
import faiss

d, m, nbits = 128, 8, 8  # 128-dim vectors, 8 subquantizers, 8 bits each -> 1 byte/subvector
pq = faiss.IndexPQ(d, m, nbits)
pq.train(training_vectors)      # learns the codebooks
pq.add(corpus_vectors)          # compresses and stores
distances, ids = pq.search(query_vectors, k=10)
```

**31. `nprobe` (IVF) vs. `ef_search` (HNSW) — what's being controlled in each?**
Both are runtime recall/latency knobs, but over different structures: `nprobe` controls how many of the
`nlist` coarse clusters get searched (a breadth knob over a flat partitioning), while `ef_search` controls
how large the candidate frontier is while traversing a graph (a breadth knob over graph exploration).
Conceptually equivalent purpose, structurally different mechanism.

**32. Why is HNSW's memory footprint ~1.5-2x the raw vector data?**
Beyond storing the full-precision vectors themselves, HNSW stores an adjacency list of `M` (typically
16-64) neighbor edges per node at the base layer, plus fewer edges at higher layers — that graph structure
is pure overhead on top of the vectors. At billion-scale, this overhead becomes the dominant cost driver,
which is why billion-vector deployments often pair HNSW with quantization (reducing the vector cost) or
switch to disk-resident structures like DiskANN.

**33. How does DiskANN (Vamana graph) enable billion-vector search mostly on SSD?**
DiskANN builds a Vamana graph optimized to minimize the number of *sequential disk reads* needed per query
(unlike HNSW, which assumes random-access RAM), keeps a compressed (PQ) copy of vectors in memory for fast
approximate scoring, and only fetches full-precision vectors from SSD for final re-ranking of the shortlist.
This lets an index far larger than available RAM still hit low double-digit-millisecond latencies, since
most of the graph traversal cost is paid against cheap in-memory compressed vectors.

**34. LSH's fundamental trade-off vs. HNSW, and why it's fallen out of favor.**
LSH hashes vectors so that similar vectors are more likely to collide into the same bucket, giving
probabilistic (not graph-based) approximate retrieval with theoretical guarantees and simple, embarrassingly
parallel updates. In practice it needs many hash tables to reach competitive recall, and at equal recall
targets it's typically slower and uses more memory than HNSW/graph-based methods on real embedding data —
its main remaining niche is streaming/theoretical settings that value LSH's simple insert/delete semantics
over raw performance.

**35. IVF-PQ vs. HNSW for a 500M-vector, memory-constrained deployment.**
IVF-PQ is the stronger fit: its compression ratio (often 8-32x) directly attacks the memory constraint,
while HNSW's uncompressed vectors plus graph overhead would require far more RAM at that scale. The
trade-off is IVF-PQ generally needs a re-ranking pass with exact distances on a shortlist to recover
accuracy lost to quantization, and its recall is more sensitive to how well the `nlist`/`nprobe` and PQ
codebook were tuned for your data's distribution.

**36. Why is exact re-ranking after ANN pre-filtering a common two-stage pattern?**
The ANN stage (HNSW, IVF-PQ) is optimized for speed over a huge corpus but sacrifices precision; re-scoring
just the top ~100-1000 candidates with an exact (or heavier, e.g., cross-encoder) method recovers most of
that lost precision at a fraction of the cost of running the exact method over the whole corpus. It's the
same "cheap filter, expensive re-rank" pattern used throughout information retrieval, from search engines
to recommendation systems.

**37. What breaks in HNSW recall guarantees under metadata filtering?**
*Post-filtering* (search top-K, then discard non-matching metadata) can return far fewer than K results if
the true matches aren't in the initial unfiltered top-K — recall silently craters for selective filters.
*Pre-filtering* (only allow matching nodes into the graph traversal) fixes that but can break HNSW's
navigability assumptions if the filtered subset is sparse and poorly connected in the original graph.
*Filtered-HNSW* variants build filter-aware graph structures specifically to avoid both failure modes, at
the cost of index complexity.

**38. How do you benchmark recall@k for an ANN index against ground truth?**
Compute exact brute-force top-K for a sample of queries (using the full corpus), compute the ANN index's
top-K for the same queries, and measure the overlap fraction:

```python
def recall_at_k(ann_results, exact_results):
    scores = []
    for ann_ids, exact_ids in zip(ann_results, exact_results):
        overlap = len(set(ann_ids) & set(exact_ids))
        scores.append(overlap / len(exact_ids))
    return sum(scores) / len(scores)
```

A few hundred to a few thousand sampled queries is usually enough for a stable estimate — more matters
more when recall is already high (>95%) and you're trying to detect small regressions.

**39. What is the "entry point" problem in HNSW, and how does the top layer solve it?**
Greedy graph search needs a starting node; a poorly chosen entry point in a large, dense bottom-layer graph
could require many hops to reach the query's true neighborhood. HNSW's sparse top layer(s) act as a
long-range "highway" — search starts at a fixed entry point in the sparsest layer, quickly converges toward
the query's general region using long edges, then descends layer by layer into progressively denser,
shorter-range structure for fine-grained search.

**40. Scalar/binary quantization vs. Product Quantization for memory reduction.**
Scalar quantization independently rounds each dimension to a smaller numeric type (float32 → int8 → 1-bit),
which is simple, fast, and requires no training step, but doesn't exploit correlations between dimensions.
PQ jointly quantizes groups of dimensions via learned codebooks, generally achieving better
compression-vs-recall trade-offs for the same compression ratio, but requires a training pass and more
implementation complexity. Scalar/binary quantization has become popular recently because "simple and 4-8x
smaller, retrain-free" is often good enough, especially combined with an exact re-ranking pass.

## Vector Database & System Design

**41. Design: 100M vectors, sub-50ms p99, real-time upserts.**
Use an HNSW-based index (fast, good recall, supports incremental inserts natively unlike IVF's static
clustering) sharded across nodes by hash of document ID for horizontal scale, with a write path that
inserts into the live graph directly (HNSW tolerates online inserts reasonably well) and a background
compaction job to handle deletes (soft-delete + periodic rebuild, per Q28). Put a re-ranking stage behind
initial retrieval only if precision requirements justify the extra latency budget; at sub-50ms p99, budget
carefully between network hop, ANN search, and any re-ranking.

**42. How would you shard a vector index, and what does that do to recall?**
Shard by hashing document ID (or another uniform key) across N nodes, fan the query out to all shards in
parallel, then merge each shard's local top-K into a global top-K. Recall is generally preserved as long as
each shard runs its own ANN search independently and correctly — the risk is *latency* (tail latency = max
across shards, not average) and coordination overhead, not recall, provided you request top-K from *every*
shard rather than routing to a subset.

**43. Pre-filtering vs. post-filtering metadata — failure modes of each.**
Post-filtering (search unfiltered top-K, then drop non-matches) is simple but can return far fewer than K
results — or zero — when the filter is selective (e.g., "only my tenant's 50 documents in a 10M-vector
index"). Pre-filtering (restrict the ANN search to only candidates matching the filter first) avoids that
but is harder to implement efficiently against a graph/cluster index built without filter-awareness, and can
degrade recall if the filtered subset breaks the index's navigability assumptions (same issue as Q37).

**44. Why is hybrid search (BM25 + vector) often more robust, and how do you combine results?**
Vector search generalizes well semantically but can miss exact-term matches (SKUs, names, error codes)
that keyword search nails; BM25 is the reverse. Combining both hedges against each one's blind spots. The
standard combination technique is Reciprocal Rank Fusion (RRF), which avoids needing to normalize
incomparable score scales:

```python
def reciprocal_rank_fusion(rank_lists, k=60):
    scores = {}
    for ranks in rank_lists:                       # each ranks: ordered list of doc_ids
        for rank, doc_id in enumerate(ranks):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)

fused = reciprocal_rank_fusion([bm25_ranked_ids, vector_ranked_ids])
```

**45. Consistency guarantees for a real-time vector index.**
Chat/real-time use cases usually need read-your-writes consistency for the writer (a user should see their
own just-sent message reflected immediately) but can tolerate eventual consistency for *other* users'
recent writes being briefly missing from search. Most managed vector DBs offer eventual consistency by
default for performance; if you need stronger guarantees, route a user's own recent writes through a small
in-memory overlay checked alongside the main index until they've propagated.

**46. Multi-tenancy: shared index with `tenant_id` filtering vs. per-tenant indexes.**
A shared index with metadata filtering is simpler to operate (one index to scale/monitor) but runs into the
pre/post-filtering recall problems from Q43 when tenants are small relative to the whole corpus, and one
tenant's load can affect another's latency (noisy neighbor). Per-tenant indexes isolate performance and
avoid the filtering problem entirely, but multiply operational overhead (thousands of small indexes) and
waste resources on tiny tenants. A common middle ground: shared index for small tenants, dedicated index
past a size/traffic threshold.

**47. Managed (Pinecone) vs. self-hosted (Qdrant/Milvus) cost at 1B+ vectors.**
Managed pricing is largely driven by stored vector count and query volume, bundling in operational overhead
(scaling, backups, upgrades, on-call) you'd otherwise staff yourself. Self-hosting trades that premium for
raw infra cost (compute + storage) plus your own engineering time to operate a distributed system reliably
at that scale — at 1B+ vectors, self-hosting is usually cheaper on paper but only nets out ahead if you
already have the platform expertise to run it without regularly paging someone.

**48. Handling index rebuilds when swapping embedding models, without downtime.**
Build the new index fully offline/in parallel against the new model while the old index keeps serving
traffic, validate the new index's quality against an eval set, then atomically swap read traffic over
(blue-green deployment) once validated — never mutate the live index in place. Keep the old index available
briefly post-swap for fast rollback if the new model underperforms in production.

**49. Role of a write-ahead log in a vector database.**
A WAL persists every write to durable storage *before* acknowledging it, so an in-memory index (like HNSW,
which is expensive to rebuild) can be reconstructed after a crash without data loss. Some early/simpler
vector databases skip this for raw insert throughput, accepting that a crash means losing recent unflushed
writes — an acceptable trade for some caching/recommendation use cases, unacceptable for anything treating
the vector store as a system of record.

**50. Designing backup/DR for an index that takes 6 hours to rebuild.**
Don't rely on rebuild-from-source as your only recovery path — snapshot the built index artifact itself
(not just raw vectors) on a schedule matched to your RPO, replicate snapshots cross-region, and separately
ensure the raw source vectors/documents are durably stored so a full rebuild remains possible as a
last-resort fallback. Regularly test restoring from a snapshot; an untested backup is not a backup.

**51. How does `pgvector` integrate ANN indexing into Postgres, and where does it fall short at scale?**
`pgvector` adds a vector column type and IVFFlat/HNSW index types that plug into Postgres's normal query
planner, so vector similarity search can be combined with regular SQL `WHERE` clauses, joins, and
transactions using infrastructure you already operate. It falls short of purpose-built vector databases at
very large scale (100M+ vectors) where Postgres's general-purpose storage engine and single-writer-node
architecture become bottlenecks that dedicated, horizontally-shardable vector databases were built to avoid.

```sql
CREATE EXTENSION vector;
CREATE TABLE docs (id bigserial PRIMARY KEY, embedding vector(384), body text);
CREATE INDEX ON docs USING hnsw (embedding vector_cosine_ops);
SELECT id, body FROM docs ORDER BY embedding <=> '[0.1, 0.2, ...]' LIMIT 10;
```

**52. Impact of over-fetching before re-ranking.**
Fetching top-50 instead of top-5 gives the re-ranker more candidates to potentially recover a relevant
document that barely missed the top-5 cutoff in the first-pass retrieval — improving final precision — but
linearly increases re-ranking cost and latency, since cross-encoder re-ranking cost scales with the number
of candidates scored. Tune the fetch size to the point where recall@fetch-size plateaus on your eval set;
past that point you're paying re-ranking cost for no accuracy gain.

**53. Versioning a vector index to A/B test two embedding models.**
Maintain two fully separate indexes (one per model version), route a percentage of query traffic to each
based on a consistent hash of user/session ID (so a given user sees stable behavior during the test), and
compare downstream metrics (click-through, task success, retrieval-quality proxy metrics) between arms
before deciding to fully cut over.

**54. Caching strategy for a vector search system with repetitive queries.**
Cache at two levels: an exact-match cache keyed by the raw query string → final result list (cheap,
catches literal repeats like common FAQ phrasings), and optionally a semantic cache that checks whether a
new query's embedding is within a tight similarity threshold of a recently cached query before doing a full
ANN search. Invalidate both whenever the underlying corpus changes for the affected documents, not on a
blind TTL alone, or you'll serve stale results after content updates.

**55. Monitoring signals for a degraded vector index.**
Track recall@k against a fixed eval set on a schedule (catches silent index/algorithm regressions),
query-time embedding norm/distribution drift vs. the corpus's original distribution (catches embedding
model or input-data drift), p50/p99 query latency (catches index bloat or resource contention), and the
rate of zero-result or low-max-score queries (catches coverage gaps in the corpus).

## RAG Architecture & Chunking

**56. Why is chunk size the highest-leverage tuning knob in RAG?**
Too-large chunks dilute the embedding with multiple topics, making similarity search less precise and
wasting context-window budget on irrelevant surrounding text; too-small chunks lose surrounding context
needed to correctly answer a question, and multiply the number of chunks (and embedding/storage cost) for
the same corpus. Almost every other RAG lever (re-ranking, hybrid search, query rewriting) is compensating
for a chunking strategy that isn't well matched to the corpus's actual document structure.

**57. Fixed-size vs. sentence-based vs. semantic chunking — when does each win?**
Fixed-size (e.g., 500 tokens with overlap) is simplest and predictable but can split mid-sentence or
mid-idea; sentence-based respects grammatical boundaries but produces uneven chunk sizes; semantic chunking
(splitting where consecutive-sentence embedding similarity drops, i.e., topic shifts) best preserves
coherent ideas per chunk but costs extra embedding calls at ingestion time and is harder to reason about
predictably. Fixed-size is a reasonable default; semantic chunking earns its cost on long, topically
heterogeneous documents (reports, transcripts) where topic boundaries don't align with fixed token counts.

```python
def semantic_chunk(sentences, embed_fn, similarity_threshold=0.5):
    chunks, current = [], [sentences[0]]
    prev_emb = embed_fn(sentences[0])
    for sent in sentences[1:]:
        emb = embed_fn(sent)
        if cosine_sim(prev_emb, emb) < similarity_threshold:
            chunks.append(" ".join(current))
            current = []
        current.append(sent)
        prev_emb = emb
    chunks.append(" ".join(current))
    return chunks
```

**58. What is "lost in the middle," and how does it affect chunk ordering?**
LLMs empirically attend more reliably to content near the start and end of a long context window than
content buried in the middle, so a correct answer contained in a middle-positioned chunk is more likely to
be missed or under-weighted by the model. Mitigate by placing the highest-relevance-scored chunks at the
start and/or end of the assembled context rather than in original-document or arbitrary retrieval order.

**59. Handling documents with tables or code blocks that naive splitting mangles.**
Use structure-aware splitting: detect table/code boundaries (via markdown/HTML parsing or a
layout-detection model for PDFs) and treat them as atomic, unsplittable units even if they exceed the
target chunk size, rather than letting a fixed-token splitter cut a table row or function mid-way. For
tables specifically, consider also emitting a plain-text or JSON summary of the table alongside the raw
table, since embedding models often handle prose better than tabular structure.

**60. Parent-document retrieval — what problem does it solve?**
Retrieve using small, precise chunks (better embedding signal, more accurate similarity matching) but
return the larger parent section/document those chunks belong to as the actual LLM context, so the model
gets full surrounding context even though retrieval matched on a narrow, specific passage. This decouples
"what unit gives the best retrieval signal" from "what unit the LLM actually needs to answer well" — they're
often not the same size.

**61. Contextual retrieval / chunk-level context injection — why does it improve recall?**
Before embedding a chunk, prepend a short, LLM-generated summary of what the *whole document* is about and
how this chunk fits in, so the chunk's embedding carries context that would otherwise be lost when it's
isolated from its surrounding document. This meaningfully improves retrieval for chunks whose isolated text
is ambiguous or pronoun-heavy ("it increased by 12% that quarter" — an isolated chunk that means nothing
without knowing what "it" refers to).

**62. Designing chunk overlap — failure modes of too little/too much.**
Overlap (repeating some trailing text from chunk N at the start of chunk N+1) prevents a fact from being
silently split across a chunk boundary and lost from both chunks' embeddings. Too little overlap risks
exactly that split-fact loss at boundaries; too much overlap bloats the index with redundant near-duplicate
content, wastes storage/embedding cost, and can cause the same fact to dominate retrieved results multiple
times, crowding out other relevant chunks.

**63. Why embed a document summary alongside its chunks?**
A summary-level embedding lets a broad, document-level query ("what is this report about") match well even
when no individual chunk alone represents the whole document's gist — individual chunks are necessarily
narrow. Retrieving at both granularities (summary for broad queries, chunks for specific ones) and letting
the retrieval scores decide which wins per-query covers both query types without hand-classifying query
intent upfront.

**64. Multi-vector retrieval (ColBERT-style) — why it can beat single-vector dense retrieval.**
Compressing a whole document into one vector forces a lossy average over everything it contains; keeping
one vector per token and scoring via per-token max-similarity (then summing) lets the model match on the
*specific* tokens/phrases that are actually relevant to the query, without that signal being diluted by
the rest of the document. The cost is storage and compute — you're storing and comparing against far more
vectors per document.

**65. Designing retrieval for a corpus mixing short FAQs and 100-page PDFs.**
Chunk each document type appropriately for its own structure (FAQs might be one chunk = one Q&A pair;
PDFs need proper chunking with overlap) rather than forcing one fixed chunk-size policy across a
heterogeneous corpus, and consider normalizing for length bias at retrieval time (short, precise FAQ chunks
can score artificially high on cosine similarity against short queries purely due to their concentrated
content) — e.g., via per-source-type score calibration or separate retrieval passes merged with RRF.

**66. Query expansion / HyDE — why it helps with short, ambiguous queries.**
HyDE has an LLM first generate a *hypothetical answer* to the user's query, then embeds that hypothetical
answer (instead of the raw query) to search the corpus — since a full hypothetical answer's embedding is
often closer, semantically, to real matching documents than a short, underspecified query's embedding
would be on its own. This helps most when queries are terse or use different vocabulary than the corpus
("side effects of aspirin" vs. a corpus written in dense clinical language).

**67. Handling multi-hop questions requiring retrieval from two unrelated corpus parts.**
Single-shot retrieve-then-generate typically fails here because one embedding search can't simultaneously
target two unrelated pieces of information. The fix is iterative/agentic retrieval: have the model retrieve
for the first sub-question, read the result, formulate a follow-up query based on what it learned, retrieve
again, and only then synthesize a final answer — this is the core idea behind agentic RAG (see Q98).

**68. Trade-off: more retrieved chunks (recall) vs. context cost/noise (precision).**
Every additional chunk increases the odds the true answer is somewhere in context (recall) but also
increases token cost, latency, and the chance of "lost in the middle" or the model getting distracted by
irrelevant-but-plausible-looking chunks (precision loss). The two-stage retrieve-then-rerank pattern (Q69)
exists specifically to break this trade-off: retrieve broadly for recall, then re-rank and truncate for
precision before the LLM ever sees the context.

**69. Why re-rank after ANN retrieval instead of retrieving top-K with a cross-encoder directly?**
Cross-encoders are far more accurate at scoring relevance but require a full model forward pass per
query-document pair, making them computationally infeasible to run against an entire corpus (millions of
documents) per query. The two-stage pattern uses cheap ANN retrieval to cut the corpus down to a
manageable shortlist (e.g., top-100), then applies the expensive, accurate cross-encoder only to that
shortlist — getting cross-encoder-level precision at a small fraction of the cost.

**70. Incorporating recency/freshness into retrieval scoring without hand-tuned decay weights.**
Rather than a fixed exponential decay constant per corpus (which needs re-tuning as content velocity
changes), train or calibrate the decay function against actual user engagement/feedback data (does
freshness correlate with click-through or task success in *this* corpus?), or fold recency in as one signal
into a learned re-ranking model alongside similarity score, rather than as a hard-coded multiplier applied
uniformly regardless of query type.

## RAG Evaluation & Failure Modes

**71. Evaluating retrieval quality independently from generation quality.**
Build a labeled set of (query, relevant document IDs) pairs and measure retrieval-only metrics — recall@k,
precision@k, MRR, NDCG (Q82) — without ever invoking the LLM. This isolates "did we find the right
documents" from "did the LLM use them well," which is essential because a bad final answer could stem from
either stage, and conflating them makes debugging much slower.

**72. Detecting hallucination caused by poor retrieval vs. poor grounding.**
If the correct information genuinely isn't in the retrieved context (verify by checking retrieval recall
against ground truth), any hallucination is a retrieval-stage failure. If the correct information *is*
present in the retrieved context but the model's answer contradicts or ignores it, that's a
grounding/generation-stage failure — measured by a faithfulness metric (Q73) that checks whether each claim
in the answer is actually supported by the provided context, independent of whether the context was
correct.

**73. Faithfulness vs. answer relevance — how does RAGAS measure each?**
Faithfulness measures whether every claim in the generated answer is actually supported by the retrieved
context (typically via an LLM-judge decomposing the answer into atomic claims and checking each against the
context) — it catches hallucination even when retrieval was correct. Answer relevance measures whether the
answer actually addresses the user's question (e.g., by generating candidate questions the answer *would*
answer, and checking their similarity to the original query) — a fully faithful answer can still be
irrelevant if it faithfully answers the wrong question.

**74. Building a golden eval set without labeled query-document pairs.**
Use an LLM to generate synthetic questions from sampled corpus chunks (the source chunk becomes the known
"relevant document" for that generated question), have a human spot-check a sample of the synthetic
question-answer-source triples for quality, and supplement with real production query logs once available
— synthetic generation gets you a usable starting eval set immediately, real usage data improves it over
time.

**75. Diagnosing why a correct answer in the corpus is never retrieved.**
Work backward through the pipeline: first confirm the document is actually chunked and indexed (ingestion
bug); then run the query embedding directly against the target chunk's embedding to check raw similarity
(embedding/chunking mismatch — maybe the chunk boundary split the relevant fact away from its context, or
the chunk's phrasing is too different from the query's); then check whether the ANN index itself is
returning it in a brute-force comparison but the approximate search is missing it (ANN recall issue, tune
`ef_search`/`nprobe`, Q27/Q31).

**76. Why can more retrieved context decrease answer accuracy?**
Additional chunks that are topically related but not actually relevant to the specific question can
distract the model into blending in irrelevant details, contradict the correct chunk with a
plausible-sounding but wrong alternative source, or simply push the truly relevant chunk into a
"lost in the middle" position (Q58) — more context is not strictly better past the point where it starts
introducing noise faster than signal.

**77. Detecting and mitigating confident answers from irrelevant retrieved context.**
Add an explicit "insufficient context" instruction and option in the generation prompt so the model is
given permission to decline rather than forced to always synthesize an answer, and separately score
retrieved-context relevance (e.g., via the re-ranker's score, Q69) — if the top result's relevance score is
below a threshold, short-circuit to "not found" before even calling the LLM, rather than trusting the model
to self-detect low-quality retrieval every time.

**78. Offline vs. online RAG evaluation — why you need both.**
Offline evaluation (a fixed labeled test set) is fast, reproducible, and lets you catch regressions before
deploying, but it can't capture the full diversity and drift of real user queries or measure actual user
satisfaction. Online evaluation (production feedback signals: thumbs up/down, follow-up-question rate,
session abandonment) captures real-world performance but is slower, noisier, and only tells you *after* a
bad change has already shipped — offline evaluation is your pre-deployment gate, online evaluation is your
ongoing ground truth.

**79. LLM-as-judge for RAG evaluation — and its biases.**
An LLM judge scores generated answers against retrieved context and/or a reference answer using a rubric
prompt, scaling evaluation far beyond what manual human review can cover. Known biases include favoring
longer, more verbose answers regardless of correctness; favoring answers stylistically similar to the
judge model's own outputs; and inconsistency/sensitivity to prompt phrasing of the judging rubric itself —
mitigate with multiple judge samples, calibration against a small human-labeled set, and using a
different/stronger model as judge than the one being evaluated where possible.

**80. Impact of embedding model/corpus drift on retrieval metrics measured at launch.**
Metrics measured at launch reflect the corpus and query distribution *at that time*; if the corpus grows
with new content types, or user query patterns shift (e.g., new product launch changes what people search
for), the original eval set stops representing current reality and launch-time metrics silently become
stale, masking real degradation. Re-run evaluation periodically against a refreshed sample of recent
production queries, not just the original fixed set.

**81. A/B testing a chunking strategy change without degrading the control group.**
Route a small percentage of traffic to the new chunking strategy's index (built and validated offline
first), keep the majority on the existing, proven index, monitor both offline retrieval metrics and online
engagement signals for the experimental arm before ramping traffic up, and have a fast rollback path (route
back to 100% control) if the new arm underperforms — never fully cut over on the strength of offline
metrics alone.

**82. Precision@k, recall@k, MRR, NDCG — when to prefer NDCG over recall@k?**
Precision@k = fraction of the top-k results that are relevant; recall@k = fraction of all relevant
documents captured in the top-k; MRR = average of 1/(rank of first relevant result), rewarding getting a
relevant result *early*; NDCG additionally weights *how* relevant each result is (graded relevance, not
just binary) and discounts by position. Prefer NDCG when relevance isn't binary (some documents are
"perfect," others "somewhat relevant") and ranking order genuinely matters for user experience — recall@k
treats a perfect match at rank 1 and a mediocre match at rank k identically as long as both appear.

```python
import numpy as np

def dcg_at_k(relevances, k):
    relevances = np.array(relevances)[:k]
    return np.sum(relevances / np.log2(np.arange(2, len(relevances) + 2)))

def ndcg_at_k(relevances, ideal_relevances, k):
    dcg = dcg_at_k(relevances, k)
    idcg = dcg_at_k(sorted(ideal_relevances, reverse=True), k)
    return dcg / idcg if idcg > 0 else 0.0
```

**83. "Needle in a haystack" tests vs. realistic RAG evaluation.**
Needle-in-a-haystack tests insert one synthetic, easily-verifiable fact into a long context and check
whether the model can retrieve it verbatim — a clean, narrow test of raw retrieval/attention capability.
Realistic RAG evaluation involves messier, ambiguous real documents, multiple plausible-but-wrong
distractors, and questions requiring synthesis across several chunks rather than verbatim lookup of one
inserted fact — passing needle tests is necessary but far from sufficient evidence of real-world RAG
quality.

**84. Evaluating whether hybrid search actually beats vector-only for your corpus.**
Run both configurations (vector-only, hybrid with RRF) against the same labeled eval set and compare
recall@k/NDCG directly — don't assume hybrid always wins, since for a corpus with little exact-term
querying (natural-language questions against prose documents) the added complexity of a keyword index may
yield negligible or even negative gains after fusion tuning overhead is accounted for. The benefit of
hybrid search is real but corpus-and-query-distribution dependent, not universal.

**85. Risk of evaluating a RAG system solely on public benchmark scores like MTEB.**
Public benchmarks measure general-purpose retrieval ability across broad, often web-scale text — they say
little about performance on your specific domain vocabulary, document structure, or query phrasing (legal
contracts, internal engineering docs, medical notes all diverge significantly from benchmark distributions).
A model that tops MTEB can underperform a lower-ranked, domain-fine-tuned model on your actual corpus; only
your own eval set tells you the truth for your use case.

## Production, Scaling & Operations

**86. Estimating infra cost for 10M queries/day against a 50M-document corpus.**
Break the estimate into: embedding cost (one-time for 50M documents at ingestion, then per-query for 10M
daily queries — dominant recurring cost if using a hosted embedding API), vector storage/compute cost
(index size scales with document count and chosen dimensionality/compression), and LLM generation cost
(per-query, usually the single largest line item if using a hosted LLM API). Model each component's
$/1000-operations rate against expected volume, and stress-test the estimate against p99 query volume, not
just average daily rate.

**87. Re-embedding 100M documents on an embedding model switch, without downtime.**
Run the re-embedding job as a background batch process writing into a *new* index while the old index keeps
serving live traffic unchanged, validate the new index against your eval set once complete, then perform an
atomic traffic cutover (blue-green) — same pattern as Q48. Budget for the batch job's own cost and time (at
100M documents, embedding API rate limits or GPU throughput becomes the binding constraint, not the index
itself).

**88. Handling PII/access-controlled documents in a shared vector index.**
Store an access-control list or tenant/permission tag as metadata on each vector and enforce filtering at
query time (with the pre-filtering caveats from Q43), or maintain physically separate indexes for
sensitivity tiers if regulatory requirements demand hard isolation rather than logical filtering.
Critically, apply access checks *before* returning any retrieved content to the LLM or user — a
post-filtering approach risks the LLM having already "seen" unauthorized content during generation even if
it's filtered from the final response.

**89. Latency budget breakdown for a typical RAG request.**
Roughly: query embedding (a few ms for a small model, tens of ms for a large hosted API call), ANN search
(single-digit to tens of ms depending on index size/algorithm), re-ranking if present (can be the largest
non-LLM cost if using a cross-encoder over dozens of candidates), and LLM generation (typically the largest
share of total latency by far, often hundreds of ms to several seconds depending on output length) —
optimization effort is usually best spent on generation latency (streaming, smaller/faster models) once
retrieval is already reasonably tuned.

**90. Designing incremental indexing for a constantly-updated corpus.**
Support online upserts directly against the live index (HNSW handles this natively) rather than only
supporting full rebuilds, process document changes through an ingestion queue (embed → upsert) decoupled
from the write path that created the document change, and periodically run a background compaction/rebuild
job to clean up soft-deleted entries and rebalance the index structure without blocking live traffic.

**91. Caching layers in a RAG pipeline, and what invalidates each.**
Query-embedding cache (keyed by raw query text; invalidate only if the embedding model changes); retrieval
-result cache (keyed by query text + filters; invalidate when the underlying documents matching that query
change, which requires tracking which cached queries could be affected by a given document update — often
approximated with a short TTL instead of precise invalidation); LLM-response cache (keyed by the full
assembled prompt including retrieved context; invalidate whenever anything upstream — query, retrieval
result, or prompt template — changes).

**92. Handling embedding API rate limits and cost for every query and ingested document.**
Batch embedding calls wherever possible (most APIs charge and rate-limit per request, not strictly per
token, so batching many texts into one call reduces overhead), cache query embeddings for repeated queries
(Q91), and for ingestion specifically, process documents through a queue with backoff/retry rather than
firing all requests immediately — smoothing burst ingestion load against a fixed rate limit instead of
hitting it head-on.

**93. Rollback plan if a newly deployed embedding model degrades retrieval quality.**
This is only fast if you kept the old index alive during cutover (Q48/Q87) — rollback becomes "route
traffic back to the old index," a config change, not a rebuild. This is the core argument for always doing
blue-green index cutovers rather than in-place index migrations: the rollback path needs to already exist
before you need it, not be built under incident pressure.

**94. Securing against indirect prompt injection via ingested/retrieved content.**
Treat all retrieved document content as untrusted data, not instructions — use prompt structuring (clear
delimiters, system-prompt instructions that explicitly tell the model retrieved content is data to reference,
not commands to follow) and, for higher-stakes systems, a separate classifier pass over ingested documents
to flag content containing suspicious instruction-like patterns before it ever enters the index. This
mirrors the same tool-argument-validation discipline from
[Chapter 0's guardrails](../00-agentic-concepts.md#guardrails-and-control) — retrieved context is an input
boundary just like a tool call's arguments.

**95. Batch vs. streaming ingestion — how it affects index choice.**
Batch ingestion (nightly reindex from a full corpus snapshot) tolerates index types that are expensive to
update incrementally (e.g., IVF, which needs re-clustering as data grows) since you're rebuilding from
scratch on a schedule anyway. Streaming/near-real-time ingestion requires an index that supports cheap
incremental upserts without a full rebuild — favoring HNSW or similar graph-based structures — since
documents must become searchable within seconds to minutes of being created, not hours.

## Advanced / Research & Emerging Topics

**96. GraphRAG — how does a knowledge graph change retrieval vs. flat chunk-based RAG?**
Instead of retrieving isolated text chunks by similarity, GraphRAG extracts entities and relationships from
the corpus into a knowledge graph, then retrieval can traverse relationships explicitly ("find all events
connected to entity X within two hops") — enabling multi-hop and aggregation queries ("summarize everything
related to project Y across all documents") that flat chunk retrieval struggles with, since flat retrieval
has no notion of entity identity or relationship structure connecting otherwise-unrelated chunks.

**97. Is RAG becoming obsolete as context windows reach millions of tokens?**
Long-context "put everything in the prompt" avoids retrieval failure modes entirely (no wrong chunk
selected) but doesn't eliminate the "lost in the middle" problem (Q58), and it's dramatically more
expensive and slower per query — re-processing millions of tokens on every request, even with prompt
caching, versus retrieving only the relevant few thousand. In practice the two are complementary rather
than RAG being replaced: long context reduces how *aggressively* you need to chunk/filter, while retrieval
remains the cost-and-precision-efficient default for corpora too large to fit in context at all (or where
per-query cost matters).

**98. Agentic RAG vs. single-shot retrieve-then-generate — architectural difference.**
Single-shot RAG performs one retrieval pass, assembles context, and generates — no feedback loop. Agentic
RAG wraps retrieval as a tool call inside an agent loop (the same perceive→reason→act→observe loop from
[Chapter 0](../00-agentic-concepts.md)): the model can evaluate whether its current context is sufficient,
issue a follow-up or reformulated query if not, retrieve again, and repeat until it decides it has enough
to answer — directly solving the multi-hop problem from Q67 at the cost of more LLM calls and latency per
request.

**99. Self-RAG / corrective RAG — critiquing and re-retrieving.**
The model (or a dedicated critic step) evaluates whether the retrieved context actually supports answering
the query — checking relevance and sufficiency explicitly, often via special reflection tokens or a
structured self-critique prompt — and triggers a re-retrieval (e.g., a reformulated query, or falling back
to a web search) if the context is judged inadequate, rather than generating an answer from insufficient
context regardless. This directly targets the failure mode from Q77 (confident answers from irrelevant
context) by making insufficiency detection an explicit step rather than hoping the model self-polices.

**100. Fine-tuning the LLM on retrieved-context format vs. prompt engineering — reliability and cost.**
Prompt engineering (instructing the model how to use retrieved context via the system prompt) is fast to
iterate and works across model updates without retraining, but relies on the base model's general
instruction-following holding up consistently for your exact context format. Fine-tuning the LLM
specifically on your retrieval format (e.g., training it to reliably cite sources, decline when context is
insufficient, or handle your specific document structure) can meaningfully improve consistency and reduce
prompt-engineering brittleness, but adds real maintenance cost: every base-model upgrade potentially
requires re-fine-tuning, and you lose the ability to freely swap in a newer off-the-shelf model without
redoing that investment.

**101. Late chunking — how does embedding a full document before splitting change what a chunk vector
captures, and where does the technique break down?**
Every strategy in Q57 and Q61 embeds *after* splitting: each chunk is a separate, independent forward pass
through the embedding model with zero visibility into the rest of the document — exactly the blind spot
contextual retrieval (Q61) patches by manually prepending an LLM-written summary before embedding. Late
chunking inverts the order instead of patching around it: run the *entire* document through a long-context
embedding model's token encoder in one pass, producing one contextualized token embedding per token (each
one shaped by self-attention over the whole document), and only *then* apply chunk boundaries by
mean-pooling the relevant span of token embeddings into each chunk's final vector.

```python
def late_chunk(text: str, chunk_token_spans: list[tuple[int, int]], embed_tokens_fn) -> list[list[float]]:
    token_embeddings = embed_tokens_fn(text)  # one forward pass over the whole document
    return [
        token_embeddings[start:end].mean(axis=0)
        for start, end in chunk_token_spans  # boundaries still chosen by any splitter, e.g. Q57
    ]
```

Because pooling happens *after* a full-document attention pass, chunk *N*'s vector already reflects
terminology and pronouns resolved elsewhere in the document (what "it" or "the company" refers to)
without an LLM ever writing an explicit summary — cheaper per document than contextual retrieval (one
embedding pass vs. one LLM call per chunk) once a suitable model is available. It breaks down in two
concrete ways: the whole document must fit inside the embedding model's context window in a single pass,
which bounds the technique to documents at or under that limit (an LLM's summary in Q61 has no such
ceiling); and it requires an embedding model that exposes *per-token* output before pooling — most hosted
embedding APIs return only a single already-pooled vector per input, so late chunking is currently mostly
a self-hosted/open-weight-model technique, not something you can bolt onto an arbitrary embedding API.

See [Chunking Strategies, In Depth](Chunking_Strategies_In_Depth.md) for this and every other chunking
strategy referenced across this section, with full code for each.

Next: back to the [RAG Knowledge Base overview](index.md), or
[Vector Search: Tools and Technology](07_Vector_Search_Tools_and_Technology.md) for the concrete tooling
landscape these answers reference.

# Qdrant Basics

Qdrant is a dedicated vector database: unlike FAISS (an in-process library), it runs as its own server
with a REST API (port 6333) and a gRPC API (port 6334), and it persists data to disk itself.

Core concepts:

- **Collection** — the equivalent of a table. Created once with a fixed vector dimension and distance
  metric (cosine, dot product, or Euclidean).
- **Point** — one record: an id (integer or UUID), a vector, and a JSON **payload** (arbitrary metadata —
  source, chunk index, original text, tags, timestamps, ...). The payload is stored natively alongside
  the vector, so a search result already includes it — no separate lookup table needed.
- **Upsert** — the write operation for points. If the id already exists, its vector and payload are
  replaced in place; if not, a new point is created. This gives Qdrant a true update-by-id, unlike FAISS
  which has no in-place update and needs a remove-then-add.
- **Filter** — a structured query (e.g. `source = "chapter_2.md"`) that can be combined with vector
  search, so you can search "only within these documents" instead of filtering client-side after the
  fact.
- **HNSW index** — Qdrant builds an HNSW graph per collection by default for fast approximate search;
  this is configurable per collection (`hnsw_config`) alongside quantization for memory reduction.

A local Qdrant instance, via Docker, exposes a web dashboard at `http://localhost:6333/dashboard` for
browsing collections and points interactively.

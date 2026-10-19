# Vector Database Lifecycle

Regardless of which vector database you use (FAISS, pgvector, Pinecone, Qdrant, Weaviate...), the
operations you perform against it fall into the same lifecycle:

1. **Create** — initialize an empty index with a fixed vector dimension and a distance metric (cosine,
   dot product, or Euclidean).
2. **Insert** — embed content with a model, then add `(vector, id, payload)` to the index. The payload
   (original text + metadata) is what you get back on a search hit; the vector alone cannot be turned
   back into text.
3. **Read** — either fetch a known record by id, or run a similarity search: embed a query, ask the
   index for the nearest K vectors, and get back their ids, scores, and payloads.
4. **Update** — change a record's content. Most ANN indexes (including FAISS) have no true in-place
   vector update; the common pattern is delete the old vector by id, then insert the new one under the
   same id.
5. **Delete** — remove a record by id so it no longer appears in the index or in future searches.
6. **Persist** — serialize the index (and, for libraries like FAISS that don't store payloads
   themselves, the id-to-payload sidecar) to disk or a durable store.
7. **Load** — deserialize a previously persisted index back into memory, ready to search again.

A managed vector DB (Pinecone, Qdrant, Weaviate, pgvector-in-Postgres) does steps 6-7 for you
automatically and stores the payload alongside the vector natively. FAISS is a library, so this project's
`store.py` implements all seven steps explicitly, plus a separate JSON payload store.

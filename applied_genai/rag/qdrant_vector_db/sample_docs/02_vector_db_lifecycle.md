# Vector Database Lifecycle

Regardless of which vector database you use (FAISS, pgvector, Qdrant, Pinecone, Weaviate...), the
operations you perform against it fall into the same lifecycle:

1. **Create** — initialize a collection/index/table with a fixed vector dimension and a distance metric.
2. **Insert** — embed content with a model, then add `(vector, id, payload)`. The payload (original text
   + metadata) is what you get back on a search hit; the vector alone cannot be turned back into text.
3. **Read** — either fetch a known record by id, or run a similarity search: embed a query, ask the
   index for the nearest K vectors, and get back their ids, scores, and payloads.
4. **Update** — change a record's content. How this works depends on the backend: FAISS has no in-place
   vector update (delete-then-insert under the same id); Qdrant and pgvector both support a true
   upsert-by-id that replaces the vector and payload in one call.
5. **Delete** — remove a record by id, or by a filter/`WHERE` clause over its metadata, so it no longer
   appears in the index or in future searches.
6. **Persist / Load** — for an in-process library like FAISS, this is an explicit step (`write_index` /
   `read_index`). For a client-server database like Qdrant or pgvector, every write is already durable
   the moment it succeeds — there's nothing extra to do.

Comparing this project's `store.py` to `../faiss_vector_db/store.py` and `../rag_pgvector_local/db.py` is
a good way to see the same seven-stage lifecycle implemented three different ways.

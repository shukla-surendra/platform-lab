# Payload Filtering

A payload filter narrows a vector search to points matching a metadata condition, evaluated alongside
(not after) the nearest-neighbor search. For example, restricting results to chunks from one source file:

    Filter(must=[FieldCondition(key="source", match=MatchValue(value="chapter_2.md"))])

This is more efficient than searching the whole collection and discarding non-matching results
client-side, and it composes with `must`, `should`, and `must_not` clauses for AND/OR/NOT logic across
multiple fields (source, tags, date ranges, numeric thresholds, and so on).

The same idea exists in pgvector as a plain SQL `WHERE` clause combined with `ORDER BY embedding <=>
query`, and in FAISS only as a client-side post-filter (or an `IDSelector` restricting which ids the
search considers) — Qdrant and pgvector both push the filter down into the search itself.

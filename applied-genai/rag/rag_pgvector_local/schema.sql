-- Runs automatically on first container start (mounted into
-- /docker-entrypoint-initdb.d/ by docker-compose.yml). To apply changes to
-- an already-initialized database, run this file manually instead:
--   docker compose exec -T pgvector psql -U rag -d rag < schema.sql

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1024) NOT NULL,
    UNIQUE (source, chunk_index)
);

-- HNSW index for cosine-similarity search (embeddings are stored normalized,
-- see embeddings.py). See docs/RAG_Knowledge_Base_Starter/05_HNSW.md in the
-- repo root for how this index works.
CREATE INDEX IF NOT EXISTS documents_embedding_hnsw_idx
    ON documents USING hnsw (embedding vector_cosine_ops);

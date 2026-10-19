# Azure AI Search: Index, Indexer, and Skillset

Purpose: Microsoft's fully managed cloud search service (formerly
"Azure Cognitive Search"). Does classic keyword/full-text search
(BM25) and vector/hybrid search, over data you point it at — and,
unlike a bare vector DB, can also run the ingestion pipeline for you.

## Chapters

| # | Chapter | You'll learn |
|---|---------|---------------|
| 1 | [Setup: Indexing PDFs from Blob Storage](01_setup_pdf_index_from_blob_storage.md) | Data Source → Index → Skillset → Indexer, in order, with JSON and Python SDK for each, run/monitor, and query |

## The gap it fills, relative to a bare vector DB

A vector DB (Qdrant, pgvector, FAISS —
[`RAG_Knowledge_Base_Starter/04_Vector_Databases.md`](../RAG_Knowledge_Base_Starter/04_Vector_Databases.md))
stores and searches vectors. Someone still has to build the pipeline in
front of it: pull data from the source, chunk it, embed it, upsert it,
and re-run all of that when the source changes. In this repo, that
pipeline is your own code — `rag_pgvector_local/ingest.py` +
`chunking.py` + `embeddings.py` + `search.py`.

Azure AI Search moves that pipeline into the service itself and
expresses it as three declarative resources (plus the Data Source
connection each of them assumes):

| Resource | Role | Repo equivalent |
|---|---|---|
| **Index** | Schema — fields, types, which are searchable/filterable/vector-searchable. What queries actually run against. | `qdrant_vector_db/store.py` collection def, `rag_pgvector_local/schema.sql` |
| **Indexer** | Scheduled/triggered pull job: reads from a data source, maps fields, writes documents into the Index. | `ingest.py` in each vector-DB folder |
| **Skillset** | Optional AI-enrichment pipeline attached to an indexer: OCR, entity/key-phrase extraction, embedding generation, run per document before it lands in the Index. | `chunking.py` + `embeddings.py` combined, plus OCR/NER this repo doesn't currently do |

## Why skillset exists

An indexer alone just copies fields verbatim from source to Index. If
the source data isn't already what you want indexed, the indexer has
nothing useful to write. Concretely:

- **Scanned PDFs / images in Blob Storage** — no extractable text at
  all without OCR first.
- **Long documents** — too big for one vector field; need chunking
  before embedding, and no embeddings exist yet at ingestion time.
- **Need entity/PII/key-phrase metadata for filtering** — not present
  in the raw source.

A skillset is a chain of "skills" that runs per document, inside the
same indexer job, so you don't stand up separate OCR/embedding
services and glue them together by hand — Azure runs the chain and
writes the results straight into the Index's fields.

## Data flow

```
Data Source (Blob container)
      │
      ▼
   Indexer  ── pulls documents, cracks each PDF (extracts text + metadata)
      │
      ▼
  Skillset (optional)
      [scanned pages only] OCR → split into chunks → call embedding model
      │
      ▼
   Indexer maps enriched output → Index fields
      │
      ▼
     Index — queryable: keyword, vector, hybrid, semantic rerank
```

Order matters because the Indexer references the other three by name —
**Data Source, Index, and Skillset must all exist before you create the
Indexer.** Chapter 1 walks through creating them in that order.

## Production notes

- **Incremental indexing**: indexers detect changed documents (Blob's
  `LastModified`, a SQL `rowversion` column) and only re-run the
  skillset on those — without this, every run would re-embed the whole
  corpus and burn embedding-model tokens for nothing.
- **Enrichment cache**: skill output is cached per document. Changing
  the Index schema alone doesn't force skills to re-run if the source
  document itself is unchanged.
- **Cost/latency**: skills run per document, so an indexer over
  millions of scanned PDFs with an OCR skill can be slow and
  expensive — `parallelIndexing`, batching, and a coarser
  `textSplitMode` matter here the same way batch size matters in this
  repo's own embedding scripts.
- **FAISS has no equivalent** — it's a library, not a service, so
  there's no "data source" concept at all; you always write the
  ingestion code (`faiss_vector_db/ingest.py`).

## How this relates to the rest of this repo

- [`RAG_Knowledge_Base_Starter/`](../RAG_Knowledge_Base_Starter/index.md)
  covers the vendor-neutral RAG concepts (embeddings, chunking, HNSW,
  vector databases) this doc assumes.
- `rag_pgvector_local/`, `qdrant_vector_db/`, `faiss_vector_db/` are the
  hand-rolled versions of the same ingest → chunk → embed → store →
  query pipeline Azure AI Search runs as a managed service.

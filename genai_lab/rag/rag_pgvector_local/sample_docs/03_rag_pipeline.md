# RAG Pipeline

Retrieval-Augmented Generation grounds an LLM's answer in retrieved documents instead of relying only on
what the model memorized during training, which reduces hallucination and lets the model answer questions
about content it was never trained on.

The pipeline has two phases. Ingestion: documents are split into chunks, each chunk is embedded into a
vector, and the vector plus the original text is stored in a vector database. Query time: the user's
question is embedded with the same model, the vector database returns the top-K most similar chunks, and
those chunks are inserted into the LLM's prompt as context before it generates an answer.

This project implements exactly that pipeline: `ingest.py` handles the ingestion phase against a pgvector
table running in Docker, and `rag.py` handles the query-time phase, calling a local Ollama model for
generation so the whole system runs without any external API calls.

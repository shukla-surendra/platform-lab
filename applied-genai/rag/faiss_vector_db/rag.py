#!/usr/bin/env python3
"""End-to-end local RAG: retrieve top-K chunks from FAISS, generate an answer with Ollama.

Mirrors ../rag_pgvector_local/rag.py but backed by the local FaissVectorStore instead of pgvector.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

import config
from search import search


def build_prompt(question: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
        f"[Source: {chunk['source']}#{chunk['chunk_index']}]\n{chunk['text']}" for chunk in chunks
    )
    return (
        "Answer the question using only the context below. "
        "If the context does not contain the answer, say you don't know — do not guess.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"
    )


def call_ollama(prompt: str) -> str:
    payload = {"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False}
    request = urllib.request.Request(
        config.OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach Ollama at {config.OLLAMA_URL}. Make sure `ollama serve` is running."
        ) from exc
    return str(body.get("response", "")).strip()


def answer(question: str) -> str:
    try:
        chunks = search(question)
    except FileNotFoundError:
        return "No documents indexed yet. Run `python ingest.py` first."
    if not chunks:
        return "No documents indexed yet. Run `python ingest.py` first."

    prompt = build_prompt(question, chunks)
    response = call_ollama(prompt)

    sources = ", ".join(f"{c['source']}#{c['chunk_index']}" for c in chunks)
    return f"{response}\n\n(Sources: {sources})"


def main() -> int:
    question = " ".join(sys.argv[1:]).strip() or "What is a vector database?"
    try:
        print(answer(question))
    except RuntimeError as exc:
        print(exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

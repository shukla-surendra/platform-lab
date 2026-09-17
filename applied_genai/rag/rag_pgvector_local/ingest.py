#!/usr/bin/env python3
"""Chunk, embed, and load local .md/.txt documents into the pgvector table.

Usage:
  python ingest.py                # ingests ./sample_docs
  python ingest.py path/to/folder # ingests any folder of .md/.txt files
  python ingest.py ../docs        # e.g. ingest this repo's own tutorial chapters
"""

from __future__ import annotations

import sys
from pathlib import Path

import config
from chunking import chunk_text
from db import get_connection
from embeddings import embed

SUPPORTED_SUFFIXES = {".md", ".txt"}


def load_documents(folder: Path) -> list[tuple[str, str]]:
    documents = []
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            documents.append((str(path.relative_to(folder)), path.read_text(encoding="utf-8")))
    return documents


def ingest(folder: Path) -> None:
    documents = load_documents(folder)
    if not documents:
        print(f"No .md/.txt files found under {folder}")
        return

    conn = get_connection()
    cur = conn.cursor()

    total_chunks = 0
    for source, text in documents:
        chunks = chunk_text(text, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
        if not chunks:
            continue

        vectors = embed(chunks)
        cur.execute("DELETE FROM documents WHERE source = %s", (source,))
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            cur.execute(
                """
                INSERT INTO documents (source, chunk_index, content, embedding)
                VALUES (%s, %s, %s, %s)
                """,
                (source, idx, chunk, vector),
            )
        total_chunks += len(chunks)
        print(f"Ingested {source}: {len(chunks)} chunks")

    conn.commit()
    cur.close()
    conn.close()
    print(f"Done. {len(documents)} documents, {total_chunks} chunks.")


def main() -> int:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("sample_docs")
    if not folder.exists():
        print(f"Folder not found: {folder}")
        return 1
    ingest(folder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

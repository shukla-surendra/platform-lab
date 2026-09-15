#!/usr/bin/env python3
"""Build data/profiles/books/{train,test}.txt from tools/corpus-extractor's book JSONL
(~/Downloads/books) alone — no chat data. Mirrors gpt.data.prepare.build_corpus()'s own
extra_documents handling (seed-42 shuffle, 90/10 split, DOCUMENT_SEPARATOR join) so the
result follows the same "<|endoftext|>" hard-boundary convention as this project's
documented mixed corpus (see DATASET.md), just applied to books only, and without the
mixed pipeline's requirement of >=10 downloaded chat conversations.

    uv run python scripts/build_books_profile.py
"""

import random
from pathlib import Path

from gpt.data.prepare import DOCUMENT_SEPARATOR, load_extra_documents

JSONL = Path("data/books_staging/dataset.jsonl")
OUT_DIR = Path("data/profiles/books")
TRAIN_RATIO = 0.9
SEED = 42


def main():
    docs = load_extra_documents(JSONL)
    print(f"[info] loaded {len(docs):,} book chunks from {JSONL}")

    random.seed(SEED)
    random.shuffle(docs)
    split = int(len(docs) * TRAIN_RATIO)
    train_docs, test_docs = docs[:split], docs[split:]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "train.txt").write_text(
        DOCUMENT_SEPARATOR.join(train_docs) + "\n", encoding="utf-8"
    )
    (OUT_DIR / "test.txt").write_text(
        DOCUMENT_SEPARATOR.join(test_docs) + "\n", encoding="utf-8"
    )

    print(f"train: {len(train_docs):,} chunks -> {OUT_DIR / 'train.txt'}")
    print(f"test:  {len(test_docs):,} chunks -> {OUT_DIR / 'test.txt'}")


if __name__ == "__main__":
    main()

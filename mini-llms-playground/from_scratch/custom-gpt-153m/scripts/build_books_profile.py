#!/usr/bin/env python3
"""Build data/train.txt + data/test.txt from tools/corpus-extractor's book JSONL
(~/Downloads/books) alone — no chat data. Mirrors gpt.data.prepare.build_corpus()'s own
extra_documents handling (seed-42 shuffle, 90/10 split, DOCUMENT_SEPARATOR join) so the
result matches what `gpt-data --extra-jsonl <path>` would have produced with zero chat
conversations, without that path's >=10-conversation requirement.

Uses this project's own DOCUMENT_SEPARATOR ("\\n\\n" — see prepare.py's module
docstring for why this project reverted away from custom-gpt-50m's "<|endoftext|>"
convention), so the same book chunks as the sibling custom-gpt-50m run stay
byte-comparable in content but correctly follow this project's own boundary format.

    uv run python scripts/build_books_profile.py
"""

import random
from pathlib import Path

from gpt.data.prepare import DOCUMENT_SEPARATOR, load_extra_documents

JSONL = Path("data/books_staging/dataset.jsonl")
TRAIN_RATIO = 0.9
SEED = 42


def main():
    docs = load_extra_documents(JSONL)
    print(f"[info] loaded {len(docs):,} book chunks from {JSONL}")

    random.seed(SEED)
    random.shuffle(docs)
    split = int(len(docs) * TRAIN_RATIO)
    train_docs, test_docs = docs[:split], docs[split:]

    Path("data/train.txt").write_text(
        DOCUMENT_SEPARATOR.join(train_docs) + "\n", encoding="utf-8"
    )
    Path("data/test.txt").write_text(
        DOCUMENT_SEPARATOR.join(test_docs) + "\n", encoding="utf-8"
    )

    print(f"train: {len(train_docs):,} chunks -> data/train.txt")
    print(f"test:  {len(test_docs):,} chunks -> data/test.txt")


if __name__ == "__main__":
    main()

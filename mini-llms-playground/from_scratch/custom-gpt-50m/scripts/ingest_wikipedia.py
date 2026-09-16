#!/usr/bin/env python3
"""Build data/wikipedia_staging/dataset.jsonl from Simple English Wikipedia — factual
grounding data, mergeable into the training corpus through the same `--extra-jsonl` path
`gpt-data` already uses for books/repos (gpt.data.prepare.load_extra_documents(), one
{"text": ...} record per line — see docs/BOOKS_CORPUS_INTEGRATION.md).

Why Simple English Wikipedia specifically: this project's own QA reports
(reports/qa_report_50m_step*.html) show the model rambling into narrative/story-shaped
text instead of answering factual questions — expected, given the live corpus is
books (fiction-leaning prose) + chat data, with nothing genuinely encyclopedic. Simple
Wikipedia (not full English Wikipedia) is deliberately chosen: plainer sentence
structure closer to what a 50M-param model can actually learn from, at a size
(~240k articles) that does not swamp the existing corpus the way full Wikipedia would.

Same chunking convention as tools/corpus-extractor's book extraction: GPT-2 BPE
(tiktoken), 1024-token windows (matching this project's context_length=1024) with a
100-token overlap between consecutive windows of the same article, so no fact sits
right at a hard chunk boundary in every occurrence. Whole articles under 200 characters
(stubs/disambiguation pages) are dropped before chunking; a final trailing window under
64 tokens is dropped rather than kept as a near-empty scrap.

    uv run python scripts/ingest_wikipedia.py
    uv run python scripts/ingest_wikipedia.py --limit 2000   # quick smoke test
"""

import argparse
import json
import time
from pathlib import Path

import tiktoken
from datasets import load_dataset

from gpt.data.prepare import clean_text

HF_DATASET = "wikimedia/wikipedia"
HF_CONFIG = "20231101.simple"
OUT_DIR = Path("data/wikipedia_staging")
CHUNK_TOKENS = 1024
OVERLAP_TOKENS = 100
MIN_ARTICLE_CHARS = 200
MIN_TRAILING_CHUNK_TOKENS = 64


def chunk_article(tokenizer, title, body):
    text = f"Title: {title}\n\n{body}"
    ids = tokenizer.encode(text, disallowed_special=())
    stride = CHUNK_TOKENS - OVERLAP_TOKENS
    chunks = []
    for start in range(0, len(ids), stride):
        window = ids[start:start + CHUNK_TOKENS]
        if len(window) < MIN_TRAILING_CHUNK_TOKENS:
            break
        chunks.append(tokenizer.decode(window))
        if start + CHUNK_TOKENS >= len(ids):
            break
    return chunks


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--limit", type=int, default=None,
                    help="Stop after this many source articles (smoke-testing)")
    p.add_argument("--out", default=None, help="Output JSONL path (default: "
                    f"{OUT_DIR / 'dataset.jsonl'})")
    args = p.parse_args()

    out_path = Path(args.out) if args.out else OUT_DIR / "dataset.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tokenizer = tiktoken.get_encoding("gpt2")
    print(f"Streaming {HF_DATASET} ({HF_CONFIG})...")
    ds = load_dataset(HF_DATASET, HF_CONFIG, split="train", streaming=True)

    t0 = time.time()
    articles_seen = 0
    articles_kept = 0
    stubs_dropped = 0
    chunks_written = 0
    tokens_written = 0

    with open(out_path, "w", encoding="utf-8") as f:
        for row in ds:
            articles_seen += 1
            if args.limit and articles_seen > args.limit:
                break

            title = clean_text(row.get("title", ""))
            body = clean_text(row.get("text", ""))
            if len(body) < MIN_ARTICLE_CHARS:
                stubs_dropped += 1
                continue
            articles_kept += 1

            for chunk_text in chunk_article(tokenizer, title, body):
                f.write(json.dumps({"text": chunk_text}) + "\n")
                chunks_written += 1
                tokens_written += len(tokenizer.encode(chunk_text, disallowed_special=()))

            if articles_seen % 5000 == 0:
                elapsed = time.time() - t0
                print(f"\r  articles: {articles_seen:,} scanned, {articles_kept:,} kept, "
                      f"{stubs_dropped:,} stubs dropped | chunks: {chunks_written:,} | "
                      f"~{tokens_written:,} tokens | {elapsed:.0f}s", end="", flush=True)

    print()
    print("=== Simple English Wikipedia ingestion complete ===")
    print(f"  articles scanned: {articles_seen:,}")
    print(f"  articles kept:    {articles_kept:,}")
    print(f"  stubs dropped:    {stubs_dropped:,} (<{MIN_ARTICLE_CHARS} chars)")
    print(f"  chunks written:   {chunks_written:,}")
    print(f"  tokens written:   {tokens_written:,}")
    print(f"  output: {out_path}")


if __name__ == "__main__":
    main()

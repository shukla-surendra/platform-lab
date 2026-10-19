# Chunking Strategies, In Depth

Chunking is the step before embedding: splitting a source document into smaller pieces so each piece can
get its own vector. It happens once, at ingestion time, but every downstream retrieval and generation
result depends on it — a chunk that splits a fact from the sentence explaining it, or that merges three
unrelated topics into one embedding, cannot be fixed later by a better vector database, a better ANN
index, or a better LLM. See [Interview Questions Q56](08_Interview_Questions.md#rag-architecture--chunking)
for why this makes chunking the single highest-leverage tuning knob in most RAG pipelines.

## The core tension

- **Chunks too large** → the embedding blends multiple topics into one vector, diluting the similarity
  signal for any single one of them; more irrelevant text rides along into the LLM's context window per
  retrieved chunk, and per-chunk relevance becomes harder to rank.
- **Chunks too small** → a chunk loses the surrounding context needed to make sense on its own (a
  paragraph ending in "...which increased it by 12%" means nothing once separated from what "it" refers
  to), and the corpus fragments into far more chunks, multiplying embedding cost, storage, and the number
  of near-duplicate results competing for the same top-K slots.

There is no universal correct chunk size — the right answer depends on document structure, query style,
and the embedding model's own behavior (see "Choosing a chunk size" below), which is why chunking is
better treated as a per-corpus tuning problem than a single fixed constant to copy from a tutorial.

## Strategy catalog

### 1. Fixed-size chunking (word/character count)

Split every document into equal-sized pieces on a raw count, with some overlap between consecutive
chunks so a fact near a boundary isn't lost from both sides:

```python
def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    words = text.split()
    step = max(chunk_size - overlap, 1)
    chunks, start = [], 0
    while start < len(words):
        chunks.append(" ".join(words[start : start + chunk_size]))
        if start + chunk_size >= len(words):
            break
        start += step
    return chunks
```

Simplest to implement, fully predictable output size, and easy to reason about — the default used by
`chunking.py` in this repo's `rag_pgvector_local`, `faiss_vector_db`, and `qdrant_vector_db` projects.
Its weakness is that it has no idea where sentences, paragraphs, or ideas actually begin and end, so it
will happily cut a sentence, a table row, or a code block in half.

### 2. Token-aware chunking

Word count and character count are both proxies for what actually matters: how many *tokens* the chunk
will consume in the embedding model's input and the LLM's context window. Word count under-counts for
languages/text with long words or dense punctuation, and over-counts for others — a chunk sized in words
can silently blow past an embedding model's token limit (commonly 512 tokens) and get truncated with no
warning. Sizing chunks by actual tokenizer output avoids this:

```python
import tiktoken

encoding = tiktoken.get_encoding("cl100k_base")

def chunk_by_tokens(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    tokens = encoding.encode(text)
    step = max(max_tokens - overlap_tokens, 1)
    chunks = []
    for start in range(0, len(tokens), step):
        chunk_tokens = tokens[start : start + max_tokens]
        chunks.append(encoding.decode(chunk_tokens))
        if start + max_tokens >= len(tokens):
            break
    return chunks
```

Use the *target embedding model's own tokenizer* where possible — `tiktoken` matches OpenAI models, but
an open-weight model (E5, BGE, Qwen) uses a different vocabulary, so its actual token count for the same
text can differ meaningfully from `tiktoken`'s count.

### 3. Recursive/structure-cascading splitting

Rather than one fixed unit, try a list of separators in priority order — paragraph breaks first, then
sentence breaks, then words, then raw characters — recursing into a still-too-large piece with the next,
finer separator until every chunk fits the target size:

```python
def recursive_split(text: str, max_size: int, separators=("\n\n", "\n", ". ", " ")) -> list[str]:
    if len(text) <= max_size or not separators:
        return [text]
    sep, rest = separators[0], separators[1:]
    parts = text.split(sep)
    chunks, current = [], ""
    for part in parts:
        candidate = current + sep + part if current else part
        if len(candidate) <= max_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = part if len(part) <= max_size else ""
            if not current:
                chunks.extend(recursive_split(part, max_size, rest))
        current = current or ""
    if current:
        chunks.append(current)
    return chunks
```

This is the approach behind LangChain's `RecursiveCharacterTextSplitter` and is a strong general-purpose
default: it prefers natural boundaries (paragraphs) but degrades gracefully to smaller units instead of
failing outright when a paragraph itself is longer than the target size.

### 4. Sentence-based chunking

Split strictly on sentence boundaries (via a sentence tokenizer, e.g. spaCy or NLTK, rather than naive
`.` splitting which breaks on abbreviations and decimals), then group consecutive sentences up to a
target size. Guarantees every chunk is grammatically whole, at the cost of uneven chunk sizes — a
document with mostly short sentences produces smaller chunks than one with long, complex sentences, for
the same target.

### 5. Semantic chunking

Embed individual sentences, then cut a new chunk boundary wherever similarity between consecutive
sentence embeddings drops below a threshold — the intuition being that a topic shift shows up as a drop
in embedding similarity between what came just before and just after it:

```python
def semantic_chunk(sentences, embed_fn, similarity_threshold=0.5):
    chunks, current = [], [sentences[0]]
    prev_emb = embed_fn(sentences[0])
    for sent in sentences[1:]:
        emb = embed_fn(sent)
        if cosine_sim(prev_emb, emb) < similarity_threshold:
            chunks.append(" ".join(current))
            current = []
        current.append(sent)
        prev_emb = emb
    chunks.append(" ".join(current))
    return chunks
```

Best chunk coherence of any text-only method — each chunk tends to correspond to one actual idea rather
than one fixed-size window — but costs one embedding call per sentence at ingestion time (far more calls
than fixed-size chunking) and the threshold itself needs tuning per corpus. Worth the cost on long,
topically heterogeneous documents (reports, meeting transcripts, books); overkill for already-short,
single-topic documents like FAQ entries.

### 6. Structure-aware chunking

Parse the document's actual structure — markdown headers, HTML tags, code fences, table boundaries — and
chunk along those boundaries instead of blind character/token counts, treating certain elements (a code
block, a table) as atomic and never splitting them even if they exceed the target size:

```python
import re

def chunk_by_markdown_headers(text: str) -> list[str]:
    sections = re.split(r"(?=^#{1,3} )", text, flags=re.MULTILINE)
    return [s.strip() for s in sections if s.strip()]
```

For PDFs specifically, this usually means a layout-detection pass (e.g. `unstructured`, a PDF-to-markdown
tool, or a vision-capable model reading page images) before chunking at all, since raw PDF text extraction
frequently loses table structure and reading order that naive fixed-size chunking would otherwise mangle
further. For tables, also consider emitting a plain-text or JSON summary alongside the raw table —
embedding models generally represent prose more faithfully than tabular grids.

### 7. Overlap tuning

Overlap — repeating some trailing text from chunk *N* at the start of chunk *N+1* — exists purely to stop
a boundary from silently cutting a fact in half. A common starting point is **10-20% of chunk size**: too
little overlap re-introduces the boundary-split problem overlap exists to solve; too much bloats the
index with near-duplicate content, wastes embedding/storage cost, and can cause the same fact to occupy
multiple top-K slots, crowding out genuinely different relevant chunks. Tune it empirically per corpus
(see "Choosing a chunk size" below) rather than copying a fixed percentage — the right value depends on
how often facts in your documents actually straddle wherever your splitter happens to cut.

### 8. Parent-document / hierarchical (small-to-big) retrieval

Decouple the unit used for matching from the unit returned to the LLM: embed and search over small,
precise chunks (a paragraph, a few sentences — better similarity signal, less topic dilution), but when a
small chunk is retrieved, return its larger parent section or whole source document as the actual context
handed to the LLM. This solves the problem that the chunk size best for *retrieval precision* is often
smaller than the chunk size the LLM actually needs to *answer well* — they are not the same size, and
forcing one size to serve both jobs is a compromise on at least one of them.

### 9. Contextual retrieval (context injection before embedding)

Before embedding a chunk, prepend a short, LLM-generated note describing what the whole document is
about and how this specific chunk fits into it, so the embedded text carries context the isolated chunk
would otherwise lose:

```
Original chunk: "Revenue increased by 12% in that period."
Contextualized: "This chunk is from Acme Corp's Q3 2025 earnings report, discussing quarterly
                 revenue. Revenue increased by 12% in that period."
```

This directly fixes the pronoun/reference-ambiguity failure mode ("that period," "it," "the company") that
plain isolated chunking produces, at the cost of one extra LLM call per chunk at ingestion time.

### 10. Late chunking

The techniques above all embed *after* splitting: each chunk is a separate, independent call into the
embedding model with zero visibility into the rest of the document — which is exactly the blind spot
contextual retrieval (above) patches by manually re-injecting a summary. Late chunking inverts the order:
run the *entire* document through a long-context embedding model's token encoder in one pass, producing
one contextualized token embedding per token — computed with self-attention over the whole document, so
every token's representation already reflects everything around it. Only after that single pass are chunk
boundaries applied, by mean-pooling the relevant span of token embeddings into each chunk's final vector:

```python
def late_chunk(text: str, chunk_token_spans: list[tuple[int, int]], embed_tokens_fn) -> list[list[float]]:
    token_embeddings = embed_tokens_fn(text)  # one forward pass over the whole document
    return [
        token_embeddings[start:end].mean(axis=0)
        for start, end in chunk_token_spans  # boundaries still chosen by any splitter above
    ]
```

Chunk *N*'s vector ends up implicitly aware of what chunks 1 and 9 said, without an LLM ever writing an
explicit summary — cheaper than contextual retrieval (one embedding pass instead of one LLM call per
chunk) once you already have a long-context embedding model. The catch is the whole document (or however
much of it you want reflected in the pooling) must fit in that model's context window in one pass, which
bounds the technique to documents within that limit, and only a subset of embedding models expose the
per-token output this requires — most hosted embedding APIs return only a single pooled vector, not
per-token ones.

### 11. LLM-proposed chunk boundaries

Ask an LLM to read the document and directly propose semantically coherent chunk boundaries (or a full
split), rather than deriving them from an embedding-similarity signal (semantic chunking) or fixed rules
(everything else in this list). Can outperform embedding-similarity-based semantic chunking on documents
with subtle structure an LLM can reason about explicitly but a similarity threshold can't (e.g., "this
paragraph is a caveat to the previous one, keep them together") — at meaningfully higher ingestion cost
and latency, and results depend on prompt quality the way any LLM-based pipeline step does.

## Choosing a chunk size: an eval-driven method

Treat chunk size (and overlap) as a hyperparameter to sweep, not a constant to guess:

1. Build a small labeled eval set of `(query, relevant_chunk_or_document)` pairs from your own corpus —
   synthetic-question generation from sampled chunks is a fast way to bootstrap this (see
   [Interview Questions Q74](08_Interview_Questions.md#rag-evaluation--failure-modes)).
2. Re-chunk and re-index the corpus at a handful of candidate sizes (e.g., 128/256/512/1024 tokens, with
   overlap fixed at ~15%).
3. Measure recall@k / NDCG (Q82) at each size against the eval set — not proxy metrics like index size or
   ingestion time.
4. Pick the size where retrieval quality plateaus, not necessarily the maximum tested size — quality
   commonly *degrades* past a corpus-specific optimum as topic dilution (too large) or context loss (too
   small) starts to dominate.
5. Re-run this sweep after any meaningful corpus composition change or embedding model swap — the
   optimum is a property of the corpus and model pairing, not a fixed constant that transfers between
   projects.

## Domain-specific starting points

| Corpus type | Suggested approach |
|---|---|
| FAQs / Q&A pairs | One chunk = one question+answer pair; don't fixed-size split across pairs |
| Prose reports / articles | Recursive splitting (paragraph → sentence) at ~256-512 tokens, ~15% overlap |
| Long, topically mixed documents (transcripts, books) | Semantic chunking, or structure-aware splitting on headers if present |
| Source code | Split on function/class boundaries (AST-aware), never mid-function |
| Markdown/HTML docs | Structure-aware splitting on headers/sections, treat code fences and tables as atomic |
| PDFs with tables/figures | Layout-aware extraction first, then structure-aware chunking; emit a text summary of tables alongside raw table content |
| Chat/support transcripts | Chunk per conversation turn or per resolved thread, not by raw character count |

## Common pitfalls

- **Copying a chunk size from a tutorial or another team's project** without re-validating it against
  your own corpus and query distribution — the optimum is corpus-specific (see above).
- **Sizing chunks in words/characters when the embedding model has a hard token limit** — a chunk that
  looks reasonably sized in words can silently truncate at the model's token boundary, discarding the
  tail of the chunk with no error raised.
- **One fixed strategy across a heterogeneous corpus** (Q65) — FAQs and 100-page PDFs need different
  chunking policies, not one global constant applied uniformly.
- **Ignoring overlap entirely** to save storage/embedding cost, then being surprised when facts near
  chunk boundaries never retrieve correctly.
- **Treating chunking as a one-time ingestion detail** instead of the first thing to revisit when
  retrieval quality regresses — a chunking change is often a higher-leverage fix than swapping the
  embedding model or adding a re-ranker.

## See also

- [RAG Architecture](06_RAG_Architecture.md) — where chunking sits in the end-to-end pipeline
- [Interview Questions Q56-70](08_Interview_Questions.md#rag-architecture--chunking) — the same
  strategies above as staff-level interview Q&A, plus late chunking as Q101 under
  [Advanced / Research & Emerging Topics](08_Interview_Questions.md#advanced--research--emerging-topics)
- `chunking.py` in `../../rag_pgvector_local`, `../../faiss_vector_db`, and `../../qdrant_vector_db` —
  this repo's own fixed-size, word-based implementation (strategy 1 above), used by all three vector DB
  projects

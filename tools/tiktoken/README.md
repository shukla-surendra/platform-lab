# tiktoken

**Category:** tokenization (LLM input/output preprocessing)

## What it is

LLMs don't operate on characters or words — they operate on a fixed vocabulary of integer
tokens, and every model is trained against one specific tokenization scheme. Without a way
to reproduce that exact scheme, you're stuck guessing: "roughly 4 characters per token" is
the common rule of thumb, but it's an estimate, and estimates aren't good enough when you're
budgeting a hard context-window limit, chunking documents for RAG so each chunk fits a
target token count, or estimating API cost before a call goes out — all of these need the
*exact* count the model will actually see and be billed on.

tiktoken is OpenAI's own tokenizer library (core written in Rust, wrapped for Python) that
reproduces that exact scheme. It implements byte-pair encoding (BPE): the vocabulary — a
fixed table mapping token strings to integer IDs — was built once, offline, by repeatedly
merging the most frequent adjacent symbol pair in a huge training corpus into a new symbol,
and recording each merge. tiktoken doesn't learn anything at runtime; calling `.encode()`
just replays that fixed, precomputed merge table against new text. That's why it's
deterministic and fast, and why it exactly matches what the model was trained on.

## What it's used for

- Counting tokens before a call, to stay under a model's context window or to estimate cost
  (OpenAI bills per token, not per character or word).
- Chunking long documents for RAG so each chunk fits a target token budget instead of an
  approximate character budget.
- Inspecting how a prompt actually gets split — useful for debugging prompt-engineering
  issues that trace back to unexpected token boundaries (e.g. a rare word splitting into
  many subword tokens and eating more budget than expected).

## Alternatives / related

- Every model family has its own tokenizer trained on its own vocabulary — tiktoken is
  **OpenAI-specific**. Anthropic/Claude models use a different vocabulary; a tiktoken count
  is not a Claude token count and the two aren't interchangeable for budgeting or billing
  math on Claude calls.
- Hugging Face's `tokenizers` library is the general-purpose equivalent for open models
  (BERT, Llama, etc.) — same BPE/WordPiece/SentencePiece family of ideas, different
  vocabularies per model.

## Usage

Encodings map to specific OpenAI model families:

| Encoding | Models |
|---|---|
| `o200k_base` | GPT-4o and newer |
| `cl100k_base` | GPT-3.5-turbo, GPT-4 (pre-4o) |
| `p50k_base` | older GPT-3 (`text-davinci-003`, Codex) |
| `r50k_base` / `gpt2` | original GPT-2/GPT-3 |

```python
import tiktoken

enc = tiktoken.encoding_for_model("gpt-4o")   # or tiktoken.get_encoding("o200k_base")

tokens = enc.encode("Tokenization is fun!")
print(tokens)          # e.g. [3404, 2065, 374, 2523, 0]
print(len(tokens))     # exact token count — what you'd actually be billed for

print(enc.decode(tokens))              # "Tokenization is fun!" — round-trips exactly
for t in tokens:
    print(t, repr(enc.decode([t])))    # inspect each token's text
```

Gotchas worth knowing when reading token output:
- Token boundaries don't follow word boundaries — a leading space is usually fused into the
  next token (`" is"` is one token, not `" "` + `"is"` as two).
- Non-English text tokenizes less efficiently (more tokens per character than English),
  especially for languages without spaces or with heavy Unicode use — this has real cost
  and context-budget implications for non-English prompts/documents.

### More examples: counting chat tokens, truncation, batch encoding

Real usage is rarely "encode one string" — the questions that actually come up are "how
many tokens will this whole chat request cost," "how do I cut this text down to exactly N
tokens," and "how do I do this for a thousand documents without it being slow." Full,
runnable recipes for all three: `examples/counting-and-truncation.py`.

The chat-counting one matters most in practice: a chat request's token cost isn't just the
sum of `len(encoding.encode(text))` over each message — OpenAI's API adds a small fixed
overhead per message (for role/name formatting) and per reply, so summing raw text tokens
alone under-counts and is the most common reason people hit a context-window error despite
their own math checking out.

## FAQ

**Install?**
`pip install tiktoken`. No API key or network call needed to tokenize — it's a local,
offline library. (First use of a given encoding *may* download its merge-table file if it
isn't already cached locally — see the offline/proxy question below.)

**`encoding_for_model("some-new-model")` raises a `KeyError` — why?**
`encoding_for_model` looks the model name up in a hardcoded map from model name → encoding.
Brand-new or less-common model names aren't always in that map yet. Fix: call
`tiktoken.get_encoding("o200k_base")` (or whichever encoding you know the model actually
uses) directly instead of going through the model-name lookup.

**Why does my token count not match the count OpenAI's tokenizer web UI shows?**
Almost always because of encoding mismatch — the web UI defaults to whichever encoding
matches its currently-selected model, so if you called `get_encoding("cl100k_base")` locally
but the UI is set to a GPT-4o model (which uses `o200k_base`), the counts will differ. Match
the encoding to the exact model you're actually calling.

**`encode()` raises `Not allowed to encode special tokens` — what's happening?**
Strings like `<|endoftext|>` are reserved special tokens, not ordinary text, and by default
`encode()` refuses to silently swallow one from untrusted input (this is a real prompt-
injection vector — someone crafting input containing a raw special token to manipulate
context boundaries). If you deliberately need to allow or encode one, pass
`enc.encode(text, allowed_special={"<|endoftext|>"})` (or `allowed_special="all"`) —
only do this for text you trust.

**Is an `Encoding` object safe to reuse / thread-safe?**
Yes — create it once (`enc = tiktoken.encoding_for_model(...)`) and reuse it across calls
and threads. Recreating it per call/per document just re-does the setup work for no benefit;
see `batch_token_counts` in the examples file for the pattern.

**Does tiktoken need internet access at runtime?**
Only to fetch an encoding's merge-table file the first time that specific encoding is used
on a machine — after that it's cached locally (`~/.cache/tiktoken` by default, overridable
via the `TIKTOKEN_CACHE_DIR` env var) and runs fully offline. This is the usual culprit
behind tiktoken working locally but failing in a locked-down CI runner or corporate
proxy/firewall with no egress: pre-warm the cache (or vendor the cache directory into the
image) rather than relying on a first-run download inside the restricted environment.

**`encode()` vs `encode_ordinary()` — what's the difference?**
`encode_ordinary()` is a faster path that skips special-token handling entirely (it treats
everything, including strings that look like special tokens, as plain text). Use it when you
know the input has no special tokens and you just want raw token counts as fast as possible;
use plain `encode()` (with an explicit `allowed_special`/`disallowed_special` policy) when
the input could plausibly contain one.

**How do I turn a token count into a dollar cost?**
tiktoken only gives you the count — pricing is separate and changes over time, so multiply
the count by whatever OpenAI's current per-model, per-input/output-token rate is rather than
hardcoding a rate here.

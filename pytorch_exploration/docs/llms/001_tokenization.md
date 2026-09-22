# Tokenization — very briefly

Tokenizer has a predefined vocabulary

```text
ID → Token
1  → "The"
2  → "cat"
3  → "ing"
```

Text is given to tokenizer

```text
"The cat"
```

Tokenizer splits text into vocabulary pieces

```text
["The", "cat"]
```

Pieces are converted to IDs

```text
[1, 2]
```

Vocabulary doesn't need every complete word. It can contain subwords:

```text
"playing" → ["play", "ing"]
```

So:

```text
Text
 ↓
Tokenizer
 ↓
Tokens
 ↓
Token IDs
```

The next step is embeddings: how do [1, 2] become useful vectors that the neural network can understand?

---

> **Note (added):** how the vocabulary itself gets built. Real tokenizers don't have a
> human writing rules like `"playing" → ["play", "ing"]` — they learn the vocabulary from
> a text corpus, most commonly with **BPE (Byte Pair Encoding)**: start from individual
> characters/bytes, repeatedly merge the most frequent adjacent pair into one new
> vocabulary entry, and stop once the vocabulary hits a target size (~50K for GPT-2,
> ~100K+ for GPT-4's `tiktoken`; LLaMA uses a similar idea via SentencePiece). Frequent
> whole words end up as single tokens; rare words get split into smaller, more common
> pieces — that's why `"ing"` earns its own ID (it's a common suffix) while a rare word
> might get chopped into three or four pieces. `mini_llm.py`'s `CharTokenizer` skips this
> entirely and uses one character = one token, which is why its vocab is only ~65 entries
> instead of tens of thousands.

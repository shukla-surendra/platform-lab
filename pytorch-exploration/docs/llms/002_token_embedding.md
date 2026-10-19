# Phase 1

> **Note (added):** everything from here down to "Phase 2 — Embeddings" is a verbatim
> recap of [`001_tokenization.md`](001_tokenization.md). Left as-is (not deduping per
> instructions) — just flagging so you know it's intentional duplication, not two
> different explanations.

Tokenization — very briefly

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




phase 2

# Phase 2 — Embeddings

## 1. Token IDs are not meaningful by themselves

After tokenization:

```text
"The cat sat"
      ↓
[10, 25, 37]
```

25 does not mean that the number itself represents "cat" mathematically.

It is simply an ID/index.

## 2. Embedding table

The model has a learnable table:

```text
Vocabulary Size × Embedding Dimension
```

For example:

```text
50,000 × 64
```

means:

```text
50,000 possible tokens
Each token has a vector of 64 numbers
```

Example:

```text
ID 42 → [0.2, -0.4, 0.7, ...]   ← 64 numbers
```

So embedding dimension = 64 means:

> How many numbers represent one token.

If there are 3 tokens:

```text
3 tokens × 64 dimensions
```

→ 3 × 64 matrix

> **Note (added):** `mini_llm.py` uses the exact same shape logic at a smaller scale —
> `N_EMBD = 64` (same embedding dimension as this example, coincidentally), but
> `vocab_size` is only ~65 (one entry per distinct character in the training text) instead
> of 50,000, because it's a char-level tokenizer (see the note in `001_tokenization.md`
> about BPE vs char-level). So `token_emb.weight.shape == (65, 64)` there, not `(50000,
> 64)` — same idea, much smaller table.

## 3. How are the vectors created?

Initially, the vectors are generally randomly initialized.

```text
"cat"
  ↓
[initial random numbers]
```

During training:

```text
prediction
   ↓
loss
   ↓
backpropagation
   ↓
gradient update
   ↓
embedding values change
```

This happens repeatedly over huge amounts of training data.

Eventually, the vectors become useful learned representations.

## 4. Important confusion you had: "If the vector changes, how does the model know it's still the?"

This is the key distinction:

Tokenizer vocabulary:

```text
42 → "the"
```

is separate from:

Embedding table:

```text
42 → [0.3, 0.7, -0.2, ...]
```

The embedding vector can change:

```text
42 → vector A
42 → vector B
42 → vector C
```

while:

```text
42 → "the"
```

remains the same.

The model doesn't decode the vector to figure out which word it is.

It simply does:

```text
token ID 42
     ↓
look up row 42
     ↓
current learned vector
```

So:

```text
Token ID = identity/index
Embedding vector = learned representation
```

## 5. What does the embedding learn?

Through training, the vectors can develop useful relationships between tokens.

For example, conceptually:

```text
cat ↔ dog       related
cat ↔ banana    less related
```

But embedding is not the complete understanding of the model.

The Transformer layers later process these representations using context.

> **Note (added):** the mechanism behind "related" here — nothing tells the model
> explicitly that cats and dogs are both animals. During training, the *only* signal is
> next-token prediction loss (see the diagram in section 3 above:
> `prediction → loss → backprop → gradient update`). If "cat" and "dog" tend to appear in
> similar surrounding contexts across the training data (e.g. both follow "the" and
> precede "chased/ran/barked"), gradient descent nudges their embedding vectors toward
> similar directions purely because that reduces the loss — not because "animal-ness" is
> programmed in. Once trained, "related" is measurable directly on the vectors: a high dot
> product / cosine similarity between two rows of `token_emb.weight` means the model
> learned to treat those tokens similarly.

## Current LLM pipeline

```text
"The cat sat"
       ↓
   Tokenizer
       ↓
 Token IDs
       ↓
Embedding Lookup
       ↓
Embedding Vectors
       ↓
   Transformer
```

## One-line takeaway

Embedding is a learnable lookup table that converts each token ID into a vector, and training continuously adjusts those vectors to produce better representations.

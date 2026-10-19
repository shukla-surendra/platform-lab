# Phase 3 — Position Information

## Goal

After tokenization and embeddings, the model needs information about **where each token occurs in the context**.

Example:

```text
"The cat sat"

The → position 0
cat → position 1
sat → position 2
```

Token embeddings tell the model **what token** it is. Position information tells the model **where the token is**.

---

## 1. What is BLOCK_SIZE?

In the example code:

```python
BLOCK_SIZE = 64
```

`BLOCK_SIZE` means the **maximum context length**: the maximum number of tokens the model can work with in one context/window.

So with `BLOCK_SIZE = 64`, possible positions are:

```text
0, 1, 2, ... 63
```

This is why a learned position table can have 64 position entries.

Simple mental model:

> BLOCK_SIZE = maximum number of tokens the model can consider in one context/window at a time.

---

## 2. Why do we need position information?

Consider:

```text
"The cat"
"cat The"
```

The same tokens are present, but their order is different.

A token's embedding alone does not tell the model where that token occurs.

Therefore the model needs both:

```text
WHAT? → token embedding
WHERE? → position information
```

---

## 3. Two ways to represent position

There are different techniques. For Phase 3, we only need to understand these two at a high level.

### A. Learned Position Embedding Table

This is what the uploaded mini-LLM code uses.

The code has:

```python
self.token_emb = nn.Embedding(vocab_size, n_embd)
self.pos_emb = nn.Embedding(block_size, n_embd)
```

So there are two separate tables:

```text
Token embedding table
= vocabulary size × embedding dimension

Position embedding table
= BLOCK_SIZE × embedding dimension
```

For example:

```text
vocab_size = 10,000
BLOCK_SIZE = 64
N_EMBD = 64

Token table:
10,000 × 64

Position table:
64 × 64
```

Each position gets a learnable vector:

```text
position 0 → [....]
position 1 → [....]
position 2 → [....]
...
position 63 → [....]
```

The vectors are learnable parameters and are updated during training.

#### Simple PyTorch example

```python
import torch
import torch.nn as nn

BLOCK_SIZE = 8
N_EMBD = 4

pos_emb = nn.Embedding(BLOCK_SIZE, N_EMBD)

positions = torch.arange(5)

position_vectors = pos_emb(positions)
```

Conceptually:

```text
position 0 → 4 numbers
position 1 → 4 numbers
position 2 → 4 numbers
...
```

---

### B. RoPE (Rotary Position Embedding)

Many modern LLM architectures use RoPE.

RoPE does **not** use a separate learned `BLOCK_SIZE × N_EMBD` position table in the same way.

Instead, position information is incorporated using a mathematical rotation, associated with the attention computation (specifically Q and K).

High-level idea:

```text
Learned position embedding:

position
   ↓
position vector
   ↓
token embedding + position vector


RoPE:

token representation
   ↓
position-dependent rotation
   ↓
Q / K used by attention
```

Do not worry about the rotation mathematics yet. That belongs naturally with the later attention/Q/K/V phase.

> **Note (added):** *why* RoPE matters, at a high level, without the rotation math yet.
> A learned position table (approach A) only has rows for positions `0..BLOCK_SIZE-1` — it
> literally cannot represent a position beyond what it was trained with, so the context
> window is hard-capped at `BLOCK_SIZE`. RoPE encodes position as a rotation applied to Q/K
> rather than as a lookup row, and rotations compose smoothly for positions the model never
> saw in training, so RoPE-based models generalize to longer sequences more gracefully.
> That's the main practical reason most current LLMs (LLaMA, Qwen, Mistral, and others)
> use RoPE instead of a learned absolute position table like `mini_llm.py` does.

---

## 4. Important distinction: Position is NOT attention

This was one of the confusions during Phase 3.

They are separate concepts:

```text
Position information
→ tells the model WHERE a token is

Attention
→ allows tokens to interact/look at other tokens
  and determine which tokens are relevant
```

Attention exists whether the model uses a learned position table or RoPE.

So:

```text
Learned position embedding
        ↓
     Transformer
        ↓
     Attention
```

and:

```text
RoPE
  ↓
Attention
```

RoPE and attention are not the same thing.

---

## 5. How the learned position table is used

For the current mini-LLM, the code creates the positions:

```python
positions = torch.arange(T)
```

If:

```text
T = 3
```

then:

```text
[0, 1, 2]
```

These positions are looked up in the position embedding table.

The model then combines token and position representations:

```python
x = self.token_emb(idx) + self.pos_emb(positions)
```

Conceptually:

```text
The → token vector + position-0 vector
cat → token vector + position-1 vector
sat → token vector + position-2 vector
```

Each resulting representation still has `N_EMBD` dimensions.

---

## 6. Important doubts/questions resolved

### Q: Is the position table separate from the token embedding table?

Yes.

```text
Token embedding table
        +
Position embedding table
```

They are separate tables in the learned-position approach.

---

### Q: Is `BLOCK_SIZE` the position table size?

It determines the **number of possible positions**.

If:

```text
BLOCK_SIZE = 64
N_EMBD = 64
```

then:

```text
Position table = 64 × 64
```

---

### Q: Does BLOCK_SIZE mean the model can process 64 tokens in one go?

As an intuition, yes.

More precisely:

> BLOCK_SIZE/context length is the maximum number of tokens the model can consider in one context/window at a time.

---

### Q: Are the position vectors learnable?

For learned positional embeddings, yes.

They are parameters of the model and are updated during training.

---

### Q: Why are there multiple techniques for position?

Because position information can be represented in different ways.

The two approaches covered here are:

1. **Learned positional embeddings** — a separate learnable position table.
2. **RoPE** — position is incorporated through a mathematical rotation in the attention-related Q/K representations.

For now, do not go deeper into RoPE mathematics.

---

## Phase 3 Mental Model

```text
Text
 ↓
Tokenizer
 ↓
Token IDs
 ↓
Token Embedding
 ↓
"What token?"
 +
Position Information
 ↓
"Where is the token?"
 ↓
Transformer / Attention
```

The simplest takeaway:

> **Token embedding tells the model WHAT the token is. Position information tells it WHERE the token is.**

And for the code being studied:

```text
BLOCK_SIZE = maximum context/window length

token_emb = learned token representation table

pos_emb = learned position representation table
```

Phase 3 is complete. The next phase is **Attention**, where we will learn how tokens interact with each other.




## Phase 3 Addendum — Position Embeddings: The Confusion Cleared

### The main confusion

The important realization was that the position embedding table is **not tied to particular words**.

If the context length is 1024, the model has position representations for:

```text
0, 1, 2, ... 1023
```

These positions are reused for every new context/window.

---

### Example

Consider:

```text
"The cat chased the dog"
```

Positions:

```text
The     → 0
cat     → 1
chased  → 2
the     → 3
dog     → 4
```

Now another context:

```text
"The dog chased the cat"
```

Positions:

```text
The     → 0
dog     → 1
chased  → 2
the     → 3
cat     → 4
```

Notice:

```text
First context:
cat → position 1

Second context:
dog → position 1
```

This is completely fine.

**Position 1 does not mean "cat."**

It means:

> "Whatever token is currently in position 1 of this context."

---

### The position table is reused

The position table is a model parameter, not a table created for each batch.

For example:

```text
P0 → position-0 vector
P1 → position-1 vector
P2 → position-2 vector
...
P1023 → position-1023 vector
```

A new context simply looks up the same position vectors.

```text
Context 1 → uses P0, P1, P2, ...
Context 2 → uses P0, P1, P2, ...
Context 3 → uses P0, P1, P2, ...
```

During training, these vectors are updated through the normal gradient/backpropagation process and continue to be reused in later batches.

---

### Does position tell the model that something is a noun, verb, subject, etc.?

No.

The position table only represents **where the token occurs**.

For example:

```text
position 1 → P1
```

does NOT mean:

```text
position 1 = noun
```

or:

```text
position 1 = subject
```

The model is not given explicit linguistic labels such as:

```text
cat     = noun
chased  = verb
dog     = noun
```

Instead, during training it sees many examples and learns patterns that help it predict the next token.

---

### Then how can it learn things like grammar?

The model learns patterns from the training data.

For example, it repeatedly encounters structures such as:

```text
The cat chased the dog
The dog chased the cat
The boy kicked the ball
The girl opened the door
...
```

It can learn statistical and structural relationships between tokens.

Position is one piece of information that helps distinguish different arrangements of the same tokens.

For example:

```text
"The cat chased the dog"
```

is different from:

```text
"The dog chased the cat"
```

because the tokens occur in different positions and have different relationships with one another.

Later, **attention** allows tokens to interact with other tokens and is a major mechanism for learning these relationships.

---

### Important mental model

Think of the information entering the Transformer as containing:

```text
WHAT?
→ token embedding

WHERE?
→ position information

RELATIONSHIPS / CONTEXT?
→ learned through Transformer mechanisms such as attention
```

The model is not explicitly told the linguistic rules.

Instead:

> **It learns patterns from data that help it predict the next token.**

---

### Final takeaway

The position table does not memorize:

```text
P1 = cat
```

It represents:

```text
P1 = position 1
```

So in different contexts:

```text
cat  can be at position 1
dog  can be at position 1
banana can be at position 1
```

All use the same `P1`.

The token embedding identifies/represents the token, while the position representation provides its location in the current context.

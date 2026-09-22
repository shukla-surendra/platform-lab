# Phase 6 — Multi-Head Attention (MHA)

## 1. What is Multi-Head Attention?

One attention calculation is called **one attention head**:

```text
X
↓
Q, K, V
↓
Q × K
↓
Softmax
↓
Attention weights × V
↓
Output
```

**Multi-Head Attention (MHA)** means running several attention heads in parallel.

```text
                 X
              /     \
          Head 1    Head 2
             ↓         ↓
        Q1,K1,V1    Q2,K2,V2
             ↓         ↓
         Attention  Attention
             ↓         ↓
            O1        O2
              \       /
               Concatenate
                   ↓
                Output
```

---

## 2. Do all heads follow the same rules?

**Yes.**

All heads follow the same attention algorithm:

1. Create Q, K, V
2. Calculate `Q × K`
3. Apply causal mask (for GPT-style causal attention)
4. Apply softmax
5. Use the attention weights to combine V

However, the heads have **different learned parameters**.

For example:

```text
Head 1:
Q1 = X WQ1
K1 = X WK1
V1 = X WV1

Head 2:
Q2 = X WQ2
K2 = X WK2
V2 = X WV2
```

`WQ1` and `WQ2` are different learned matrices.

Therefore, different heads can learn different relationships/patterns.

### Mental model

> **Same calculation rules + different learned weights = different attention heads.**

For example, one head might learn to focus on nearby words while another might learn longer-range relationships. These are learned from training; they are not manually assigned.

---

## 3. Three ways to understand MHA

These are **not three different types of MHA**. They are different ways to conceptualize/implement the same multi-head idea.

### Method 1 — Split the embedding into heads

Suppose:

```text
embedding dimension = 4
number of heads = 2
```

Then each head gets 2 dimensions:

```text
X = [x1, x2, x3, x4]

Head 1 → [x1, x2]
Head 2 → [x3, x4]
```

Each head performs attention independently.

```text
Head 1: X1 → Q1,K1,V1 → Attention → O1
Head 2: X2 → Q2,K2,V2 → Attention → O2
```

Then the outputs are concatenated.

---

### Method 2 — Same X into different projections

Conceptually:

```text
              X
          /   |   \
        /     |     \
      WQ1    WK1    WV1
       ↓      ↓      ↓
      Q1     K1     V1

              X
          /   |   \
        /     |     \
      WQ2    WK2    WV2
       ↓      ↓      ↓
      Q2     K2     V2
```

Then:

```text
Head 1 → Q1,K1,V1 → Attention → O1
Head 2 → Q2,K2,V2 → Attention → O2
```

This is the easiest conceptual model:

> **Same X → different learned Q/K/V projections → separate attention heads → combine outputs.**

---

### Method 3 — One big projection, then split

A practical implementation can use large projection matrices:

```text
X → WQ → all Q heads
X → WK → all K heads
X → WV → all V heads
```

Then split:

```text
Q → Q1 | Q2
K → K1 | K2
V → V1 | V2
```

Each head performs attention independently:

```text
Head 1 → Q1,K1,V1 → Attention → O1
Head 2 → Q2,K2,V2 → Attention → O2
```

Finally:

```text
O1 | O2
 ↓
Concatenate
 ↓
Final linear projection
 ↓
MHA output
```

> **Note (added):** this is exactly what `mini_llm.py`'s `CausalSelfAttention` does.
> `self.qkv_proj = nn.Linear(n_embd, 3 * n_embd)` is the "one big projection" (all Q, K,
> and V heads at once), then `qkv.split(C, dim=-1)` separates it into Q/K/V, and
> `.view(B, T, self.n_head, self.head_size).transpose(1, 2)` is the "split into heads"
> step. `self.out_proj` at the end is the "final linear projection" after concatenating
> head outputs. Method 3 isn't just a conceptual option — it's the actual implementation
> pattern used here (and in most real transformer code), because one big matmul is faster
> on a GPU than `n_head` small separate ones.

---

## 4. Why multiple heads?

A single attention head has one set of learned projections.

Multiple heads give the model multiple learned attention spaces.

Conceptually:

```text
Head 1 → learns one kind of relationship
Head 2 → learns another kind
Head 3 → learns another kind
...
```

The exact relationships are learned during training.

---

## 5. Causal attention + MHA

GPT-style LLMs generally use:

```text
Multi-Head Attention
        +
Causal Masking
```

The important distinction is:

- **Causal** → controls which tokens can see which other tokens.
- **Multi-head** → controls how many separate attention mechanisms operate in parallel.

Every head follows the causal rule.

For:

```text
a b c d
```

each head can have:

```text
a → a
b → a,b
c → a,b,c
d → a,b,c,d
```

---

## 6. PyTorch — Multi-Head Attention

PyTorch provides `nn.MultiheadAttention`.

A simple example:

```python
import torch
import torch.nn as nn

# --------------------------------
# Configuration
# --------------------------------

batch_size = 1
seq_len = 4
embed_dim = 8
num_heads = 2

# embed_dim must be divisible by num_heads
# 8 / 2 = 4 dimensions per head


# --------------------------------
# Input
# --------------------------------

X = torch.randn(
    batch_size,
    seq_len,
    embed_dim
)

print("X shape:", X.shape)
# [1, 4, 8]


# --------------------------------
# Multi-Head Attention
# --------------------------------

mha = nn.MultiheadAttention(
    embed_dim=embed_dim,
    num_heads=num_heads,
    batch_first=True
)


# Self-attention:
# Q = X
# K = X
# V = X

output, attention_weights = mha(
    X,
    X,
    X
)

print("Output shape:", output.shape)
print("Attention shape:", attention_weights.shape)
```

Output shapes:

```text
X:
[batch_size, seq_len, embed_dim]
[1, 4, 8]

Output:
[1, 4, 8]
```

The embedding dimension remains 8 because the outputs of the heads are combined back into the model dimension.

---

## 7. Causal MHA in PyTorch

For GPT-style causal attention, we need a causal mask.

```python
import torch
import torch.nn as nn

batch_size = 1
seq_len = 4
embed_dim = 8
num_heads = 2

X = torch.randn(
    batch_size,
    seq_len,
    embed_dim
)

mha = nn.MultiheadAttention(
    embed_dim=embed_dim,
    num_heads=num_heads,
    batch_first=True
)

# --------------------------------
# Causal mask
# --------------------------------

causal_mask = torch.triu(
    torch.ones(seq_len, seq_len),
    diagonal=1
).bool()

print(causal_mask)
```

Conceptually the mask is:

```text
False True  True  True
False False True  True
False False False True
False False False False
```

Meaning:

```text
Token 1 → can see token 1
Token 2 → can see token 1,2
Token 3 → can see token 1,2,3
Token 4 → can see token 1,2,3,4
```

Then:

```python
output, attention_weights = mha(
    X,
    X,
    X,
    attn_mask=causal_mask
)
```

Now every head follows the causal rule.

---

## 8. What is happening inside MHA?

At a high level:

```text
                 X
                 │
       ┌─────────┼─────────┐
       ↓         ↓         ↓
     Q/K/V     Q/K/V     Q/K/V
    Head 1    Head 2    Head 3
       ↓         ↓         ↓
  Attention  Attention  Attention
       ↓         ↓         ↓
      O1        O2        O3
       └─────────┼─────────┘
                 ↓
            Concatenate
                 ↓
          Final projection
                 ↓
              Output
```

The important idea is:

> MHA is several independent attention calculations performed in parallel, using different learned projections, followed by combining their outputs.

---

## 9. Key points to remember

```text
One head:
X → Q,K,V → Attention → O

Multiple heads:
X → Head 1 ─→ O1
  → Head 2 ─→ O2
  → Head 3 ─→ O3
  ...
       ↓
   Concatenate
       ↓
 Final projection
       ↓
    Output
```

### Remember:

1. All heads use the **same attention algorithm**.
2. Each head has **different learned parameters**.
3. Therefore heads can learn different relationships.
4. In GPT-style models, **each head also follows causal masking**.
5. MHA is not a different attention formula; it is multiple attention heads working in parallel.
6. After attention, head outputs are concatenated and projected back to the model embedding dimension.

---

## What comes next?

After MHA, the next phase is:

**Phase 7 — Transformer Block**

The Transformer Block will combine:

```text
MHA
 ↓
Residual connection
 ↓
LayerNorm
 ↓
Feed Forward Network (MLP)
 ↓
Residual connection
 ↓
LayerNorm
```

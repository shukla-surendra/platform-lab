# Phase 8 — Stacking Transformer Blocks

## 1. Main idea

Phase 7 focused on **what is inside one Transformer Block**.

Phase 8 focuses on:

> **What happens when we stack many Transformer Blocks sequentially?**

```text
Input
  ↓
Transformer Block 1
  ↓
Transformer Block 2
  ↓
Transformer Block 3
  ↓
...
  ↓
Transformer Block N
  ↓
Output
```

---

## 2. Why stack Transformer Blocks?

One Transformer Block transforms the token representations.

Instead of stopping after one block, the output is passed into another block:

```text
X
 ↓
Block 1 → X₁
 ↓
Block 2 → X₂
 ↓
Block 3 → X₃
```

Each block further transforms the representation.

---

## 3. Shape stays the same

Suppose:

```text
B = 2       batch size
T = 10      sequence length
d = 768     model dimension
```

Input:

```text
[B, T, d]
=
[2, 10, 768]
```

After each Transformer Block:

```text
Block 1 → [2, 10, 768]
Block 2 → [2, 10, 768]
Block 3 → [2, 10, 768]
```

So:

```text
[B,T,d]
  ↓
[B,T,d]
  ↓
[B,T,d]
  ↓
[B,T,d]
```

The **shape stays the same**, but the values inside the representation change.

---

## 4. Are the blocks identical?

The blocks have the **same architecture**, but their learned parameters are different.

For example:

```text
Block 1 → MHA weights W₁, FFN weights F₁
Block 2 → MHA weights W₂, FFN weights F₂
Block 3 → MHA weights W₃, FFN weights F₃
```

Therefore:

```text
Block 1 ≠ Block 2
```

in terms of learned parameters.

They are separate copies of the same architecture.

---

## 5. Number of layers

When an LLM configuration says:

```python
n_layers = 3
```

it generally means:

```text
3 Transformer Blocks
```

```text
Block 1
  ↓
Block 2
  ↓
Block 3
```

If:

```python
n_layers = 100
```

then:

```text
Block 1
  ↓
Block 2
  ↓
...
  ↓
Block 100
```

So:

> **`n_layers` = number of Transformer Blocks.**

It does not mean the number of individual `Linear` or `LayerNorm` operations.

---

## 6. PyTorch — creating the stack

Use `nn.ModuleList`:

```python
self.blocks = nn.ModuleList([
    TransformerBlock(...)
    for _ in range(n_layers)
])
```

For:

```python
n_layers = 3
```

this creates:

```text
Block 1
Block 2
Block 3
```

For:

```python
n_layers = 32
```

it creates 32 Transformer Blocks.

---

## 7. How are the blocks connected?

`ModuleList` itself does not automatically connect the blocks.

The `forward()` method connects them:

```python
for block in self.blocks:
    x = block(x)
```

This means:

```text
x
 ↓
Block 1
 ↓
x
 ↓
Block 2
 ↓
x
 ↓
Block 3
 ↓
x
```

The output of one block becomes the input of the next.

---

## 8. Complete LLM flow

At the architecture level:

```text
Text
 ↓
Tokenizer
 ↓
Token IDs
 ↓
Token Embedding
 ↓
+ Position Information
 ↓
X
 ↓
Transformer Block 1
 ↓
Transformer Block 2
 ↓
...
 ↓
Transformer Block N
 ↓
Final LayerNorm
 ↓
LM Head
 ↓
Logits
```

---

## 9. What is the LM Head?

The **LM Head** is the final layer that converts the Transformer representation into scores for every vocabulary token.

Example:

```text
Transformer output
[B, T, 768]
       ↓
LM Head
Linear(768 → 32000)
       ↓
[B, T, 32000]
```

For each position, there is now one score for every possible vocabulary token.

These scores are called **logits**.

Later, softmax can convert logits into probabilities.

Simple mental model:

```text
Transformer Blocks
→ process the context

LM Head
→ converts the final representation into next-token scores
```

---

## 10. Final LayerNorm

Before the LM Head, many Transformer architectures use a final LayerNorm:

```text
Block N
  ↓
Final LayerNorm
  ↓
LM Head
  ↓
Logits
```

The final LayerNorm keeps the final representation normalized before it is passed to the output layer.

---

## 11. What happens when `n_layers` increases?

Suppose:

```python
n_layers = 3
```

```text
Embedding
 ↓
Block 1
 ↓
Block 2
 ↓
Block 3
 ↓
Final LayerNorm
 ↓
LM Head
```

If:

```python
n_layers = 100
```

```text
Embedding
 ↓
Block 1
 ↓
Block 2
 ↓
...
 ↓
Block 100
 ↓
Final LayerNorm
 ↓
LM Head
```

Increasing `n_layers` means:

- More Transformer Blocks
- More learnable parameters
- More computation
- Greater model depth

The model dimension `d` does not automatically increase.

---

## 12. Parameter scaling

A useful quick estimate for a standard Transformer is:

```text
P ≈ 12 × L × d²
```

where:

```text
L = number of Transformer Blocks
d = model/embedding dimension
```

This is an approximate estimate for the Transformer blocks and ignores some smaller components such as embeddings, LayerNorm parameters, and biases.

### Example

```text
L = 12
d = 768
```

Then:

```text
P ≈ 12 × 12 × 768²
```

which is approximately:

```text
85 million parameters
```

for the Transformer blocks.

> **Note (added) — checked against `mini_llm.py`:** running the actual model gives
> `vocab_size=33, params=206,272` (its config: `L=4, d=64`). The formula predicts
> `12 × 4 × 64² = 196,608` — off by only ~5%, closer than you might expect for such a
> tiny model. That's partly luck: the formula ignores the embedding table entirely, but
> `mini_llm.py` ties `lm_head.weight` to `token_emb.weight` (see `docs/mini_llm_qa.md`
> Q1), so there's only one embedding matrix instead of two, which keeps the "ignored"
> part small relative to the rest. With a large vocab (32K–100K+, as in real LLMs) and no
> weight tying, the embedding table would be a much bigger share of the total and the
> formula's error would grow.

---

## 13. How parameter count scales

### Increase number of blocks

If `d` stays fixed:

```text
L doubles
→ parameters roughly double
```

### Increase model dimension

If `L` stays fixed:

```text
d doubles
→ parameters roughly 4×
```

because:

```text
P ∝ d²
```

This is an important reason why increasing model width can increase parameter count very quickly.

---

## 14. Complete mental model

The hierarchy is:

```text
LLM
│
├── Token Embedding
│
├── Transformer Block 1
│   ├── LayerNorm
│   ├── MHA
│   ├── Residual
│   ├── LayerNorm
│   ├── FFN
│   └── Residual
│
├── Transformer Block 2
│   └── Same architecture, different weights
│
├── ...
│
├── Transformer Block N
│
├── Final LayerNorm
│
└── LM Head
```

Remember:

```text
Phase 7:
Understand ONE Transformer Block

Phase 8:
Understand MANY Transformer Blocks stacked together
```

---

## 15. Small PyTorch example

```python
import torch.nn as nn


class Model(nn.Module):

    def __init__(self, n_layers):
        super().__init__()

        self.blocks = nn.ModuleList([
            TransformerBlock(...)
            for _ in range(n_layers)
        ])

    def forward(self, x):

        for block in self.blocks:
            x = block(x)

        return x
```

The important part is:

```python
for block in self.blocks:
    x = block(x)
```

This creates the sequential flow:

```text
x → Block 1 → Block 2 → Block 3 → ... → Block N
```

---

## Phase 8 Summary

The key ideas are:

1. **One Transformer Block** is repeated many times.
2. Blocks are connected **sequentially**.
3. Each block has the **same architecture but separate learned parameters**.
4. `n_layers` controls the **number of Transformer Blocks**.
5. `ModuleList` stores the blocks.
6. `forward()` connects them sequentially.
7. The tensor shape normally stays `[B, T, d]` through the stack.
8. `Final LayerNorm` comes after the final block.
9. The **LM Head** converts the final representation into vocabulary logits.
10. Increasing `n_layers` increases depth, parameters, and computation.
11. Quick parameter estimate:

```text
P ≈ 12 × L × d²
```

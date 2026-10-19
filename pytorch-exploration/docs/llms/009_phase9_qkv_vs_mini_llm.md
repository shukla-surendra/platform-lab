# Phase 9 — Understanding the Two LLM Codes: QKV Demo vs Mini LLM

> **Note (added):** this file had 8 broken leftover tokens like `fileciteturn1file0L4-L7`
> scattered through the text (visible as raw garbage, not meant to be read as-is —
> apparently citation markup from whatever tool drafted this that never got converted).
> Converted all of them to plain `(see file.py, lines A–B)` citations below, verified
> against the actual source files. One of them turned out to point at the wrong class —
> flagged in place in section 10.

## 1. Why do the two files look different?

The two files are showing **different levels of the same architecture**.

### `qkv_demo.py`

This file isolates and demonstrates **one attention mechanism**.

It explicitly creates:

```text
X
 ↓
Q, K, V
 ↓
Q × Kᵀ
 ↓
Causal mask
 ↓
Softmax
 ↓
Attention weights × V
 ↓
Context-aware output
```

The file itself says it is **not a trainable model** and has no optimizer, loss, MLP, or stacked blocks. *(see `qkv_demo.py`, lines 4–7)*

It keeps Q, K, and V as separate `Linear` layers so that the concept is easy to see. *(see `qkv_demo.py`, lines 61–74)*

---

## 2. `mini_llm.py`

This is a **complete tiny LLM**.

Its overall flow is:

```text
Raw text
 ↓
Tokenizer
 ↓
Input/target windows
 ↓
Token + position embeddings
 ↓
N Transformer Blocks
 ↓
Final LayerNorm
 ↓
LM Head
 ↓
Logits
 ↓
Cross-entropy loss
 ↓
Backprop + AdamW
```

The file describes this complete pipeline explicitly. *(see `mini_llm.py`, lines 4–16)*

So it includes much more than QKV attention:

```text
Tokenization
Embeddings
MHA
Causal masking
MLP
Residuals
LayerNorm
Multiple blocks
LM Head
Loss
Training
Generation
```

---

## 3. Why doesn't `mini_llm.py` show Q, K, V separately?

This is the main difference.

In `qkv_demo.py`:

```python
W_q = torch.nn.Linear(n_embd, head_size, bias=False)
W_k = torch.nn.Linear(n_embd, head_size, bias=False)
W_v = torch.nn.Linear(n_embd, head_size, bias=False)

Q = W_q(x)
K = W_k(x)
V = W_v(x)
```

There are three explicit Linear layers.

This is done for **learning/visibility**.

---

## 4. `mini_llm.py` combines them

In `mini_llm.py`:

```python
self.qkv_proj = nn.Linear(n_embd, 3 * n_embd)
```

Instead of:

```text
X → WQ → Q
X → WK → K
X → WV → V
```

it does:

```text
             X
             ↓
       qkv_proj
             ↓
       [Q | K | V]
```

Then:

```python
qkv = self.qkv_proj(x)
q, k, v = qkv.split(C, dim=-1)
```

So **Q, K, and V still exist**.

They are simply produced together by one larger Linear layer.

The code comments explicitly say that the three projections are fused into one `qkv_proj` for efficiency. *(see `qkv_demo.py`, lines 61–64 — the comment sits in the demo file, explaining why the real model does it differently)*

---

## 5. Why can one Linear produce Q, K and V?

Suppose:

```text
d_model = 64
```

Separate version:

```text
WQ: 64 → 64
WK: 64 → 64
WV: 64 → 64
```

Combined version:

```text
qkv_proj: 64 → 192
```

because:

```text
192 = 3 × 64
```

The output is split:

```text
192 values

[ first 64 ] [ second 64 ] [ third 64 ]
      ↓           ↓             ↓
      Q           K             V
```

So conceptually:

```text
X
│
├── WQ ──→ Q
├── WK ──→ K
└── WV ──→ V
```

is equivalent in purpose to:

```text
X
 ↓
one 3d Linear
 ↓
Q | K | V
```

The second form is convenient for efficient implementation.

---

## 6. Why does `qkv_demo.py` have only one head?

It explicitly says:

```python
head_size = n_embd
```

so:

```text
head_size = embedding dimension
```

There is no splitting into multiple heads. *(see `qkv_demo.py`, lines 67–75)*

Therefore its flow is:

```text
X
 ↓
Q K V
 ↓
One attention head
 ↓
Output
```

It is intentionally simplified so the Q/K/V mechanism can be printed and inspected.

---

## 7. `mini_llm.py` has Multi-Head Attention

Its configuration is:

```python
N_EMBD = 64
N_HEAD = 4
```

so:

```text
head_size = 64 / 4
          = 16
```

The code checks that the embedding dimension is divisible by the number of heads. *(see `mini_llm.py`, lines 123–127)*

The flow is:

```text
X
 ↓
qkv_proj
 ↓
Q K V
 ↓
Split into 4 heads
 ↓
Attention independently in each head
 ↓
Merge heads
 ↓
Output projection
```

The actual code performs this split and later merges the heads back. *(see `mini_llm.py`, lines 141–156)*

---

## 8. Side-by-side comparison

| | `qkv_demo.py` | `mini_llm.py` |
|---|---|---|
| Purpose | Understand Q/K/V | Complete tiny LLM |
| Trainable model | No | Yes |
| Q/K/V | Separate Linear layers | One fused Linear |
| Attention heads | 1 | 4 |
| Causal mask | Yes | Yes |
| MLP/FFN | No | Yes |
| Residual | No | Yes |
| LayerNorm | No | Yes |
| Transformer blocks | No | 4 |
| Loss | No | Cross-entropy |
| Optimizer | No | AdamW |
| Generation | No | Yes |

---

## 9. Where Q/K/V fit into the Transformer Block

From Phase 7 we learned:

```text
Transformer Block
│
├── LayerNorm
├── Multi-Head Attention
│   │
│   ├── Q
│   ├── K
│   ├── V
│   ├── Attention
│   └── Output projection
│
├── Residual
│
├── LayerNorm
│
├── FFN
│
└── Residual
```

So Q/K/V were **not removed** in `mini_llm.py`.

They are simply **inside the Multi-Head Attention implementation**.

---

## 10. Exact flow inside `mini_llm.py`

For one Transformer Block:

```text
X
 ↓
LayerNorm
 ↓
qkv_proj
 ↓
Q | K | V
 ↓
Split into heads
 ↓
Q × Kᵀ / √head_size
 ↓
Causal mask
 ↓
Softmax
 ↓
Attention weights
 ↓
Attention weights × V
 ↓
Merge heads
 ↓
Output projection
 ↓
Residual addition
 ↓
LayerNorm
 ↓
MLP / FFN
 ↓
Residual addition
 ↓
Block output
```

The `Block.forward()` code is:

```python
x = x + self.attn(self.ln1(x))
x = x + self.mlp(self.ln2(x))
```

The attention implementation is inside `CausalSelfAttention`. *(see `mini_llm.py`, lines 177–191)*

> **Note (added) — citation was pointing at the wrong class:** lines 177–191 are actually
> the `Block` class (the residual wrapper shown in the two lines just above — `x = x +
> self.attn(...)`, `x = x + self.mlp(...)`), not `CausalSelfAttention` itself.
> `CausalSelfAttention` — the actual Q/K/V-and-softmax math — is at `mini_llm.py:110–157`.
> The sentence is still true (the attention math *is* inside `CausalSelfAttention`, and
> `Block` *does* call it via `self.attn`), the citation just pointed one class over.

---

## 11. Full `mini_llm.py` architecture

Now connect everything from Phases 0–8:

```text
Text
 ↓
Tokenizer
 ↓
Token IDs
 ↓
Token Embedding
 +
Position Embedding
 ↓
X
 ↓
┌──────────────────────────┐
│ Transformer Block 1      │
│                          │
│ LayerNorm                │
│    ↓                     │
│ MHA                      │
│  ├── Q                   │
│  ├── K                   │
│  ├── V                   │
│  └── attention           │
│    ↓                     │
│ Residual                 │
│    ↓                     │
│ LayerNorm                │
│    ↓                     │
│ MLP                      │
│    ↓                     │
│ Residual                 │
└──────────────────────────┘
 ↓
Block 2
 ↓
Block 3
 ↓
Block 4
 ↓
Final LayerNorm
 ↓
LM Head
 ↓
Logits
 ↓
Cross-Entropy Loss
```

The model configuration in the file uses:

```text
BLOCK_SIZE = 64
N_EMBD = 64
N_HEAD = 4
N_LAYER = 4
```

and the file describes the model as a tiny GPT-2-like architecture. *(see `mini_llm.py`, lines 99–106)*

---

## 12. Why did we learn `qkv_demo.py` first?

Because if we started directly with:

```python
qkv = self.qkv_proj(x)
q, k, v = qkv.split(C, dim=-1)
```

it would hide the important concept.

For learning:

```text
X
 ↓
WQ → Q
WK → K
WV → V
```

is easier to understand.

Then implementation can optimize it:

```text
X
 ↓
One big projection
 ↓
Q | K | V
```

So:

> **The mathematical idea is the same; the implementation is different.**

---

## 13. One very important connection

You have now learned:

### Phase 5

```text
Q, K, V
 ↓
Attention
```

### Phase 6

```text
Multiple attention heads
```

### Phase 7

```text
MHA + FFN + LayerNorm + Residual
= one Transformer Block
```

### Phase 8

```text
Many Transformer Blocks
= deep Transformer/LLM
```

### Phase 9

Now we connect the **simple attention implementation** to the **complete LLM implementation**.

The key realization is:

> **Q/K/V are still present in the real model. They are just hidden inside the Multi-Head Attention module and often computed together for efficiency.**

---

## 14. The one-line answer

If you see:

```python
nn.Linear(d, d)       # Q
nn.Linear(d, d)       # K
nn.Linear(d, d)       # V
```

and elsewhere:

```python
nn.Linear(d, 3*d)
```

don't think they are different attention mechanisms.

Think:

```text
Three separate projections:

X → Q
X → K
X → V

             ≈

One fused projection:

X → [Q | K | V]
```

The second implementation simply computes them together and splits the result afterward.

---

## Phase 9 takeaway

The two files are at different abstraction levels:

```text
qkv_demo.py
    ↓
"How does attention work?"

mini_llm.py
    ↓
"How do all the pieces combine into a trainable LLM?"
```

And the bridge between them is:

```text
QKV demo
    ↓
Multi-Head Attention
    ↓
Transformer Block
    ↓
Stacked Transformer Blocks
    ↓
Mini LLM
```

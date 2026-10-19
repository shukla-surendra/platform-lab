# LLM Learning — Phase 4: Attention + PyTorch Implementation

## Where we are

So far we have covered:

```text
Text
 ↓
Tokenization
 ↓
Token IDs
 ↓
Token Embeddings
 ↓
Position Embeddings
 ↓
X
 ↓
Q, K, V
 ↓
Attention
```

This document captures the concepts, doubts, clarifications, causal attention, related attention variants, and the educational PyTorch implementation we discussed.

---

## 1. Tokenization → Token IDs

A tokenizer converts text into tokens and then token IDs.

Toy example:

```text
"a b c d"
    ↓
[0, 1, 2, 3]
```

The token ID is an identity/index into the vocabulary.

---

## 2. Token Embeddings

Each token ID is looked up in an embedding table.

If:

```text
embedding dimension = 4
```

then each token gets a vector of 4 numbers:

```text
a → Xa = [....]
b → Xb = [....]
c → Xc = [....]
d → Xd = [....]
```

These are the vector representations of the tokens.

For example:

```text
a → Xa = [0.2, 0.7, -0.1, 0.5]
```

The actual values are learned during training.

---

## 3. Position Embeddings

Token embeddings tell the model about the token.

Position embeddings tell the model where the token occurs.

For:

```text
a b c d
```

the positions are:

```text
a → position 0
b → position 1
c → position 2
d → position 3
```

With learned positional embeddings:

```text
X = token_embedding + position_embedding
```

This is important for Phase 4:

> Position information is already included in X before Q/K/V are calculated.

The flow is:

```text
Token embedding + Position embedding
              ↓
              X
              ↓
          Q, K, V
              ↓
          Attention
```

We initially almost skipped this point while discussing attention, so it is intentionally highlighted here.

---

## 4. Q, K, V

For each token representation X:

```text
Q = XWQ
K = XWK
V = XWV
```

For a token with dimension 4:

```text
X = 1 × 4
```

If Q/K/V dimension is also 4:

```text
WQ = 4 × 4
WK = 4 × 4
WV = 4 × 4
```

Therefore:

```text
Q = 1 × 4
K = 1 × 4
V = 1 × 4
```

The model architecture decides the Q/K/V dimension.

The general shape idea is:

```text
weight matrix:
input dimension × Q/K/V dimension

result:
Q/K/V dimension
```

---

## 5. What Q, K, V Mean

At initialization, Q/K/V do not inherently have their semantic meanings.

The matrices are initially randomly initialized and learn useful roles through training.

A useful mental model is:

```text
Q → What am I looking for?
K → What do I match on?
V → What information do I provide?
```

Important clarifications:

- K is not simply "previous token information".
- V is not simply the original token preserved unchanged.
- Q/K/V are learned transformations of X.

---

## 6. Q-K Comparison

Suppose the sequence is:

```text
a b c d
```

For causal attention, the allowed comparisons are:

```text
        K
        a   b   c   d
Q a     ✓
Q b     ✓   ✓
Q c     ✓   ✓   ✓
Q d     ✓   ✓   ✓   ✓
```

The key interpretation is:

> Rows = Q tokens  
> Columns = K tokens  
> Each cell = one Q·K comparison

For example:

```text
Qa · Ka
Qb · Ka
Qb · Kb
Qc · Ka
Qc · Kb
Qc · Kc
...
```

There is no special sequential order required for the mathematical calculation.

Actual implementations calculate the comparisons together using matrix multiplication.

---

## 7. What Does One Q-K Comparison Produce?

Suppose:

```text
Qd = [q1, q2, q3, q4]
Ka = [k1, k2, k3, k4]
```

The dot product is:

```text
Qd · Ka
=
q1k1 + q2k2 + q3k3 + q4k4
```

It produces one scalar.

Shape-wise:

```text
(1 × 4) · (4 × 1)
        ↓
      1 × 1
```

The Q and K vectors themselves are still 4-dimensional.

The `1 × 1` is only the result of their comparison.

---

## 8. Why Compare Q and K?

Q and K determine relevance.

Conceptually:

```text
Q + K
  ↓
How strongly do they match?
  ↓
Attention score
```

V is not used for this comparison because V contains the information that will later be passed forward.

The rough mental model is:

```text
Q → what am I looking for?
K → what do I match on?
V → what information do I provide?
```

---

## 9. Score Matrix

For all allowed Q-K comparisons, we get a matrix of scores.

Conceptually:

```text
        K
        a      b      c      d
Q a    score
Q b    score  score
Q c    score  score  score
Q d    score  score  score  score
```

For example, the d row might be:

```text
[2.1, 0.5, 3.2, 1.0]
```

These numbers represent the Q-K matching strengths before softmax.

---

## 10. Softmax

Softmax is applied to the scores for a row.

Example:

```text
scores:
[2.1, 0.5, 3.2, 1.0]

        ↓ softmax

weights:
[0.20, 0.04, 0.55, 0.21]
```

These are attention weights.

Interpretation:

```text
a → 20%
b → 4%
c → 55%
d → 21%
```

The weights tell us how much information to take from each allowed token.

---

## 11. Weighted Sum of V

Now the attention weights are applied to V.

For token d:

```text
Output_d =
  weight_a × Va
+ weight_b × Vb
+ weight_c × Vc
+ weight_d × Vd
```

We do NOT add the weights directly to V.

We:

1. multiply each V by its attention weight
2. add the resulting vectors

The result is one new vector:

```text
d → Output_d
```

This is the context-aware representation of d.

The same process produces:

```text
a → Output_a
b → Output_b
c → Output_c
d → Output_d
```

---

## 12. Complete Basic Attention Flow

The complete flow we learned is:

```text
Token embedding + Position embedding
              ↓
              X
              ↓
          Q, K, V
              ↓
       Q × K comparisons
              ↓
        Score matrix
              ↓
           Softmax
              ↓
       Attention weights
              ↓
   weights × corresponding V
              ↓
        Attention output
```

The attention output is a new context-aware representation for every token.

---

## 13. Causal Attention

"Causal" describes the visibility rule.

In causal attention, a token cannot look at future tokens.

For:

```text
a b c d
```

the allowed visibility is:

```text
a → a
b → a b
c → a b c
d → a b c d
```

So:

```text
        K
        a   b   c   d
Q a     ✓
Q b     ✓   ✓
Q c     ✓   ✓   ✓
Q d     ✓   ✓   ✓   ✓
```

This is also called masked self-attention because future positions are masked.

For example:

```text
Output_b =
  weight_ba × Va
+ weight_bb × Vb
```

`Vc` and `Vd` are not available to b because they are future tokens.

---

## 14. Why Causal Attention Is Needed for Next-Token Prediction

Suppose the model is learning:

```text
a b c d → e
```

When predicting the next token, it should not be allowed to see the future answer.

Causal masking ensures that each position can only use information available up to that position.

This makes the training setup consistent with autoregressive generation.

---

## 15. Causal Attention vs Other Attention Structures

There are two separate ideas that should not be mixed up.

### A. Visibility / direction rule

Causal attention answers:

> Which tokens am I allowed to see?

Causal:

```text
a → a
b → a b
c → a b c
d → a b c d
```

Bidirectional/full self-attention allows a token to see all positions:

```text
a → a b c d
b → a b c d
c → a b c d
d → a b c d
```

BERT-style encoder attention is commonly associated with this bidirectional pattern.

### B. Q/K/V head organization

MHA, GQA, and MQA answer a different question:

> How are Q, K, and V organized across attention heads?

Therefore these concepts can be combined.

For example:

```text
Causal + MHA
Causal + GQA
Causal + MQA
```

So MHA/GQA/MQA are NOT simply three different names for causal attention.

They describe different Q/K/V head organizations.

---

## 16. MHA — Multi-Head Attention

So far we have conceptually learned one attention head:

```text
Q → K → scores → softmax → weights → V → output
```

Multi-Head Attention performs multiple attention calculations in parallel.

Conceptually:

```text
             ┌→ Attention head 1 → output
Q/K/V ───────┼→ Attention head 2 → output
             ├→ Attention head 3 → output
             └→ Attention head 4 → output
```

The reason for multiple heads is that different heads can learn different relationships/patterns.

We have NOT studied the detailed MHA mathematics yet.

---

## 17. GQA and MQA

We only established their high-level relationship so far.

```text
MHA → Multi-Head Attention
GQA → Grouped-Query Attention
MQA → Multi-Query Attention
```

These are different ways of organizing/sharing Q/K/V across heads.

They can be used with causal attention:

```text
Causal + MHA
Causal + GQA
Causal + MQA
```

Do not treat GQA/MQA as separate visibility rules.

Detailed GQA/MQA has not yet been studied.

---

## 18. Context Window During Generation

Suppose:

```text
BLOCK_SIZE = 4
```

Current context:

```text
a b c d
```

The model predicts:

```text
e
```

Now there are 5 tokens, but the active context is limited to 4.

So the next context becomes:

```text
b c d e
```

Then:

```text
b c d e → f
```

and:

```text
c d e f → g
```

Overall:

```text
[a b c d] → e
  [b c d e] → f
    [c d e f] → g
```

The model generates one token at a time.

If an old token falls outside the context window, it is no longer directly available to the current attention computation.

---

## 19. Is Attention Recalculated During Generation?

In the simple generation process we have studied:

```text
[a b c d] → e
[b c d e] → f
[c d e f] → g
```

attention is calculated again for each new context/prediction.

Conceptually:

```text
Pass 1 → Attention → e
Pass 2 → Attention → f
Pass 3 → Attention → g
```

Later we will study KV cache, which makes generation more efficient by reusing previously calculated K/V information.

KV cache is a later topic and is not part of the basic attention calculation.

---

## 20. PyTorch: Manual Educational Implementation

The following is intentionally simple and educational.

It shows the exact concepts we learned rather than trying to implement a production LLM.

```python
import torch
import torch.nn as nn
import torch.nn.functional as F


# ============================================================
# 1. TOKENIZATION
# ============================================================

text = "a b c d"

# Very simple toy tokenizer
vocab = {
    "a": 0,
    "b": 1,
    "c": 2,
    "d": 3,
}

tokens = text.split()

# Text → Token IDs
idx = torch.tensor([vocab[token] for token in tokens])

print("Tokens:", tokens)
print("Token IDs:", idx)


# ============================================================
# 2. TOKEN EMBEDDING
# ============================================================

vocab_size = 4
block_size = 4
n_embd = 4

token_embedding = nn.Embedding(vocab_size, n_embd)

# Token IDs → token vectors
token_vectors = token_embedding(idx)

print("Token embedding shape:", token_vectors.shape)
# [4, 4]
#
# 4 tokens
# each token has 4 numbers


# ============================================================
# 3. POSITION EMBEDDING
# ============================================================

position_embedding = nn.Embedding(block_size, n_embd)

positions = torch.arange(len(tokens))

position_vectors = position_embedding(positions)

print("Position embedding shape:", position_vectors.shape)
# [4, 4]


# ============================================================
# 4. TOKEN + POSITION
# ============================================================

X = token_vectors + position_vectors

print("X shape:", X.shape)
# [4, 4]

# X now contains:
#
# token information
# +
# position information


# ============================================================
# 5. CREATE Q, K, V
# ============================================================

WQ = nn.Linear(n_embd, n_embd, bias=False)
WK = nn.Linear(n_embd, n_embd, bias=False)
WV = nn.Linear(n_embd, n_embd, bias=False)

Q = WQ(X)
K = WK(X)
V = WV(X)

print("Q shape:", Q.shape)
print("K shape:", K.shape)
print("V shape:", V.shape)

# All are:
#
# [4, 4]
#
# 4 tokens × 4-dimensional Q/K/V


# ============================================================
# 6. Q × K
# ============================================================

scores = Q @ K.T

print("Score matrix:")
print(scores)


# ============================================================
# 7. CAUSAL MASK
# ============================================================

# Prevent each token from looking at future tokens.

mask = torch.tril(torch.ones(block_size, block_size))

scores = scores.masked_fill(mask == 0, float("-inf"))

print("Causal scores:")
print(scores)


# ============================================================
# 8. SOFTMAX
# ============================================================

attention_weights = F.softmax(scores, dim=-1)

print("Attention weights:")
print(attention_weights)


# ============================================================
# 9. WEIGHTED SUM OF V
# ============================================================

attention_output = attention_weights @ V

print("Attention output shape:")
print(attention_output.shape)

# [4, 4]
#
# One context-aware output vector
# for each token.
```

> **Note (added):** step 6 above (`scores = Q @ K.T`) is missing the `1/sqrt(d_k)` scaling
> that real implementations apply before the causal mask/softmax — this is called out
> honestly in section 25 below ("What We Have NOT Covered Yet", item 8), so it's a known
> gap, not an oversight to worry about yet. For reference, the actual `mini_llm.py` does
> it as: `att = (q @ k.transpose(-2, -1)) / math.sqrt(self.head_size)` — i.e. insert
> `scores = scores / (n_embd ** 0.5)` right after step 6, before the causal mask. Without
> it, scores grow with the embedding dimension and push softmax into a near-zero-gradient
> regime, which hurts training — worth adding once you revisit this script.

---

## 21. Mapping the Code to the Theory

The code:

```python
X = token_vectors + position_vectors
```

means:

```text
Token embedding + Position embedding → X
```

Then:

```python
Q = WQ(X)
K = WK(X)
V = WV(X)
```

means:

```text
X → Q
X → K
X → V
```

Then:

```python
scores = Q @ K.T
```

means:

```text
Q × K → score matrix
```

Then:

```python
scores = scores.masked_fill(mask == 0, float("-inf"))
```

means:

```text
apply causal masking
```

Then:

```python
attention_weights = F.softmax(scores, dim=-1)
```

means:

```text
scores → attention weights
```

Finally:

```python
attention_output = attention_weights @ V
```

means:

```text
attention weights × V → attention output
```

This one matrix multiplication performs the weighted sums for all tokens simultaneously.

---

## 22. PyTorch Provides Attention APIs Too

For learning, the manual implementation above is useful because it exposes the mathematics.

PyTorch also provides higher-level mechanisms.

A core attention primitive is:

```python
torch.nn.functional.scaled_dot_product_attention()
```

It handles the core scaled dot-product attention operation, including masking and the softmax/weighted-value calculation.

PyTorch also provides:

```python
torch.nn.MultiheadAttention
```

for multi-head attention.

So there are two useful levels:

```text
Educational:
manually calculate Q, K, scores, mask, softmax, V

Production/optimized:
use PyTorch attention primitives/modules
```

The manual version is valuable for understanding what the framework is doing.

---

## 23. Important Distinction: One Head vs Multi-Head

Everything in the basic attention walkthrough above is conceptually:

```text
single-head attention
```

We have not yet gone through the detailed mathematics of:

```text
Multi-Head Attention
```

That is the next natural topic after basic attention.

---

## 24. Phase 4 Mental Model

The simplest complete mental model is:

```text
Token
  ↓
Token embedding
  +
Position embedding
  ↓
X
  ↓
Q, K, V
  ↓
Q asks:
"What am I looking for?"
  ↓
K answers:
"What do I match on?"
  ↓
Q · K
  ↓
Scores
  ↓
Softmax
  ↓
Attention weights
  ↓
Weights × V
  ↓
Context-aware representation
```

One-line version:

> **Q asks, K determines what matches, softmax turns matches into weights, V provides the information, and the weighted V sum becomes the token's context-aware representation.**

---

## 25. What We Have NOT Covered Yet

These are intentionally left for later:

1. Detailed Multi-Head Attention mathematics
2. Why multiple heads are useful
3. Head dimensions
4. Splitting Q/K/V into heads
5. Concatenating head outputs
6. GQA implementation
7. MQA implementation
8. Attention scaling by `1 / sqrt(d_k)` in detail
9. Transformer block structure
10. Residual connections
11. Layer normalization
12. MLP internals
13. Stacking multiple Transformer blocks
14. Next-token prediction head
15. Loss and training
16. KV cache
17. Efficient/optimized attention
18. Flash Attention

These should be learned incrementally rather than all at once.

---

## Final Phase 4 Summary

The complete path we have established is:

```text
Text
 ↓
Tokenizer
 ↓
Token IDs
 ↓
Token embedding
 ↓
Position embedding
 ↓
X
 ↓
Q, K, V
 ↓
Q × K
 ↓
Causal mask
 ↓
Softmax
 ↓
Attention weights
 ↓
Attention weights × V
 ↓
Context-aware attention output
```

And during autoregressive generation:

```text
[a b c d] → e
[b c d e] → f
[c d e f] → g
```

The next major concept is **Multi-Head Attention (MHA)**.

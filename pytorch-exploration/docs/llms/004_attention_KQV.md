# Phase 4 — Attention

> **Note (added):** this phase was later expanded into
> [`005_attention_and_pytorch.md`](005_attention_and_pytorch.md), which covers the same
> ground plus causal-attention variants (MHA/GQA/MQA) and a runnable PyTorch
> implementation. Keeping this file as the original pass through the concepts.

## 1. Starting point
```text
Token embedding + Position embedding
        ↓
        X
        ↓
      Q, K, V
        ↓
    Attention
```
Position information is already inside X before Q/K/V are calculated.

## 2. Q, K, V

For each token X:
```text
Q = X WQ
K = X WK
V = X WV
```
If token dimension = 4 and Q/K/V dimension = 4:
```text
X  = 1×4
WQ = 4×4
WK = 4×4
WV = 4×4
```
Therefore Q, K, V are each 1×4.

Q/K/V dimensions are chosen by the model architecture.

Initially Q/K/V do not inherently mean “query”, “key”, or “value” in a semantic sense. Their useful roles are learned during training.

Simple mental model:
- Q → what am I looking for?
- K → what do I match on?
- V → what information do I provide?

K is not simply “previous token information,” and V is not an unchanged copy of the original token.

## 3. Q-K comparison

For `a b c d`:
```text
        K
        a   b   c   d
Q a     ✓
Q b     ✓   ✓
Q c     ✓   ✓   ✓
Q d     ✓   ✓   ✓   ✓
```
Rows = Q tokens
Columns = K tokens
Each cell = one Q·K comparison.

For example:
```text
Qd·Ka
Qd·Kb
Qd·Kc
Qd·Kd
```
Each dot product produces one scalar:
```text
(1×4) · (4×1) → 1×1
```
The 1×1 is the result, not the Q/K vector.

The matrix does not mean calculations must happen sequentially. Actual implementations calculate the comparisons together using matrix multiplication.

## 4. Why Q/K and not V?

Q and K determine relevance.

Q + K → relevance score → attention weights

V contains the information that gets passed forward using those weights.

## 5. Softmax

Example score row for d:

[2.1, 0.5, 3.2, 1.0]

Softmax:

[0.20, 0.04, 0.55, 0.21]

These are attention weights.

> **Note (added):** in between the raw score and softmax, real implementations (including
> `mini_llm.py`) divide every score by `sqrt(head_size)` first — `att = (q @ k.T) /
> math.sqrt(self.head_size)` in `CausalSelfAttention.forward`. This scaling step isn't
> shown anywhere in this file; it's the "why" is: without it, the dot products grow large
> as the Q/K dimension grows, which pushes softmax into regions with near-zero gradients
> and makes training unstable. Worth folding in once you reach the code-implementation
> pass — see `005_attention_and_pytorch.md` section 25, item 8, where this is explicitly
> listed as deferred.

## 6. Apply weights to V

For d:
```text
Output_d =
  weight_a × Va
+ weight_b × Vb
+ weight_c × Vc
+ weight_d × Vd
```
We do not add weights to V. We multiply each V by its attention weight and then add the resulting vectors.

The result is one new context-aware vector: Output_d.

The same happens for every token:

a → Output_a
b → Output_b
c → Output_c
d → Output_d

## 7. Causal attention

In our decoder-style example, each token can attend to itself + previous tokens:

a → a
b → a,b
c → a,b,c
d → a,b,c,d

Future tokens are not visible.

Therefore:

Output_b = weight_ba×Va + weight_bb×Vb

Vc and Vd are not used for b.

## 8. Context window and generation

If BLOCK_SIZE = 4:

[a b c d] → e
[b c d e] → f
[c d e f] → g

The model generates one token at a time. When the context exceeds 4, the oldest token falls outside the active context.

Dropping an old token means it is no longer directly available to the current attention computation.

## 9. Is attention recalculated?

In the simple generation process:

[a b c d] → e
[b c d e] → f
[c d e f] → g

Attention is calculated again for each new prediction/context.

KV cache is a later optimization that reuses previously calculated K/V information. It has not been studied yet.

## 10. Complete Phase 4 flow

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
              ↓
   context-aware representation
              ↓
            MLP
```

## Doubts clarified during Phase 4

1. X_a, X_b, X_c, X_d are vector representations of the tokens.
2. Embedding size determines the number of numbers in each X vector.
3. Q/K/V dimension is an architectural choice.
4. Q/K/V are calculated independently for each token before token-to-token interaction.
5. Rows are Q tokens; columns are K tokens; each cell is one Q·K comparison.
6. The comparison matrix does not imply sequential calculation.
7. Starting with Qd was only because we were examining d; attention does not literally start from the end.
8. Q/K determine relevance; V provides the information.
9. Q/K/V roles are learned, not manually assigned at initialization.
10. Position embedding must be included before Q/K/V: Token embedding + Position embedding → X → Q/K/V → Attention.
11. Each token's attention weights are applied to the allowed V vectors to create its context-aware output.
12. Causal attention allows self + previous tokens, not future tokens.
13. Fixed context windows can drop old tokens.
14. In the simple generation model, attention is recalculated for each new prediction.
15. KV cache is a later topic.

## One-line mental model

Q asks, K determines what matches, softmax turns matches into weights, V provides the information, and the weighted V sum becomes the token's context-aware representation.

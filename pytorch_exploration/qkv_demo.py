"""
qkv_demo.py — Query / Key / Value attention, isolated and printed step by step.

This is NOT a trainable model — no optimizer, no loss, no training loop, no
MLP, no stacking of blocks. It's the single mechanism from `mini_llm.py`'s
`CausalSelfAttention` (that file, lines ~95-140), pulled out on its own with
a toy sentence and random (untrained) weights, so every intermediate tensor
can be printed and read by hand.

The mental model this demonstrates:
    Every token produces three different vectors from its embedding:
      - Query  ("what am I looking for?")
      - Key    ("what do I contain, that others might look for?")
      - Value  ("what do I actually hand over, if someone attends to me?")
    A token's query is compared against every other token's key (dot product)
    to get a relevance score. Those scores are masked (causal: no looking at
    the future), softmaxed into weights that sum to 1, and used to take a
    weighted average of everyone's values. That weighted average is the
    token's new, "context-aware" representation.

Run:
    uv run python qkv_demo.py
"""

from __future__ import annotations

import math

import torch
import torch.nn.functional as F

torch.manual_seed(1337)
torch.set_printoptions(precision=2, sci_mode=False)

# ----------------------------------------------------------------------------
# 1. A toy sentence, word-level (not char-level) purely so the printed
#    attention matrix is easy to read: rows/columns line up with real words.
# ----------------------------------------------------------------------------

sentence = ["the", "cat", "sat", "on", "the", "mat"]
vocab = sorted(set(sentence))
stoi = {w: i for i, w in enumerate(vocab)}
ids = torch.tensor([stoi[w] for w in sentence])  # shape (T,)
T = len(sentence)
print(f"tokens : {sentence}")
print(f"ids    : {ids.tolist()}\n")

# ----------------------------------------------------------------------------
# 2. Embed each token. n_embd is tiny (8) purely so printed vectors fit on
#    one line — real models use hundreds/thousands of dims, same idea.
# ----------------------------------------------------------------------------

n_embd = 8
token_emb = torch.nn.Embedding(len(vocab), n_embd)
pos_emb = torch.nn.Embedding(T, n_embd)

x = token_emb(ids) + pos_emb(torch.arange(T))  # (T, n_embd) — no batch dim, one sentence
print(f"embeddings x, shape {tuple(x.shape)}  (T={T} tokens x n_embd={n_embd})\n")

# ----------------------------------------------------------------------------
# 3. Project x into Query, Key, Value with three separate learned matrices.
#    In `mini_llm.py` these three are fused into one `qkv_proj` Linear for
#    efficiency; here they're kept as three separate Linears so it's obvious
#    Q, K, V are just three different views of the same input x, nothing more.
# ----------------------------------------------------------------------------

head_size = n_embd  # single head, so head_size == n_embd here (no splitting)

W_q = torch.nn.Linear(n_embd, head_size, bias=False)
W_k = torch.nn.Linear(n_embd, head_size, bias=False)
W_v = torch.nn.Linear(n_embd, head_size, bias=False)

Q = W_q(x)  # (T, head_size) — "what each token is looking for"
K = W_k(x)  # (T, head_size) — "what each token offers, to be matched against"
V = W_v(x)  # (T, head_size) — "what each token actually passes along"

print(f"Q shape {tuple(Q.shape)}, K shape {tuple(K.shape)}, V shape {tuple(V.shape)}\n")

# ----------------------------------------------------------------------------
# 4. Raw attention scores: every query dotted against every key.
#    scores[i, j] = how much token i's query matches token j's key.
#    Scaled by sqrt(head_size) purely to stop the dot products (and therefore
#    the softmax) from exploding as head_size grows — same reason GPT-2 does it.
# ----------------------------------------------------------------------------

raw_scores = Q @ K.transpose(-2, -1) / math.sqrt(head_size)  # (T, T)
print("raw attention scores (row = query token, col = key token):")
print(raw_scores, "\n")

# ----------------------------------------------------------------------------
# 5. Causal mask: token i is only allowed to see keys j <= i (itself and the
#    past). Future positions get -inf so softmax turns them into exactly 0.
# ----------------------------------------------------------------------------

causal_mask = torch.tril(torch.ones(T, T, dtype=torch.bool))
masked_scores = raw_scores.masked_fill(~causal_mask, float("-inf"))
print("scores after causal mask (upper triangle = -inf = 'not allowed to look ahead'):")
print(masked_scores, "\n")

# ----------------------------------------------------------------------------
# 6. Softmax turns each row into a probability distribution over "how much
#    attention this token pays to every token up to and including itself."
# ----------------------------------------------------------------------------

attn_weights = F.softmax(masked_scores, dim=-1)  # (T, T), each row sums to 1
print("attention weights (each row sums to 1.0):")
print(attn_weights, "\n")

for i, tok in enumerate(sentence):
    # Label by "word@position", not just word — "the" appears at both
    # position 0 and 4, so keying a dict by word text alone would silently
    # drop one of the two weights.
    weights_for_i = {
        f"{sentence[j]}@{j}": round(attn_weights[i, j].item(), 2) for j in range(i + 1)
    }
    print(f"  '{tok}' (position {i}) attends to: {weights_for_i}")
print()

# ----------------------------------------------------------------------------
# 7. Final output: for each token, take the weighted average of every
#    (allowed) token's Value vector, weighted by the attention weights above.
#    This is the "context-aware" version of that token's representation.
# ----------------------------------------------------------------------------

out = attn_weights @ V  # (T, T) @ (T, head_size) -> (T, head_size)
print(f"output (context-aware token representations), shape {tuple(out.shape)}:")
print(out)

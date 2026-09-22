"""
mini_llm.py — the smallest model that is still "an LLM", not a toy simplification of one.

Every stage a real LLM pretraining run has, present here at the smallest scale that
still exercises it for real:

    raw text
      -> tokenizer                          (char-level: build vocab, encode/decode)
      -> dataset of (input, target) windows (next-token prediction, shifted by one)
      -> embeddings                          (token embedding + learned positional embedding)
      -> N transformer blocks                (causal self-attention + MLP, residual + LayerNorm)
      -> LM head                             (projects back to vocab logits; weight-tied to
                                               the token embedding, exactly like GPT-2)
      -> cross-entropy loss over the vocab   (the *only* training signal — next-token prediction)
      -> AdamW + backprop                    (the only optimizer real LLM pretraining uses)
      -> autoregressive sampling             (generate one token at a time, feed it back in)

Nothing here is architecturally different from GPT-2 — only the sizes are tiny
(~110K params, ~65-char vocab, 4-layer, 64-dim, 4-head, 64-token context) so the
whole thing trains in a few seconds on a CPU and every tensor shape is easy to
print and inspect by hand.

Run:
    uv run python mini_llm.py
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

# Fix the RNG seed so weight init, batch sampling, and generation sampling
# are identical on every run — reproducible results instead of new random
# numbers each time. The value itself is arbitrary.
torch.manual_seed(1337)

# ----------------------------------------------------------------------------
# 1. Data — the only "corpus" a real LLM pretraining run also starts from: raw text.
# ----------------------------------------------------------------------------

# Small inline corpus (public-domain Coriolanus opening, repeated) so this
# file has zero external data dependency. Swap this for open(...).read() on
# any text file and everything below is unchanged — that substitution is the
# entire difference between this and pretraining GPT-2 on a web-scale corpus.
# It's repeated a few times purely so the 90/10 train/val split still leaves
# val_data longer than one context window (BLOCK_SIZE) — a real corpus would
# be long enough that this was never a concern to begin with.
_PASSAGE = """
first citizen: before we proceed any further, hear me speak.
all: speak, speak.
first citizen: you are all resolved rather to die than to famish?
all: resolved. resolved.
first citizen: first, you know caius marcius is chief enemy to the people.
all: we know't, we know't.
first citizen: let us kill him, and we'll have corn at our own price.
is't a verdict?
all: no more talking on't; let it be done: away, away!
second citizen: one word, good citizens.
first citizen: we are accounted poor citizens, the patricians good.
what authority surfeits on would relieve us: if they
would yield us but the superfluity, while it were
wholesome, we might guess they relieved us humanely;
but they think we are too dear: the leanness that
afflicts us, the object of our misery, is as an
inventory to particularise their abundance; our
sufferance is a gain to them. let us revenge this with
our pikes, ere we become rakes: for the gods know i
speak this in hunger for bread, not in thirst for revenge.
""".strip()
TEXT = (_PASSAGE + "\n\n") * 6


class CharTokenizer:
    """Character-level tokenizer: every distinct character is one token id.

    Real LLMs use a subword tokenizer (BPE) so the vocabulary is ~50K "word
    pieces" instead of ~65 characters. That is purely an efficiency choice
    (fewer tokens per sentence -> less compute per unit of text) — it changes
    nothing about *how* training works, which is why the smallest honest LLM
    can skip it entirely and tokenize character-by-character instead.
    """

    def __init__(self, text: str):
        chars = sorted(set(text))
        self.stoi = {ch: i for i, ch in enumerate(chars)}
        self.itos = {i: ch for i, ch in enumerate(chars)}
        self.vocab_size = len(chars)

    def encode(self, s: str) -> list[int]:
        return [self.stoi[c] for c in s]

    def decode(self, ids: list[int]) -> str:
        return "".join(self.itos[i] for i in ids)


# ----------------------------------------------------------------------------
# 2. Model config — same knobs GPT-2's config has, just tiny.
# ----------------------------------------------------------------------------

BLOCK_SIZE = 64   # context length: how many past tokens attention can look at
N_EMBD = 64       # embedding / residual-stream width
N_HEAD = 4        # attention heads (head_size = N_EMBD // N_HEAD = 16)
N_LAYER = 4       # transformer blocks stacked
DROPOUT = 0.0


class CausalSelfAttention(nn.Module):
    """Multi-head causal self-attention, written out explicitly rather than
    calling a fused kernel, so every step is visible:
      1. project x -> queries, keys, values
      2. split into heads
      3. scaled dot-product attention scores: q @ k^T / sqrt(head_size)
      4. causal mask: a token may only attend to itself and earlier tokens
      5. softmax over the (masked) scores -> attention weights
      6. weighted sum of values
      7. merge heads back, project out
    This is the exact mechanism GPT-2/GPT-3 use — only the tensor sizes differ.
    """

    def __init__(self, n_embd: int, n_head: int, block_size: int):
        super().__init__()
        assert n_embd % n_head == 0
        self.n_head = n_head
        self.head_size = n_embd // n_head

        self.qkv_proj = nn.Linear(n_embd, 3 * n_embd)
        self.out_proj = nn.Linear(n_embd, n_embd)
        self.dropout = nn.Dropout(DROPOUT)

        # Causal mask: True where attention is allowed. Registered as a
        # buffer (not a parameter) since it's fixed, not learned.
        mask = torch.tril(torch.ones(block_size, block_size, dtype=torch.bool))
        self.register_buffer("causal_mask", mask)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape  # batch, time (sequence length), channels (n_embd)

        qkv = self.qkv_proj(x)                      # (B, T, 3*C)
        q, k, v = qkv.split(C, dim=-1)               # each (B, T, C)

        # split into heads: (B, T, n_head, head_size) -> (B, n_head, T, head_size)
        q = q.view(B, T, self.n_head, self.head_size).transpose(1, 2)
        k = k.view(B, T, self.n_head, self.head_size).transpose(1, 2)
        v = v.view(B, T, self.n_head, self.head_size).transpose(1, 2)

        # scaled dot-product attention scores
        att = (q @ k.transpose(-2, -1)) / math.sqrt(self.head_size)  # (B, nh, T, T)
        att = att.masked_fill(~self.causal_mask[:T, :T], float("-inf"))
        att = F.softmax(att, dim=-1)
        att = self.dropout(att)

        out = att @ v                                # (B, nh, T, head_size)
        out = out.transpose(1, 2).contiguous().view(B, T, C)  # merge heads back
        return self.out_proj(out)


class MLP(nn.Module):
    """The feed-forward sublayer: expand 4x, GELU, project back down. Same
    ratio GPT-2 uses; this is where most of a transformer block's raw
    parameter count and compute goes at any scale."""

    def __init__(self, n_embd: int):
        super().__init__()
        self.fc_in = nn.Linear(n_embd, 4 * n_embd)
        self.fc_out = nn.Linear(4 * n_embd, n_embd)
        self.dropout = nn.Dropout(DROPOUT)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.gelu(self.fc_in(x))
        x = self.fc_out(x)
        return self.dropout(x)


class Block(nn.Module):
    """One transformer block: pre-norm residual attention, then pre-norm
    residual MLP. `x = x + sublayer(norm(x))` twice — this residual +
    pre-LayerNorm pattern is what makes deep transformers trainable at all."""

    def __init__(self, n_embd: int, n_head: int, block_size: int):
        super().__init__()
        self.ln1 = nn.LayerNorm(n_embd)
        self.attn = CausalSelfAttention(n_embd, n_head, block_size)
        self.ln2 = nn.LayerNorm(n_embd)
        self.mlp = MLP(n_embd)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.ln1(x))
        x = x + self.mlp(self.ln2(x))
        return x


class MiniGPT(nn.Module):
    """The full model: token embedding + positional embedding -> N blocks ->
    final norm -> LM head. Structurally identical to GPT-2; only vocab_size,
    n_embd, n_head, n_layer, block_size are smaller."""

    def __init__(self, vocab_size: int, n_embd: int, n_head: int, n_layer: int, block_size: int):
        super().__init__()
        self.block_size = block_size

        self.token_emb = nn.Embedding(vocab_size, n_embd)
        self.pos_emb = nn.Embedding(block_size, n_embd)
        self.blocks = nn.ModuleList(
            [Block(n_embd, n_head, block_size) for _ in range(n_layer)]
        )
        self.ln_f = nn.LayerNorm(n_embd)
        self.lm_head = nn.Linear(n_embd, vocab_size, bias=False)

        # Weight tying: the LM head reuses the token embedding matrix instead
        # of learning a second, separate (vocab_size x n_embd) matrix. GPT-2
        # does this too — it roughly halves the embedding-related parameter
        # count with no measured loss in quality.
        self.lm_head.weight = self.token_emb.weight

        self.apply(self._init_weights)

    @staticmethod
    def _init_weights(module: nn.Module):
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, idx: torch.Tensor, targets: torch.Tensor | None = None):
        B, T = idx.shape
        assert T <= self.block_size, "sequence longer than the model's context window"

        positions = torch.arange(T, device=idx.device)
        x = self.token_emb(idx) + self.pos_emb(positions)  # (B, T, n_embd)

        for block in self.blocks:
            x = block(x)
        x = self.ln_f(x)
        logits = self.lm_head(x)  # (B, T, vocab_size)

        loss = None
        if targets is not None:
            # Next-token prediction: flatten (B, T, vocab) / (B, T) and score
            # every position's prediction against the *next* character. This
            # single loss is the entire training objective of pretraining,
            # at any model scale.
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1))
        return logits, loss

    @torch.no_grad()
    def generate(self, idx: torch.Tensor, max_new_tokens: int, temperature: float = 1.0) -> torch.Tensor:
        """Autoregressive sampling: predict the next token, append it, repeat.
        Identical procedure to how GPT-3/4-style models generate text."""
        self.eval()
        for _ in range(max_new_tokens):
            idx_cond = idx[:, -self.block_size:]        # crop to context window
            logits, _ = self(idx_cond)
            logits = logits[:, -1, :] / temperature      # only need the last position
            probs = F.softmax(logits, dim=-1)
            next_id = torch.multinomial(probs, num_samples=1)
            idx = torch.cat([idx, next_id], dim=1)
        self.train()
        return idx


# ----------------------------------------------------------------------------
# 3. Batching — random fixed-length windows, input shifted by one from target.
# ----------------------------------------------------------------------------

def get_batch(data: torch.Tensor, block_size: int, batch_size: int) -> tuple[torch.Tensor, torch.Tensor]:
    max_start = len(data) - block_size - 1
    starts = torch.randint(0, max_start, (batch_size,))
    x = torch.stack([data[s : s + block_size] for s in starts])
    y = torch.stack([data[s + 1 : s + block_size + 1] for s in starts])
    return x, y


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"

    tok = CharTokenizer(TEXT)
    data = torch.tensor(tok.encode(TEXT), dtype=torch.long)

    n = int(0.9 * len(data))
    train_data, val_data = data[:n], data[n:]

    model = MiniGPT(
        vocab_size=tok.vocab_size,
        n_embd=N_EMBD,
        n_head=N_HEAD,
        n_layer=N_LAYER,
        block_size=BLOCK_SIZE,
    ).to(device)

    n_params = sum(p.numel() for p in model.parameters())
    print(f"vocab_size={tok.vocab_size}  params={n_params:,}  device={device}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)

    batch_size = 16
    max_steps = 500
    eval_every = 100

    for step in range(1, max_steps + 1):
        xb, yb = get_batch(train_data, BLOCK_SIZE, batch_size)
        xb, yb = xb.to(device), yb.to(device)

        _, loss = model(xb, yb)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()

        if step % eval_every == 0 or step == 1:
            with torch.no_grad():
                xv, yv = get_batch(val_data, BLOCK_SIZE, batch_size)
                xv, yv = xv.to(device), yv.to(device)
                _, val_loss = model(xv, yv)
            print(f"step {step:4d}  train_loss {loss.item():.4f}  val_loss {val_loss.item():.4f}")

    print("\n--- sample generation ---")
    prompt = "first citizen:"
    idx = torch.tensor([tok.encode(prompt)], dtype=torch.long, device=device)
    out = model.generate(idx, max_new_tokens=200, temperature=0.8)
    print(tok.decode(out[0].tolist()))


if __name__ == "__main__":
    main()

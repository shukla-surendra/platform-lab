# Attention, Encoder and Decoder — Study Notes

![Attention Is All You Need (Vaswani et al., 2017) — summary poster](attention_is_what%20you_need.png)

> **Note (added):** this poster is the reference sheet for this whole file. Panel 1
> (Overall Architecture) is section 17 below, side by side. Panel 2 (Scaled
> Dot-Product Attention) is the exact formula in section 8. Panel 3 (Intuition with an
> Example) is the "I love dogs" walkthrough in sections 6–10. Panel 6 (Multi-Head
> Attention) is section 14. Panel 7 (Positional Encoding) is section 15 — note the poster
> shows the *original paper's* fixed sinusoidal formula, while `mini_llm.py` (and this
> doc's Phase 3 notes) use the **learned** position-embedding-table approach the poster's
> own sidebar calls out ("Later models, e.g. GPT, often use learned position embeddings
> instead of sinusoidal ones"). Panel 8 (Decoder Masking) is section 13's causal-mask
> diagram, same idea. Panel 9 (Encoder vs Decoder vs Both) is directly relevant to section
> 5 below — see the added note there about cross-attention, which this poster's table
> mentions but this doc hadn't covered yet.

## 1. Big Picture

A Transformer is an architecture built around **attention**.

There are three common ways Transformer models are organized:

```text
Encoder-only       → BERT
Decoder-only       → GPT
Encoder-Decoder    → Original Transformer / T5-style models
```

The important distinction is what the Transformer stack is used for and how attention is allowed to operate.

---

## 2. Encoder vs Decoder

### Encoder — understand / represent the input

The encoder takes an input sequence and transforms it into **context-aware numerical representations**.

Example:

```text
"I love dogs"
      ↓
   Encoder
      ↓
┌─────────────────┐
│ representation  │
│ of "I"          │
│                 │
│ representation  │
│ of "love"       │
│                 │
│ representation  │
│ of "dogs"       │
└─────────────────┘
```

A representation is usually a vector.

For example:

```text
"I"     → [0.2, -0.7, 0.4, ...]
"love"  → [0.8,  0.1, -0.3, ...]
"dogs"  → [-0.2, 0.9, 0.5, ...]
```

These are not simply the original embeddings. The encoder's attention allows each token representation to incorporate information from other tokens.

For example, the representation of `"love"` can use information from:

```text
"I" + "love" + "dogs"
```

#### Encoder attention

Encoder self-attention is normally **bidirectional**:

```text
        I    love    dogs

I       ✓     ✓       ✓
love    ✓     ✓       ✓
dogs    ✓     ✓       ✓
```

Every token can attend to every other token.

So the simple mental model is:

> **Encoder = take the input and build rich, context-aware representations of it.**

It does not necessarily mean "correct the input."

---

## 3. Decoder — generate / predict output

A decoder is used to generate an output sequence.

For a GPT-style decoder:

```text
"The cat is"
      ↓
   Decoder
      ↓
predict next token
      ↓
"sleeping"
```

Then the new sequence becomes:

```text
"The cat is sleeping"
              ↓
           Decoder
              ↓
         predict next token
              ↓
             "on"
```

So the simple mental model is:

> **Decoder = use the available context to generate/predict the next output.**

For GPT, the decoder uses **causal self-attention**.

Example:

```text
        The   cat   is   sleeping

The      ✓
cat      ✓     ✓
is       ✓     ✓    ✓
sleeping ✓     ✓    ✓      ✓
```

A token can see itself and previous tokens, but not future tokens.

---

## 4. Why is GPT called Decoder-Only?

GPT does not have a separate encoder.

Its architecture is roughly:

```text
Token IDs
   ↓
Token Embedding + Position
   ↓
Transformer Block
   ↓
Transformer Block
   ↓
Transformer Block
   ↓
...
   ↓
Final LayerNorm
   ↓
LM Head
   ↓
Logits
   ↓
Next-token prediction
```

The Transformer blocks in this stack use **causal self-attention**, so this stack is called the **decoder** side.

Therefore:

```text
GPT = Decoder-only Transformer
```

This connects directly to the phases we studied earlier.

Everything from Q/K/V through Multi-Head Attention, Transformer Blocks, and stacking blocks was essentially building the **decoder side** of a GPT-style model.

---

## 5. Encoder-Decoder Transformer

Some Transformer architectures use both.

```text
Input
  ↓
Encoder
  ↓
Contextual representations
  ↓
Decoder
  ↓
Output
```

A classic example is translation.

```text
"I love dogs"
      ↓
   Encoder
      ↓
understands / represents input
      ↓
   Decoder
      ↓
"J'aime les chiens"
```

The encoder processes the source sentence.

The decoder generates the target sentence.

So:

```text
Encoder → understand/represent source
Decoder → generate target
```

> **Note (added) — the missing piece: cross-attention.** The attached poster's panel 9
> table lists the encoder-decoder decoder as: "Decoder: causal (+ cross-attention)" — and
> that `+ cross-attention` is new, not yet covered anywhere in this doc series. In a
> GPT-style decoder-only block, self-attention's Q, K, and V *all* come from the decoder's
> own sequence (section 12 below). In an encoder-decoder model's decoder, each block has
> a **second** attention sub-layer where the queries (Q) come from the decoder's own
> sequence-so-far, but the keys and values (K, V) come from the **encoder's output** —
> that's how the decoder "looks at" the source sentence while generating the target one.
> This is exactly why `mini_llm.py` (decoder-only, no encoder at all) has no such
> sub-layer: `CausalSelfAttention` only ever has one attention calculation per block, all
> self-attention. Worth its own phase later if you build an encoder-decoder model.

---

## 6. The Attention Mechanism

The central idea of attention is:

> **Each token looks at other relevant tokens and creates a weighted combination of their information.**

Example:

```text
"I love dogs"
```

The token `"love"` may need information from `"I"` and `"dogs"`.

Conceptually:

```text
       I       love       dogs
       ↓         ↓          ↓
       └─────────┼──────────┘
                 ↓
          Self-Attention
                 ↓
        new representation
             of "love"
```

---

## 7. Where Q, K and V Come From

Before attention, we have token + position information:

```text
Token embedding
       +
Position embedding
       ↓
       X
```

Then X is projected into Q, K and V:

```text
X → WQ → Q
X → WK → K
X → WV → V
```

The intuition is:

```text
Q = What am I looking for?

K = What information do I contain / what can
    I be matched on?

V = What information should I provide?
```

These are learned transformations. Q, K and V are not manually assigned meanings; the model learns useful projections during training.

---

## 8. Attention Calculation

The core scaled dot-product attention is:

```text
Attention(Q,K,V)
=
softmax(QKᵀ / √dₖ)V
```

The process is easier to remember as:

```text
Q + K
 ↓
Compare
 ↓
Attention scores
 ↓
Softmax
 ↓
Attention weights
 ↓
Weighted sum of V
 ↓
Output representation
```

### Step 1 — Compare Q and K

For every query, compare it with the available keys.

Example:

```text
Q_love · K_I
Q_love · K_love
Q_love · K_dogs
```

Each comparison produces one scalar score.

---

## 9. Softmax Converts Scores into Weights

Suppose the scores for `"love"` are:

```text
[2.0, 3.0, 1.0]
```

Softmax converts them into weights whose sum is 1:

```text
[0.24, 0.67, 0.09]
```

The interpretation is approximately:

```text
24% → information from I
67% → information from love
 9% → information from dogs
```

The exact numbers depend on the actual scores.

---

## 10. Weighted Sum of V

Now use those weights on the value vectors:

```text
Output_love =
    0.24 × V_I
  + 0.67 × V_love
  + 0.09 × V_dogs
```

The result is a new, context-aware representation for `"love"`.

This is the core idea of attention.

---

## 11. Why Q and K Are Compared, Not V

Q and K determine **which information is relevant**.

V contains the **information that gets passed forward**.

```text
Q × K
 ↓
How relevant?
 ↓
Weights
 ↓
Weights × V
 ↓
Information
```

A simple mental model:

```text
Q → "What am I looking for?"
K → "How relevant am I?"
V → "Here is the information I provide."
```

---

## 12. Self-Attention

When Q, K and V all come from the same sequence:

```text
X
 ↓
Q K V
 ↓
Attention
 ↓
Output
```

this is called **self-attention**.

For:

```text
"I love dogs"
```

the Q, K and V for all three tokens come from the same input sequence.

---

## 13. Causal Self-Attention

Decoder-only GPT uses **causal self-attention**.

The model is not allowed to use future tokens when predicting the current token.

For:

```text
I love dogs
```

the visibility pattern is:

```text
        I   love   dogs

I       ✓
love    ✓    ✓
dogs    ✓    ✓      ✓
```

This prevents the model from cheating during next-token prediction.

For example, when predicting:

```text
I love → ?
```

the model cannot already look at `"dogs"`.

---

## 14. Multi-Head Attention

Instead of having one attention mechanism, a Transformer can use multiple heads.

```text
             X
             ↓
     ┌───────┼───────┐
     ↓       ↓       ↓
   Head 1  Head 2   Head 3  ...
     ↓       ↓       ↓
     └───────┼───────┘
             ↓
        Concatenate
             ↓
       Linear projection
             ↓
           Output
```

Each head has different learned projections and can learn different relationships.

For example, one head may learn a useful syntactic relationship while another may learn a different dependency.

These roles are learned; they are not manually assigned.

---

## 15. Position Information

Attention by itself does not inherently know token order.

Therefore the model needs position information.

The simplified flow we studied is:

```text
Token embedding
       +
Position embedding
       ↓
       X
       ↓
    Q K V
       ↓
   Attention
```

This is important:

> **Q, K and V are calculated from X, and X already contains positional information.**

---

## 16. How This Connects to Our Previous Phases

We built the concepts in this order:

```text
Phase 1
Text → Tokens

Phase 2
Tokens → Token IDs

Phase 3
Token IDs → Token Embeddings
              +
           Position

Phase 4–5
X → Q K V → Attention

Phase 6
Attention → Multi-Head Attention

Phase 7
MHA + FFN + LayerNorm + Residual
        ↓
Transformer Block

Phase 8
Block 1 → Block 2 → ... → Block N

Phase 9
Simple QKV attention code
        vs
Complete mini GPT
```

Now we can label the complete stack:

```text
Token + Position
      ↓
Transformer Block
      ↓
Transformer Block
      ↓
...
      ↓
Transformer Block
      ↓
Final LayerNorm
      ↓
LM Head
      ↓
Next-token prediction
```

For GPT:

```text
This is the DECODER.
```

---

## 17. One Picture to Remember Everything

```text
                    TRANSFORMER
                         │
             ┌───────────┴───────────┐
             │                       │
          ENCODER                 DECODER
             │                       │
      Bidirectional             Causal
       attention                attention
             │                       │
      Understand /              Generate /
       represent                 predict
             │                       │
           BERT                    GPT
```

And an encoder-decoder model combines them:

```text
Input
  ↓
ENCODER
  ↓
Contextual representations
  ↓
DECODER
  ↓
Generated output
```

---

## 18. Most Important Mental Model

Do not think:

```text
Encoder = some special preprocessing
Decoder = some special decoding function
```

Instead think:

```text
Encoder
    ↓
build useful representations of the input


Decoder
    ↓
use context to generate an output sequence
```

And for our current GPT learning:

```text
GPT
 ↓
Decoder-only
 ↓
Causal self-attention
 ↓
Transformer Blocks
 ↓
Next-token prediction
```

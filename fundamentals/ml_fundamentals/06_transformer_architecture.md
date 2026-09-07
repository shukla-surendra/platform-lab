# ML Fundamentals, Part 6: The Transformer Architecture

Part 5 ended on two specific, named problems a plain RNN can't escape: it has to process a sequence one step at a time (the **sequential bottleneck**, which blocks GPU parallelism), and even with LSTM gating, information connecting two far-apart words still has to survive every step in between (**long-range dependency decay**). The Transformer, introduced by Vaswani et al. in "Attention Is All You Need" (2017), removes both problems in one mechanism: self-attention.

## Self-Attention, the Core Mechanism, From First Principles

**The problem, precisely restated from Part 5:** how can every position in a sequence directly access every other position's information, in one parallel step, instead of relying on information relayed step-by-step through a chain of hidden states?

**In Plain English first:** imagine you're in a library trying to answer a question. You have a search query in mind. Every book on the shelf has a catalog tag summarizing what it's about. You compare your query against every book's tag, and the better a tag matches what you're looking for, the more you actually read from that book's contents when forming your answer. You don't read every book equally — you weight your attention by how relevant each one's tag is to your query.

That's exactly self-attention, with three names attached to the pieces of this analogy:

- **Query** — what a given word is "looking for" from the rest of the sentence (your search query).
- **Key** — what each word (including itself) "advertises" about its own content, for other words to match against (a book's catalog tag).
- **Value** — the actual content a word contributes if it gets attended to (the book's contents you actually read).

**The mechanism, precisely:** for every word in the sequence, the model computes a Query vector, a Key vector, and a Value vector (each is a learned linear projection of that word's embedding). To compute the new representation for one word, its Query is compared against every word's Key (including its own) via a similarity score — typically a dot product. Those raw scores are passed through a **softmax** function, which turns them into a set of weights that are all positive and sum to 1 — think of softmax as converting "how well does this match" into "what fraction of my attention goes here." The word's new representation is then a weighted sum of every word's Value vector, using those softmax weights.

**A concrete illustrative example, to make this land:** take the sentence *"The trophy didn't fit in the suitcase because it was too big."* Resolving what "it" refers to requires connecting back to either "trophy" or "suitcase" — words that could be arbitrarily far away in a longer sentence. Under self-attention, when the model computes the representation for "it," "it"'s Query vector is compared against the Keys of every other word, including "trophy" and "suitcase." If the model has learned that "too big" more plausibly describes a trophy not fitting than a suitcase being too big for itself, "it"'s Query will match "trophy"'s Key more strongly, so the softmax weight on "trophy" ends up large — most of "it"'s new representation comes directly from "trophy"'s Value, in one single computation, not by information being relayed word-by-word from "trophy" all the way to "it" through every hidden state in between (which is exactly what Part 5 flagged as the failure mode of a plain RNN over long distances).

## Why This Is Parallelizable — the Other Half of "Why It Matters"

The Query/Key/Value computation above depends only on the input sequence as a whole — it never depends on some previous timestep's output the way an RNN's hidden-state update does. That means every word's attention computation can be done **at the same time**, across all positions, spread across a GPU's thousands of cores. This directly removes Part 5's sequential-bottleneck problem: an RNN has to finish step 1 before it can even start step 2; a Transformer layer processes an entire sequence in one parallel pass. This parallelism — not some deeper mathematical superiority — is a large part of why Transformers scale to the massive training runs behind today's large language models in a way RNNs structurally never could, no matter how much hardware you threw at them.

## Multi-Head Attention

**The problem:** a single attention computation, as described above, produces one specific pattern of "what matches what." But language has many simultaneous kinds of relationships in the same sentence at once — subject-verb agreement, pronoun coreference, which adjective modifies which noun — and one shared Query/Key/Value projection can't specialize in all of them simultaneously.

**The mechanism:** run several independent attention computations — called **heads** — in parallel, each with its own learned Query/Key/Value projection matrices. One head might, over training, end up specializing in tracking subject-verb agreement; another might specialize in coreference resolution like the "it" example above; nobody hand-assigns these specializations, they emerge from training. The outputs of all heads are concatenated and passed through one more learned projection to combine them into a single representation per word.

## Positional Encoding — the Piece Attention Alone Is Missing

**The problem, precisely:** self-attention as described treats the input as an unordered set — the similarity computation between two words' Query and Key doesn't inherently know or care whether one came before the other. But "dog bites man" and "man bites dog" use the exact same words and would produce the exact same set of attention scores under plain self-attention, despite meaning something completely different. Order matters, and nothing described so far encodes it.

**The mechanism:** before self-attention ever runs, information about each word's position in the sequence is injected directly into its input representation. The original Transformer paper used fixed sine and cosine functions of each position, at a range of different frequencies, added to each word's embedding. The reason a smooth, mathematically structured signal like this works is that it lets the model infer *relative* distances between positions (via how these sine/cosine values shift predictably from one position to the next), not just each word's raw absolute position number. Many modern models use variants instead — learned positional embeddings, or newer relative-position schemes; **RoPE (Rotary Position Embedding)** is worth knowing by name as the common choice in a lot of current LLMs, encoding position by rotating the Query/Key vectors as a function of position rather than adding a separate positional vector — the mechanism detail matters less here than knowing the term exists and roughly what problem it's solving.

## Residual Connections and Layer Normalization — the Boring But Load-Bearing Plumbing

A real Transformer stacks many attention-plus-feedforward blocks on top of each other — often dozens. Part 4 covered why very deep networks suffer from vanishing gradients (repeatedly multiplying small numbers through the chain rule shrinks the signal toward zero), and Part 5 named residual (skip) connections as the fix architectures like ResNet use. Transformers use exactly the same fix: each attention block and each feedforward block is wrapped in a residual connection, so the gradient has a direct, short path back to earlier layers instead of only the long path through every block's transformation. **Layer normalization** — rescaling the activations flowing between blocks to a stable range — is the other piece of plumbing that keeps a stack this deep trainable. Neither idea is new to this doc; they're the same anti-vanishing-gradient toolkit from Parts 4 and 5, now essential rather than optional at Transformer scale.

## Encoder-Only, Decoder-Only, and Encoder-Decoder — the Three Shapes

Not every Transformer is used the same way, and which of these three shapes a model is changes what it's actually good at:

- **Encoder-only** — every word attends to every other word in the input, including words that come *after* it (full bidirectional attention). This is the right shape when the goal is *understanding* the whole input at once — classification, generating embeddings for search/retrieval. **BERT** is the canonical encoder-only model.
- **Decoder-only** — uses **masked (causal) attention**: a word can only attend to words at or before its own position, never ones that come later. This restriction is what makes autoregressive generation possible — the model produces one token at a time, and at each step it's only allowed to see what it (or the prompt) has already produced, exactly matching how text actually gets generated left-to-right. The **GPT family** is the canonical decoder-only architecture, and this is the shape underlying essentially every modern general-purpose LLM — Part 7 builds directly on this.
- **Encoder-decoder** — combines both: an encoder fully processes the input (bidirectional), then a decoder generates an output, attending back to the encoder's representation as it goes (in addition to attending causally over its own generated output so far). **T5** is the canonical example. This shape is the natural fit for tasks with a clear input-to-output transformation — translation, summarization — where the model needs to fully understand one thing before producing a different thing.

The Hugging Face `transformers` library is the de facto standard implementation covering all three shapes, with pretrained checkpoints for BERT-, GPT-, and T5-family models available directly.

## Designing and Operating From First Principles

1. Am I reaching for a Transformer because the problem genuinely needs long-range context and parallelizable training, or out of habit — would a much simpler model (Part 1-3) actually suffice for this task?
2. Do I actually need bidirectional context (encoder-only), pure left-to-right generation (decoder-only), or a genuine input→output transformation (encoder-decoder) — have I picked the shape that matches the task, or defaulted to whichever one is most popular?
3. If I'm debugging a model that seems to ignore something stated much earlier in a long input, is that a genuine attention/positional-encoding limitation at my context length, or a different problem entirely (truncation, retrieval, prompt structure)?
4. Do I understand why residual connections and layer normalization are load-bearing here, not decorative — could I explain what would break in training without them?
5. When someone says "attention," am I distinguishing self-attention (within one sequence) from cross-attention (a decoder attending to an encoder's output) — do I know which one a given architecture actually uses where?

## Key Takeaways

- Self-attention lets every position directly query every other position's information in one parallel step, using Query/Key/Value vectors and a softmax-weighted combination of Values — this is the direct fix for Part 5's long-range-dependency problem.
- Self-attention's lack of dependence on a previous timestep's output is what makes it parallelizable across a GPU's cores — the direct fix for Part 5's sequential-bottleneck problem.
- Multi-head attention runs several attention computations in parallel with independently learned projections, letting different heads specialize in different kinds of relationships without anyone hand-assigning those specializations.
- Positional encoding (sinusoidal originally, RoPE commonly today) exists because self-attention alone is order-blind — word order has to be injected into the input explicitly.
- Residual connections and layer normalization are the same anti-vanishing-gradient toolkit from Parts 4 and 5, now essential for training a deep stack of attention blocks.
- Encoder-only (BERT, bidirectional, understanding tasks), decoder-only (GPT family, causal, generation — the basis of modern LLMs), and encoder-decoder (T5, both, transformation tasks) are three genuinely different shapes suited to different problems, not three interchangeable options.

## Quick Self-Check

- Walk through, in your own words, what a Query, a Key, and a Value each represent, and why the library-search analogy maps onto them the way it does.
- Why can the "trophy/suitcase" pronoun-resolution example be solved in one attention step, when a plain RNN would have to relay that information through every intervening hidden state?
- Explain precisely why self-attention's parallelizability follows from what it does NOT depend on — what exactly is missing compared to an RNN's step-by-step dependency?
- Why isn't one attention head enough — what does multi-head attention buy you that a single, larger head wouldn't?
- Why does self-attention need positional encoding at all — what specific property of the attention computation makes it "order-blind" without it?
- What specific training problem do residual connections and layer normalization solve in a deep Transformer stack, and where else in this series has that exact problem already appeared?
- Given a new NLP task, how would you decide between an encoder-only, decoder-only, or encoder-decoder model — what property of the task actually drives that choice?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Problem-first framing (the default for "explain the Transformer" or "why not use an RNN" questions):** "RNNs have two structural problems — they can't be parallelized because each step depends on the last one, and information degrades over long distances even with gating. Self-attention fixes both at once by letting every position directly query every other position in one parallel computation, instead of relaying information step by step."
- **Mechanism-first framing (good for demonstrating you understand the actual math, not just the pitch):** "Every word produces a Query, Key, and Value vector. You compare each word's Query against every other word's Key to get similarity scores, softmax those into weights, and take a weighted sum of Values. That's the whole mechanism — everything else, multi-head attention, positional encoding, is built around making that one operation richer or giving it the ordering information it doesn't have natively."
- **Architecture-shape framing (good for questions about choosing or comparing specific models):** "Whether a model is encoder-only, decoder-only, or encoder-decoder isn't an implementation detail — it determines what attention pattern is even allowed. BERT can see the whole input at once because it doesn't need to generate anything; GPT can only see what came before because it generates one token at a time; T5 does both because translation genuinely has two separate stages, understanding and then producing."
- **Lineage/continuity framing (good for showing this isn't an isolated topic):** "A lot of what makes a Transformer trainable isn't new here — residual connections and layer norm are the same fix for vanishing gradients that showed up with ResNet for very deep CNNs. The genuinely new idea is self-attention itself; the rest is the same deep-learning plumbing applied to a new architecture."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **self-attention** (n.) — every position in a sequence computing a weighted combination of all positions' Values, weighted by Query-Key similarity. *"Self-attention lets the model connect 'it' back to 'trophy' in one step."*
- **Query / Key / Value (Q/K/V)** (n. phrases) — the three learned projections behind attention: what a position is looking for, what it advertises, and what it actually contributes if attended to.
- **multi-head attention** (n. phrase) — several independent attention computations run in parallel, each free to specialize in a different kind of relationship.
- **positional encoding** (n. phrase) — information about token order injected into the input, since attention itself is order-blind; sinusoidal (original) or RoPE (common in modern LLMs) are the two most cited approaches.
- **causal / masked attention** (adj. phrase) — attention restricted so a position can only see itself and earlier positions, never later ones; what makes autoregressive, left-to-right generation possible.
- **residual connection** (n. phrase) — a shortcut adding a block's input directly to its output, giving gradients a short path back through a deep stack; the same fix ResNet used for CNNs, now used around every Transformer block.
- **encoder-only / decoder-only / encoder-decoder** (adj. phrases) — the three Transformer shapes, distinguished by which attention pattern (bidirectional, causal, or both) each part uses; BERT, GPT, and T5 respectively.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…relaying information step by step versus every word querying every other word directly"** — a fluent one-line contrast between RNN sequence processing and self-attention.
- **"…the architecture doesn't just describe the model, it describes what attention pattern is even legal"** — a precise way to explain why encoder/decoder shape matters beyond naming conventions.

---

**Previous:** [Part 5: CNNs and RNNs — Architectures for Structure](05_cnns_and_rnns.md) | **Next:** [Part 7: LLM Fundamentals — Tokenization, Fine-Tuning, and Evaluation](07_llm_fundamentals.md)

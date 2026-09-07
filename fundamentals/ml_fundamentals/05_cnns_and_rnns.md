# ML Fundamentals, Part 5: CNNs and RNNs — Architectures for Structure

[Part 4](04_neural_networks_and_backpropagation.md) built a plain feedforward network — every input feature treated as an independent, unordered number, with backpropagation as the general mechanism that trains it. That's a fine starting point, but it quietly throws away something real: an image's pixels aren't independent (a pixel's neighbors matter), and a sentence's words aren't unordered (word order changes meaning). This part covers two architectures built specifically to exploit that structure instead of ignoring it — convolutional networks for spatial structure, recurrent networks for sequential structure — and ends by explaining exactly why the second one hit a wall that [Part 6](06_transformer_architecture.md)'s Transformer was invented to knock down.

## Why a Plain Feedforward Network Is a Bad Fit for Images

**In plain English:** imagine describing a photo to someone by reading out every single pixel's brightness value, left to right, top to bottom, as one long list of numbers with no sense of "these numbers are next to each other in the picture." That's exactly what a feedforward network does with an image once you flatten it into a vector — it sees a list of numbers, not a picture.

**The problem, precisely:** a fully-connected feedforward layer treats every input feature as independent and unordered. Feed it a flattened image and two consequences follow, both bad. First, it has no built-in notion that pixel (10, 10) and pixel (10, 11) are spatially adjacent and probably related — it would have to *learn* that from scratch, for every possible pair of pixels, which is an enormous amount to learn. Second, a network trained to recognize a cat's ear in the top-left corner of an image has learned nothing about recognizing that same ear if it appears in the bottom-right corner instead — there's no **translation invariance**, no built-in assumption that "this pattern means the same thing regardless of where it appears."

**The scale problem, concretely:** a modest 224×224 color photo has 224 × 224 × 3 ≈ 150,000 input numbers. A fully-connected layer with even a modest 1,000 neurons in the next layer would need roughly 150 million weights for that one layer alone (illustrative, order-of-magnitude figure) — before the network has learned anything useful at all. Something has to reduce that parameter count, and it needs to come from a real structural insight about images, not just "make the network smaller and hope."

## The Convolution Operation, Mechanically

**The problem it solves:** detect a local visual pattern — an edge, a corner, a patch of texture — regardless of where in the image it appears, using far fewer parameters than a fully-connected layer would need to learn the same thing independently at every location.

**In Plain English:** picture a small rubber stamp — say, a 3×3 grid — that you press against every possible position on a sheet of paper, one position at a time, sliding it one step to the right (then down a row) each time. At every position, the stamp doesn't just mark "yes/no" — it computes a weighted score for how well the pattern under it matches a specific shape the stamp was designed to detect. Critically, it's the *same* stamp used at every single position — you're not carving a new stamp for the top-left corner and a different one for the bottom-right.

**The mechanism, precisely:** a convolutional layer applies a small learnable filter (also called a kernel — e.g., 3×3 or 5×5 weights) that slides across the input, computing a weighted sum of the pixels it currently overlaps at each position, producing one output value per position (collectively, a *feature map*). The filter's weights are **shared** across every position — this is the single mechanical idea that solves both problems named above at once: because the same small set of weights is reused everywhere, the parameter count for a filter depends only on its size (e.g., 3×3×3 channels ≈ 27 weights, illustrative), not on the size of the image; and because the identical filter is applied at every position, a pattern it learns to detect in one corner is automatically detected anywhere else it appears — translation invariance falls out of weight sharing for free, not because anyone had to teach it separately for each location.

A convolutional layer typically learns many filters in parallel (e.g., 32 or 64), each specializing in a different local pattern, producing a stack of feature maps rather than just one.

## Pooling and the Hierarchy of Features

**The problem:** even after convolution, feature maps are still large, and a small shift in exactly where a pattern appears (one pixel left or right) shouldn't matter much for the final decision — some further tolerance for exact position, and some further parameter reduction, is worth having.

**The mechanism:** a pooling layer (most commonly **max-pooling**) slides a small window across each feature map and keeps only the strongest value in that window, discarding the rest — throwing away the exact position of the strongest signal within the window while keeping the fact that it fired at all. This shrinks the feature map (fewer numbers to process downstream), adds a further degree of translation tolerance on top of what convolution already provides, and acts as a mild, built-in form of regularization (in the sense [Part 1](01_bias_variance_and_the_ml_workflow.md) covered — less information surviving to later layers means less opportunity to memorize noise).

**Why the resulting hierarchy matters:** stack several convolution-then-pooling blocks, and something genuinely useful emerges without anyone hand-designing it. Early layers, working directly on raw pixels, tend to learn simple, generic patterns — edges, color blobs, short line segments. Middle layers combine those simple patterns into more complex ones — corners, textures, small parts of objects (an eye, a wheel). Later layers combine *those* into whole-object-level concepts (a face, a car). This is a **learned hierarchy of features**, not something a human engineer specified layer by layer — it's an emergent consequence of stacking the same simple mechanism (convolve, then pool) repeatedly and letting gradient descent (from [Part 4](04_neural_networks_and_backpropagation.md)) find the filter weights that minimize error.

## Why This Matters in Practice

The architecture lineage is worth knowing by name, since it maps directly onto ideas already covered: LeNet (1990s, the original small-scale proof of concept) → AlexNet (2012, the moment deep CNNs decisively beat hand-engineered computer-vision features, enabled by GPUs) → ResNet (2015), whose specific contribution was **residual/skip connections** — a direct callback to [Part 4](04_neural_networks_and_backpropagation.md#vanishing-and-exploding-gradients-why-depth-isnt-free)'s vanishing-gradient problem: a skip connection lets the gradient flow backward through a shortcut path that bypasses a block of layers entirely, which is precisely what made training networks with over a hundred layers actually work, rather than degrading as depth increased.

CNNs remain the genuinely right default today for image classification, object detection, and segmentation, and see real use on other data that has a grid-like local structure (spectrograms for audio, for instance). Worth knowing this exists without a deep dive here: Vision Transformers (ViT) have since applied [Part 6](06_transformer_architecture.md)'s attention mechanism to images too, and are competitive with or exceed CNNs at large data/compute scale — but CNNs' built-in translation invariance and strong performance at smaller data scales keep them a real, current choice, not a purely historical one.

---

## Why a Plain Feedforward Network (or a CNN) Is a Bad Fit for Sequences

**In plain English:** a sentence isn't just a bag of words — "the dog bit the man" and "the man bit the dog" contain the exact same words, and mean opposite things. Order carries meaning. A feedforward network's fixed-size input vector has no natural place to put "this word came before that one," and sentences (or a stock's price history, or an audio waveform) don't even arrive at a fixed length the way an image's pixel grid does.

**The problem, precisely:** language, time-series, and audio all share two properties a feedforward layer or a spatially-local convolution don't naturally capture: **order matters** (swapping two elements changes the meaning), and **length varies** (a five-word sentence and a fifty-word sentence both need to be handled by the same model). Something is needed that can consume a sequence one element at a time, of whatever length it happens to be, while keeping track of what it's already seen.

## The RNN Mechanism — A Hidden State Carried Forward Through Time

**In Plain English:** think of reading a sentence one word at a time while keeping a running mental summary of what it's been about so far — not re-reading the whole sentence from the beginning every time a new word arrives, just updating your existing summary with the new information.

**The mechanism, precisely:** a recurrent neural network (RNN) maintains a **hidden state** — a vector summarizing everything it has processed so far. At each timestep, it takes two inputs: the current element of the sequence (e.g., the current word's embedding) and its own hidden state *from the previous timestep* — and combines them (through the same kind of weighted-sum-plus-nonlinearity as [Part 4](04_neural_networks_and_backpropagation.md)'s single neuron) to produce a new hidden state, and optionally an output at that step. The crucial structural choice, worth explicitly naming as the sequence-domain analog of CNN weight sharing: the **same weights are reused at every timestep** — the network doesn't learn a separate set of weights for word 1, word 2, word 3, and so on; it learns one update rule and applies it repeatedly, which is exactly why it can handle sequences of any length with a fixed number of parameters.

## Why Plain RNNs Struggle With Long Sequences — Vanishing Gradients Over Time

**The problem, precisely:** training an RNN means backpropagating the error backward through every timestep the sequence contains — mathematically, this is the exact same repeated-multiplication problem [Part 4](04_neural_networks_and_backpropagation.md#vanishing-and-exploding-gradients-why-depth-isnt-free) already covered for very deep feedforward networks, except here "depth" means "how many timesteps back." Multiply enough small gradient terms together across many timesteps and the signal vanishes — a plain RNN effectively **forgets** information from many steps earlier, not because it chose to, but because the gradient carrying "that earlier information mattered" shrinks toward zero before it can update the weights responsible for retaining it.

**The mitigation, at the mechanism level:** LSTMs (Long Short-Term Memory networks), and the simpler GRU (Gated Recurrent Unit), address this with **gates** — small, learned, per-step decisions about how much of the existing memory to keep versus how much new information to let in. Conceptually, rather than the hidden state being overwritten wholesale at every step (as in a plain RNN), a gate learns something closer to "for this specific input, keep 90% of what I already knew and blend in 10% of this new word" — a *forget gate* controlling what to discard, an *input gate* controlling what new information to add, an *output gate* controlling what to expose as this step's output. This doesn't eliminate the vanishing-gradient problem, but it gives the network an explicit, learnable mechanism for preserving important information across many steps instead of leaving retention to chance.

## The Fundamental Limitation Transformers Were Invented to Fix

Even with LSTM/GRU gating, two specific, named problems remain — and both matter enough that an entirely new architecture ([Part 6](06_transformer_architecture.md)) was built specifically to remove them:

- **The sequential bottleneck.** An RNN must process timestep 1, then timestep 2, then timestep 3 — in strict order, because each step's computation genuinely depends on the previous step's hidden state. That dependency chain cannot be parallelized across a GPU's thousands of cores the way, say, a convolution's independent per-position computations can — training on long sequences is slow specifically because of this forced sequentiality, not because of raw compute cost.
- **Long-range dependencies remain hard even with gating.** Connecting a word at position 1 to one at position 1,000 still requires information to flow, one step at a time, through every intermediate hidden state. Gates make that flow more deliberate, but they mitigate degradation over long distances — they don't eliminate it. A direct, one-step connection between any two positions in a sequence, regardless of distance, is a genuinely different capability than "pass a summary through a thousand intermediate steps and hope it survives."

Part 6 covers the architecture — the Transformer — that was designed specifically to remove both of these limitations at once: full parallelism across a sequence during training, and a direct path between any two positions regardless of distance, via self-attention rather than a recurrent hidden state.

## Designing and Operating From First Principles

1. Does my data have spatial structure (nearby elements are related, and the same pattern can appear anywhere), sequential structure (order carries meaning), or neither — and have I picked an architecture that actually matches which one it is, rather than defaulting to whatever I already know?
2. If I'm using a CNN, do I understand *why* weight sharing gives me both parameter efficiency and translation invariance at once, or am I treating "convolution" as a black-box layer type to stack?
3. Am I about to reach for an RNN/LSTM for a new sequence problem in 2025-2026 without first asking whether a Transformer-based approach (Part 6) would simply do better, given that RNNs are now the exception rather than the default for most sequence tasks?
4. If a very deep CNN is failing to train well, have I checked whether residual/skip connections are present — the same vanishing-gradient problem from Part 4 doesn't go away just because the architecture changed?
5. Can I explain specifically *why* an RNN cannot be parallelized across timesteps the way a CNN can be parallelized across spatial positions — is that difference clear to me at the mechanism level, not just as a fact I've memorized?
6. If I'm debugging an RNN/LSTM that seems to "forget" early context in long sequences, do I know whether that's the expected, named limitation (long-range dependency decay) rather than a bug in my specific implementation?

## Key Takeaways

- A plain feedforward network throws away structure that images and sequences actually have — spatial adjacency for images, order and variable length for sequences — and both CNNs and RNNs exist specifically to exploit that structure instead of ignoring it.
- Convolution's core mechanical idea is **weight sharing across space**: the same small filter, applied at every position, giving parameter efficiency and translation invariance as a single consequence of one design choice.
- Pooling downsamples feature maps, adds further position tolerance, and enables the emergent, learned hierarchy of simple-to-complex features across stacked conv/pool layers.
- ResNet's residual connections are a direct application of Part 4's vanishing-gradient fix to very deep CNNs, and are what made networks over a hundred layers deep actually trainable.
- An RNN's core mechanical idea is **weight sharing across time**: the same update rule applied at every timestep to a hidden state carried forward, letting a fixed number of parameters handle sequences of any length.
- LSTMs/GRUs add learned gates to combat the same vanishing-gradient problem, now occurring across timesteps instead of across layers — mitigating, not eliminating, long-range forgetting.
- RNNs have two specific, named limitations — the sequential bottleneck (no parallelism across timesteps) and long-range dependency decay (even with gating) — that Transformers (Part 6) were built specifically to remove.
- RNNs/LSTMs are now largely a legacy or niche choice (some time-series and audio work) for most sequence tasks in 2025-2026, having been displaced by Transformer-based architectures.

## Quick Self-Check

- Why does flattening an image into a plain vector for a feedforward network throw away information that actually matters for recognizing objects in it?
- Explain, in your own words, how weight sharing in a convolutional filter produces translation invariance as a side effect, rather than as something separately learned.
- What specifically does max-pooling discard, and why is discarding it usually a good trade rather than a loss of useful information?
- Why is the feature hierarchy a CNN learns (edges → textures → parts → objects) described as "emergent" rather than "designed"?
- What problem do ResNet's skip connections solve, and how does that problem connect back to what Part 4 already covered about deep networks?
- Why can't a sentence be handled the same way an image is — what two properties does sequential data have that spatial data in an image doesn't?
- Explain the parallel between "weight sharing across space" (CNNs) and "weight sharing across time" (RNNs) — what's the same about the underlying idea, and what's different about what's being shared across?
- Why does an RNN's vanishing-gradient problem specifically get worse for longer sequences, using the same underlying mechanism Part 4 described for very deep networks?
- What does an LSTM's gate actually decide at each timestep, at a conceptual level — and why does adding gates mitigate the vanishing-gradient problem rather than eliminate it entirely?
- Name the two specific limitations of RNNs that motivated the Transformer architecture, and explain why gating (LSTM/GRU) doesn't fully solve either one.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Structure-exploitation framing (the default for "why not just use a plain neural network"):** "Both of these architectures exist because a plain feedforward network throws away structure that's actually there in the data — spatial adjacency in an image, order and variable length in a sequence. CNNs and RNNs both work by sharing weights — across space for CNNs, across time for RNNs — which is what gives them the right inductive bias for that kind of data, instead of forcing the network to relearn the same pattern separately at every position or every timestep."
- **Historical-arc framing (good for showing you know where the field is now, not just the theory):** "CNNs are still the right default for most vision tasks today — ResNet's skip connections solved the depth problem, and that lineage still holds up. RNNs are more of a 'why this mattered, and why it was superseded' story now — LSTMs were a real fix for vanishing gradients over time, but they never solved the sequential-bottleneck problem, which is exactly why Transformers replaced them for almost everything except some time-series and audio work."
- **Mechanism-parallel framing (good for demonstrating genuine understanding, not memorized facts):** "I think of CNNs and RNNs as the same underlying idea — reuse a small set of weights across a dimension where the same pattern can recur — applied to two different dimensions. A CNN reuses a filter across spatial position; an RNN reuses an update rule across time. Once you see that parallel, the vanishing-gradient story is the same story too, just 'depth' meaning layers in one case and timesteps in the other."
- **Failure-mode framing (good for a debugging/production-reasoning question):** "If I saw an RNN-based model losing context on long inputs, my first thought wouldn't be 'the model is broken' — it's the expected long-range dependency decay this architecture has, even with LSTM gating. That's usually my cue to ask whether a Transformer-based approach would just avoid the problem structurally instead of trying to tune around it."

### Vocabulary Builder

**Technical shorthand:**

- **translation invariance** (n. phrase) — a pattern is recognized the same way regardless of where it appears in the input. *"Weight sharing is what gives a CNN translation invariance for free."*
- **weight sharing** (n. phrase) — reusing the identical set of weights at multiple positions (CNN: across space) or timesteps (RNN: across time) instead of learning separate weights for each.
- **feature map** (n.) — the output of applying one convolutional filter across an entire input, itself a grid of values rather than a single number.
- **receptive field** (n. phrase) — the region of the original input that a given neuron's output is actually influenced by, which grows larger as you stack more convolutional layers.
- **hidden state** (n. phrase) — the vector an RNN carries forward from one timestep to the next, summarizing everything processed so far.
- **gating** (n., v.) — a learned, per-step mechanism (as in LSTM/GRU) deciding how much existing information to retain versus how much new information to incorporate.
- **sequential bottleneck** (n. phrase) — the specific limitation that an RNN's timesteps must be processed strictly in order, preventing parallelization across a GPU during training.

**Expressive phrases:**

- **"…the same idea applied to a different dimension"** — a fluent way to connect CNN weight-sharing-across-space to RNN weight-sharing-across-time in one sentence.
- **"…mitigates, doesn't eliminate"** — precise phrasing for what LSTM gating actually does to the vanishing-gradient problem, avoiding the overclaim that gating "solves" it.
- **"…why this mattered, and why it was superseded"** — a fluent, honest way to frame RNNs' place in a 2025-2026 conversation without either dismissing them or overstating their current relevance.

---

**Previous:** [Part 4: Neural Networks & Backpropagation, From First Principles](04_neural_networks_and_backpropagation.md)  |  **Next:** [Part 6: The Transformer Architecture](06_transformer_architecture.md)

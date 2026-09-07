# ML Fundamentals, Part 7: LLM Fundamentals — Tokenization, Fine-Tuning, and Evaluation

[Part 6](06_transformer_architecture.md) covered the architecture — self-attention, multi-head
attention, positional encoding, and the decoder-only stack that GPT-style models are built
from. Architecture alone isn't a usable product, though. This part covers what actually turns
that architecture into something you can feed raw text into, adapt to a new task without
retraining from scratch, run affordably, and — hardest of all — actually judge as "good" or
"bad" once it's running.

## Tokenization — the Step Before Any Transformer Math Happens

**The problem, precisely**: a neural network is a machine that multiplies and adds numbers.
It has no native concept of a letter, a word, or a sentence — everything has to become a
number before a single matrix multiplication in Part 6's attention mechanism can run at all.
The naive fix — assign every whole word its own number — breaks in two directions at once.
Assign a slot to every word in the English language and you get a vocabulary in the hundreds
of thousands, most of which the model will see only a handful of times during training,
which wastes capacity and slows learning. Worse, language keeps inventing new words,
misspellings, product names, and other languages entirely — a whole-word vocabulary frozen
at training time simply has no slot at all for anything it hasn't seen, and has to fall back
to a generic "unknown word" placeholder that throws away all the information in that word.

**The mechanism: subword tokenization.** Instead of whole words, break text into a vocabulary
of common *pieces* of words — sometimes a whole word, sometimes a fragment, sometimes a
single character as a last resort. The dominant technique, **Byte-Pair Encoding (BPE)** (and
close relatives like WordPiece and SentencePiece, used by different model families), builds
this vocabulary by starting from individual characters and repeatedly merging whichever pair
of adjacent symbols appears most often across a huge training corpus into a new, single
symbol — then repeating that merge process tens of thousands of times. The result is a fixed
vocabulary (commonly 30,000-100,000+ entries for modern LLMs) built entirely bottom-up from
what's statistically common in real text, rather than hand-designed.

**In plain English**: imagine building a vocabulary the way you'd build a phrasebook for a
language you're learning by watching people talk — you don't start with a dictionary, you
notice that "-ing" and "un-" and "-tion" keep showing up glued to lots of different words, so
you learn those chunks once and reuse them everywhere, rather than memorizing every whole
word that happens to contain them separately.

**A concrete, illustrative example**: take the word "unbelievably." A whole-word vocabulary
either has this exact word as one of its slots (unlikely, if it's rare enough) or it doesn't,
in which case the model sees only "unknown word." A BPE tokenizer, by contrast, has almost
certainly learned common pieces like `un`, `believ`, and `ably` from other words during
training (`unhappy`, `unable`, `believe`, `believer`, `probably`, `reasonably`), so
"unbelievably" tokenizes into roughly three or four subword pieces built from parts it's
genuinely seen thousands of times, rather than either one rare whole-word token or thirteen
individual, information-poor character tokens. **As a rough, illustrative, approximate rule
of thumb** — not a precise conversion — GPT-style tokenizers average around 4 characters of
English text per token, which is why a roughly 750-word English page works out to
approximately 1,000 tokens in casual estimates you'll see quoted around LLM context-window
limits.

**Why this specific middle ground matters practically**: common words (`the`, `is`, `running`)
usually survive as a single token because they're frequent enough to earn their own slot
during the merge process; rare or entirely novel words decompose gracefully into familiar
fragments instead of vanishing into an unknown-word placeholder. This is also, mechanically,
why LLMs are sometimes visibly bad at character-level tasks (counting the letters in a word,
reversing a string) — the model never actually sees individual characters as its unit of
computation once tokenization has already happened; it sees the subword tokens the tokenizer
chose to split the word into, and has no reliable internal notion of the individual
characters inside a token it's never had to decompose.

## Pretraining — What the Base Model Actually Learns, and From What Objective

**The problem, precisely**: given a decoder-only Transformer's architecture from Part 6 —
which processes a sequence left-to-right with causal (can't-see-the-future) attention — what
training objective could possibly teach it grammar, facts, reasoning, and style, all from
plain text, with no human labeling of any of it?

**The mechanism: next-token prediction.** Take a huge amount of text, and at every position
in every sequence, train the model to predict the single token that actually comes next,
given everything before it. This maps directly onto [Part 6](06_transformer_architecture.md)'s
causal-attention design — the architecture is built specifically so that predicting position
`N` can only look at positions `1` through `N-1`, exactly what this objective requires — and
onto [Part 4](04_neural_networks_and_backpropagation.md)'s cross-entropy loss and
[Part 2](02_linear_and_logistic_regression.md)'s log-loss: predicting the correct next token
out of a vocabulary of tens of thousands of possible tokens is a classification problem, at
enormous scale, using the exact same loss mechanism a much smaller classifier uses to choose
among a handful of classes. Backpropagation (Part 4) then updates every weight in the network
based on how wrong that next-token prediction was, across billions of training examples.

**Why such a simple-sounding objective produces so much apparent capability**: to get
genuinely good at predicting the next word across a large enough, diverse enough slice of
human-written text — news, code, conversation, technical writing, stories — a model has to
implicitly build internal representations of grammar (to predict which word form fits),
facts (to predict "Paris" after "the capital of France is"), and even multi-step reasoning
patterns (to correctly continue a worked math problem or a logical argument), not because
anyone directly trained it to "know facts" or "reason," but because getting the next-token
prediction right, over and over, across millions of examples that require those skills,
turns out to require developing something functionally very close to them as a side effect.
**In plain English**: it's the difference between a student who was only ever asked "what's
the next word" on every sentence of every book in a vast library, versus one given a fixed
quiz on facts — the first student, if they get genuinely good at the game, ends up absorbing
an enormous amount of the library's actual content along the way, purely as a by-product of
getting extremely good at guessing what comes next.

## Fine-Tuning vs. RAG vs. Prompting — a Genuine Decision Framework

This is the question that actually matters day to day: given a pretrained model and a new
task, which of these three do you reach for? Each solves a different, specific gap between
what the base model already does and what you need.

**Prompting (including few-shot prompting)** — **the problem it solves**: get a pretrained
model to perform a new task using nothing but the instructions and examples you put directly
in its input, with zero changes to the model's weights. **Mechanism**: the model's next-token
prediction, applied to a prompt that describes the task (and optionally includes a few
worked examples right there in the context), naturally continues in a way that follows the
pattern — this works because the model already implicitly learned an enormous range of
task-following behavior during pretraining, and a well-written prompt is essentially pointing
it at the right slice of that already-learned behavior. **When to use it**: it's the cheapest
and fastest option by a wide margin — no training run, no data collection, iterate in
seconds — but it's bounded by two hard limits: the model's context window (how much text it
can attend to at once, per Part 6) and by what the base model already implicitly knows how to
do at all, however cleverly you phrase the request.

**RAG (Retrieval-Augmented Generation)** — **the problem it solves**: the model's knowledge
was frozen the moment pretraining ended. It has no access to your private documents, and no
way to know about anything that happened, or changed, after its training cutoff, and
retraining the whole model every time a document changes is wildly impractical. **Mechanism**:
before generating an answer, retrieve the most relevant documents (via an embedding model
that turns text into vectors, and a similarity search over a **vector database** — Pinecone,
Weaviate, Milvus, and similar, already covered in this repo's system-design content) and
inject that retrieved text directly into the prompt as extra context, so the model is
answering with the right facts sitting right in front of it rather than relying on what it
memorized months or years earlier. **When to use it**: factual, frequently-changing, or
proprietary knowledge — RAG changes *what the model knows about*, not *how it thinks or
behaves*; a model's underlying skill, reasoning style, and output format are untouched by
adding retrieval.

**Fine-tuning** — **the problem it solves**: you need to change the model's actual behavior —
its style, its output format, a specialized reasoning pattern, or a skill it doesn't do well
out of the box — and neither better prompting nor better retrieved context can fix that,
because the gap isn't missing facts, it's missing *capability or style*. **Mechanism**:
continue training the model — the exact same backpropagation-and-gradient-descent mechanism
from [Part 4](04_neural_networks_and_backpropagation.md) — on a smaller, task-specific,
labeled dataset, adjusting the model's actual weights toward the behavior you want.
**When to use it**: it's the most expensive and slowest of the three to iterate on (a real
training run, real labeled data, real compute), and it only works if you actually have
enough quality task-specific data to meaningfully move the model's behavior — fine-tuning on
too little data just makes the base model worse without teaching it anything reliable.

**The decision framework, stated plainly**: reach for prompting first, always — it's free to
try and instantly reversible. Add RAG when the actual gap is missing or changing *knowledge*
the model can't be expected to already have. Reach for fine-tuning only when the gap is
*behavior, format, or skill* that no amount of better prompting or better retrieved context
would fix. In real production systems these are frequently combined, not exclusive — a model
fine-tuned to answer in a specific format still commonly uses RAG on top of that fine-tuning
to stay current on facts.

## LoRA and QLoRA — Why Full Fine-Tuning Is Often Impractical

**The problem, precisely**: a modern LLM can have tens of billions of parameters. Fully
fine-tuning all of them the naive way requires, for every single one of those parameters,
storing not just the weight itself but also the optimizer's running state for it (for a
common optimizer like Adam, roughly two additional numbers per weight) — multiplying the
effective memory footprint several times over the model's own size — and produces, at the
end, an entirely new full-size copy of the model for every separate fine-tuning task. For a
70-billion-parameter model, that's simply not something that fits on a single GPU, and
maintaining a separate full copy per task is a real, ongoing storage cost.

**The mechanism: LoRA (Low-Rank Adaptation).** Freeze the entire original pretrained model —
none of its billions of weights get updated at all — and instead train a much smaller pair
of newly-added, low-rank matrices that get added on top of specific weight matrices inside
the model (commonly the attention projection matrices from Part 6). The insight this rests
on: the actual *change* a model needs to adapt to a new task tends to have far lower
"intrinsic rank" — far less genuinely new information content — than the full weight matrix
it's being added to. **In plain English**: if the full weight matrix is a huge, detailed map
of everything the model already knows, adapting it to a new task doesn't usually require
redrawing the whole map — it requires a much smaller, much simpler set of corrections
overlaid on top of it, and LoRA trains exactly that small overlay instead of the whole map.
Because that overlay has vastly fewer trainable parameters than the full model, both the
memory needed for training and the size of what you need to store per task shrink
dramatically — often to well under 1% of the original model's parameter count.

**QLoRA** extends this one step further by additionally **quantizing** the frozen base
model's weights down to 4-bit precision during fine-tuning (quantization itself is unpacked
fully in the next section), while still training the small LoRA matrices in higher
precision. Because the giant frozen base model is now compressed to a fraction of its
original memory footprint, and only the small LoRA overlay needs full-precision training
memory, this combination — a heavily compressed frozen base plus a tiny trainable overlay —
is specifically what made fine-tuning genuinely large models feasible on a single
consumer-or-prosumer-grade GPU, rather than requiring a multi-GPU training cluster the way
full fine-tuning of the same model would.

## Quantization — the Same Idea, Applied to Inference, Not Just Fine-Tuning

**The problem, precisely**: model weights are normally stored as 32-bit or 16-bit floating
point numbers. At billions of parameters, that precision costs real memory just to hold the
model at all, and — for inference specifically — real time spent moving that many bytes from
memory to the compute units before any math can even happen.

**The mechanism**: represent each weight using fewer bits — INT8 (8-bit integers) or even
INT4 — instead of 16 or 32-bit floats. What's actually lost is precision: instead of each
weight being one of an enormous range of possible floating-point values, it becomes one of a
much smaller set of discrete values, an approximation of the original number rather than the
exact original. **Why this costs surprisingly little accuracy in practice for LLM inference
specifically**: neural network weights are famously tolerant of small perturbations — the
network's behavior emerges from the combined effect of enormous numbers of weights working
together, not from any single weight's exact value, so rounding every weight to the nearest
value in a coarser grid tends to barely move the model's overall output. **Why it helps speed,
not just memory** — and this is a first-principles point, not just "smaller files load
faster": modern LLM inference is very often *memory-bandwidth-bound*, not
compute-bound — the bottleneck is how fast weights can be moved from memory to the
processor, not how fast the processor can multiply numbers once they arrive. Cutting a
weight's size in half or to a quarter directly cuts how much data has to move for the exact
same computation, which is why quantization frequently speeds up inference meaningfully, not
merely shrinking the file on disk.

This progression — **FP32 → FP16/BF16 → INT8 → INT4** — is a real, actively-used spectrum in
production LLM serving today (via libraries like `bitsandbytes` and dedicated quantization
toolchains), not a theoretical extreme reserved for research papers; the right point on that
spectrum for a given deployment is itself a trade-off between acceptable accuracy loss and
the memory/latency budget available.

## Evaluating LLMs — Why This Is Genuinely Harder Than Evaluating a Classifier

**The problem, precisely**: the evaluation this series has used so far — accuracy, precision,
recall against a fixed set of labeled correct answers — assumes there's one unambiguous
correct answer to compare against. Open-ended text generation usually has no such single
correct answer: many different phrasings of a summary, an answer, or a piece of generated
code can all be equally good, and a metric that only rewards exact matches to one reference
answer would unfairly penalize all the others.

**The actual landscape, and what each piece measures**:

- **Perplexity** — a direct measurement of how well the model predicts held-out text under
  its own next-token training objective from earlier in this doc. Cheap to compute, and a
  genuinely useful signal during pretraining — but it measures how *unsurprised* the model is
  by real text, not whether a specific generated answer is actually correct or useful for a
  downstream task.
- **Reference-based metrics (BLEU, ROUGE)** — compare generated text against one or more
  human-written reference answers via n-gram (word/phrase sequence) overlap. Genuinely useful
  for tasks like translation and summarization where a reference exists, but famously poor at
  recognizing a correct answer that's phrased differently from the reference — a
  meaning-preserving paraphrase can score badly purely for not sharing the reference's exact
  wording.
- **Benchmark suites (MMLU, HellaSwag, and similar)** — standardized batteries of
  multiple-choice or fixed-format tasks, used specifically to compare general capability
  *across different models* on a level playing field, rather than to evaluate one specific
  application's output quality.
- **LLM-as-judge and human evaluation** — using either another strong LLM, or actual human
  raters, to score open-ended output quality against criteria a fixed reference answer simply
  can't capture (helpfulness, tone, factual accuracy given context, following instructions).
  This has become the practical default for evaluating anything open-ended in production,
  with the honest caveat that it introduces its own biases (an LLM judge can share the same
  blind spots as the models it's judging) and real ongoing cost.

**The practical takeaway**: no single metric here is sufficient on its own. Real evaluation
pipelines combine several of these — perplexity during training, benchmark suites for
general capability comparisons, LLM-as-judge or human evaluation for actual application
quality — chosen based on what's actually being measured, not one universal score standing
in for "is this model good."

This model-level mechanism — what fine-tuning, RAG, and quantization actually *are* — is a
different layer from the production *systems* built around deploying and operating them at
scale: prompt-management, guardrails, canarying a new fine-tuned model, and ongoing
evaluation pipelines in production are covered in depth in this repo's
[LLMOps tutorial](../system_design_foundation/01_ml_system_design/11_llmops.md), which is the
natural next stop from here.

## Designing and Operating From First Principles

1. Am I about to fine-tune a model to fix a problem that's actually missing or outdated
   knowledge — something RAG would fix far more cheaply and reversibly?
2. Am I reaching for prompting/few-shot examples as the first, cheapest option before
   assuming I need RAG or fine-tuning at all?
3. If I do need fine-tuning, have I checked whether I actually have enough quality
   task-specific data to move the model's behavior reliably, or would fine-tuning on too
   little data just degrade a perfectly good base model?
4. Am I choosing full fine-tuning by default, or have I actually checked whether LoRA/QLoRA
   would get comparable results at a small fraction of the compute and storage cost?
5. If I'm quantizing a model for deployment, have I actually measured the accuracy trade-off
   for my specific task, or am I assuming "it's usually fine" without checking?
6. Am I judging generation quality with whichever single metric was easiest to compute
   (perplexity, BLEU), or have I matched the evaluation method to what I actually need to
   know about the output?
7. If I'm using an LLM-as-judge, have I accounted for the possibility that it shares blind
   spots with the model it's evaluating, rather than treating its score as ground truth?

## Key Takeaways

- **Tokenization turns text into the numeric units a Transformer can actually process**,
  using subword pieces (BPE and relatives) specifically to avoid both an exploding
  whole-word vocabulary and an inability to represent novel words.
- **Pretraining's objective — next-token prediction — is deceptively simple but produces
  broad capability as a side effect**, because getting genuinely good at predicting text
  across a huge, diverse corpus implicitly requires learning grammar, facts, and reasoning
  patterns along the way.
- **Prompting, RAG, and fine-tuning solve three different, specific gaps**: missing
  instructions (prompting), missing/changing knowledge (RAG), or missing behavior/skill/format
  (fine-tuning) — and picking the wrong one for the actual gap wastes cost and time without
  fixing the real problem.
- **LoRA exploits the fact that adapting a model needs far less new information than
  retraining the whole model** — a small trainable overlay on frozen weights, not a full
  weight update; QLoRA combines this with quantizing the frozen base to make large-model
  fine-tuning feasible on much smaller hardware.
- **Quantization trades numeric precision for memory and speed, and often costs surprisingly
  little accuracy** — and it speeds up inference specifically because LLM inference is
  frequently memory-bandwidth-bound, not compute-bound.
- **Evaluating generated text is harder than evaluating a classifier because there's rarely
  one correct answer** — perplexity, reference-based metrics, benchmark suites, and
  LLM-as-judge/human evaluation each measure a different thing, and real pipelines combine
  several rather than trusting one.
- **The whole seven-part arc is one continuous through-line**: the bias-variance trade-off
  and train/val/test discipline from Part 1 apply just as much to an LLM as to a linear
  regression; linear and logistic regression's loss-and-gradient-descent mechanism from
  Part 2 is the same mechanism a Transformer's backpropagation uses at far larger scale;
  decision trees and ensembles in Part 3 showed a different, non-neural path to the same
  bias-variance goals; neural networks and backpropagation in Part 4 are the literal engine
  every deep learning model in Parts 5-7 trains with; CNNs and RNNs in Part 5 solved
  structure-aware learning for images and sequences, and RNNs' specific weaknesses directly
  motivated Part 6's attention mechanism; and this part's LLMs are, mechanically, exactly
  that Part 6 architecture, trained with Part 2's loss function, adapted with Part 1's
  bias-variance discipline still fully in force.

## Quick Self-Check

- Why does whole-word tokenization fail in two opposite directions at once, and how does
  subword tokenization (BPE) avoid both failure modes with one mechanism?
- Why is next-token prediction, by itself, enough of a training signal to produce a model
  that appears to reason and know facts — what has to be true about the training data for
  that to work?
- A team wants their support chatbot to know about a product launched yesterday. Which of
  prompting, RAG, or fine-tuning actually fixes this, and why would the other two either not
  work or be needlessly expensive?
- Why can't RAG teach a model a new output format or reasoning style, even if you retrieve
  and inject perfect example documents into the prompt?
- What does "intrinsic rank" mean in the context of LoRA, and why does a low-rank
  approximation of a weight update still capture most of the useful adaptation?
- Why does QLoRA quantize the frozen base model but not the LoRA matrices themselves?
- Explain, from first principles, why quantizing a model can make inference *faster*, not
  just smaller — what specifically is the bottleneck being relieved?
- Why is BLEU/ROUGE a poor judge of a correct answer that's phrased differently from the
  reference — what is the metric actually measuring instead of correctness?
- Why would a benchmark suite like MMLU be a poor way to evaluate one specific production
  chatbot's output quality, even though it's a legitimate way to compare two base models?
- Name one real risk of relying on LLM-as-judge evaluation that human evaluation doesn't
  share, and one advantage LLM-as-judge has over pure reference-based metrics.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Decision-framework framing (the default for "when would you fine-tune vs. use RAG"
  questions):** "I'd separate the three by what gap they actually close — prompting for
  instructions the model can already follow, RAG for knowledge the model doesn't have or
  that changes over time, and fine-tuning only when the gap is actual behavior or skill that
  neither of the other two can touch. In practice I'd try them roughly in that order, since
  cost and iteration speed increase in that same order."
- **Mechanism-first framing (good for LoRA/quantization questions, showing this isn't just
  memorized buzzwords):** "LoRA works because adapting a pretrained model to a new task
  usually needs far less new information than retraining the whole thing — so instead of
  updating billions of frozen weights, you train a small low-rank overlay on top of them.
  Quantization is a similar trade: fewer bits per weight, and because LLM inference is often
  memory-bandwidth-bound rather than compute-bound, that shrinkage speeds things up, not just
  shrinks the file."
- **Evaluation-honesty framing (good for demonstrating depth beyond "we measure accuracy"):**
  "Open-ended generation doesn't have one correct answer the way a classifier's label does,
  so I wouldn't trust a single metric. I'd use perplexity during training, benchmark suites
  to compare general capability, and LLM-as-judge or human eval for actual output quality —
  and I'd be upfront that an LLM judge can share blind spots with the model it's grading."
- **Through-line framing (good for tying this back to earlier ML fundamentals):** "An LLM
  isn't a separate discipline from the rest of ML — it's the same next-token classification
  objective, the same cross-entropy loss, and the same backpropagation mechanism as a much
  smaller model, just applied at enormous scale with an architecture built for
  parallelizable long-range attention instead of recurrence."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **tokenization / BPE (Byte-Pair Encoding)** (n. phrases) — breaking text into subword
  units by iteratively merging the most frequent adjacent symbol pairs; the step that turns
  raw text into the numeric input a Transformer requires. *"The tokenizer split that rare
  word into three subword pieces instead of failing on it entirely."*
- **pretraining objective** (n. phrase) — the next-token-prediction task a base LLM is
  trained on before any task-specific adaptation happens.
- **RAG (Retrieval-Augmented Generation)** (n. phrase, initialism) — injecting retrieved,
  relevant documents into a prompt so the model answers with current/proprietary facts it
  wasn't trained on.
- **LoRA / QLoRA (Low-Rank Adaptation)** (n. phrases) — fine-tuning by training a small
  low-rank overlay on frozen pretrained weights; QLoRA additionally quantizes the frozen base
  to 4-bit during that process.
- **quantization** (n.) — representing model weights with fewer bits (INT8, INT4 instead of
  FP32/FP16) to reduce memory and, since LLM inference is often memory-bandwidth-bound,
  frequently speed up inference too.
- **perplexity** (n.) — a measure of how well a language model predicts held-out text under
  its own training objective; a training-time signal, not a measure of output correctness.
- **LLM-as-judge** (n. phrase) — using a strong LLM to score another model's open-ended
  output quality, in place of or alongside human evaluation.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…the gap is knowledge, not skill"** — a fast, precise way to justify choosing RAG over
  fine-tuning in a design discussion.
- **"…memory-bandwidth-bound, not compute-bound"** — the first-principles reason quantization
  speeds up inference, not just shrinks the model on disk.
- **"…no single metric is sufficient here"** — the honest, defensible answer to "how do you
  evaluate an LLM," instead of naming one metric as if it settles the question.

---

**Previous:** [Part 6: The Transformer Architecture](06_transformer_architecture.md)

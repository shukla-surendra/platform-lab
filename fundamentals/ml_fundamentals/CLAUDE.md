# ML Fundamentals

First-principles ML/DL primer, Parts 1-7. The goal of every doc here is to take a reader
from **complete beginner to interview-ready depth on that one topic**, in a single
continuous doc — not a beginner doc and a separate advanced doc.

This tree is scoped deliberately to **breadth, not research depth** — matching
`private_profile/ml-platform-prep-plan-v2.md`'s Track 6 ("ML Fundamentals"): enough to
reason about *why* an approach was chosen in an ML system design interview, not enough to
pass a research-scientist interview. It covers the mechanism-level "what actually happens
inside the model" layer; the separate, much larger
[`../system_design_foundation/01_ml_system_design/`](../system_design_foundation/01_ml_system_design/)
tree covers the systems/production layer built *on top of* these mechanisms (serving,
feature stores, observability, LLMOps) — read this tree first if system design content
there ever assumes ML vocabulary you don't already have solid.

## Explanation shape: layman → principal, every time

Every concept must be introduced in **plain, jargon-free language first** — the kind of
explanation you'd give a smart friend with no ML background — before any formula or
technical term appears. Only after that plain-English grounding is in place does the doc
build upward through the formal mechanism, the trade-offs, the real tools/libraries that use
this mechanism, and finally the depth a strong ML system design candidate is expected to
have (what breaks it, what it costs, when you'd reach for it versus when you wouldn't).

Concretely, that means:

- Open with the **problem** in relatable terms before naming the **mechanism** that solves
  it, before explaining **why it matters** at interview depth — problem → mechanism → why it
  matters, never definition-first.
- Don't assume the reader already has the vocabulary a term requires. Define it in plain
  language the first time it's used in a doc, even if a prior part already defined it —
  point back to that part for depth, but don't require having read it to follow along here.
- A concrete analogy earns its place whenever it makes an abstract mechanism click — the
  "walking downhill in fog" (gradient descent), "20 questions" (decision trees), and
  "library search" (attention's Query/Key/Value) analogies already in this series are the
  bar.
- The doc should still end at genuine interview depth: precise definitions, the actual
  source when one exists (Vaswani et al. for Transformers, the original LoRA/QLoRA papers,
  etc.), real production trade-offs, and the "Articulate It" interview-framing section every
  part already ends with.

## Analogies, real tools, and current trends — required, not decorative

Every mechanism gets a concrete analogy — not an occasional nice-to-have, an expected part
of introducing it. Every mechanism also gets named, real, currently-relevant tooling — never
left as pure abstract theory: scikit-learn, XGBoost/LightGBM/CatBoost, PyTorch, Hugging
Face's `transformers`/`peft`/`bitsandbytes`, and named real model families (BERT, GPT, T5)
so the reader leaves knowing not just the idea but where they'd actually encounter or reach
for it.

**Stay current, not textbook-frozen**: favor what an ML system design candidate would
actually be asked about in 2025-2026 (RoPE positional encoding, LoRA/QLoRA, quantization for
LLM inference, LLM-as-judge evaluation) alongside the foundational papers and classics
(backpropagation, CAP-adjacent bias-variance theory, "Attention Is All You Need") that still
explain *why* the modern defaults are built the way they are.

## Plain English is the entry ramp, never a substitute for precision

Simplifying the *on-ramp* into a concept must never mean cutting the exact technical
vocabulary a reader needs later. Every advanced term the concept actually has must still
appear, correctly and precisely defined — the plain-English pass is what earns the reader
the right to encounter that term without getting lost, not a reason to leave the term out.

## First principles, not memorized facts

Every explanation must be derivable from **why**, not just stated as **what**. Before naming
a technique or architecture, name the actual structural or mathematical constraint that
makes it necessary — Part 4's chain-rule motivation for backpropagation, Part 5's "why a
single layer can't learn XOR" framing, and Part 6's "why attention removes the sequential
bottleneck" framing are the house style. If a doc introduces a technique without first
establishing the problem it exists to solve, that's a gap to fix, not an acceptable
shortcut.

## Practical implications for new/edited content

- New parts follow the numbered `NN_topic_name.md` convention, get wired into this folder's
  own navigation (`Previous`/`Next` footer links, using real U+00A0 non-breaking-space
  characters around the `|`, not plain spaces or an HTML entity) and this file's own
  README.md part list, and end with `Designing and Operating From First Principles`, `Key
  Takeaways`, `Quick Self-Check`, and `Articulate It` sections matching every existing part.
- Cross-reference liberally instead of re-deriving mechanism a prior part already covered —
  link back to it, then build on it, rather than repeating it (Part 4's neuron-is-logistic-
  regression callback to Part 2, and Part 6's residual-connection callback to Part 4/5, are
  the model to follow).
- This folder still follows the repo-wide `## Articulate It: Interview Framing & Vocabulary`
  convention from `../CLAUDE.md` — this file adds the layman-to-interview-depth shape on top
  of that, it doesn't replace it.
- The `engineering-fundamentals` skill (repo root, `.claude/skills/`), Mode 1, covers
  authoring a new first-principles concept-primer doc from scratch — this tree's docs were
  written following that mode's guidance, generalized from `00_prerequisite_concepts/`'s own
  house style rather than copying its (distributed-systems-specific) content.

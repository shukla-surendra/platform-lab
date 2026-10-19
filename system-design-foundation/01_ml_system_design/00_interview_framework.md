# The System Design Interview Framework

Every tutorial in this section is written around one four-step structure. Internalize this
once and it transfers to every design question you'll get, ML-specific or not.

```mermaid
flowchart LR
    A["1. Clarify\nRequirements"] --> B["2. High-Level\nDesign"]
    B --> C["3. Deep-Dive\none component"]
    C --> D["4. Trade-offs\n& failure modes"]
    D -.->|"new constraint surfaces"| A
```

## Step 1: Clarify Requirements

This is the step senior candidates get scored on the hardest, and the step most candidates
rush through. The questions you ask here signal seniority more than anything you say later
— they show you know that "design a recommendation system" is underspecified until you've
pinned down scale, latency, and consistency needs.

**Ask about, in roughly this order:**

1. **Functional scope** — what does the system actually need to do? (e.g. "batch scoring
   only, or real-time inference too?")
2. **Scale** — requests/sec, data volume, number of models/features, number of users.
   Orders of magnitude change the design: 100 req/s and 100K req/s are different systems,
   not the same system with more servers.
3. **Latency requirements** — p50/p99 targets, and *why* (a fraud-check API and a nightly
   batch report have wildly different latency budgets — don't assume "fast" means the same
   thing in both).
4. **Consistency needs** — can this tolerate eventual consistency, or does it need strong
   consistency? (Directly determines database/replication choices later.)
5. **Failure tolerance** — what's the cost of a wrong answer vs. no answer vs. a slow
   answer? (A model returning a slightly stale recommendation is fine; a fraud model
   returning nothing when it should block a transaction is not.)
6. **Existing constraints** — cloud provider, team size, budget, must-integrate-with
   systems. Real systems are built inside constraints, not on a blank slate — asking this
   shows you've actually shipped something.

**A concrete sentence to have ready:** *"Before I sketch anything, can I confirm the scale
we're targeting and the latency budget — I want to design for the actual constraint, not a
generic version of this system."* That one sentence, asked before you touch the whiteboard,
does more for your signal than most of what follows it.

## Step 2: High-Level Design

Sketch the major components and how data flows between them — boxes and arrows, not
implementation detail yet. For ML systems specifically, the recurring shape is:

```mermaid
flowchart LR
    Ingest["Ingestion"] --> Store["Storage /\nFeature Store"]
    Store --> Train["Training"]
    Train --> Registry["Model\nRegistry"]
    Registry --> Serve["Serving Layer"]
    Serve --> Client["Client / App"]
    Serve --> Monitor["Observability &\nDrift Detection"]
    Monitor -.->|"triggers retrain"| Train
```

Every tutorial in this section is one piece of this larger loop, zoomed in. Naming this
whole loop out loud in the first 30 seconds of your high-level design — even before you
zoom into your assigned piece — is a strong senior signal: it shows you see where the
requested component sits in the broader ML lifecycle, not just in isolation.

## Step 3: Deep-Dive One Component

The interviewer usually steers this, but come prepared to *offer* a component to deep-dive
into rather than waiting passively — it shows you know which part of your design is
actually interesting or risky. Good candidates for a self-initiated deep-dive:

- The part with the tightest latency constraint.
- The part most likely to fail under load or partial outage.
- The part where you made a non-obvious trade-off in the high-level sketch (call it out:
  *"I glossed over X here — want me to go deeper on how that actually works?"*).

Go deep enough to write pseudocode, a schema, or a sequence diagram — not just more boxes.

## Step 4: Trade-offs & Failure Modes

This is the step senior interviewers weight heaviest, and it's a discussion, not a
monologue — expect pushback and follow-up "what if" questions. For every major decision in
your design, be ready to state:

- **What you chose, and the specific alternative you rejected.** ("I chose eventual
  consistency here over strong consistency because—" beats "I used eventual consistency.")
- **What breaks it.** Every component you drew can fail, be slow, or receive bad/adversarial
  input — name the failure mode before the interviewer asks, and say what happens next
  (retry? fallback? degrade gracefully? page someone?).
- **What you'd change at 10x scale.** This is a favorite follow-up because it tests whether
  your design choices were principled or accidental.

## The Trade-off Vocabulary Cheat Sheet

Fluently naming these axes — and which side of each axis your design landed on, and why —
is most of what "senior" sounds like in these interviews.

| Axis | One side | Other side | Where it shows up |
|---|---|---|---|
| Consistency vs. Availability | Strong consistency (CP) | High availability (AP) | Feature stores, model registries under partition |
| Latency vs. Throughput | Optimize for fast individual responses | Optimize for total requests/sec | Real-time serving vs. batch scoring |
| Freshness vs. Cost | Real-time features/retraining | Cached/batch features, periodic retraining | Feature store design, drift response |
| Accuracy vs. Latency | Larger model, better accuracy | Smaller/quantized model, faster inference | Model-serving deep-dive, LLM serving |
| Build vs. Buy | Hand-roll (more control) | Managed tool — Feast, KServe, Pinecone | Almost every "what would you use for X" question |
| Push vs. Pull | Push updates to consumers immediately | Consumers poll/pull on their schedule | Feature freshness, monitoring pipelines |
| Coupling | Tightly coupled (simpler, less flexible) | Loosely coupled via queues/events (more resilient, more ops overhead) | Ingestion pipelines, serving-to-monitoring hookup |

## A Reusable Opening Line

When a design question comes in cold, this ordering keeps you from freezing or rambling:

1. Restate the problem in your own words in one sentence.
2. Ask 2-4 clarifying questions from the list above (don't ask all of them — pick the ones
   that actually change your design).
3. State the resulting scale/latency/consistency targets *out loud* before drawing
   anything — this anchors the rest of the conversation and gives the interviewer a chance
   to correct you early, cheaply, instead of 15 minutes in.
4. Sketch the high-level loop, narrating each box's purpose in one clause as you draw it.
5. Propose a deep-dive target yourself, then follow where the interviewer steers.
6. Close every component you discuss with its trade-off and failure mode, unprompted.

## How the Rest of This Section Uses This Framework

Each of the six topic tutorials is structured as: core concepts → reference architecture →
a deep-dive walkthrough → a trade-off table → failure modes → a "Make It Yours" section
prompting you to attach your own production-system specifics → practice questions. That structure
*is* this framework, applied to one recurring ML-systems topic at a time.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Trade-off-first (the default for a senior round):** "I treat every design round as a
  loop, not a checklist — clarify, sketch, deep-dive, then trade-offs, and any of those
  steps can send me back to clarify again if a new constraint surfaces. The trade-off step
  is where I spend the most airtime, because that's what's actually being scored."
- **Narrative-first (good when asked 'walk me through how you approach these'):** "The
  first time I skipped clarifying questions and jumped straight to a whiteboard, I designed
  a beautiful system for the wrong scale — the interviewer had to walk me back fifteen
  minutes in. Now the very first thing I say out loud is the scale and latency target I'm
  designing for, before I draw a single box."
- **Meta-framing (good for 'how do you evaluate a candidate' or self-assessment
  questions):** "Interviewers weight the clarify step and the trade-off step far more
  heavily than the box diagram in the middle — the diagram just proves you can hold the
  system in your head; the other two prove you can reason about it."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **blast radius** (n.) — how much of the system is affected if a given component fails or
  a decision goes wrong; naming it shows you're thinking about failure scope, not just the
  happy path.
- **degrade gracefully** (v. phrase) — a system losing some functionality in a controlled
  way under stress, rather than failing outright.
- **crossover point** (n.) — the scale or condition at which one design's trade-off starts
  beating another's; useful shorthand for "it depends, and here's exactly on what."
- **first-order vs. second-order effect** (n. phrase) — the direct consequence of a
  decision versus its downstream ripple effects; naming which one you're discussing avoids
  talking past an interviewer.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"Let me anchor this before I go further…"** — a clean way to pause and restate scale/
  latency assumptions before continuing, rather than let them drift unstated.
- **"I chose X over Y because…"** — always prefer this construction to a bare "I used X"; it
  forces you to name the rejected alternative, which is most of what signals seniority.
- **principled** (adj.) — a decision made from reasoned trade-offs rather than habit or
  guesswork. *"I want this to sound principled, not accidental, when the 10x-scale
  follow-up comes."*
- **unprompted** (adv.) — offered before being asked. *"I raise the failure mode
  unprompted, rather than waiting for the interviewer to probe for it."*
- **"That's a fair pushback — here's how I'd reconsider it…"** — the fluent way to receive
  interviewer pushback without sounding defensive; treats the round as a discussion, which
  is exactly what Step 4 is supposed to be.

---

**Previous:** [Prerequisite Concepts, Part 24: Cardinality — One Word, Five Meanings, One Underlying Idea](../00_prerequisite_concepts/24_cardinality.md)  |  **Next:** [1. Fundamentals & Building Blocks](00_interview_framework_fundamentals.md)

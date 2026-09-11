# Architecture Walkthrough Framework and Design Review Framework

These are the two highest-stakes recurring formats for a senior engineer: presenting an architecture (proposing or explaining) and participating in — or leading — a design review of someone else's. Both get their own formal framework because "just present the diagram" reliably fails in the specific ways covered below.

## The Architecture Walkthrough Framework

A superset of the Project Walkthrough (`06_Project_Presentation/01`), formalized for high-stakes presentations — proposing a new system, or presenting to an unfamiliar or skeptical audience.

```
┌─────────────────────────────────────────────────────────────┐
│ 1. CONTEXT       Why does this system need to exist? (SCQA-style │
│                   situation + complication, 03_Explanation_Fr.)   │
├─────────────────────────────────────────────────────────────┤
│ 2. REQUIREMENTS   Functional + non-functional, stated explicitly  │
│                   BEFORE the design — this is the step most        │
│                   often skipped, and skipping it is why design     │
│                   reviews devolve into "why didn't you consider X" │
│                   — because X was never stated as a requirement.   │
├─────────────────────────────────────────────────────────────┤
│ 3. HIGH-LEVEL SHAPE  The 3-5 major components and how data/       │
│                       control flows between them — mid-altitude,   │
│                       no implementation detail yet.                │
├─────────────────────────────────────────────────────────────┤
│ 4. KEY DECISIONS  2-3 decisions that were genuinely non-obvious,  │
│                    each with the alternative considered and why    │
│                    it was rejected — THIS is where seniority is    │
│                    actually evaluated in a design review.          │
├─────────────────────────────────────────────────────────────┤
│ 5. FAILURE MODES  What happens when a dependency is down, when     │
│                    load spikes, when data is malformed — proactive,│
│                    not just answered when asked.                   │
├─────────────────────────────────────────────────────────────┤
│ 6. WHAT'S OUT OF SCOPE  Explicitly named, so it can't be silently  │
│                          assumed to be missing or forgotten.        │
└─────────────────────────────────────────────────────────────┘
```

### Why Step 4 (Key Decisions) Is the Section That Gets You Promoted

Any competent engineer can present step 3 — the shape of a system, once decided, is straightforward to describe. What's hard, and what design reviews are actually evaluating, is the *reasoning that got you there* — the road not taken and why. A walkthrough that only covers "here's what I built" reads as execution. A walkthrough that covers "here's what I built, here's what I seriously considered instead, and here's the specific reason I didn't go that way" reads as judgment — which is the thing Staff+/Principal roles are evaluated on.

**Template for a Key Decision:**
> "For [component], I considered [alternative]. I went with [chosen approach] instead because [specific reason tied to a requirement from Step 2] — the trade-off is [honest cost], which I judged acceptable because [reasoning]."

### Worked Example — Key Decisions Section, Full

> "Three decisions worth walking through in detail:
>
> **First — sync vs. async processing for the enrichment step.** I considered doing feature enrichment synchronously in the request path, which is simpler. I went with async via a queue instead, because our p99 latency requirement is 200ms and the enrichment step alone was taking 150ms in prototyping — leaving no budget for anything else. The trade-off is added complexity — we now need to handle partial/missing enrichment gracefully on the read side — but that was a better trade than blowing our latency SLA.
>
> **Second — one shared table vs. per-tenant tables.** I considered per-tenant tables for stronger isolation. I went with one shared, partitioned table instead, because we're targeting 500+ tenants and per-tenant tables would mean 500+ objects to migrate on every schema change — an operational cost that outweighs the isolation benefit at this tenant count. If we ever have a handful of very large tenants needing hard isolation, that's a case for revisiting, but it's not our current shape.
>
> **Third — build vs. buy for the queue.** I considered SQS. I went with Kafka instead, since we already run it for the events pipeline — no new operational surface, and we get ordering guarantees SQS doesn't provide for free, which matters here because enrichment order affects correctness."

Each decision follows the same shape: alternative → chosen approach → reason tied to a stated requirement → honest trade-off. This is dense, information-rich, and unmistakably senior — and it's a template, not a talent.

---

## The Design Review Framework (As a Reviewer)

Design reviews fail in two opposite directions: rubber-stamping (no real scrutiny, low value) or unstructured pile-on (everyone raises a different pet concern, no prioritization, the presenter leaves without a clear signal). A structured review avoids both.

### Reviewer's Structured Pass

```
1. CLARIFY FIRST   Ask questions to understand before evaluating —
                    "what's the expected scale" before "have you
                    considered X" — evaluating an incomplete mental
                    model produces bad feedback.
2. REQUIREMENTS CHECK  Does the design actually satisfy the stated
                        requirements? (Not: does it match how I'd
                        have built it.)
3. FAILURE MODE CHECK  What happens under partition, overload,
                        dependency failure, bad input?
4. SCALE CHECK          Does this hold at 10x current load? At 10x
                        current data volume? Where's the first thing
                        that breaks?
5. OPERABILITY CHECK   Can this be debugged at 3am by someone who
                        didn't build it? Is there sufficient
                        observability?
6. PRIORITIZED FEEDBACK  Separate "blocking" from "worth considering"
                          from "nit" — explicitly, out loud, so the
                          presenter knows what must change vs. what's
                          optional.
```

### Giving Prioritized Feedback — The Explicit Labeling Pattern

The single highest-leverage habit for a design review *participant* (not just presenter) is explicitly labeling the severity of your own feedback, because unlabeled feedback forces the presenter to guess whether "have you thought about read replicas?" is a blocking concern or idle curiosity — and they'll often guess wrong in the direction of over-indexing on whoever spoke most confidently, not whoever raised the most important point.

- "This is a blocker for me: ..." *(must be resolved before approval)*
- "This is worth considering, not blocking: ..." *(presenter's call whether to address now or later)*
- "Nit: ..." *(cosmetic, ignore if time-constrained)*
- "Question, not a concern yet — I want to understand before I form an opinion: ..."
- "I'll flag this but defer to you — you have more context than me on this trade-off: ..."

Full phrase bank for feedback delivery is in `05_Phrase_Library/03_recommendations_disagreement_feedback.md`.

### Facilitating a Design Review (As the Organizer)

- Open by restating the decision that needs to be made and the timebox: *"We're here to decide whether to approve this design for [system]. We have 45 minutes. [Presenter] will walk through it in about 15, then we'll open for structured feedback."*
- After the walkthrough, go around explicitly rather than open-floor: *"Let's go around — one blocking concern or pass, from each person, then we'll open general discussion."* This surfaces quieter but important objections that get lost in open-floor dynamics dominated by whoever speaks first/loudest.
- Close with an explicit decision, not a fade-out: *"Sounds like we have two blocking items — [X] and [Y]. [Presenter], can you address those and we'll do a lightweight async follow-up rather than a full second meeting?"*

## Design Review Anti-Patterns to Avoid

| Anti-pattern | Why it fails | Fix |
|---|---|---|
| "Why didn't you consider X?" with no context | Presenter can't tell if this is a blocker or curiosity | Label severity explicitly (see above) |
| Litigating a decision that's out of scope for this review | Wastes the room's limited time | "That's a great question, but out of scope for today — want to take it offline?" |
| Silent nodding with no real engagement | False confidence, issues surface in production instead | Facilitator should go around explicitly, not rely on open-floor |
| Presenter gets defensive at every question | Shuts down useful scrutiny | Reframe questions as help, not attack: "these questions are making the design stronger, not stalling it" |
| Design review with no stated decision at the end | Ambiguous outcome, re-litigated later | Facilitator closes with an explicit decision and next step |

## Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Devolve (into)** | To deteriorate or decline into a worse, less structured state. |
| **Rubber-stamping** | Approving something without real scrutiny or independent judgment. |
| **Pile-on** | An uncoordinated stack of criticism with no prioritization, everyone raising a separate concern at once. |
| **Over-index (on)** | To give disproportionate weight to one factor — here, confidence — relative to what actually matters. |
| **Litigate (a decision)** | To re-argue or reopen a settled or out-of-scope decision, as if disputing it in court. |
| **Fade-out** | An unclear, drifting ending with no explicit resolution. |
| **Blow (a budget/SLA)** | To exceed or violate a limit beyond what's acceptable. |
| **Scrutiny** | Close, critical examination. |
| **Reads as** | Comes across as; gives the impression of. |

**Next:** [`02_describing_diagrams_and_tradeoffs_in_words.md`](./02_describing_diagrams_and_tradeoffs_in_words.md) — the specific skill of describing a visual architecture verbally, for calls/interviews where you can't just point at a whiteboard.

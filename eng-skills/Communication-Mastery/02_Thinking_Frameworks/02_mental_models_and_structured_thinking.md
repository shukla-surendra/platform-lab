# Mental Models and Structured Thinking Before Speaking

Answer-first thinking (`01`) tells you where to *start*. This chapter covers how to organize everything that comes *after* the first sentence, using a small set of reusable mental shapes you can drop any technical content into on demand.

## Why You Need Reusable Shapes

Without a pre-loaded structure, you have to *invent* an organization scheme live, for every single explanation, which is expensive (see the working-memory discussion in `01_Foundations/02`). Experienced communicators don't invent structure live — they recognize "oh, this is a comparison" or "this is a trade-off decision" and drop it into a shape they've used hundreds of times before. The shape becomes free; only the content is new.

This chapter covers four general-purpose thinking shapes. `03_Explanation_Frameworks` covers the more formal, named frameworks (PREP, STAR, SCQA) that sit on top of these.

## Shape 1: The Rule of Three

The human working-memory sweet spot (`01_Foundations/02`) is 3–5 chunks. Three is the number that's almost always safe, easy to hold, and easy to generate on demand — which makes "pick your top 3" the fastest default structuring move available to you.

**Application pattern:** "There are three things worth knowing about X: [1], [2], [3]."

```
Example — describing a migration decision:
"There are three reasons we chose Databricks over self-managed Spark:
 1. Cluster lifecycle management — we stopped hand-rolling EMR bootstrap scripts.
 2. Unified governance — Unity Catalog gave us one permission model instead of
    three (S3 IAM, Hive metastore, cluster policies).
 3. Collaborative notebooks — data scientists stopped emailing .ipynb files."
```

**When you have more than 3 real points:** don't force a fourth into the top-level list. Pick the 3 most decision-relevant ones, and mention "there were a couple of smaller factors too" — offering to expand only if asked. This is altitude control (`01_Foundations/03`) applied to breadth, not just depth.

## Shape 2: Compare/Contrast Grid

Whenever the underlying question is "why this and not that" (Kafka vs. SQS, Terraform vs. CloudFormation, EKS vs. ECS), think in a 2-axis grid *before* speaking, even if you never draw it. The axes are always: **the options**, and **the 2–3 dimensions that actually drove the decision** (not every possible dimension — the ones that mattered).

```
                 Kafka                    SQS
Ordering    │  Per-partition ordering │  No ordering guarantee
            │  (what we needed)       │  (would've required extra work)
────────────┼──────────────────────────┼───────────────────────────
Ops burden  │  Already running it for  │  Fully managed, zero new
            │  events — zero new       │  infra
            │  surface area            │
────────────┼──────────────────────────┼───────────────────────────
Throughput  │  Higher, but we don't    │  Sufficient for our volume
            │  need it here            │
```

Speaking from a grid you've mentally built (even unspoken) produces sentences like: *"We picked Kafka over SQS mainly for ordering guarantees — SQS doesn't give you per-key ordering without extra work, and since we already run Kafka for the events pipeline, there was no new operational surface either."* One sentence, two dimensions, a clear winner and why — because the grid was built first.

Full templates for verbalizing this live in `05_Phrase_Library/02_comparisons_tradeoffs_architecture.md`.

## Shape 3: Problem → Cause → Solution → Result (PCSR)

This is the default shape for almost anything that started as a problem: incidents, performance issues, bugs, technical debt. It mirrors how engineers naturally think about problems, which makes it fast to slot content into, but the discipline is saying it **in this order** rather than the order you discovered it in (which is usually Cause → Problem → messy investigation → Solution → Result, i.e., backwards from what the listener needs).

```
PROBLEM   → one sentence, the symptom that was visible/impactful
CAUSE     → the actual root cause (not the first thing you suspected —
             the thing that turned out to be true)
SOLUTION  → what you did about it
RESULT    → the measurable outcome, ideally with a number
```

```
Example:
PROBLEM:  "Our nightly Spark job started taking 6 hours instead of 45 minutes."
CAUSE:    "A data skew — one partition key had 80% of the records after an
           upstream schema change, so one executor was doing 80% of the work
           while the others sat idle."
SOLUTION: "We salted the join key to spread that partition across executors,
           and added a data-skew check to the pipeline's pre-flight validation."
RESULT:   "Runtime dropped back to 40 minutes, and we've caught two more
           skew events before they hit production since adding the check."
```

This shape is formalized further in `03_Explanation_Frameworks/01` (it's the backbone of RCA communication and the Problem→Cause→Solution→Result framework specifically) and drilled heavily in `04_Technical_Storytelling` and `05_Phrase_Library/04_incidents_rca_performance_risk.md`.

## Shape 4: The Decision Tree Summary

For "why did you choose X" questions where there were genuinely multiple viable paths (not just one obvious answer), think in terms of a decision tree with your chosen branch highlighted — and communicate only the **branch points that mattered**, not the full tree.

```
Question: "Why microservices instead of a modular monolith?"

Full tree (in your head):                Spoken summary (one sentence,
                                           built from the highlighted path):
  Need independent deploy cadence?
   ├─ No  → modular monolith               "We went with microservices
   └─ Yes → keep going                      mainly because three teams
       Need independent scaling?             needed independent deploy
        ├─ No → could still be modular       cadence and independent
        └─ Yes → microservices ✅ (us)        scaling — the recommendations
                                              service scales completely
                                              differently from checkout,
                                              and a modular monolith would've
                                              coupled their release trains."
```

You do not need to narrate the tree. You need to have *walked* the tree mentally so you can state the one or two branch points that actually determined the outcome, instead of listing every factor you ever considered (completeness bias — `01_Foundations/01`).

## Choosing a Shape Fast: The Trigger-Word Map

With practice, a trigger word in the question tells you which shape to reach for before you've even finished parsing the question:

| Question sounds like... | Reach for... |
|---|---|
| "What happened with...", "Walk me through the outage" | PCSR (Shape 3) |
| "Why X and not Y", "How does this compare to..." | Compare/Contrast Grid (Shape 2) |
| "What should I know about...", "Give me the overview" | Rule of Three (Shape 1) |
| "Why did you choose...", "What was the decision process" | Decision Tree Summary (Shape 4) |
| "Tell me about a time you..." | STAR — see `03_Explanation_Frameworks/01` |
| Anything needing a written/structured recommendation | Pyramid Principle / SCQA — see `03_Explanation_Frameworks` |

## Putting It Together With Answer-First Thinking

The full pre-speech routine, combining `01` and `02`:

```
1. ANSWER   — what's my one-sentence conclusion? (from 02_Thinking_Frameworks/01)
2. SHAPE    — which of the 4 shapes above fits this question?
3. FILL     — populate that shape with 3, not 12, supporting points
4. SPEAK    — answer first, then the shape, then an explicit so-what
```

This whole routine is meant to compress to under 3 seconds with practice — it is not meant to be a 30-second visible pause while you plan out loud ("um, let me think about how to structure this..."). If you need visible planning time, it's fine to take a genuine short pause (`01_Foundations/02` on why pauses read fine) — but the goal of drilling this daily (`10_Daily_Practice`) is to make the routine itself instant, so the pause you take is for *content* recall, not *structure* invention.

## Self-Check

- [ ] Before I answered, did I pick a shape, or did I just start talking and hope one emerged?
- [ ] Did I limit myself to 3 supporting points, or did I list everything I could think of?
- [ ] If this was a comparison, did I name the 2–3 dimensions that actually drove the decision, not every dimension that exists?
- [ ] If this was a problem/incident, did I say Problem → Cause → Solution → Result in that order, not the order I discovered it in?

## Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Sweet spot** | The optimal point within a range — here, the working-memory capacity that's neither too little nor too much. |
| **Narrate** | To describe events or reasoning aloud, step by step. |
| **Crowding out** | Displacing something by taking up all the available space or attention. |
| **Walked (a tree, mentally)** | Mentally traced a path through a branching structure, step by step. |
| **Backbone** | The core structural element that everything else depends on or attaches to. |
| **Formalize** | To turn an informal habit or pattern into an explicit, named structure. |
| **Populate** | To fill a structure or template with specific content. |
| **Fires** (a reflex) | Triggers automatically, the way a reflex activates without conscious decision. |

**Next:** [`03_debugging_and_architectural_decision_making.md`](./03_debugging_and_architectural_decision_making.md) — how to apply structured thinking to the reasoning process itself: debugging complex systems, understanding them deeply, and making architectural decisions. From there, [`../03_Explanation_Frameworks/01_core_frameworks_PREP_STAR_SCQA.md`](../03_Explanation_Frameworks/01_core_frameworks_PREP_STAR_SCQA.md) covers the named, formal frameworks that build on these thinking shapes.

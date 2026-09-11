# Project Presentation: Status Updates, Walkthroughs, and Executive Summaries

Three related but distinct formats, each with a different correct altitude (`01_Foundations/03`) and length. Confusing them — giving an executive-summary audience a full technical walkthrough, or giving your team an executive summary when they need implementation detail — is one of the most common and most avoidable presentation mistakes.

## Format 1: Status Updates

### The Universal Status Update Shape

```
STATE   — Green / Yellow / Red, stated first, no ambiguity
WHY     — One sentence justifying the state (only needed for yellow/red)
DELTA   — What changed since the last update (not a re-summary of everything)
RISK    — The one thing most likely to change the state, named proactively
ASK     — What you need from the listener, if anything (often nothing)
```

### Worked Example — Written Status (Slack/email)

> **Status: Yellow.**
> Migration to EKS is 2 days behind the original estimate — we hit an unexpected issue with our ingress controller not supporting a health-check pattern our legacy load balancer had, and we're implementing a workaround rather than restructuring health checks across 12 services under time pressure.
> **Since last update:** completed the networking layer migration (was the riskiest piece — done, stable).
> **Watching:** if the ingress workaround takes more than 2 more days, we'll need to reconsider scope for this sprint.
> **No ask right now** — flagging for visibility; will escalate if the workaround isn't resolved by Thursday.

### Worked Example — Spoken Status (Standup, ~20 seconds)

> "EKS migration — yellow, two days behind. Networking layer's done, which was the risky part. Current blocker is an ingress controller gap, workaround in progress. I'll know by Thursday if that holds the timeline or if I need to flag scope."

### Common Status Update Failure: Burying the State

**Bad:** "So we've been working on the EKS migration, we finished the networking piece which took a while because of some VPC peering complexity, and then we hit an issue with the ingress controller, so overall I'd say we're maybe a couple days behind."

**Why it fails:** the listener has to hold four facts in working memory (`01_Foundations/02`) waiting to learn the one thing they actually need first — are we on track or not. State it first; everything else becomes context for an already-known headline instead of unexplained buildup.

## Format 2: Project Walkthroughs

Used for design reviews, onboarding a new team member to a system, or demoing completed work. Longer than a status update, shorter than a full architecture deep-dive (`07_Architecture_Communication`).

### The Walkthrough Shape

```
1. PURPOSE       What this system/project does, in one sentence, before
                  any detail — orient before you navigate.
2. SCOPE         What's in view for this walkthrough vs. what's explicitly
                  out of scope (prevents scope-creep questions mid-walkthrough).
3. MAIN FLOW     The primary path through the system, at a consistent
                  altitude — pick mid-altitude by default, offer to go
                  deeper on request.
4. KEY DECISIONS 1-2 non-obvious choices and why (this is where seniority
                  shows — see 01_Foundations/03 on trade-off layers).
5. CURRENT STATE Where it stands today — done, in progress, known gaps.
6. QUESTIONS     Explicit invitation, not just a pause at the end.
```

### Worked Example — Opening 45 Seconds of a Project Walkthrough

> "This is the feature-store service — it's what lets our ML models fetch pre-computed features at inference time without recomputing them from raw data on every request. For today I'll walk through the write path and the read path, and I'll skip the batch backfill job since that's a separate, well-understood piece — happy to cover it after if useful.
>
> Main flow: upstream jobs write features into this store on a schedule, keyed by entity ID and feature name. At inference time, the serving layer does a batch lookup — not N individual lookups — which was actually the key design decision: we found early on that per-feature lookups were adding 40ms+ to inference latency at our request volume, so we redesigned the client to batch-fetch everything a model needs in one call.
>
> Current state: write path's been stable for three months. Read path had a rough two weeks after a client library change — that's resolved now, tracked in the postmortem if anyone wants that.
>
> I'll pause here before going deeper — questions on the overall shape before I get into the write path internals?"

Notice step 2 (scope) and the closing explicit invitation are both easy to skip and both do real work — scope prevents the walkthrough from sprawling into a Q&A about the backfill job nobody came to hear about, and an explicit "questions before I go deeper?" gets far more engagement than a passive pause at the end, because it signals *this is a checkpoint*, not just dead air.

## Format 3: Executive Summaries

The shortest, highest-altitude format — written or spoken, but almost always needs to survive being read/heard in under 60 seconds, often by someone who will only engage with the first two sentences.

### The Executive Summary Shape

```
1. OUTCOME/ASK    What happened, or what you need — first sentence, no exceptions.
2. WHY IT MATTERS  Business terms: cost, risk, revenue, time — never
                    purely technical framing.
3. NUMBERS         2-3 hard numbers, no more.
4. NEXT STEP       What happens next, or what decision is needed.
```

### Worked Example — Executive Summary (Written, e.g. top of a doc or email)

> **We're recommending a $340k/year investment in migrating our data platform to Databricks, expected to pay back within 14 months through reduced infrastructure and engineering-hours cost.**
>
> Our current self-managed Spark infrastructure requires roughly 0.75 FTE of ongoing operational maintenance and has caused two SLA-impacting incidents this year from cluster management issues. Databricks eliminates that operational burden and adds governance capabilities (Unity Catalog) that our upcoming SOC 2 audit will require regardless of this decision.
>
> **The numbers:** $340k/year platform cost vs. ~$290k/year in current infra + estimated engineering time, plus removal of a recurring reliability risk that's hard to price but has cost us [X hours] of incident response this year.
>
> **Decision needed:** budget approval by [date] to hit our Q3 migration window before the SOC 2 audit timeline tightens.

Notice: zero mention of Spark internals, cluster configuration, or any implementation detail — every sentence is in business terms (cost, risk, compliance, timeline) even though the underlying content is deeply technical. This is altitude control (`01_Foundations/03`) at its most extreme, and it's the format executives most reliably respond well to.

### The Compression Test for Executive Summaries

Before finalizing, ask: *if this is the only paragraph they read, does it contain everything they need to make a decision or form an accurate impression?* If the answer requires paragraph 3, your first paragraph isn't doing its job — move the load-bearing content up.

## Choosing the Right Format Fast

| You're asked to... | Use format | Target length |
|---|---|---|
| "Give me a status on X" | Status Update | 15–30 sec spoken / 3–5 lines written |
| "Walk me through how X works" | Project Walkthrough | 3–5 min, expandable |
| "Summarize this for leadership" | Executive Summary | Under 60 sec / one paragraph |
| "Present this at the all-hands" | Executive Summary opener + light Walkthrough | 2–3 min total |

## Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Sprawl (into)** | To spread out messily and uncontrolled beyond what was intended. |
| **Dead air** | A silence or pause that reads as passive and empty rather than as an active, deliberate signal. |
| **Load-bearing (content)** | Structurally essential — removing it causes the whole thing to fail, borrowed from architecture. |
| **Burying the lede** | Delaying or obscuring the single most important fact instead of stating it first (adapted from the journalism idiom "bury the lede"). |
| **Orient (before you navigate)** | To establish basic bearings and context first, before moving into detail. |
| **Buildup** | An accumulation of preceding detail that withholds or postpones the main point. |
| **Headline (fact)** | The single most important piece of information, by analogy to a news headline. |

**Next:** [`../07_Architecture_Communication/01_architecture_walkthrough_and_design_review.md`](../07_Architecture_Communication/01_architecture_walkthrough_and_design_review.md) — the deeper, more formal version of the walkthrough format, built specifically for architecture and design review contexts.

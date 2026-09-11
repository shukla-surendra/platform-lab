# Architect & Influence Register — A Starter Active Rotation Set

`surface-vs-deep-lexicon.md` argues that a listener in a meeting never hears the three thousand entries sitting in `vocab.md` — they hear the couple hundred words and phrases that fire unprompted, and that the scarce resource is production reps, not collection size. This chapter is that framework applied to one specific, high-value register: the vocabulary that reads as **architect** (structural, trade-off-aware, precise about scope) and **influential** (owns a position, closes a decision, disagrees without friction) in a design review, a standup, or an interview. Every entry below has already been scored against `surface-vs-deep-lexicon.md` §3 — high frequency fit in real work speech, business/engineering register, fills a gap a vaguer paraphrase currently occupies — so this list can be dropped straight into the Active Rotation queue (§5–6 of that chapter) rather than treated as another deep reservoir to read once and forget.

`architect-influence-rehearsal-script.md` turns this sourcing pool into a daily spoken
rehearsal — a read-aloud monologue plus a seven-day production-rep cycle — for anyone using
this list to actually drill rather than just read. `architect-influence-word-table.md` is
the same twenty entries as one flat table, one row each, for scanning without jumping
between the six sections below. `architect-influence-lexicon.md` is the deep reservoir
these twenty were originally sourced from — 200+ additional architect/leadership terms,
organized by function, not meant for direct drilling (see that file's own note on why).

**This is a sourcing pool, not the queue itself.** The queue is capped at 15–20 items; this list runs to ~20 across six functions, deliberately more than one week's worth. Pull 3–5 per week (§6, step 1), starting with whichever function currently produces the most hesitation in real meetings — that's the gap-sourced signal the framework asks for, not this list's ordering.

## Index

0. [Bare List — For Repetition Drilling](#0-bare-list--for-repetition-drilling)
1. [Opening a Position](#1-opening-a-position)
2. [Naming the Trade-off](#2-naming-the-trade-off)
3. [Signaling Calibrated Judgment](#3-signaling-calibrated-judgment)
4. [Structural Precision](#4-structural-precision)
5. [Disagreeing With Authority](#5-disagreeing-with-authority)
6. [Closing the Decision](#6-closing-the-decision)
7. [First Week's Suggested Slice](#7-first-weeks-suggested-slice)
8. [Glossary](#8-glossary)

---

## 0. Bare List — For Repetition Drilling

No meanings, no examples — just the reps. Read it out loud, daily, until each one fires on its own. Full definitions and example sentences for every item are in §1–6 below if a meaning ever needs a refresher.

1. The way I'd frame this is…
2. My read on this is…
3. The design goal here is…
4. Trade-off
5. That buys us X at the cost of Y
6. Directionally
7. Calibrated
8. First-order / second-order effect
9. Conviction
10. Orthogonal
11. Load-bearing
12. Decouple / Coupling
13. Surface area
14. I'd push back on…
15. I'd flag…
16. Where this breaks down is…
17. Steelman
18. My recommendation is…
19. I'd bias toward…
20. The call I'd make is…

[↑ Back to index](#index)

## 1. Opening a Position

The architect's opening move is to name a frame before giving an opinion — it signals the statement is a considered position, not a reaction.

| Phrase | Meaning | Say it like this |
|---|---|---|
| "The way I'd frame this is…" | Introduces a deliberate lens before the opinion itself | "The way I'd frame this is a build-vs-buy question, not a performance question." |
| "My read on this is…" | States an assessment while marking it as judgment, not fact | "My read on this is the bottleneck is the schema, not the query." |
| "The design goal here is…" | Anchors the discussion to intent before mechanism | "The design goal here is to keep the write path idempotent, everything else is negotiable." |

[↑ Back to index](#index)

## 2. Naming the Trade-off

Naming a trade-off explicitly — rather than arguing one side as if it were free — is the single most architect-coded move in a design conversation.

| Term/Phrase | Meaning | Say it like this |
|---|---|---|
| [Trade-off](vocab.md#trade-off) | A gain accepted at the cost of something else | "There's a trade-off between latency and consistency here." |
| "That buys us X at the cost of Y" | States what's gained and what's given up in one breath | "Caching buys us latency at the cost of staleness." |
| Directionally | Correct in overall trend, without claiming precision | "Directionally, this is the right call — the exact numbers need a spike." |

[↑ Back to index](#index)

## 3. Signaling Calibrated Judgment

Influence reads as precision about *how sure* you are, not just what you think — overclaiming and hedging both cost credibility.

| Term/Phrase | Meaning | Say it like this |
|---|---|---|
| [Calibrated](technical-english.md#calibrate) | Adjusted to match actual confidence or scale, not over- or under-stated | "I'd call this a calibrated guess — 70% confidence, not certainty." |
| First-order / second-order (effect) | The direct consequence vs. the consequence of that consequence | "The first-order effect is faster deploys; the second-order effect is less review discipline." |
| [Conviction](vocab.md#conviction) | The strength of belief behind a stated position | "I'll say this with low conviction — I haven't seen the traffic data." |

[↑ Back to index](#index)

## 4. Structural Precision

The words that describe *how a system is put together* are what separate an architect's description from an engineer's status update.

| Term/Phrase | Meaning | Say it like this |
|---|---|---|
| Orthogonal | Independent of, with no bearing on, another factor | "That concern is orthogonal to this decision — it doesn't change the outcome either way." |
| Load-bearing | Something the rest of the system silently depends on, expensive to remove | "That retry logic is load-bearing — three other services assume it exists." |
| [Decouple](technical-english.md#decouple) / Coupling | Separating (or the degree two components depend on) each other | "This is a tight-coupling problem — decoupling the two services solves it upstream." |
| Surface area | The scope of what a change or system touches or exposes | "That approach has a much smaller surface area — fewer places it can break." |

[↑ Back to index](#index)

## 5. Disagreeing With Authority

Influence is largely the ability to disagree without triggering defensiveness — these constructions do the pushback and the goodwill in the same sentence.

| Phrase | Meaning | Say it like this |
|---|---|---|
| "I'd push back on…" | Disagrees while framing it as a considered position, not a reflex | "I'd push back on that — it optimizes for the common case and breaks the tail case." |
| "I'd flag…" | Raises a concern without yet demanding it be resolved | "I'd flag the retry storm risk before we ship this." |
| "Where this breaks down is…" | Locates precisely the point a proposal stops holding, rather than rejecting it wholesale | "Where this breaks down is at write volume above 10k/s." |
| Steelman | To argue the strongest version of a position, including one you disagree with, before critiquing it | "Let me steelman the other approach before I say why I'd still pick this one." |

[↑ Back to index](#index)

## 6. Closing the Decision

An architect is expected to end a discussion with an owned call, not an open-ended list of options — these phrases close the loop.

| Phrase | Meaning | Say it like this |
|---|---|---|
| "My recommendation is…" | States the owned conclusion after the trade-offs are on the table | "My recommendation is we go with the managed service — the operational cost isn't worth owning." |
| "I'd bias toward…" | States a leaning where the evidence isn't fully conclusive | "I'd bias toward simplicity here — we can always add the abstraction later." |
| "The call I'd make is…" | Explicitly takes ownership of a decision, inviting challenge rather than hiding behind consensus | "The call I'd make is ship behind a flag and roll out gradually." |

[↑ Back to index](#index)

## 7. First Week's Suggested Slice

Per `surface-vs-deep-lexicon.md` §6, add 3–5 candidates to the Active Rotation queue this week, not all twenty at once. If there's no stronger gap-sourced signal yet from a real meeting or Recorded Rep review, start with the highest-leverage cross-functional five:

1. **Trade-off** (§2) — the single most-used architect word, and already a deep-lexicon entry, so the retrieval barrier is low.
2. **"The way I'd frame this is…"** (§1) — usable as the opening line of nearly any technical answer.
3. **"I'd push back on…"** (§5) — the highest-leverage influence phrase; disagreement is the moment fluency usually collapses under pressure.
4. **Calibrated** (§3) — replaces the vaguer, overused "I think maybe."
5. **"My recommendation is…"** (§6) — forces a habit of closing with an owned call instead of trailing off.

Track these with the same three-check counter as any other Active Rotation item (§6 of `surface-vs-deep-lexicon.md`): produced unprompted, outside drilling, in a real context, on three separate days → promoted to Surface, slot freed for the next candidate.

[↑ Back to index](#index)

## 8. Glossary

| Term/Phrase | Meaning |
|---|---|
| Register | The level of formality and vocabulary appropriate to a specific setting or audience |
| Frame | A chosen lens or angle through which a topic is presented |
| Anchor (a discussion) | To fix a conversation to a stated reference point so it doesn't drift |
| Gap-sourced | Selected because a real, observed shortfall exposed the need for it, per `surface-vs-deep-lexicon.md` §3 |
| Leverage (as adjective: high-leverage) | Producing an outsized effect relative to the effort invested |

[↑ Back to index](#index)

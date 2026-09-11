# Phrase Library: Explaining a Bug, a Situation, or an Architecture — Walkthrough Language

`02_comparisons_tradeoffs_architecture.md` covers *describing* a system statically — what it looks like at rest. This file covers *walking someone through* something that unfolds — a bug from symptom to fix, a situation from start to now, a request's journey through a system. That's a different skill: sequencing, cause-and-effect, zooming in and out, and checking the listener is still with you.

## 1. Opening a Walkthrough (Set the Destination First)

- "Let me walk you through what's happening, start to finish — should take about two minutes."
- "I'll explain this chronologically — it'll make more sense in the order it happened than if I jump to the punchline."
- "Quick roadmap before I start: I'll cover what broke, why, and what fixes it."
- "There are three parts to this: the symptom, the cause, and the fix. Let's go in that order."

## 2. Explaining a Bug — Symptom First

- "Here's what the user actually sees: [symptom] — that's the starting point."
- "The observable behavior is [X], but that's a downstream effect, not the cause — bear with me."
- "It only happens under [specific condition] — that's the first clue."
- "It's intermittent, which usually means a race condition or a resource limit, not a straightforward logic bug."

## 3. Explaining a Bug — The Investigation

- "The first thing I checked was [X], to rule out [common cause]."
- "I traced it backward from the error — the stack trace pointed at [Y], but that turned out to be a symptom too."
- "I reproduced it locally by [steps] — that let me isolate it from the noise of production."
- "Once I added logging around [component], the pattern became obvious: [finding]."
- "I ruled out [hypothesis A] and [hypothesis B] before landing on [hypothesis C] — here's why the first two didn't hold up."

## 4. Explaining a Bug — The Root Cause

- "The root cause is [X] — everything else was a symptom of that."
- "Under the hood, what's actually happening is [mechanism] — that's why it only shows up when [condition]."
- "It comes down to a mismatch between [assumption A] and [assumption B] that nobody had reconciled."
- "It's a classic off-by-one / race condition / stale-cache issue — once you see it, it's obvious; it just wasn't obvious going in."

## 5. Explaining a Bug — The Fix and Why It Works

- "The fix addresses the actual cause, not just the symptom — here's the difference."
- "This closes the specific gap: [before] used to allow [bad state]; now it can't."
- "I chose this fix over [alternative] because it doesn't require touching [risky area]."
- "This is the immediate fix; the longer-term fix — to prevent this whole class of bug — is [X], which I'll track separately."

## 6. Walking Through Code or a Function, Verbally

- "Starting from the entry point: this function takes [input], and the first thing it does is..."
- "Skip the validation block for now — the interesting part is what happens after line [X]."
- "This branch handles the common case; this other branch is the edge case we care about here."
- "The state gets mutated in exactly one place — that's this line — which is what makes this bug possible."
- "Follow the data, not the code: it comes in as [X], gets transformed into [Y], and ends up as [Z]."

## 7. Explaining "What Happened" in a Situation (Non-Technical-Friendly)

- "Here's the short version of what happened, then I'll add detail if useful."
- "Three things happened, roughly in this order: [1], [2], [3]."
- "The turning point was [X] — everything before that was normal, everything after was reacting to it."
- "None of the individual pieces were unusual on their own; it was the combination that caused the problem."

## 8. Cause-and-Effect Chaining Language

- "[X] caused [Y], which in turn triggered [Z] — it's a chain, not a single failure."
- "That's a downstream effect of [root cause], not a separate issue."
- "One led to the other: because [A] happened, [B] became inevitable."
- "It's correlation, not causation — [X] and [Y] happened together, but [X] didn't cause [Y]; both came from [Z]."

## 9. Zooming In and Out Mid-Explanation

- "Zooming out for a second — the big picture is [X]. Now zooming back into the detail..."
- "That's the ten-thousand-foot view; if you want, I can go one level deeper into [specific part]."
- "I'm going to go deep on this one part because it's the part that matters — the rest you can take on faith."
- "Stepping back from the mechanism for a second: the impact on the user was [X]."

## 10. Checking the Listener Is Still Following

- "Does that part make sense before I go further, or should I back up?"
- "I realize I skipped a step there — want me to fill that in?"
- "That's the hardest part to explain verbally — happy to draw it if that's easier."
- "Let me know if I'm going too fast, or too slow, and I'll adjust."

## 11. Using a Quick Analogy Mid-Explanation

- "Think of it like [everyday analogy] — [system component] is basically the [analogous everyday role]."
- "It's the same pattern as [familiar system] — if you know how that works, this will feel familiar."
- "The simplest way to think about it: [component] is just a queue with extra rules."

## 12. Explaining a System Architecture as a Journey (Not a Static Diagram)

- "Follow one request end to end: it lands here, gets routed to..., and finally..."
- "Let's trace a single piece of data from ingestion to the point it's served to a user."
- "At each stage, ask 'what can go wrong here' — that's usually the fastest way to understand a system's actual shape."
- "The interesting part isn't the happy path — it's what happens at [failure point] when [dependency] is slow or down."

## 13. Explaining Why It's Built This Way (Design Rationale)

- "It's built this way because of a constraint that isn't obvious from the diagram: [X]."
- "This looks more complex than it needs to be until you know it has to handle [edge case]."
- "The simple version existed first; this version exists because the simple one broke under [condition]."
- "If I were designing this today with no history, I might do it differently — but here's why it evolved this way."

## 14. Practice Drill

Pick a real bug you've fixed recently. Explain it out loud in under two minutes using this shape: symptom (§2) → investigation (§3) → root cause (§4) → fix (§5). Then do the same for a piece of architecture you know well, but framed as a journey (§12) instead of a static description. Notice which one is harder — most people default to describing structure and have to consciously practice narrating sequence.

## Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Unfolds** | Develops or reveals itself gradually over time, rather than being fixed and static. |
| **At rest** | Static, idle, or unchanging — what a system looks like when nothing is currently happening to it. |
| **Zoom in / zoom out** | To shift deliberately between fine-grained detail and the broader, high-level picture while explaining something. |

**Next:** [`08_assertive_communication_conflict.md`](08_assertive_communication_conflict.md) — assertive communication and conflict scenarios specific to engineering, MLOps, and cloud-architecture work.

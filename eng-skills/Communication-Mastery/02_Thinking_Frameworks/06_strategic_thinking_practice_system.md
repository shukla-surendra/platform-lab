# Strategic Thinking — A Practice System

`01`–`03` train how you organize and deliver a decision once you've made it. `04` is a reference catalogue of the models that make decisions better. Neither one, on its own, makes your *decisions* better — reading a catalogue of mental models produces recognition ("oh yeah, inversion, I know that one"), not the reflex to reach for it live, under real constraints, on a real problem. This chapter is the missing piece: a regularly-applied practice system for the thinking itself, built on the same logic as `10_Daily_Practice` — skill comes from repeated retrieval on real material, not from reading.

## Why "Read The Mental Models List" Doesn't Work

`04`'s own usage note says to apply one model to a real decision monthly. In practice that's too infrequent to build a reflex — a habit exercised once a month is re-learned, not strengthened, each time. The fix isn't a longer list or a better-written one; it's a shorter feedback loop, applied to problems you already have, on a fixed cadence, with the outcome checked later. That last part — checking the outcome — is the piece almost everyone skips, and it's the actual mechanism that separates someone whose judgment improves year over year from someone who's made the same-quality decision confidently for a decade.

Three strategies below, each solving a different failure mode:

| Failure mode | Strategy |
|---|---|
| Committing to the first workable idea and calling it "the solution" | **Strategy 1 — Options-First (3 Before 1)** |
| Knowing the mental models but not reaching for them under real pressure | **Strategy 2 — The Weekly Model Rotation** |
| Feeling confident in a decision with no way to know if that confidence is earned | **Strategy 3 — The Decision Journal** |

## Strategy 1: Options-First Thinking ("3 Before 1")

**The failure this fixes:** the first workable idea arrives, relief kicks in (same mechanism as `05_removing_hurry_pause_before_acting.md`), and everything after that is evaluation and rationalization of that one idea rather than a genuine search. It gets called "the best solution" because it's the *only* solution that was ever actually considered.

**The rule:** for any decision that isn't trivially reversible or cheap, write three genuinely different one-line options before writing a single word evaluating any of them.

```
Question: "How do we stop this job from timing out?"

WRONG (1 idea, dressed up as analysis):
  "We should increase the timeout." → paragraph justifying it.

RIGHT (3 before 1):
  1. Increase the timeout (treats the symptom, buys time).
  2. Profile and fix the actual slow stage (treats the cause).
  3. Split the job into smaller units that can't individually time out
     (changes the failure mode entirely — no single unit is big enough
     to hit the ceiling).
  → NOW evaluate: option 2 is right if the slow stage is fixable this
    sprint; option 3 is right if the data volume keeps growing regardless.
    Option 1 alone is only right as a stopgap while 2 or 3 happens.
```

**What makes an option "genuinely different," not a variation:** it should change a different variable. "Increase the timeout to 10 minutes" and "increase the timeout to 15 minutes" are one option, not two. A real second option changes the *mechanism* — build vs. buy, sync vs. async, fix-the-cause vs. treat-the-symptom, centralize vs. distribute, do-it-now vs. deliberately-defer-with-a-stated-trigger.

**If you get stuck on option 2 or 3:** use Inversion (`04` §3) — "what would guarantee this keeps happening?" — or ask what the answer would be if the obvious/cheap/fast option were explicitly off the table. Forcing constraints is the fastest way to generate a real second option when the first one is crowding everything else out.

This is `03_debugging_and_architectural_decision_making.md`'s OPTIONS step made into a standalone habit you apply below the threshold of a formal architecture decision — a config choice, a bug fix approach, a one-line design call in a PR. The discipline scales down; most people only apply it when it's already labeled "big decision," which is exactly when it's too late to catch the smaller decisions compounding underneath it.

## Strategy 2: The Weekly Model Rotation

**The failure this fixes:** `04`'s catalogue is large enough that under real time pressure, you default to whichever two or three models you already think in, and the other fifteen sit unused indefinitely — not because they're less useful, but because they were never rehearsed against a live problem.

**The drill (10 minutes, once a day, rotating through the week):** pick a real, currently-unresolved problem or decision from your actual work — not a hypothetical. Apply that day's model to it deliberately, in writing, even if you end up doing something else in the end. The point is the rep, not that every application produces a change of plan.

```
MONDAY      Circle of Competence — where's the actual boundary of what
            I know here, versus what I'm assuming?
TUESDAY     Inversion — what would guarantee this fails, and is any of
            that currently true?
WEDNESDAY   Second-order thinking — if this works, then what happens
            next, and what happens after that?
THURSDAY    Pre-mortem — assume this decision failed in 3 months; what's
            the most likely reason?
FRIDAY      Chesterton's Fence / Occam's Razor — for anything I'm about
            to remove or simplify: do I know why it's there, and is the
            simpler option actually equal in power, not just simpler?
SATURDAY    Stakeholder Matrix or Pareto — pick whichever fits something
            live: who actually needs to be managed vs. informed here,
            or which 20% of this is driving 80% of the pain?
SUNDAY      Free choice — whichever model from `04` you noticed yourself
            needing this week but didn't reach for. That gap IS the log
            entry for next week.
```

Write the application in one or two sentences, not an essay — that sentence is the entire rep. Three more examples of what a real entry looks like:

```
TUESDAY (Inversion) — goal: "improve deploy reliability."
  What would guarantee bad deploys? No rollback tested in the last
  quarter. That's actually true right now. Fixing that is higher
  priority than the dashboard I was about to build instead.

WEDNESDAY (Second-order thinking) — decision: "add a Redis cache in
  front of the pricing service."
  1st order: latency drops. 2nd order: pricing can now be stale for
  up to the TTL, which I hadn't stated anywhere. 3rd order: finance's
  reconciliation job assumes pricing is always live — a stale read
  during their nightly run would silently produce a wrong number
  they'd trust. Added explicit cache-bypass for that one job before
  shipping, instead of after someone noticed.

FRIDAY (Chesterton's Fence) — about to delete: a retry loop that
  looks redundant now that the client has its own retries.
  Checked git blame before removing it: it was added after an
  incident where the client's retries were disabled by a config bug,
  and this was the only thing that kept requests succeeding that day.
  Not removing it — flagged the redundancy in a comment instead, so
  the next person has the context I almost didn't look for.
```

Do this daily and the model stops being an entry in a list and becomes a question your brain asks unprompted, the same way the answer-first reflex in `01` eventually fires without conscious effort.

## Strategy 3: The Decision Journal (The Actual Feedback Loop)

**The failure this fixes:** without this, "getting better at strategic thinking" has no feedback signal at all. You feel more confident over time regardless of whether your decisions are actually improving, because confidence and accuracy are trained by completely different things — confidence grows from repetition alone; accuracy only grows from finding out whether you were right. This is the single highest-leverage habit in this chapter, and the one most people skip because it doesn't feel productive in the moment.

**At decision time**, for anything Type 1 (hard to reverse, per `04` §4) or with real cost either way, write four lines before acting:

```
DECISION:            [one sentence — what you're doing]
OPTIONS CONSIDERED:  [the 3 from Strategy 1, in one line each]
CONFIDENCE:          [rough %, e.g. "70% this is right"]
EXPECTED RESULT:     [what you predict happens, specifically enough
                      to be provably right or wrong later]
```

**Seal it.** Don't reread it until the review date.

**At a set interval later** (2–4 weeks for most engineering decisions; longer for hires, architecture, or anything whose consequences take time to surface), reopen it and add:

```
ACTUAL RESULT:       [what actually happened]
CALIBRATION:         [was the confidence % about right, too high, or
                      too low? — this is the number that should trend
                      toward accurate over months of entries]
WHAT I'D CHANGE:     [one sentence — not a full retro, just the one
                      thing that would've made this decision better,
                      knowable only in hindsight]
```

**Worked example, start to finish:**

```
--- Written 2026-06-10, sealed ---
DECISION:            Moving the recommendation service from a shared
                      RDS instance to its own dedicated database.
OPTIONS CONSIDERED:  1. Dedicated DB now. 2. Add read replicas to the
                      shared instance instead. 3. Do nothing until the
                      shared instance actually shows contention.
CONFIDENCE:          65% this is the right call at this time.
EXPECTED RESULT:     Query p99 for the recommendation service drops
                      below 150ms within 2 weeks, with no measurable
                      impact on the other services still on the shared
                      instance.

--- Reopened 2026-06-28 ---
ACTUAL RESULT:       p99 dropped to 90ms — better than predicted. But
                      the migration took 3 days longer than planned
                      because of an undocumented cross-service query
                      that assumed co-location, discovered only after
                      cutover.
CALIBRATION:         65% was about right on "was this the correct
                      decision" — it clearly was. It was miscalibrated
                      on a question I never actually asked: how
                      confident was I in the migration effort estimate?
                      That gap is the real lesson, not the decision
                      itself.
WHAT I'D CHANGE:     Add "map cross-service query dependencies" as an
                      explicit step before estimating any data-layer
                      migration, not just before executing it.
```

Notice the useful finding here wasn't "was the decision right" — it usually is, roughly, most of the time, for anyone with reasonable judgment. It was the *specific, nameable gap* (effort estimation on migrations, not decision quality) that only shows up because the prediction was written down concretely enough to be wrong in a specific way. A vague journal entry ("this seemed like the right move") can't produce this kind of finding — only a checkable one can.

**Why the confidence percentage matters more than it looks like it should:** most people's stated confidence is either always ~90% (overconfidence, never corrected because it's never checked) or vague ("pretty sure") in a way that can't be scored at all. Writing an actual number, and checking it against reality later, is what turns "I have good instincts" from a belief into something you can actually verify — and specifically where you're miscalibrated (consistently overconfident on architecture calls but underconfident on people calls, for instance) is exactly the kind of pattern you cannot see without the log, the same way `13_Common_Mistakes` says you can't see your own recurring communication mistake without a recording.

**Where to keep it:** a single running note, dated entries, oldest at the bottom. Five minutes to write, five minutes to close out — the cost is trivial next to what a single well-calibrated Type 1 decision is worth.

## Putting It Together: A Realistic Weekly Cadence

```
DAILY (10 min)     Strategy 2 — one model, one real problem, one written
                    sentence. Folds into 10_Daily_Practice as an optional
                    extra block, or stands alone if you're not running
                    that system.
AS NEEDED           Strategy 1 — every time a non-trivial decision is
                    about to be made, 3 options before any evaluation.
                    This isn't scheduled; it's a trigger-based habit —
                    the trigger is "I'm about to commit to the first
                    idea."
WEEKLY (10 min)     Open the Decision Journal. Log any new Type 1
                    decisions from the week. Close out any whose review
                    date has arrived.
MONTHLY (15 min)    Read back 4–6 weeks of closed-out journal entries.
                    Look specifically for a calibration pattern — a
                    category where confidence and outcome consistently
                    diverge. That pattern is next month's actual focus,
                    not a new model from the catalogue.
```

## Self-Check

- [ ] Before committing to this decision, did I write 3 genuinely different options, or did I evaluate the first idea that arrived?
- [ ] Is today's model rotation entry about a real, current problem, or a hypothetical I made up to fill the block?
- [ ] For my last Type 1 decision, does a sealed journal entry exist with a stated confidence number and a checkable prediction?
- [ ] When I last reopened a journal entry, was I honest about the calibration gap, or did I quietly reinterpret the prediction to match what happened?

## Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Rationalization** | Constructing after-the-fact justification for a decision already made, rather than genuinely evaluating it. |
| **Crowding out** | Displacing something by taking up all the available space or attention. |
| **Calibration / calibrated** | How accurately stated confidence matches actual outcomes over time. |
| **Stopgap** | A temporary fix that holds things together without solving the underlying problem. |
| **Sealed** (an entry) | Closed off from further editing until a set later date, to preserve an honest record. |
| **Nameable** (gap) | Specific and identifiable enough to be stated precisely, rather than vague. |
| **Dressed up as** | Presented or disguised as something more legitimate than it actually is. |
| **Compounding** | Accumulating and building on itself over time, so small effects become large ones. |

**See also:** [`04_mental_models_operating_system.md`](./04_mental_models_operating_system.md) — the model catalogue this chapter's rotation drill pulls from; [`03_debugging_and_architectural_decision_making.md`](./03_debugging_and_architectural_decision_making.md) — the CONTEXT/CONSTRAINTS/OPTIONS/TRADE-OFFS/DECISION/CONSEQUENCES skeleton that Strategy 1 is the lightweight, everyday version of; [`../10_Daily_Practice/01_daily_and_weekly_practice_system.md`](../10_Daily_Practice/01_daily_and_weekly_practice_system.md) — the parallel practice system for communication delivery, which this chapter mirrors for thinking quality instead.

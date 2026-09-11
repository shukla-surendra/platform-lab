# Common Mistakes: Causes and Fixes

Every mistake here maps back to a mechanism from `01_Foundations` — the goal is recognizing your specific pattern, not vaguely trying to "communicate better."

## Structural Mistakes

### 1. Chronological Instead of Answer-First

**What it looks like:** "So first we tried X, then we noticed Y, then after some investigation we found Z, and eventually that led us to..." — the actual point arrives last.

**Why it happens:** you're navigating your own memory graph in retrieval order instead of choosing an entry point before speaking (`01_Foundations/01`).

**Fix:** the Answer-First Reflex Drill (`02_Thinking_Frameworks/01`). Specifically notice: is your answer literally your *last* sentence right now? If so, cut everything before it, say it first, then use the rest as supporting material.

### 2. No Explicit Structure Signposting

**What it looks like:** a genuinely well-organized explanation that still feels hard to follow, because the listener can't tell when you've moved from one point to the next.

**Why it happens:** the structure exists in your head but was never made audible.

**Fix:** use explicit transition phrases (`05_Phrase_Library/01`, Section 6-7) — "there are three things here, first..." Announce the shape before delivering it.

### 3. Burying the Lede in Written Communication

**What it looks like:** a Slack message or doc where the actual point is in paragraph 3.

**Why it happens:** written communication removes the time pressure that forces answer-first thinking verbally, so the habit doesn't transfer automatically — it has to be practiced separately.

**Fix:** the compression test from `06_Project_Presentation/01` — if someone only reads your first sentence, does it contain the point?

### 4. No MECE Grouping in Multi-Point Arguments

**What it looks like:** a list of "reasons" that actually overlap with each other, or that misses the one reason that mattered most, making the argument feel padded or unconvincing.

**Why it happens:** points get added by free association rather than deliberate categorization.

**Fix:** the MECE check in `03_Explanation_Frameworks/02` (Pyramid Principle) — before presenting, verify your groups don't overlap and aren't missing the biggest driver.

---

## Language Mistakes

### 5. Completeness Bias / Over-Explaining

**What it looks like:** every caveat, every alternative considered, every acronym's full expansion, all included, every time — the listener disengages before the point arrives.

**Why it happens:** engineering training rewards exhaustiveness (missed edge cases break systems); that instinct wrongly transfers to conversation, where the actual risk is the opposite (`01_Foundations/01`).

**Fix:** decide your altitude and target length *before* speaking (`01_Foundations/03`). Practice the Compression Ladder exercise (`11_Exercises/3.6`) to build comfort cutting detail deliberately.

### 6. Unexplained Jargon (Curse of Knowledge)

**What it looks like:** terms like "backpressure," "idempotent," or "shuffle spill" used as if self-explanatory, because they stopped feeling like jargon to you once you fully understood them.

**Why it happens:** the curse of knowledge (`01_Foundations/02`) — you can no longer simulate not knowing what you know.

**Fix:** run a Feynman pass before high-stakes explanations (`03_Explanation_Frameworks/02`). When in doubt, define the term in one clause the first time you use it: "backpressure — basically the system telling upstream to slow down — is what..."

### 7. Hedging Language That Undermines Authority

**What it looks like:** "I think maybe this could possibly be because..." when you actually have a confident, well-reasoned answer.

**Why it happens:** discomfort with sounding too certain, especially when the audience includes more senior people — often overcorrection from a good instinct (not wanting to overstate confidence) into an instinct that undersells real expertise.

**Fix:** reserve hedging for genuine uncertainty, and calibrate it precisely (`05_Phrase_Library/01`, Section 9) — "I don't have a confident answer" for real uncertainty, but a flat declarative for things you actually know.

### 8. Vague Quantifiers Instead of Real Numbers

**What it looks like:** "a lot of errors," "it took a while," "significantly faster" — imprecise where precision was available and would have been more convincing.

**Why it happens:** habit, or not having the number readily retrievable in the moment.

**Fix:** the Concrete Detail Rule (`04_Technical_Storytelling/01`) — prepare at least one real number for any recurring story before you need to tell it.

---

## Delivery Mistakes

### 9. Filling Every Pause With Filler Words

**What it looks like:** "um," "so basically," "kind of," "you know" appearing every few seconds, especially at decision points in the explanation.

**Why it happens:** silence aversion — a brief pause feels far longer to the speaker than it actually is, and feels riskier than it actually is (`01_Foundations/01`, `01_Foundations/02`).

**Fix:** deliberate pause practice (`10_Daily_Practice`) — replace the filler with genuine silence, even briefly. Recording yourself (`12_Recording_Analysis`) is the fastest way to notice the actual frequency, which is usually higher than self-perception suggests.

### 10. Speeding Up When Uncertain

**What it looks like:** pace increases noticeably at exactly the point where structure or content gets shaky, as if trying to rush past the weak spot.

**Why it happens:** an unconscious attempt to minimize time spent in the uncomfortable, high-social-load moment of not knowing exactly what to say next.

**Fix:** counter-intuitively, slow down deliberately when you notice uncertainty rising — it buys more actual thinking time than speeding up does, and it reads as composed rather than rattled. Practice this explicitly in recorded reps. The same impulse shows up outside live delivery too — see `02_Thinking_Frameworks/05_removing_hurry_pause_before_acting.md` for the written-reply and debugging versions of it.

### 11. Losing Structure Mid-Answer and Not Recovering Visibly

**What it looks like:** trailing off, restarting three different ways, never landing anywhere clean.

**Why it happens:** no rehearsed recovery move — the derailment itself isn't the problem (it happens to everyone), the lack of a clean recovery is.

**Fix:** the explicit recovery phrases in `09_Meeting_Communication/01` ("let me restart that more cleanly — the core point is...") — rehearse this move specifically, since it's used under exactly the pressure that makes improvisation hardest.

### 12. Monotone / Flat Delivery on Key Points

**What it looks like:** the trade-off, the recommendation, the actual answer — delivered at the same energy as everything else, so it doesn't register as the important part.

**Why it happens:** focus is entirely on content correctness, with no attention paid to vocal emphasis as a structural signal.

**Fix:** deliberately mark your answer sentence and your so-what sentence with a slight pause before and a touch more emphasis — vocal signposting mirrors the verbal signposting from Mistake #2.

---

## Storytelling Mistakes

### 13. All Setup, No Tension

**What it looks like:** "we had an issue, we fixed it, it's better now" — technically complete, immediately forgotten.

**Why it happens:** engineers under-value showing the wrong turn or false lead, worried it makes them look less competent, when the opposite is usually true (`04_Technical_Storytelling/01`).

**Fix:** deliberately include one honest "we initially thought X, but..." moment in every incident/project story.

### 14. "We" Instead of "I" in Behavioral Answers

**What it looks like:** an interview STAR answer entirely in "we decided," "we noticed," "we built" — leaving the interviewer unable to assess individual contribution.

**Why it happens:** natural team-first framing, appropriate in most contexts, but specifically wrong for behavioral interviews where individual judgment is what's being evaluated (`03_Explanation_Frameworks/01`).

**Fix:** explicitly switch to "I" for the Action section of STAR, even when discussing team decisions — "the team was leaning toward X; I specifically pushed for Y because..."

---

## Meta-Mistake: Trying to Fix Everything at Once

**What it looks like:** after reading this list, attempting to simultaneously fix answer-first structure, filler words, pacing, storytelling, and jargon in the very next explanation you give.

**Why it happens:** enthusiasm after diagnosis, but it overloads working memory in exactly the way `01_Foundations/02` describes — you can't consciously monitor five things while also generating content live.

**Fix:** pick the single most common mistake from your own recordings (per the self-review checklist, `12_Recording_Analysis/02`) and focus on that alone for a full week before adding a second focus area.

## Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Burying the lede** | Journalism idiom: placing the most important point deep in a piece of writing/speech instead of upfront. |
| **Signposting** | Explicitly announcing structure aloud ("there are three things here") so a listener can track where the explanation is going. |
| **Overcorrection** | Swinging too far in fixing one problem, so far that it creates a new, opposite problem. |
| **Hedging** | Softening a statement with qualifiers ("maybe," "possibly") to avoid sounding too certain. |
| **Declarative** | Stated plainly and directly, as fact, without qualification. |
| **Counter-intuitively** | In a way that goes against what instinct would suggest is the right approach. |
| **Rattled** | Visibly unsettled or thrown off composure, as opposed to remaining calm under pressure. |
| **Derailment** | A sudden loss of structure or direction mid-explanation, veering off the intended track. |

**Next:** [`../14_Advanced/01_case_studies.md`](../14_Advanced/01_case_studies.md) — full end-to-end case studies applying everything in this repository to realistic, complex scenarios.

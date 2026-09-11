# Dev → Architect: A Growth Track for Mental Models, Communication, and Thinking

Technical judgment, communication, and thinking process don't level up separately — they compound together, and the gap between levels is mostly a gap in *which questions you've trained yourself to ask by default*, not raw technical ability. This file is the integration layer: it sequences `02_Thinking_Frameworks/04_mental_models_operating_system.md` and the rest of this curriculum into four stages, names what actually changes in your thinking at each one, and adds the architect-specific mental models that don't exist anywhere else in this repo yet.

Use it as a map, not a ladder to climb once — re-read the stage above your current one every few months; you'll notice models that didn't make sense before starting to click.

---

## Stage 1: Developer — "Does this work?"

**The mental shift:** from "does this compile / pass the test" to "does this actually solve the problem, including the cases nobody wrote a ticket for."

**Mental models to install** (`02_Thinking_Frameworks/04_mental_models_operating_system.md`):
- §1 Foundational Truths, all five — this is the bedrock; everything later assumes these are already reflexive.
- §2 Overriding Default Behavior — Hurry Bias and Face-Saving Default specifically. Most junior-level mistakes are these two defaults firing unchecked, not a knowledge gap.
- §5 State-space thinking — design all five states (empty, loading, partial, error, ideal) for anything you build, every time, before it's asked for.

**Communication skill this stage demands:**
- `03_Explanation_Frameworks/01` (PREP) — answer-first, every time someone asks you a status question. This alone is the highest-leverage communication skill at this stage.
- `05_Phrase_Library/03_recommendations_disagreement_feedback.md` §5 (Receiving Pushback on Your Own Work Gracefully) — this stage gets the most code review; how you receive it shapes your reputation faster than your code does.

**Thinking process shift:** from reactive ("fix what's flagged") to a standing checklist you run on your own work before anyone else sees it — the five states, the obvious edge cases, one re-read for "would future-me understand this with no context."

**Practice drill:** before marking anything done, run the Hurry Bias override explicitly (`02_Thinking_Frameworks/04_mental_models_operating_system.md` §2): "what would surface if I gave this twice the time?" Do this even when it feels unnecessary — especially then.

---

## Stage 2: Senior Developer — "Will this still work?"

**The mental shift:** from correctness at the moment of writing to correctness under change — time passing, scale increasing, other people touching the code, requirements shifting under you.

**Mental models to install:**
- §1 Reversibility and §4 Type 1/2 decisions — you're now making calls with real blast radius; classify before deciding, not after.
- §5 Design for failure, Omega/Alpha Mess triage — you're now expected to know which bad code to leave alone and which to fix.
- §3 Second-order thinking, Chesterton's Fence — "why is this here" needs a real answer before you remove it, and "what happens next" needs an answer before you ship it.
- §11 Swiss Cheese Model and Checklists Beat Memory Under Load — you're now trusted with higher-stakes actions (deploys, migrations); build the layers and the checklist rather than relying on carefulness.

**Communication skill this stage demands:**
- `07_bug_and_system_walkthroughs.md` in full — you're now the person others come to when something breaks; narrating symptom → investigation → root cause → fix clearly is a core job function now, not a nice-to-have.
- `08_assertive_communication_conflict.md` §2–§9 — saying no to scope creep, pushing back on deadlines, giving critical code review feedback without either softening it into uselessness or making it land as an attack.

**Thinking process shift:** from "what does this need to do" to "what does this need to keep doing, and what would break it later." You start writing tests for the failure you can imagine, not just the happy path someone asked for.

**Practice drill:** pick a system you own. Run a Pre-mortem (`02_Thinking_Frameworks/04_mental_models_operating_system.md` §3) on it right now, unprompted — assume it broke in production last week, and write down what most likely caused it. Fix the highest-confidence answer before it happens for real.

---

## Stage 3: Tech Lead / Staff Engineer — "Should this exist, and who else does it affect?"

**The mental shift:** individual output stops being the primary lever. The job becomes multiplying other people's output and making calls that affect a team, not just a codebase.

**Mental models to install:**
- §6 Staff+ leverage archetypes (Tech Lead, Architect, Solver, Right Hand) — know explicitly which mode a given moment calls for; this is the single highest-leverage model at this stage.
- §4 Expected value, Stakeholder Matrix, Parkinson's Law — decisions now involve other people's time and priorities, not just your own judgment.
- §11 Decision Rights Before the Decision — you're now making calls that affect people who didn't get a vote; make the "who decides, who's consulted, who's informed" split explicit before it becomes a complaint.
- §5 Ubiquitous Language, Conway's Law — cross-team friction starts showing up now; both of these are diagnostic tools for it.

**Communication skill this stage demands:**
- `06_grilling_challenge_questions.md` in full — design reviews and leadership updates start including real pressure-testing; recognizing the question pattern (past-accountability vs. future-alternative vs. evidence-demanding) keeps you composed under it.
- `09_Meeting_Communication` and `05_Phrase_Library/05_stakeholder_leadership_interview.md` §2–§4 — you're now translating between your team and people who don't share your context by default.
- `08_assertive_communication_conflict.md` §10–§16 — being talked over, redirecting derailed meetings, cross-team and turf conflict all become regular occurrences, not edge cases.

**Thinking process shift:** from "what's the right answer" to "what's the right answer given this team's actual constraints, and how do I get five people aligned on it without personally deciding for all of them." You start optimizing for decisions that don't need you in the room to execute correctly.

**Practice drill:** the next time you're about to make a call unilaterally because it's faster, stop and name the decision rights explicitly first (§11) — even if the answer is "it's mine to make alone," say that out loud rather than assuming it.

---

## Stage 4: Architect — "What shape should this have, for people I'll never meet?"

**The mental shift:** from decisions that affect the current team to decisions that outlive any one project, get inherited by engineers who join after you've moved on, and shape what's *easy* and what's *hard* for years. The job is setting the terrain other people build on, not building on it yourself most of the time.

**New mental models — architect-specific, not yet covered elsewhere in this repo:**

**Architecture Decision Records (ADRs) as a forcing function.** Write the decision down before it's final: context, options considered, the choice made, and the consequences accepted — not after, as documentation theater. The act of writing forces the trade-off into the open while it's still cheap to change (ties to Reversibility, §1); a decision that can't survive being written down plainly usually wasn't as settled as it felt in the room.

**Technology Radar — staged adoption, not a binary adopt/reject.** Classify any new technology as Hold / Assess / Trial / Adopt rather than a single yes-or-no. Most bad technology bets come from skipping straight to "Adopt" on something only ever validated at "Trial" scale. Pairs directly with the Boring Technology principle (§5) — the radar is how innovation tokens get spent deliberately instead of impulsively.

**The cost-of-change curve.** The cost of fixing a decision rises non-linearly the later it's caught — cheap in design, more expensive in code review, expensive in production, extremely expensive once external consumers depend on it. An architect's real job is shifting *where on this curve* mistakes get caught, not eliminating mistakes entirely — that's not achievable, catching them earlier is.

**Non-functional requirements are first-class, not an afterthought.** Latency, availability, security, and cost targets are requirements, exactly as binding as functional ones — they get skipped only because nobody asks for them explicitly the way a stakeholder asks for a feature. Part of the job is asking on their behalf, every time, before design starts rather than after an incident.

**Decisions made on behalf of people you'll never meet.** The real distance between senior engineer and architect is a distance in who's affected by your calls — from your current teammates to an engineer joining in two years who inherits a decision with zero memory of why it was made. Write and design for that specific person (ties to "code is a communication artifact," §1) — they're the actual audience, more than the reviewer in the room today.

**Communication skill this stage demands:**
- `07_Architecture_Communication` in full — design reviews, whiteboard walkthroughs, and describing diagrams in words are now a primary job function, not an occasional task.
- `05_Phrase_Library/02_comparisons_tradeoffs_architecture.md` in full — describing architecture verbally, presenting trade-offs, and giving recommendations need to be fluent, not assembled live under pressure.
- `05_Phrase_Library/05_stakeholder_leadership_interview.md` §3, §6, §12–§14 — executive-compressed communication, explaining failures to leadership, cost/budget conversations become routine.
- `08_assertive_communication_conflict.md` §17–§19 — pushing back on unrealistic AI/ML expectations, cost pushback, and holding the line on security/compliance are now regularly your call to make and defend.

**Thinking process shift:** from "what's correct" to "what's correct, cheap to change later, understandable to someone with none of my context, and worth the organizational cost of getting agreement on." Every decision now has three audiences at once — the system, the team building it, and the org paying for it — and a good answer accounts for all three, explicitly, not just the one that's loudest in the room.

**Practice drill:** take a real architectural decision you're currently sitting on. Write it as a one-page ADR — context, options, choice, consequences — before discussing it with anyone. Notice which part is hardest to write down plainly; that's usually the part of the decision that was actually the least settled.

---

## Moving Between Stages: A Self-Check

Don't wait for a title change to start operating at the next stage — the mental models transfer immediately; the title is a lagging indicator, not a prerequisite.

- **1 → 2:** Are you finding your own edge cases before review, consistently, without being asked? Are you the one others ask "will this hold up" rather than the one being asked?
- **2 → 3:** Are people outside your immediate task asking for your input on decisions before they're made, not just your review after? Are you noticing when a disagreement is really a decision-rights gap, not a technical one?
- **3 → 4:** Are you being asked to weigh in on decisions before there's a concrete proposal — on the *shape* of the problem, not a specific solution? Do people two teams away know your name because of a decision you made, not a project you shipped?

## The Combined Weekly Loop

Run this alongside `10_Daily_Practice` — this is the leveling-specific layer on top of it:

```
WEEKLY:
  Pick one mental model from your current stage (above) that you did NOT
  consciously apply this week. Name a real decision from this week where
  it would have applied. That gap is more informative than any hypothetical.

MONTHLY:
  Re-read the stage above your current one, in full, even if it doesn't
  feel relevant yet.
  Do one practice drill from that next stage, on real work, not a toy example.

QUARTERLY:
  Run the Self-Check above, honestly. If you're clearly operating a stage
  higher than your title, that's a conversation to have deliberately
  (see 05_Phrase_Library/05_stakeholder_leadership_interview.md §2)
  — not a grievance to sit on.
```

---

*This is the end of the core curriculum. Return to [`../README.md`](../README.md) for the suggested learning path, [`02_challenges_30_60_90.md`](./02_challenges_30_60_90.md) to start a structured program, or [`04_recommended_resources.md`](./04_recommended_resources.md) for further reading.*

## Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Bedrock** | The fundamental, foundational layer that everything else is built on. |
| **Reflexive** | Automatic and instinctive, performed without conscious deliberation. |
| **Blast radius** | The scope of impact a decision or failure could have, borrowed from explosives. |
| **Triage** | To sort and prioritize problems by severity, deciding what needs attention first (borrowed from medicine). |
| **Forcing function** | A mechanism or step deliberately built into a process to compel a certain behavior or decision. |
| **Documentation theater** | Writing documentation only for appearance's sake, after a decision is already final, rather than as a genuine forcing function. |
| **Non-linearly** | Increasing at a rate that isn't proportional or steady — here, costs that spike rather than climb evenly. |
| **Terrain** (metaphor) | The underlying landscape or constraints that shape what's easy or hard for others building on top of it. |
| **Unilaterally** | Done by one party alone, without consulting or involving others affected by it. |
| **Turf conflict** | Disputes over territory, authority, or ownership between people or teams. |
| **Lagging indicator** | A signal that only shows up after impact has already occurred (here, a title lagging behind actual scope of work). |
| **A ladder to climb (once)** | Idiom used negatively here: something meant to be revisited repeatedly, not a one-time linear progression. |

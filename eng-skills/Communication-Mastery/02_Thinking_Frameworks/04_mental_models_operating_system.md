# Mental Models — Operating System

A working set of principles, decision frameworks, and habits for engineering judgment, systems/platform architecture, technical leadership, and long-horizon career growth. Every entry exists because it changes a real decision — not because it's interesting.

**Bar for adding a new entry:** would this have changed a decision made in the last 90 days? If not, it doesn't belong here, no matter how good it sounds.

**How this fits with `01`–`03`:** those chapters are a linear sequence — read once, drilled daily — for structuring thought *before you speak*. This file is not a chapter to read once; it's the standing reference those chapters draw on and point back to (`03`'s root-cause/decision-making loop is this document's §3/§4 applied specifically to debugging and architecture). Keep it open as a working reference, not a read-through. `16_engineering_judgment_as_a_contractor_architect.md` is the narrower, contractor/consultant-specific companion — client-dependency risk, working altitude, and the AI-era differentiators argument — drawn from live project experience rather than general reference.

## How to Use This Document

- **Weekly:** skim section headers only. Notice which model should have been used on a decision this week but wasn't.
- **Monthly:** re-read one section in full. Pick one model and deliberately apply it on a real decision.
- **Quarterly:** prune. Delete anything that hasn't earned its place. Add anything a real decision exposed as missing.
- **Never:** read this front-to-back as motivation. It's a reference and a training program, not a pep talk.

---

## 1. Foundational Truths

These calibrate how much weight to give everything else. They don't change; the rest of the document is downstream of them.

**You are bad at predicting the future.** Software projects are novel by construction — if the outcome were fully predictable, it wouldn't need engineering. Past-project timelines are weak evidence for the next one. Plan lightly; don't be confident in the plan itself.

**Reversibility determines how much process a decision deserves, not its size.** A cheap-sounding decision that's hard to undo (a data schema, a public API contract, a hiring decision) deserves more scrutiny than an expensive-sounding one that's easy to reverse (a vendor trial, a feature flag rollout). Ask "how hard is this to undo" before asking "how big is this," every time.

**Systems are sociotechnical, not technical.** The system includes the humans. Almost every "technical" incident, stalled project, or bad architecture has a people/incentive root cause one layer down. Look there first.

**Code is a communication artifact aimed at humans; correctness is necessary but not sufficient.** The compiler is not the primary reader. Optimize for the engineer who inherits this code with no context, including future-self.

**Optimize for cheap change, not for being right the first time.** Requirements, scale, and priorities will be misjudged repeatedly over a system's life. A system that's easy to change survives being wrong. A system that's "correct" but rigid does not.

---

## 2. Overriding Default Behavior — From Average to Expert

The gap between average and expert output is mostly a gap in which default cognitive patterns someone has trained themselves to catch and override — not a gap in raw ability. Untrained defaults optimize for short-term comfort (ending uncertainty fast, avoiding visible incompetence, avoiding effort that feels unrewarding in the moment). Every one of those defaults actively works against building deep expertise. Each entry below pairs a specific default with a specific, drillable override.

**Hurry Bias — rushing to end uncertainty, not to finish well.**
*Default:* an unresolved problem reads as a threat, so the brain rushes to *any* answer to relieve the discomfort of not knowing, mistaking speed-to-closure for productivity.
*Override:* before calling something done, force one explicit checkpoint: "what would surface if I gave this twice the time?" Acting on the answer is optional — the pause alone catches most rushed mistakes. Pair with the Pre-mortem (§3) on anything with real stakes.

**Face-Saving Default — hiding what isn't known.**
*Default:* avoiding the "obvious" question, hiding unfinished work, staying quiet at the edge of the Circle of Competence (§3) — all to skip the momentary discomfort of looking incompetent.
*Override:* treat the flinch before asking a "dumb" question as a direct readout of where the real learning is, and ask it anyway, in public, every time. Expertise is built from thousands of moments of visible not-knowing that the average path spends a whole career avoiding.

**Boredom Avoidance — skipping the repetition that actually builds skill.**
*Default:* attention is wired to chase novelty and treat repetitive, unglamorous practice as aversive — even though repetition on fundamentals is the actual mechanism that produces expertise.
*Override:* schedule the boring repetition as a fixed, protected block, the same way a meeting with someone important gets protected. The least stimulating activity available is usually the highest-leverage one.

**Comfort Homeostasis — retreating to what already feels easy.**
*Default:* "unfamiliar and effortful" reads as a danger signal, quietly steering behavior back toward already-mastered tasks — which feels like productivity but caps the growth rate at zero.
*Override:* if a task isn't producing a specific, nameable discomfort, it's maintenance, not growth. Keep at least one active task at the edge of the Circle of Competence at all times.

**Validation-Seeking — optimizing to look right instead of be right.**
*Default:* social instinct rewards agreement and in-the-moment competence signaling, which quietly biases toward defending a first answer instead of updating it.
*Override:* actively seek out whoever is most likely to disagree, before committing. Being proven wrong early and cheaply is the system working, not a failure — treat it that way without exception.

**Present Bias — trading long-term compounding for immediate relief.**
*Default:* the discomfort of doing the hard thing now is concrete and immediate; the benefit is diffuse and distant — so the easy-but-worthless action wins by default in the moment.
*Override:* don't rely on willpower at the moment of temptation — it's the least reliable variable available. Decide the rule in advance, remove the easy alternative from the environment, and make the good action the default one before the moment arrives.

**Local Calibration — benchmarking against whoever is nearby.**
*Default:* "good effort" and "good output" get calibrated unconsciously against whoever is physically or socially close, which guarantees average results whenever the surrounding baseline is average.
*Override:* benchmark deliberately against the best specific, named practitioners in the exact skill being built, not against local peers. An unexamined bar drifts down to whatever's comfortable — recalibrate it explicitly and often.

**Preparation-as-Procrastination — endless readiness as avoidance.**
*Default:* "more learning/planning first" is often not caution — it's a disguised way to avoid producing something that can be evaluated and found wanting.
*Override:* force real, evaluable output on a deadline before it feels ready, every time (Parkinson's Law, §5). Readiness is a feeling that shows up after starting, not a precondition for starting.

### Installing One Override

Grinding all eight at once fails — that's Hurry Bias applied to fixing Hurry Bias. Install one at a time:

1. Pick whichever override above would have changed the most recent moment of self-directed frustration.
2. Name its exact trigger — the specific instant right before the default fires (e.g., "the half-second before saying 'looks good' without actually checking").
3. For one week, track catches only — log every time the default fires, whether or not it gets overridden in time. Noticing is the skill being trained first; correction follows automatically once noticing is reliable.
4. Move to the next override only once catching this one has become automatic rather than effortful.

---

## 3. Thinking and Problem-Solving

**Circle of Competence.** Know the boundary between what's actually known and what's assumed. Inside the circle, move fast on judgment alone. Outside it, seek an expert or explicitly flag the uncertainty — don't extend confident-sounding opinions past the boundary.

**5 Whys.** The first cause found is rarely the root cause. Keep asking "why did that happen" until hitting something systemic (a missing process, a missing check) rather than something incidental (one person's specific mistake). Stop when the next "why" would just restate the same fact differently.

**Inversion.** When stuck moving forward ("how do we get more signups"), flip the question ("what would guarantee nobody signs up, and is any of that currently happening"). Inversion surfaces blockers that forward-reasoning skips past because they feel too obvious to state.

**Chesterton's Fence.** Before removing something not understood — a weird config, an odd check, a legacy code path — find out why it's there. "This looks unnecessary" and "this is unnecessary" are different claims; only act on the second, and only after doing the work to tell them apart.

**Occam's Razor.** Given two solutions with equal power, the simpler one is usually correct and always cheaper to maintain. Simplicity is a tiebreaker to apply deliberately, not an aesthetic preference to abandon under the first sign of real constraints.

**Pre-mortem.** Before committing to a plan, assume it failed and ask what most likely killed it. This surfaces risks that post-hoc retros never catch, because it happens while there's still time to act. Run this on every plan with real cost of failure — a launch, a migration, a hire.

**Second-order thinking.** Ask "and then what happens" at least twice past the first, obvious effect. A cache fixes latency (first order) but creates a staleness/invalidation problem (second order), which changes consistency guarantees for downstream consumers (third order). Most bad technical decisions are correct at first order and wrong at second or third.

**Externalize your thinking.** Explaining a problem out loud — to a person, a rubber duck, or in writing — forces an associative mental model into a linear one, which exposes exactly where the reasoning breaks down, usually before anyone responds. Use this as a debugging tool for thinking itself, not just for code.

**Pareto Principle (80/20).** For most efforts, a small input fraction drives most of the output. Apply it explicitly: which 20% of a system's code causes 80% of the incidents? Which 20% of a feature's scope delivers 80% of its value? Use it to sequence work — not to justify skipping the remaining 20% when it's actually load-bearing.

---

## 4. Decision-Making

**Type 1 vs Type 2 decisions (one-way vs two-way doors).** Type 1: hard or impossible to reverse — invest real deliberation. Type 2: reversible, cheap to undo — decide fast and adjust. Misclassifying a Type 2 decision as Type 1 is the single most common cause of organizational slowness. Most decisions are Type 2; treat them that way by default and justify treating something as Type 1 rather than the reverse.

**Prefer fast decisions for anything reversible.** Information-gathering has diminishing returns — the first 80% of relevant information is cheap, the last 20% is expensive, and most decisions don't need that last 20% to be good enough. Combined with most decisions being Type 2, the default should be: decide with 80% of the information, act, and correct based on real feedback rather than more analysis.

**Expected value over point predictions.** Don't ask "will this work" — ask what the range of outcomes is, how likely each is, and what the cost is if the bad ones happen. A 70% chance of a small win with a 30% chance of catastrophic, unrecoverable loss is usually worse than a 50% chance of a moderate win with a 50% chance of a cheap, recoverable loss. Weight by reversibility (§1), not probability alone.

**Every multi-factor trade-off is a "pick two" triangle.** Velocity, quality, and customer impact — pick two, the third suffers. CAP theorem — pick two of consistency, availability, partition tolerance. Cost, reliability, and speed of delivery — same shape. Before debating a trade-off, name which two vertices are actually being optimized for; most trade-off arguments are really disagreements about which vertex to sacrifice, left implicit.

**Parkinson's Law.** Work expands to fill the time allotted. A team given three weeks will find enough minor issues to use all three; the same team given a realistic two-week deadline usually ships equivalent quality faster. Set deadlines deliberately, even imperfect ones — the deadline is the forcing function.

**Stakeholder Matrix.** Plot stakeholders on interest × influence. High interest + high influence → manage actively. High influence + low interest → keep satisfied (can derail things over a minor issue if ignored). High interest + low influence → keep informed. Low both → monitor only, spend no more effort than that.

---

## 5. Systems, Architecture, and Platform Engineering

*The section most directly tied to operating as a platform/cloud/ML-infrastructure architect. Re-read this one most often.*

**Boring technology principle.** Every project has a limited budget of "innovation tokens." Spend them on the one or two things that are the actual novel value — spend zero on the database, the queue, the deploy mechanism, unless the boring option is a genuine, demonstrated bottleneck. A platform built on unfamiliar tech at every layer is a platform nobody, a year from now, can operate confidently at 3am.

**Conway's Law.** Systems end up shaped like the communication structure of the organization that built them. A modular architecture requires modular team boundaries first — org design is a design tool, not just an HR concern. When an architecture keeps drifting back toward a bad shape despite repeated redesigns, check whether the team structure is silently forcing it.

**Design for failure, not just for the happy path.** In distributed and ML systems specifically: assume every network call fails, every retry happens more than once (design for idempotency by default), every dependency eventually becomes unavailable, and every input eventually becomes malformed. The question is never "could this fail" — it's "what happens, specifically, when it does, and is that acceptable."

**Observability and error budgets over vague reliability targets.** "Make it reliable" is not actionable. An explicit SLO (e.g., 99.9% success over a rolling 30 days) plus an error budget makes reliability a resource spent deliberately — burn it on a risky launch when there's budget, freeze changes when there isn't. Instrument for the failure modes named above; a system that can't be observed is a system being debugged blind.

**State-space thinking (generalized).** Every interface — a UI, an API, a model-serving endpoint, a pipeline stage — has at minimum five states: empty, loading, partial, error, and the ideal/full-data state. Most bugs and bad UX live in the four states that aren't the ideal one, because that's the state that gets built and demoed first while the others get treated as afterthoughts. Design all five deliberately, every time — especially for ML systems, where "partial/degraded" (a stale model, a missing feature) is a common silent failure mode, not an edge case.

**Discover abstractions; don't design them upfront.** Don't build for requirements that don't exist yet — the future is poorly predicted (§1). Use a rule of three: the first two times similar logic is needed, duplicate it. The third time, pause and consider whether a real abstraction has revealed itself. Premature abstraction is harder to undo than premature duplication — duplication is a Type 2 decision (§4); a bad abstraction baked into a public interface is closer to Type 1.

**Ubiquitous Language.** Maintain one glossary of terms that every contributor — including product, customers, and adjacent teams — uses identically. Most cross-team friction, and a surprising fraction of production bugs, trace back to two groups using the same word ("active user," "event," "feature") to mean different things. Naming precision is a bug-prevention mechanism, not pedantry.

**Omega Mess vs. Alpha Mess (technical debt triage).** Not all bad code deserves fixing. Omega Messes are well-encapsulated, rarely touched, low blast radius — ignore them deliberately and redirect the energy. Alpha Messes sit in high-churn code or critical paths and compound over time — fix these before they get worse. Classify which kind is in front of you before any cleanup effort; "this code is ugly" is not sufficient justification on its own.

---

## 6. Engineering Leadership

**Three axes of success: Impact, Scale, Reliability.** Impact — continuously delivering value to real users, not just shipping tickets or improving internal developer experience in isolation. Scale — the organization and system growing linearly or better, not just surviving at current size. Reliability — calibrated to stage; five-nines is the wrong target pre-product-market-fit, and the wrong target to *not* have once there are enterprise customers. Weigh all three deliberately; optimizing only one is the most common leadership failure mode.

**Staff+ leverage models — multiplying beyond individual output.** At Principal/Distinguished level, individual code output stops being the primary lever. Four recognized archetypes (Will Larson, *Staff Engineer*) for where leverage actually comes from:
- **Tech Lead** — directing a team's technical decisions and unblocking them.
- **Architect** — the shape of systems across teams, setting technical direction that outlives any one project.
- **Solver** — depth on the hardest, highest-ambiguity problems no one else can crack.
- **Right Hand** — extending an executive's reach and judgment across the org.

Know which archetype a given role or moment calls for; operating in "Solver" mode when the org needs "Architect" mode is a common way to be technically excellent and organizationally ineffective at the same time.

**Ownership Radius — depth of understanding is not the same as granted authority.** Two different things get conflated under "responsibility": how deeply a system is personally understood, and how much authority is actually held over it. Understanding should almost always run ahead of granted authority — knowing more than the current mandate covers is what makes the next scope expansion credible. But *acting* on that depth — making unilateral calls, speaking for a system, redirecting others' work — before the authority has been explicitly granted reads as overreach, not initiative, and is one of the most common ways someone technically strong ends up cut out of decisions. Before claiming more ground in meetings, reviews, or decisions, check explicitly with whoever holds Decision Rights (§11) whether the scope was actually granted or only assumed from having done the work.

**Being sidelined is a scope-mismatch signal to diagnose, not just a verdict on competence to absorb.** Getting cut out of decisions or conversations expected to be part of is data, not just painful — apply System Cause Before Individual Cause (§11) to a personal situation the same way it's applied to an incident, before concluding it's personal. Ask, in order: was this scope ever made explicit and agreed with a manager or peer, or only assumed from workload? Is there one specific, nameable incident that triggered the narrowing, or has it drifted with no single trigger? Has the scope claimed been reasserted lately, or is it running on an agreement that's now stale? The fix is almost never "do more unseen work to prove it" — it's the same direct, explicit conversation Decision Rights (§11) prescribes *before* a decision, applied here to re-establish current scope rather than re-litigating why it narrowed.

**Calibrate collaboration style to the individual, not to a default.** The same follow-up cadence reads as "supportive" to one person and "micromanaging" to another. Ask directly, and adjust — a natural style is not neutral by default.

**Review everything, even work that "just works."** Working code can still be a disaster waiting to happen (a missed edge case, a scaling cliff, a security gap). "It works" is necessary, not sufficient, for approval.

**Confidence and competence are different channels, weighted differently by stage.** Early-stage / individual-contributor-facing: competence (can this actually be built) dominates. Growth-stage / executive-facing: delivery confidence matters as much as plan quality, because non-technical stakeholders can't directly evaluate technical competence — they read delivery as the proxy. Structure exec updates as: lead with confidence, show the competence (the substance), close with confidence again.

**Spend real time outside the immediate team, deliberately, when operating at senior scope.** A recurring sync with peer leads in product, sales, or adjacent engineering teams is not optional networking — it's how "impact" gets defined beyond a single backlog.

---

## 7. Communication and Influence

Kept short here deliberately — full frameworks, phrase libraries, and drills live in `Communication-Mastery/`. Two principles specific to influence-without-authority belong in this document:

**Prototypes are magic.** A rough, two-day working prototype persuades faster and more durably than a polished four-week spec document. Abstract arguments don't move people; something they can click through does. Use this deliberately when buy-in is needed, not just when there happens to be spare time.

**Seek feedback early and in public, not late and polished.** Share the ugly, half-working version, on purpose, before it's comfortable to show it. The cost of early, rough feedback is embarrassment (§2). The cost of late feedback is discovering the whole direction was wrong after the expensive part is already built.

For everything else — structuring explanations, disagreement, incident communication, interview answers, executive presence — start at `Communication-Mastery/README.md`.

---

## 8. Learning and Long-Horizon Career Growth

**Expand the Circle of Competence deliberately, not accidentally.** Don't just wait for a project to force new skills. Pick the next expansion on purpose, based on what compounds (below), not based on whatever's loudest in the industry this month.

**Invest in skills with a long half-life over skills with a short one.** Systems thinking, distributed-systems fundamentals, communication, and judgment under uncertainty are still valuable in fifteen years. A specific framework's API surface usually isn't valuable in three. Weight for durability, not just current demand — this matters more, not less, in a field where the specific tools are changing unusually fast right now.

**Teach it to learn it (Feynman).** Inability to explain a system simply to someone junior means it isn't understood as well as it feels understood — the gap exposed while trying to simplify is exactly the gap in the underlying model. Use this as a genuine diagnostic, not just a communication exercise.

**Retrieval practice beats passive consumption for durable skill.** Reading about a skill and being able to produce it under real pressure are different capabilities; only producing it, repeatedly, with feedback, builds the second one. This applies to technical skills as much as communication skills.

**Favor asymmetric bets when the downside is bounded and reversible.** A side project, a stretch assignment, or a role change with capped downside (revertible) and uncapped upside (it works and compounds) is a good bet even at low odds of success — the career application of Expected Value (§4) combined with Reversibility (§1). Avoid the reverse: bounded upside, unbounded downside, however low the stated probability.

---

## 9. Focus and Sustainable Performance

Kept intentionally short — an operating manual, not a wellness program. Four techniques, each immediately actionable under real time pressure:

**Protect blocks for single-tasking.** Deep technical work (design, debugging a hard problem, writing) degrades sharply under context-switching. Defend unbroken blocks for it explicitly, rather than assuming focus will happen in the gaps between meetings.

**Worry triage (3 steps).** When a recurring worry resurfaces mid-work: name it explicitly; ask if there's something actionable *right now* — if yes, do it or schedule it and move on; if no, consciously set it down. Most worries never materialize, and ruminating on an unactionable one is pure cost with no benefit.

**Breath as a fast reset.** A short, deliberate breathing pause measurably lowers physiological stress response faster than most other available tools, and costs under a minute. Use it before a high-stakes conversation, not just once already overwhelmed.

**Senses-grounding to break a rumination loop.** When stuck cycling on the past or a hypothetical future instead of the problem at hand, deliberately name what's currently seen, heard, and felt. This interrupts the loop by forcing attention back to present, concrete input — a fast, low-effort circuit-breaker, not a meditation practice to master.

---

## 10. Cookbook — Applied Scenarios

**"This project isn't progressing — meetings keep happening instead of shipping."**
Check for a deadline (Parkinson's Law, §4). Check whether decisions blocking progress are being treated as Type 1 when they're actually Type 2 (§4). Build a Stakeholder Matrix (§4) if a specific person or group is the actual bottleneck.

**"This interface/API/pipeline feels awkward and nobody can say exactly why."**
Check all five states, not just the ideal one (§5, State-space thinking). The awkwardness is almost always in the empty, loading, partial, or error state that got skipped during design.

**"Two teams keep debating instead of converging."**
Check for a Ubiquitous Language gap first — confirm both teams mean the same thing by the contested terms (§5). Get a rough prototype in front of both sides instead of continuing to debate in the abstract (§7).

**"A model works in the notebook and degrades or breaks in production."**
Almost always a Design-for-Failure gap (§5) — training and serving reading from different feature sources, no idempotency on retraining/serving retries, or a missing "partial/degraded" state (a stale model silently still serving). Check observability next (§5) — if feature drift or serving-latency regression can't be seen directly, it's being found the hard way, in production, instead of the cheap way, on a dashboard.

**"The team ships fast but reliability keeps degrading."**
Name the actual SLO and error budget (§5) — without one, "reliability" isn't a target, it's a vague feeling, and it will keep losing to shipping speed by default. Check the Velocity/Quality/Impact triangle (§4) — confirm the team and its stakeholders agree, explicitly, on which two vertices are currently the priority.

**"Work keeps feeling rushed, avoided, or stuck at 'good enough.'"**
This is Section 2, not a scheduling problem. Identify which specific default is firing — Hurry Bias, Face-Saving, Boredom Avoidance, Comfort Homeostasis — and run the one-week catch-tracking protocol on it before changing anything about the actual work.

**"A postmortem keeps turning into 'whose fault was this.'"**
Run System Cause Before Individual Cause and the Hindsight Bias Tax (§11) explicitly, and state them as ground rules before the meeting starts — not something applied silently after the fact.

**"A decision got made by one person and the team feels blindsided."**
Check whether Decision Rights (§11) were ever made explicit for this call — usually they weren't. Fix that going forward instead of re-litigating this one decision; the process gap, not this specific person, is the actual finding.

**"I feel sidelined or singled out at work."**
Check Ownership Radius (§6) first — has the scope believed to be held ever been explicitly confirmed with a manager or peer, or only assumed from the work done? Apply System Cause Before Individual Cause (§11) to the situation before concluding it's personal: look for one specific triggering incident versus a slow, undiscussed narrowing. Then have the direct, explicit scope conversation — Decision Rights (§11) applied to yourself — instead of doing more unseen work to try to prove it.

---

## 11. Blame, Mistakes, and Decision Legitimacy

*Three failure modes that look like separate problems — pointing at a person after something breaks, repeating avoidable mistakes, and decisions that land as unilateral — but share one root: skipping the system-level question in favor of the fast, person-level one.*

### Avoiding finger-pointing

**System Cause Before Individual Cause (Just Culture).** When something breaks, the reflexive question is "who did this" — resist it. Ask "what about the system made this error possible, likely, or undetected" first. A single person's mistake is rarely a sufficient explanation on its own; it's evidence of a missing guardrail, a bad default, or absent review — all system properties. Reserve individual attribution for genuine recklessness or repeated, willful disregard; nearly everything else is a system finding wearing a person's name.

**Contributing Factors, Not a Single Cause.** Real failures almost always have several contributing factors that each look "sufficient" only in isolation and in hindsight. Naming one person, one commit, or one decision as "the cause" hides the other factors that also had to line up — and guarantees the same failure mode recurs wearing a different name next time. In a postmortem, list contributing factors as a set, not a chain that terminates in one culprit.

**Hindsight Bias Tax.** Once an outcome is known, the decision that led to it looks far more avoidable than it actually was at the time — this is a well-documented cognitive bias, not a moral failing in the person reviewing it. Before judging a past decision, reconstruct what was actually knowable at that moment, not what's obvious now with the outcome already in hand. This single check is the most effective lever against reflexive blame in any retro.

### Making fewer mistakes

**Swiss Cheese Model — layered defenses, not one gate.** No single check should be the only thing standing between a mistake and production — code review, tests, staging, canary, monitoring, and rollback are independent layers, each with its own holes. The incidents that matter are the rare cases where every hole lined up at once. Judge a mistake by which layer was missing or thin, not by whether one person "should have caught it" — a real fix adds or strengthens a layer, it doesn't just ask people to be more careful.

**Checklists Beat Memory Under Load.** Under time pressure or fatigue, working memory degrades before judgment or skill does. A short, written checklist for repeatable high-stakes actions — a production deploy, a schema migration, an on-call handoff — catches exactly the failures that "being careful" doesn't, because it doesn't depend on remembering to be careful in the moment.

**Near-Misses Are Free Signal.** Treat a caught-in-time error — a bad deploy stopped by canary, a bug caught in review — as data, not a non-event. The ratio of near-misses to actual incidents for a given failure mode is usually large, and a near-miss is cheaper information about the same underlying gap than waiting for the full incident. Log and review these on purpose, not just the ones that escaped.

### Avoiding unilateral decisions

**Decision Rights Before the Decision, Not After.** Before a contested call gets made, name explicitly who has the authority to decide, who must be consulted, and who is merely informed — a lightweight RACI, stated out loud. Most "that was a unilateral decision" complaints aren't really about the decision being wrong; they're about decision rights never having been made explicit, so any single-person call feels like overreach regardless of its merit.

**Fast and Single-Owner Is Correct for Type 2; a Warning Sign for Type 1.** Combine directly with Type 1 vs Type 2 (§4): for reversible decisions, one owner deciding quickly after a light consult is the *correct* behavior, not a unilateral one — waiting for full consensus on a cheap-to-undo call is the actual failure mode. For hard-to-reverse decisions, that same single-owner speed is exactly where explicit sign-off from whoever's named in Decision Rights (above) is required before proceeding, not after.

**Ask Who Would Object, Not Just Whether Anyone Did.** For any decision that's hard to reverse, the cost of a short delay to solicit real dissent is nearly always smaller than the cost of the decision being wrong and undiscovered until much later. Before finalizing, explicitly ask "who would push back on this if they saw it, and have I actually asked them" — not just "did anyone happen to raise a concern unprompted."

---

## Sources

- *Superforecasting* — Philip Tetlock & Dan Gardner (prediction, calibration)
- *Staff Engineer* — Will Larson (leverage archetypes, §6)
- *99 Bottles of OOP* and "Go Ahead, Make a Mess" — Sandi Metz (discovered abstractions, Omega Mess)
- *Domain-Driven Design* — Eric Evans (Ubiquitous Language)
- "Choose Boring Technology" — Dan McKinley (§5)
- Amazon's one-way-door / two-way-door decision framing (§4)
- Google SRE book (error budgets, §5)
- Basecamp's Hill Charts writeup
- "How to Fix a Bad User Interface" — Scott Hurff (state-space thinking origin, §5)
- Donella Meadows, *Thinking in Systems* (second-order thinking, leverage points, §3)
- Carol Dweck, *Mindset*; Anders Ericsson, *Peak* (deliberate practice and default-behavior override, §2, §8)

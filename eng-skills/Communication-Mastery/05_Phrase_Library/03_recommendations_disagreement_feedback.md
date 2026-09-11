# Phrase Library: Disagreement, Objection Handling, and Feedback

## 0. Signaling You're Following Someone's Reasoning (Before You Respond)

Two phrases that get used as if they were interchangeable, but they track different things — worth distinguishing before folding either into Section 1's acknowledge → position → reason → invite pattern, since which one you reach for signals *what* you followed, not just *that* you followed.

| Phrase | What It Tracks | Structure | When to Use |
|---|---|---|---|
| "I see where you're going (with this)" | The **direction** an argument is headed — its destination, before it arrives | "I see" + "where" + subject + "is/are going" — a motion verb applied metaphorically to an argument's trajectory | Mid-argument, while the other person is still building toward a conclusion — signals you're tracking it in real time, often as a preface to redirecting or pushing back before they finish stating it |
| "I follow your line of thought" | The **logical sequence** — the chain of steps connecting premise to conclusion | "I follow" + "your line of thought" (a noun phrase for a connected chain of reasoning, not a single point) | After someone has laid out a multi-step justification — confirms you've tracked the *mechanism*, so you can pinpoint exactly which step is where you diverge |

**A register note on "get" vs. "follow":** "I get your line of thought" is understandable, but it reads as informal — "get" pairs naturally with concrete, single objects ("I get it," "I get your point"), while native speakers pair "follow" with abstract, multi-step things ("I follow your line of thought," "I follow your reasoning," "I follow the logic"). In a design review or a meeting with a senior stakeholder, "follow" is the more calibrated choice.

Both phrases signal comprehension, not agreement — they're a hinge, not a full response. Pair them with Section 1's pattern rather than letting them stand alone:

- "I see where you're going with this — you're about to argue we should decouple the two services. Before you get there, can I flag a constraint?"
- "I see where you're going, and I think it holds for the read path. I'm less convinced on writes."
- "I follow your line of thought up to the caching layer — that's where I think the assumption breaks down."
- "I follow your reasoning end to end; I'd just weight the trade-off differently."

## 1. Disagreeing Professionally

The pattern that works: **acknowledge the merit → state your position → give the specific reason → invite response.** Never skip the acknowledgment — it's not politeness padding, it's what keeps the conversation collaborative instead of adversarial, which materially changes whether the other person can actually hear your reasoning.

- "I see the appeal of that, and I'd push back on one part of it — ..."
- "That's a fair point on [X]. Where I land differently is on [Y], because..."
- "I want to offer a different take — not because [their point] is wrong, but because I think [additional factor] changes the calculus."
- "I'm not fully convinced yet — can I walk through my concern?"
- "I'd frame this differently: ..."
- "I think we're optimizing for different things here — you're weighting [X], I'm weighting [Y]. Let's align on which matters more first."
- "Devil's advocate for a second — what happens if [edge case]?"
- "I respectfully disagree, and here's specifically why: ..."
- "That matches my understanding up to a point — where it diverges is..."
- "I'd like to flag a risk with that approach before we commit: ..."
- "Can I offer a counter-example? [specific case] suggests [X] might not hold here."
- "I think there's a version of this I'd fully agree with — it's [modification]. As stated, I have a concern about [specific part]."

## 2. Handling Objections to Your Proposal

- "That's a legitimate concern — here's how I've thought about it: ..."
- "Good pushback. To address that specifically: ..."
- "I considered that, and here's why I still landed where I did: ..."
- "You're right that [X] is a real risk. I'd weigh it against [Y], and on balance still recommend [Z] — happy to be talked out of it though."
- "That's a fair objection I don't have a complete answer to yet — let me take it as an action item and come back with data."
- "I don't think that objection changes the recommendation, but it does change how we should roll it out — specifically..."
- "Let's stress-test that — what would have to be true for your concern to be the deciding factor?"
- "I'd rather surface that risk now than discover it in production — let's spend two minutes on it."

## 3. Disagreeing With a Senior Stakeholder (Manager, Exec, Principal)

Calibrated to preserve the relationship while still being direct — the mistake to avoid is over-softening to the point the actual disagreement doesn't land.

- "I want to raise a concern before we finalize this — I don't think it changes the outcome, but I'd be doing you a disservice not to flag it."
- "I understand the time pressure, and I think it's worth 10 more minutes given [specific stake] — here's why."
- "I'm going to push back here, because I think the cost of being wrong on this one is high enough to warrant it."
- "If I'm wrong about this, I'd want to know why — can I walk through my reasoning?"
- "I'll defer to your call, but I want to make sure the trade-off is explicit before we move: ..."
- "I've changed my mind on this before when I got new information — right now, based on what I know, I still think [X]."

## 4. Giving Feedback (Technical / Code / Design)

- "Strong overall — the part I'd tighten up is..."
- "This solves the problem; I'd flag one risk before we ship it: ..."
- "I like the direction. One question that would change my confidence: ..."
- "Nit, not a blocker: ..."
- "This is a blocker for me, and here's specifically why: ..."
- "I want to understand the reasoning before I comment further — walk me through why you chose [X] over [Y]?"
- "Small thing, but it'll save the next person time: ..."
- "I'd approve this as-is, with one non-blocking suggestion for later: ..."
- "This works, but I think there's a simpler version — want me to sketch it?"
- "I don't have a strong opinion on [X], but I do on [Y] — specifically..."

## 5. Receiving Pushback on Your Own Work Gracefully

- "That's a good catch — you're right, let me fix that."
- "I hadn't considered that angle — give me a second to think through it."
- "Fair — I think I was optimizing for [X] and missed [Y]. Let me revise."
- "I still lean toward my original approach, and I want to make sure I understand your concern fully first — can you say more about [specific part]?"
- "That changes my recommendation — thanks for catching it before it shipped."
- "I hear the concern. I'd like to try it my way with a fallback plan if [specific signal] shows up — does that address the risk?"

## 6. Making a Decision When the Room Disagrees

- "We have two reasonable positions here. Given the deadline, I'm going to make the call: we're going with [X], for [reason]. I want to note [Y]'s objection in case we need to revisit."
- "Let's timebox this — 5 more minutes of debate, then I'll make the call if we haven't converged."
- "This is reversible, so let's not over-invest in getting it perfect — we'll go with [X] and adjust if [signal] shows up."
- "I want to make sure dissent is on the record, not because I expect to be wrong, but because if we are, I want the reasoning traceable."
- "Given we're split, let's define what evidence would resolve this, and go get it, rather than debate priors further."

## 7. Delivering Bad News / Explaining a Failure

- "I want to give you the direct version first: [what went wrong], and then walk through why."
- "This didn't go the way we planned. Here's what happened, and here's what we're doing about it."
- "I owe you a heads-up that [X] is behind / broken / not going to work as scoped."
- "The honest assessment is [X] — I'd rather tell you now than let the timeline slip silently."
- "This is on me — I underestimated [X]. Here's the corrected plan."
- "We made the wrong call on [X] in hindsight. Here's what we learned and what changes going forward."

## 8. Communicating Risk

- "The risk I'd flag is [X], with a likelihood of [low/medium/high] and an impact of [low/medium/high]."
- "This is a known risk we're accepting, not an oversight — here's the reasoning: ..."
- "The blast radius if this goes wrong is [scope] — contained to [X], won't touch [Y]."
- "I'd rate this a medium risk — worth a mitigation plan, not worth blocking the launch."
- "The risk isn't in the happy path, it's in [specific edge case] — that's what I'd want tested before we ship."
- "We're carrying this risk knowingly, with [monitoring/rollback plan] as the safety net."

## 9. Leadership and Decision-Making Language

- "I'd rather make a reversible call fast than a perfect call slow, for something at this stakes level."
- "My job here is to make sure we're deciding on the right axis — cost, speed, or risk — not to have the loudest opinion."
- "I want to create space for the quieter disagreement in the room before we lock this in — does anyone see this differently?"
- "I'm optimizing for the team's long-term velocity here, even though it costs us short-term speed."
- "I'd rather over-communicate this decision than have three different interpretations of it next week."
- "Let's write down the reasoning, not just the decision — future us will want to know why, not just what."

## Drill: The Disagreement Rehearsal

Pick a real technical opinion you hold that a colleague has pushed back on before. Say the disagreement out loud using the acknowledge → position → reason → invite pattern from Section 1, twice — once as if to a peer, once as if to a skip-level exec (Section 3 phrasing). Notice how much the *content* stays the same and only the *calibration* changes — that's the actual skill.

## Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Adversarial** | Characterized by opposition or conflict, as between opponents rather than collaborators. |
| **Materially (change)** | Substantially or significantly, to a degree that actually matters — not just marginally. |
| **Calibrated / calibration** | Deliberately adjusted to fit the situation — here, how directly or softly a disagreement is delivered. |
| **Over-softening** | Diluting a message so much, in the name of tact, that its actual point fails to land. |
| **Land (a point/disagreement)** | To register clearly and be understood by the listener as intended. |
| **Trajectory** | The path or direction something (here, an argument) is heading, projected forward from its current course. |
| **Line of thought** | A connected chain or sequence of reasoning steps, as opposed to a single isolated point. |
| **Hinge** | A small pivot phrase that a larger exchange turns on, without itself constituting the full response. |

**Next:** [`04_incidents_rca_performance_risk.md`](./04_incidents_rca_performance_risk.md) — phrases specifically for incidents, root cause analysis, performance discussions, and postmortems.

# Phrase Library: Stakeholder, Leadership, and Interview Communication

## 1. Talking With Non-Technical Stakeholders

- "In plain terms, this means..."
- "Without the jargon: ..."
- "The business impact is [X] — the technical reason is available if useful, but the impact is the headline."
- "Think of it like [everyday analogy] — see `04_Technical_Storytelling` and `11_Exercises` for building these."
- "The short version, skipping the implementation details: ..."
- "What matters to you as a stakeholder is [X]; the how is something my team can own."
- "I'll translate that into cost/time/risk terms: ..."
- "The technical name for this is [X], but functionally what it means for the product is..."

## 2. Talking With Your Manager

- "Quick heads-up, not urgent: ..."
- "I need a decision from you on [X] by [date], here are the two options..."
- "I want to flag a risk before it becomes a surprise: ..."
- "Status: green. One thing on my radar: ..."
- "I could use air cover on [X] — here's the specific ask."
- "I'm going to make the call on [X] myself unless you object — flagging in case you have context I don't."
- "This is going to take longer than the original estimate — here's the revised timeline and why."
- "I want your read on a trade-off before I commit the team to a direction."

## 3. Talking With Executives (Compressed, Outcome-First)

- "Bottom line: [outcome]. Detail available if useful."
- "Three numbers that matter: [X], [Y], [Z]."
- "This reduces risk in [area] and costs [amount] — the ROI case is [summary]."
- "No action needed from you — this is an FYI on a decision my team already made within our mandate."
- "I need a decision, not a discussion — here's the ask, framed as a choice between two options."
- "The technical complexity is on us to manage — what I need from you is [specific, narrow ask]."
- "If this goes well, [outcome]. If it doesn't, the downside is [bounded, specific] — not open-ended."

## 4. Cross-Team / Cross-Functional Stakeholder Communication

- "I want to make sure we're aligned on scope before either team commits resources."
- "This affects your team in one specific way: [X] — everything else is contained to ours."
- "I'd like to propose an interface/contract between our systems so we can both move independently after this."
- "What's your team's constraint here? I want to design around it, not against it."
- "Let's agree on the API/contract now, and each team can iterate on implementation independently."
- "I don't want to make an assumption about your priorities — what does urgent look like from your side?"

## 5. Presenting Project Status (Non-Technical Audience)

- "We're on track for [date]. The riskiest remaining piece is [X], and here's the mitigation."
- "60% complete by scope, on pace for the original estimate."
- "We hit an unexpected complexity in [X] — it adds [time], and here's why it was worth the trade-off."
- "The headline: [outcome achieved / expected]. The detail is available, but that's the takeaway."
- "I'd rather under-promise here — realistic date is [X], not the optimistic [Y] some earlier estimates suggested."

## 6. Explaining Failures to Leadership

- "This didn't go as planned. Here's what happened, here's the impact, and here's what we're doing differently."
- "I want to own this directly rather than spread the explanation thin — the call was mine, here's my reasoning at the time, and here's what I'd change."
- "The lesson here generalizes beyond this one project — we're updating [process/checklist] so this class of issue is caught earlier next time."
- "I'd rather you hear the direct version from me now than a diluted version later."

## 7. Interview: General Answer-Structuring Phrases

- "Let me give you the structure of my answer before I dive in — I'll cover [X], then [Y]."
- "There are a couple of ways to interpret that question — I'll answer the [specific interpretation] version, let me know if you meant something else."
- "I want to make sure I'm solving the right problem before I jump to a solution — can I ask a clarifying question?"
- "I'll think out loud, since the reasoning process is probably more useful to you than just the answer."
- "Let me start with a naive approach, then improve it — that mirrors how I'd actually approach this."

## 8. Interview: Answering "Why Did You Choose X" Questions

- "I evaluated it against [criteria] — X won on [dimension], which mattered most because [context]."
- "Given the constraints — [time/team size/existing stack] — X was the pragmatic choice, even though Y might be 'more correct' in the abstract."
- "I'd make the same call again given the same information, though I'd flag [X] as something I'd revisit if [condition changed]."

## 9. Interview: Answering "Tell Me About a Time..." (STAR Openers)

- "A good example of that is a project where..." *(then STAR — see `03_Explanation_Frameworks/01`)*
- "This actually happened pretty recently — ..."
- "I'll pick an example where it didn't go smoothly at first, since I think that's more informative than a clean success story — ..."
- "There's a specific instance that comes to mind — let me set the context briefly, then get into what I actually did."

## 10. Interview: Handling a Question You Don't Know

- "I haven't worked directly with [X], but here's how I'd reason about it based on [adjacent experience]."
- "I don't know the exact answer, but let me think through it from first principles."
- "That's a gap in my experience — what I can tell you is how I'd go about closing that gap quickly."
- "I want to be honest that I'm not certain here rather than guess confidently — my best reasoning is..."

## 11. Interview: System Design Framing Phrases

- "Before I design anything, let me nail down the requirements — functional and non-functional."
- "What's the expected scale — requests per second, data volume, growth rate? That changes the design significantly."
- "Let me start with a simple version that works, then identify the bottleneck and iterate."
- "I'm going to make an assumption here — [X] — flag me if that's wrong."
- "There's a trade-off at this step between [X] and [Y] — I'd lean toward [X] for this use case because [reason], but it's worth naming the alternative."
- "Let me draw the high-level components first, then go deep on the part that's most interesting or riskiest."

Full system design and behavioral interview frameworks with complete worked answers live in `08_Interview_Communication`.

## 12. Decision-Making and Prioritization Language

- "I'm prioritizing [X] over [Y] this sprint because [X] is blocking, [Y] is not."
- "This is a P0 because [specific reason — customer-facing, revenue, security], not just because it's loud."
- "I'm deliberately deprioritizing this — it's important but not urgent, and I want to protect the team's focus on [current priority]."
- "Let's define done before we start, so we don't scope-creep silently."
- "I'd rather ship 80% of this well than 100% of it late — here's what's in the 80%."

## 13. Communication During Cross-Team Conflict

- "I think we both want the same outcome and disagree on the path — let's start from the outcome and work backward."
- "Let's separate the technical disagreement from the process frustration — I want to solve both, but they need different fixes."
- "I don't think either team is wrong here — we optimized for different things and it's surfacing now. Let's agree on the shared priority."
- "Can we get one person from each side to own a joint proposal, rather than debate in a large group?"

## 14. Cost Discussions With Finance/Business Stakeholders

- "This is a $[X]/month investment that returns [Y] in [reliability/speed/capacity] — payback period is roughly [Z]."
- "The cost driver isn't the tool, it's the usage pattern — here's what we'd need to change to reduce it."
- "I can give you a cost range with confidence, and a point estimate with less confidence — which is more useful right now?"
- "This is a sunk-cost question, not a going-forward question — the money's already spent; the question is whether continuing is still the right call."

**Next:** [`06_grilling_challenge_questions.md`](06_grilling_challenge_questions.md) — the question patterns people use to pressure-test your decisions, and how to answer them.

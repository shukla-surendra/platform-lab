# Phrase Library: Being Grilled — Challenge Questions and How to Answer Them

"Grilling" is what happens in design reviews, incident postmortems, leadership Q&A, and interview panels: a rapid sequence of pointed questions meant to pressure-test a decision, not just gather information. The questions cluster into a small number of grammatical patterns. Once you can recognize which pattern is coming at you, you can answer the *pattern*, not just the specific words — which is what makes people sound composed under pressure instead of scrambling each time.

## 0. The pair you asked about: "Why don't we...?" vs "Why didn't we...?"

These look almost identical but point in opposite directions in time, and that difference changes what kind of answer is expected.

- **"Why don't we...?"** — present/future tense. A live suggestion or challenge about what to do *from here*. Sometimes genuinely neutral ("Why don't we grab lunch?"), but in a grilling context it's pressure to justify the current plan against an alternative: *"Why don't we just automate this instead of doing it manually?"* → expects a forward-looking answer: a trade-off, a constraint, or a reason the alternative isn't as simple as it sounds.
- **"Why didn't we...?"** — past tense. An accountability question about a decision or action already made: *"Why didn't we test this in staging first?"* → expects a backward-looking answer: what happened, why, and (often unspoken but implied) what changes going forward.

Mixing these up matters: answering a "why didn't we" question with a purely forward-looking fix ("we'll add staging tests going forward") without acknowledging what actually happened reads as dodging the question.

## 1. Past-Decision Accountability ("Why didn't we...")

- "Why didn't we catch this earlier?"
- "Why didn't we test this before it shipped?"
- "Why wasn't this reviewed / signed off?"
- "Why weren't we told about this risk sooner?"
- "How did this get through without anyone noticing?"

## 2. Present/Future Alternative Pressure ("Why don't we...")

- "Why don't we just do X instead?"
- "Why not rewrite it from scratch?"
- "Why aren't we doing this the way [other team/company] does?"
- "Why can't we just throw more capacity at it?"
- "What's stopping us from doing X right now?"

## 3. Hypothetical Pressure-Testing ("What if...")

- "What if traffic doubles next month?"
- "What if this dependency goes down?"
- "What happens if a user does X in the wrong order?"
- "What's the worst case here?"
- "What would it take to break this?"

## 4. Evidence and Confidence Challenges

- "How do you know that?"
- "What data backs that up?"
- "How confident are you in that number?"
- "Is that measured, or is that an assumption?"
- "Have we actually seen this happen, or are we speculating?"

## 5. Assumption-Poking Questions

- "Did you consider X?"
- "Have you thought about Y?"
- "What about the case where Z?"
- "Isn't it true that...?"
- "Doesn't that assume [condition] holds?"

## 6. Ownership and Accountability

- "Who decided this?"
- "Who signed off on this?"
- "Whose call was this, ultimately?"
- "Who's accountable if this happens again?"

## 7. Timeline / Cost Pressure

- "Why is this taking so long?"
- "Why does this cost so much?"
- "Couldn't this have been done faster or cheaper?"
- "What exactly is the money/time going toward?"

## 8. Devil's-Advocate / Rhetorical Pushback

- "Wouldn't it make more sense to...?"
- "Isn't [simpler option] good enough?"
- "Just to play devil's advocate — what if I said we skip this entirely?"
- "Couldn't we have avoided all of this by just...?"

## 9. A Structure That Answers Any of the Above

Regardless of which family the question comes from, the same three-beat structure holds up under repeated grilling:

1. **Answer directly first** — a yes/no, a number, a one-line verdict. Don't open with context; that reads as stalling.
2. **Give the one reason that matters** — not every reason, the load-bearing one.
3. **Name the trade-off or the fix, explicitly** — what you gave up, or what changes going forward.

- "No, we didn't test it in staging — the reason was [X]. Going forward we're adding a staging gate before any release like this."
- "We're not rewriting it from scratch — the cost outweighs the benefit right now given [constraint]. We are addressing the worst part of it: [specific fix]."
- "I'm confident in that number for [scope], less confident beyond that — here's what would change my estimate."
- "That was my call. Here's the reasoning at the time, and here's what I'd do differently with what I know now."

## 10. When You Don't Have the Answer

- "I don't know that off the top of my head — I don't want to guess and give you a wrong number."
- "Let me get back to you with the actual data rather than estimate live."
- "That's a fair gap — I'll have an answer by [specific time], not 'soon.'"

## 11. Practice Drill

Pick a real decision from your own work — something with a plausible trade-off. Have someone (or yourself, out loud) fire one question from each numbered section above at you, in order, and answer each using the three-beat structure in §9. The goal isn't a perfect answer — it's not losing your structure when the question type changes mid-conversation, which is what real grilling feels like.

## Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Pointed (question)** | Direct and pressing, aimed precisely at a specific weak spot rather than asked generally. |
| **Pressure-test** | To deliberately challenge a decision or claim to see whether it holds up under scrutiny. |
| **Composed** | Calm and in control, showing no visible rattling under pressure. |
| **Dodging** | Evading a question or issue rather than addressing it directly. |
| **Holds up** | Remains valid or intact when tested or challenged, rather than falling apart. |
| **Stalling** | Delaying deliberately, often by padding with unnecessary context before getting to the point. |
| **Load-bearing (reason)** | The one reason that is actually essential to the argument — remove it and the whole case collapses. |

**Next:** [`07_bug_and_system_walkthroughs.md`](07_bug_and_system_walkthroughs.md) — phrases for walking someone through a bug, a situation, or an architecture step by step.

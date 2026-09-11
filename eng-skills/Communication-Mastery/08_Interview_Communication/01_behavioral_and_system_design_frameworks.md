# Behavioral and System Design Interview Frameworks

Interviews are a specific, high-pressure application of everything in `02` through `07` — the same frameworks, but with tighter time constraints, an evaluator actively scoring your structure (not just your content), and higher social-evaluative load (`01_Foundations/02`). This chapter covers the two dominant interview formats for senior/staff/principal roles.

## Part 1: Behavioral Interviews

### What's Actually Being Evaluated

Behavioral interviewers are scoring three things, usually without telling you explicitly: **(1) did you have real ownership/judgment in this story, not just participation; (2) can you reason about trade-offs and people, not just systems; (3) is your account calibrated and honest, or suspiciously flawless.** Structure (STAR) gets you understood; these three things get you rated highly.

### The STAR Framework, Interview-Calibrated

Full STAR mechanics are in `03_Explanation_Frameworks/01`. Interview-specific calibration:

```
TARGET LENGTH: 60-90 seconds per answer. Under 45 sec often means
                insufficient Action detail (the section that's being
                evaluated most). Over 2 minutes usually means too much
                Situation/Task setup.

TIME BUDGET WITHIN THE ANSWER:
  Situation + Task:  ~15-20% of total time
  Action:            ~50-60% of total time   ← the evaluated section
  Result:            ~20-30% of total time
```

If you notice your Situation section running long in practice (`10_Daily_Practice`, `12_Recording_Analysis`), that's the single most common and most fixable behavioral-interview flaw.

### Choosing Which Story to Tell

Before the interview, prepare a **story bank** — not memorized scripts, but a mental index of 6-8 real situations, each tagged by which behavioral themes it can answer:

| Story | Themes it covers |
|---|---|
| The RDS Proxy incident (`04_Technical_Storytelling/02`) | Incident response, ownership under pressure, prevention mindset |
| The Kubernetes migration hard decision (`04_Technical_Storytelling/02`) | Driving change, disagreement/pushback handling, stakeholder negotiation |
| [your own] | Mentoring / growing others |
| [your own] | Failure / what you'd do differently |
| [your own] | Cross-team conflict resolution |
| [your own] | Influencing without authority |
| [your own] | Scope/ambiguity — turning a vague ask into a concrete plan |
| [your own] | Technical trade-off under deadline pressure |

Build your own version of this table with real stories before any interview cycle — this table itself is a template, drilled further in `14_Advanced/03_assignments_12_weeks.md` and `11_Exercises`.

### The "What Would You Do Differently" Follow-Up

Almost every strong behavioral answer gets this follow-up, and it's not a trap — it's the interviewer checking for genuine reflection vs. a rehearsed, unexamined script. Always have a real answer ready, not a fake-humble non-answer ("I don't think I'd change anything, it went really well").

**Weak:** "Honestly I think we handled it about as well as we could have."
**Strong:** "I'd build the cross-AZ retry logic before rollout instead of discovering the gap in production — that's a class of check I now do by default on scheduling changes." *(from the project story in `04_Technical_Storytelling/02`)*

### Common Behavioral Questions and the Story-Bank Slot They Map To

| Question | Reach for |
|---|---|
| "Tell me about a time you disagreed with a decision" | Disagreement/pushback story |
| "Tell me about a failure" | Failure story — genuine, not a disguised success |
| "Tell me about a time you had to influence without authority" | Cross-team story |
| "Tell me about your proudest technical achievement" | Hard-decision project story |
| "Tell me about a time you had to deliver bad news" | Incident or scope-cut story |
| "Tell me about a conflict with a peer or manager" | Cross-team/manager disagreement story |
| "Tell me about a time you mentored someone" | Growth story |
| "Tell me about an ambiguous problem you had to scope yourself" | Scope/ambiguity story |

Full model answers for each of these live in `02_common_questions_with_excellent_answers.md`.

---

## Part 2: System Design Interviews

### What's Actually Being Evaluated

Unlike behavioral interviews, system design interviews evaluate your **process live** — the interviewer is watching how you think, not just what you eventually produce. This means narrating your reasoning out loud is not optional flavor, it's the actual content being scored. A silently-drawn perfect diagram scores worse than a narrated, slightly-imperfect one that shows clear reasoning.

### The System Design Framework

```
1. CLARIFY REQUIREMENTS (5-10 min)
   Functional: what must the system do?
   Non-functional: scale, latency, consistency, availability targets.
   Explicitly state assumptions the interviewer hasn't given you.

2. HIGH-LEVEL DESIGN (10-15 min)
   The 3-5 major components and the primary data flow — use the
   verbal-diagram techniques from 07_Architecture_Communication/02.
   Resist diving deep on any one component yet.

3. DEEP DIVE (15-20 min)
   Interviewer usually steers this — go deep on the component they're
   most interested in, using the Key Decisions pattern from
   07_Architecture_Communication/01 (alternative → chosen approach →
   reason → trade-off).

4. SCALE / FAILURE DISCUSSION (5-10 min)
   Bottlenecks at 10x scale, single points of failure, degradation
   modes — proactively, before being asked if time allows.

5. WRAP-UP (2-5 min)
   Summarize the design, name known gaps/future work explicitly.
```

### Narration Phrases for System Design (Making Your Process Visible)

- "Let me start with requirements before I design anything — can I ask a few clarifying questions?"
- "I'm going to assume [X] since it wasn't specified — flag me if that's wrong."
- "Let me sketch a simple version first, then find the bottleneck and iterate — I don't want to over-engineer the first pass."
- "There's a trade-off here between [X] and [Y] — I'm leaning toward [X] because [reason], but I want to flag the alternative explicitly."
- "Let me check this against the non-functional requirements before moving on — does this hold at [scale]?"
- "I'm intentionally deferring [X] — it's a real concern but not the most important one right now; I'll come back to it if we have time."
- "If I had more time I'd also want to think through [X] — flagging it as a known gap rather than pretending it's solved."

### The Requirements-Clarification Trap

The most common system-design interview failure isn't a bad final design — it's skipping or rushing Step 1 and designing against assumed requirements that turn out to be wrong, discovered halfway through Step 3 when it's expensive to unwind. Spend real time here even though it feels like "not designing yet" — it's the highest-leverage 10 minutes of the interview, because every subsequent decision depends on getting it right.

**Clarifying questions that are almost always worth asking:**
- "What's the expected scale — requests per second, data volume, and growth rate over the next year or two?"
- "What's more important if we have to choose — consistency or availability?"
- "What's the latency requirement, and is that p50, p99, or something else?"
- "Is this read-heavy, write-heavy, or roughly balanced?"
- "Are there existing systems this needs to integrate with, or is this greenfield?"

### Handling "What If Scale Was 100x?" Follow-Ups

This is testing whether your design has a genuine bottleneck you can identify, not whether you can produce an infinitely scalable system on the spot.

> "At 100x, the first thing to break would be [specific component] — right now it's a single [database/service instance], and at that scale I'd need to [shard by X / add read replicas / move to an async model]. I wouldn't build that from the start, because it adds complexity we don't need at current scale — but it's the first thing I'd revisit."

This answer is strong specifically because it names ONE concrete bottleneck with a concrete fix, rather than vaguely gesturing at "we'd add more scaling" — precision here is exactly what separates a senior answer from a junior one.

## Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Social-evaluative load** | The added cognitive and psychological burden of being watched and judged while performing. |
| **Calibrated** | Adjusted precisely to match reality — neither exaggerated nor understated. |
| **Fake-humble** | False modesty; an answer that appears humble but avoids genuine self-criticism. |
| **Not optional flavor** | Not a stylistic nicety layered on top, but a substantive requirement in itself. |
| **Gesture at (vaguely)** | To refer to something indirectly and imprecisely, without giving specifics. |
| **Unwind (a decision)** | To reverse or undo a decision or process already underway. |
| **High-leverage** | Producing disproportionately large returns relative to the effort or time invested. |

**Next:** [`02_common_questions_with_excellent_answers.md`](./02_common_questions_with_excellent_answers.md) — full worked model answers, bad → good → excellent, for the most common questions in both formats.

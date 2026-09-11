# Core Frameworks: PREP, STAR, SCQA

These are the three highest-utility named frameworks for engineering communication. Learn all three cold — not "understand them when you read them," but "can produce them on a 15-second timer with no notes." Together they cover the large majority of situations you'll face: explaining a fact (PREP), telling a story about something you did (STAR), and framing a proposal or written update (SCQA).

---

## PREP: Point → Reason → Example → Point

**Use for:** answering a direct question, explaining a technical decision, responding to "why did you..." in a meeting, most interview answers, most Slack/status-update explanations. This is your default — reach for it unless the situation specifically calls for STAR or SCQA.

```
P — POINT     State your answer/claim in one sentence.
R — REASON    The one mechanism/reason that makes it true.
E — EXAMPLE   Concrete evidence: a number, a story, a specific case.
P — POINT     Restate the point, often as a so-what/recommendation.
```

### Worked Example — "Why did you choose Terraform over CloudFormation?"

> **P:** We use Terraform mainly because we're multi-cloud, not purely AWS.
> **R:** CloudFormation only manages AWS resources, and we have Terraform managing Datadog monitors, GitHub repo settings, and Databricks workspaces alongside AWS infra — one tool, one state model, one CI pipeline.
> **E:** When we onboarded Databricks, we defined the workspace, cluster policies, and IAM roles in the same `terraform apply` as the VPC they sit in — no separate console click-ops step, no drift between the two.
> **P:** So it's less about Terraform being "better" than CloudFormation for pure AWS work, and more that a second tool for everything non-AWS would've meant two state models and two review processes.

Notice the second P isn't just a copy-paste repeat — it sharpens the point now that the listener has the reason and evidence, often by pre-empting the obvious follow-up ("isn't CloudFormation better for pure-AWS shops?").

### PREP for a One-Liner (Slack / quick verbal answer)

You don't always need all four beats spoken aloud — sometimes P+R alone, in one sentence, is the whole answer:

> "We're using RDS Proxy because our services were opening raw connections with no pooling." *(P + R fused)*

Add E and the closing P only when the question warrants depth (a design review, an interview, a postmortem) — not for a quick standup answer. Knowing when to compress PREP down to one sentence vs. expand it to four is itself a skill; see the altitude discussion in `01_Foundations/03`.

---

## STAR (and its cousin SOAR): Situation → Task → Action → Result

**Use for:** any question about something *you personally did* — almost all behavioral interview questions ("tell me about a time..."), performance review self-assessments, and any story where the listener needs to know your specific role and judgment, not just the system's mechanics.

```
S — SITUATION   The context: what was going on, briefly (2 sentences max)
T — TASK        What you specifically were responsible for / the goal
A — ACTION      What YOU did — first person, specific, decisions you made
R — RESULT      The outcome, quantified where possible, plus what you learned
```

**SOAR** is a close variant (Situation → Obstacle → Action → Result) that's slightly better when the story is really about overcoming a specific blocker rather than executing a plan — same shape, swap Task for Obstacle when that framing fits better.

### The Two Failure Modes STAR Is Designed to Prevent

1. **All Situation, no Action.** Engineers often over-invest in system context ("so this service handled 40k requests per second across 6 regions with a legacy sharding scheme...") and under-invest in *their own decisions*. Interviewers and reviewers are trying to assess **you**, not the system — S should be the shortest section, A should be the longest.
2. **"We" instead of "I."** Team stories are natural to tell in "we" ("we decided to...", "we noticed..."). STAR requires converting the Action section to first person: not because you're claiming sole credit, but because the listener needs to know *your specific contribution and judgment*, which "we" hides. It's fine to say "the team decided" for Situation/Task context and then switch to "I specifically owned/proposed/pushed for..." in Action.

### Worked Example — "Tell me about a time you disagreed with a technical decision."

> **S:** "On a Databricks migration, the team had already agreed to lift-and-shift our existing Airflow DAGs onto Databricks Workflows as-is, to hit a Q3 deadline."
> **T:** "I was the tech lead reviewing the migration plan before we started implementation."
> **A:** "I raised that lift-and-shift would carry over a known anti-pattern — DAGs with hardcoded cluster configs that had caused three capacity incidents that quarter. I proposed a two-week detour to introduce shared cluster policies first, and backed it with the incident count and the estimated ongoing cost of *not* fixing it, since I knew the team was deadline-focused and a vague 'this is technical debt' argument wouldn't land. I also volunteered to own that two-week piece myself so it wouldn't slip the rest of the team's timeline."
> **R:** "We took the two-week detour. The migration still landed only four days later than the original date, and we haven't had a capacity incident tied to cluster config since — it also became the template two other teams reused for their own Databricks migrations."

This is a complete STAR answer in about 45–60 seconds spoken, which is the right target length — see `08_Interview_Communication` for timing guidance and more worked answers.

---

## SCQA: Situation → Complication → Question → Answer

**Use for:** written proposals, design docs, the opening of a presentation or design review, any time you need to build shared context *before* your audience will accept your answer — because unlike PREP, SCQA deliberately delays the answer to first establish why it's needed. This is the correct exception to answer-first thinking (`02_Thinking_Frameworks/01`) — used deliberately, not by default.

```
S — SITUATION     A stable, uncontroversial fact everyone already agrees with
C — COMPLICATION  What changed / what's now a problem with that stable state
Q — QUESTION      The question this naturally raises (often left implicit)
A — ANSWER        Your proposal/recommendation — this IS your PREP point,
                   now landing with earned context instead of cold
```

### Worked Example — Opening of a design doc / design review

> **S:** "Our current ingestion pipeline processes about 2M events/day through a single-region Kafka cluster, and it's met our SLAs reliably for two years."
> **C:** "We just signed our first EU enterprise customer, and their data residency requirements mean EU event data can no longer transit through our US-region cluster — which is where 100% of our ingestion currently lives."
> **Q:** *(often left unstated, but it's: "how do we support EU data residency without duplicating our entire ingestion stack?")*
> **A:** "I'm proposing a regional Kafka cluster in eu-west-1 with MirrorMaker replicating only the non-PII aggregate topics back to US for cross-region analytics — full proposal below."

Why this works better than opening cold with the Answer: the Situation and Complication do the work of making the Answer feel *necessary* rather than *optional*, which matters enormously when you're proposing something with cost or timeline impact and need buy-in, not just comprehension. Compare to leading with the answer cold: *"I'm proposing a regional Kafka cluster in eu-west-1"* — technically answer-first, but it invites "why do we need that?" as the very next question, which SCQA has already pre-answered.

### PREP vs. SCQA — The Actual Decision Rule

| | PREP | SCQA |
|---|---|---|
| Listener already agrees the topic matters | ✅ default choice | Unnecessary overhead |
| You need buy-in / are proposing something with cost | Works, but risks feeling unmotivated | ✅ default choice |
| Quick verbal answer, meeting, interview | ✅ | Too slow |
| Design doc, proposal, presentation opening | Can work if audience is pre-aligned | ✅ default choice |
| Listener is impatient / senior / time-boxed | ✅ strongly | Risky — may want the answer sooner |

Full framework-selection logic (including Feynman and Pyramid Principle) lives in `03_framework_selection_guide.md`.

---

## Drill Script — Say All Three, Same Fact

Pick any fact about a system you work on and produce all three shapes back to back, out loud, on a timer. This single drill, repeated across different facts, is one of the fastest ways to make framework selection instinctive rather than effortful.

```
FACT: "We added a dead-letter queue to our order-processing pipeline."

PREP (10-15 sec):  Point → Reason → Example → Point
STAR (45-60 sec):  Situation → Task → Action → Result  (tell it as YOUR story)
SCQA (20-30 sec):  Situation → Complication → Question → Answer (as if opening a doc)
```

Do this for 5 different facts per session. It's built into `10_Daily_Practice/01_daily_and_weekly_practice_system.md` as a recurring block.

## Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Cousin** (framework) | A closely related variant of something, sharing most of its structure with small differences. |
| **Pre-empt** | To address an objection or question before it's raised, forestalling it. |
| **Fused** | Combined into a single unit — here, two beats of a framework compressed into one sentence. |
| **Cold** (land cold) | Delivered without prior buildup or context, so it lands abruptly. |
| **Buy-in** | Genuine agreement and support from others, not just passive understanding. |
| **Detour** | A deliberate, temporary departure from the main plan to address something first. |
| **Backed** (an argument) | Supported with concrete evidence rather than left as an assertion. |

**Next:** [`02_feynman_and_pyramid_principle.md`](./02_feynman_and_pyramid_principle.md) — the two frameworks focused on *simplification* and *structuring complex written/spoken arguments*, rather than answering a single question.

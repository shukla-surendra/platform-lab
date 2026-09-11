# Framework Selection Guide

A fast reference for "which framework do I reach for right now." The goal is that this decision eventually takes under a second — this document exists so you can drill it consciously now and stop needing it later.

## Master Decision Table

| Situation | Primary framework | Why |
|---|---|---|
| Someone asks "why did you do X" in a meeting | **PREP** | Direct question, answer-first is expected, fast |
| "Tell me about a time you..." (interview or 1:1) | **STAR / SOAR** | Needs your specific role and judgment, not just facts |
| Opening a design doc, RFC, or proposal | **SCQA** → **Pyramid Principle** for the body | Needs earned context before the ask, then structured support |
| Explaining a complex mechanism you understand well but haven't taught before | **Feynman pass**, then PREP or the Architecture Walkthrough Framework (`07`) | Pressure-tests for jargon-covered gaps first |
| Long presentation with multiple recommendations | **Pyramid Principle** | Keeps 3+ points from collapsing into an unstructured list |
| An incident summary / RCA | **Problem→Cause→Solution→Result** (`02_Thinking_Frameworks/02`, expanded in `05_Phrase_Library/04`) | Matches how the listener needs to receive incident information |
| A quick Slack update or standup line | **Compressed PREP** (P+R fused into one sentence) | No time/need for full four-beat structure |
| Defending an architecture decision under challenge | **PREP**, with the Trade-off layer mandatory (`01_Foundations/03`) | Challenge = they want the reasoning and the honest cost |
| Comparing two systems/tools | **Compare/Contrast Grid** (`02_Thinking_Frameworks/02`) inside a PREP shell | Grid organizes the thinking, PREP organizes the delivery |
| Pitching a vision/initiative, or "why do you do this work" | **Golden Circle** (`04`, Why → How → What) | Needs belief/buy-in around a purpose, not just comprehension of a fact |

## Flowchart

```
                         ┌─────────────────────────────┐
                         │ Is this a question about      │
                         │ something YOU personally did?  │
                         └───────────────┬───────────────┘
                            YES ◀─────────┴─────────▶ NO
                             │                          │
                    ┌────────▼────────┐      ┌──────────▼──────────┐
                    │  STAR / SOAR     │      │ Is this WRITTEN or a  │
                    └──────────────────┘      │ multi-point proposal? │
                                               └───────────┬───────────┘
                                                  YES ◀─────┴─────▶ NO
                                                   │                 │
                                    ┌──────────────▼───────┐   ┌─────▼──────────────────┐
                                    │ SCQA opening +          │   │ Is it an incident/bug/   │
                                    │ Pyramid Principle body   │   │ RCA-shaped problem?      │
                                    └──────────────────────┘   └───────────┬───────────────┘
                                                                  YES◀──────┴──────▶NO
                                                                   │                 │
                                                        ┌──────────▼─────┐   ┌───────▼────────┐
                                                        │ Problem→Cause→   │   │  Default: PREP   │
                                                        │ Solution→Result  │   │  (compress to    │
                                                        └─────────────────┘   │  one sentence if  │
                                                                               │  it's a quick Q)  │
                                                                               └────────────────┘
```

## The 80/20 Rule

In practice, roughly 80% of real engineering communication situations resolve to plain **PREP**, sometimes compressed to a single fused sentence (Point+Reason), sometimes fully expanded with Example and a closing Point. If you're ever unsure which framework to use and there's no time to consult this guide, default to PREP — answer first, one reason, one example, and you'll rarely be structurally wrong.

The other frameworks exist for the specific 20% where PREP under-serves the situation:
- **STAR** — when the listener needs to evaluate *you*, not just the system (interviews, performance reviews).
- **SCQA** — when the listener hasn't yet agreed the topic matters, and you need buy-in, not just comprehension (proposals, docs, cross-team asks).
- **Pyramid Principle** — when you have more than one governing point to make and need to prevent it collapsing into an unstructured list (long docs, big presentations).
- **Feynman pass** — not a delivery framework at all, but a pre-check you silently run on yourself before delivering any of the above, whenever you suspect your own understanding has an unexamined gap.
- **Golden Circle** (`04`) — when the goal is generating belief in a *direction or purpose*, not answering a question or justifying a decision already made — pitches, vision-setting, "why do you do this work."

## Combining Frameworks: A Real Example End-to-End

**Scenario:** you need to propose a Kubernetes migration in a design doc, then defend it live in a review, then later describe it in an interview as a story about your judgment.

| Context | Framework(s) used | Why |
|---|---|---|
| The design doc | SCQA opening, Pyramid Principle body (see full worked example in `02_feynman_and_pyramid_principle.md`) | Written, needs buy-in, multiple supporting arguments |
| Live design review, answering "why not just tune ECS instead?" | PREP, with explicit trade-off | Direct challenge question, needs a fast, defensible answer |
| A later interview: "tell me about a time you drove a major infra decision" | STAR | The interviewer is evaluating your judgment and process, not re-litigating the technical merits |

**Same underlying facts, three different containers** — chosen deliberately based on what the listener needs from you in that specific moment. This is the actual meta-skill this entire folder is building: not memorizing five frameworks, but developing the instinct for which one the room is asking for.

## Quick Self-Test

For each of the following, name the framework you'd reach for first (answers below):

1. Your manager Slacks: "quick q — why'd we bump the EKS node instance type?"
2. You're writing an RFC proposing a move from cron jobs to Airflow.
3. An interviewer asks: "tell me about a time a project you led went sideways."
4. You're presenting Q3 infra cost trends to leadership, with three separate cost drivers to explain.
5. A teammate asks you to walk them through last night's PagerDuty incident.

<details>
<summary>Answers</summary>

1. Compressed PREP (one or two sentences, Slack-appropriate).
2. SCQA opening + Pyramid Principle body.
3. STAR.
4. Pyramid Principle (governing conclusion = overall cost trend, three MECE supporting arguments = the three drivers).
5. Problem → Cause → Solution → Result.

</details>

## Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Under-serves** | Fails to adequately meet the needs of a situation. |
| **Meta-skill** | A higher-order skill about *when* and *how* to apply other skills, rather than a skill itself. |
| **Re-litigate** | To reopen and argue over a matter that was already settled. |
| **Sideways** (went sideways) | Idiom: went wrong or off track unexpectedly. |
| **80/20 rule** | The Pareto-derived idea that a small fraction of causes typically accounts for most of the effect. |
| **Defensible** | Able to be justified and held up under challenge. |
| **Buy-in** | Genuine agreement and support from others, not just passive understanding. |
| **Collapse** (into a list) | To lose intended structure and become a flat, undifferentiated sequence. |

**Next:** [`04_golden_circle_why_how_what.md`](./04_golden_circle_why_how_what.md) — the one
framework in this chapter that isn't about answering a question at all: generating belief in
a purpose before anyone's evaluated the specifics.

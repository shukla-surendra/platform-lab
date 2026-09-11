# Case Study: Scapegoating Inside a "Blameless" Postmortem

An eighth case study in this series. Blameless-postmortem language is a genuine, well-established engineering practice — but adopting the language of a practice is not the same as adopting its substance. This case examines what happens when a document is blameless and the room, and everything that happens after the room, is not.

## Index

1. [The Situation](#1-the-situation)
2. [Root-Cause Analysis](#2-root-cause-analysis)
3. [What the Individual Contributed](#3-what-the-individual-contributed)
4. [What the Organization Got Wrong](#4-what-the-organization-got-wrong)
5. [The Test: Was It Actually Blameless?](#5-the-test-was-it-actually-blameless)
6. [The Forward Protocol](#6-the-forward-protocol)
7. [Coaching Takeaway](#7-coaching-takeaway)
8. [Glossary — Vocabulary Used in This Chapter](#8-glossary--vocabulary-used-in-this-chapter)

---

## 1. The Situation

An organization used formal blameless-postmortem templates — the standard language explicitly instructs contributors to "focus on systems, not individuals." Following a high-visibility incident, the postmortem repeatedly circled back to a single engineer's specific action (a config change, a deploy) as "the trigger." The document never named the engineer directly, but the phrasing was transparent to everyone in the room about whose action was meant.

Other contributing factors were mentioned in the document but weighted far less heavily: an executive-mandated deadline that had skipped a normal review step, and a known-fragile system that nobody had been resourced to fix over the prior two quarters. In the weeks after the postmortem was published — officially finding no individual fault — the engineer whose action had been "the trigger" experienced a visible shift in treatment: fewer high-visibility assignments, more oversight on routine work. Nothing in the official document recommended any of this.

[↑ Back to index](#index)

## 2. Root-Cause Analysis

**Mechanism A — blameless language protects the document, not the conversation or the aftermath.** A template can enforce that no name appears on the page while doing nothing to prevent the same information from being read, discussed, and acted on informally exactly as if it had. The document's blamelessness is real and simultaneously beside the point, because the actual consequences were never routed through the document in the first place.

**Mechanism B — proximate cause substitutes for systemic cause under pressure.** A specific, easy-to-point-to action — a deploy, a config change — is much easier to name and act on than a systemic cause like chronic under-resourcing or a deadline decision that removed a safety step, especially when the systemic cause implicates a more senior stakeholder's own prior decision. Under time and political pressure to produce a clean, singular explanation, blame quietly flows toward the position with the least power to contest the framing — not necessarily toward the largest actual contributing factor.

**Why the gap survives review.** Because the process's formal output — the document, the official recommendations — looks clean and genuinely blameless, there is no written record to point to when informal consequences show up afterward. The engineer cannot cite the postmortem to contest their changed treatment, because the postmortem, on paper, never blamed them at all.

[↑ Back to index](#index)

## 3. What the Individual Contributed

- **Not pushing, in the room, for systemic contributing factors to be weighted as explicitly as the proximate trigger.** Silence about the skipped review step and the resourcing gap let the easier, more convenient causal story — "the deploy caused it" — stand without a documented counterweight.
- **Not naming the informal treatment shift directly and early**, for the same reason described in `07_case_study_managed_exit.md` — waiting allows a pattern to compound and become harder to contest before it's named at all.
- **Treating the document's official blamelessness as sufficient protection.** A clean written finding does not, by itself, guarantee that informal consequences will track it — that gap has to be actively checked, not assumed closed.

[↑ Back to index](#index)

## 4. What the Organization Got Wrong

- **Adopting blameless language as a process artifact without addressing the underlying pressure that produces blame-seeking in the first place** — the pressure, in a high-visibility incident, to identify a single, clean, easily communicated cause.
- **No mechanism connecting the postmortem's official findings to any actual review of whether subsequent treatment matches them.** A document can be perfectly blameless and still be functionally irrelevant if nothing checks that reality lines up with it afterward.
- **Allowing a systemic cause that implicated a senior stakeholder's own prior decision to be under-weighted relative to a junior engineer's proximate action, without ever acknowledging that asymmetry openly.** The unevenness itself went unexamined, which is what let it operate without resistance.

[↑ Back to index](#index)

## 5. The Test: Was It Actually Blameless?

Does the postmortem's stated causal weighting match the actual pattern of consequences that follow it? If a document concludes "systemic, no individual fault" but one specific person's subsequent treatment measurably changes while the identified systemic factors go unaddressed, the document and the reality have diverged — and the process was not actually blameless, only worded that way. The test isn't what the document says; it's whether anyone's treatment quietly moves in a direction the document doesn't account for.

[↑ Back to index](#index)

## 6. The Forward Protocol

1. **In the room, explicitly ask for contributing factors to be weighted, not just listed.** A flat list that doesn't distinguish proximate triggers from systemic root causes leaves the actual weighting to be decided informally, later, by whoever ends up retelling the story.
2. **Push for politically inconvenient systemic causes — resourcing, a skipped review step, a deadline decision — to be documented with the same specificity as the proximate technical action.** Specificity is what makes a cause actionable and hard to quietly deprioritize afterward.
3. **If informal treatment shifts after an officially blameless postmortem, name the discrepancy directly and early, citing the document itself** — "the postmortem found this was systemic, but I'm seeing a change in how assignments are being made since then — can we reconcile that?"
4. **Track assignment, inclusion, and oversight changes with a dated log**, the same practice recommended in `07_case_study_managed_exit.md` §6 — it converts "I feel like I'm being treated differently" into a checkable, citable pattern.
5. **Advocate for a scheduled follow-up check some weeks after any high-visibility postmortem**: did treatment of anyone involved actually change, and does that match the document's stated findings? A gap there is itself worth surfacing as a process failure, independent of the original incident.

[↑ Back to index](#index)

## 7. Coaching Takeaway

A blameless label describes a document, not necessarily a culture. The real test of whether blame was actually distributed systemically is not what the postmortem says, but whether anyone's treatment quietly changes afterward in a way the document doesn't account for. Silence in the room, when a systemic cause is being underweighted relative to a proximate one, is what allows the easier and more convenient story to become the operative one — regardless of how carefully the final document is worded.

[↑ Back to index](#index)

## 8. Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Blameless postmortem** | An incident-review practice designed to focus analysis on systems and processes rather than assigning fault to individuals. |
| **Proximate cause** | The immediate, most direct action or event that triggered a failure — often the easiest cause to identify but not necessarily the most important one. |
| **Systemic cause** | An underlying structural or organizational condition (resourcing, process gaps, prior decisions) that made a failure likely, independent of any single triggering action. |
| **Causal weighting** | The relative importance assigned to different contributing factors in an analysis, which determines what gets treated as the "real" cause. |
| **Under-resourcing** | A chronic gap between the effort or staffing a system needs and what it has actually been allocated. |
| **Operative story (vs. official story)** | The explanation that actually drives decisions and behavior, which may differ from the explanation formally documented. |
| **Reconcile (a discrepancy)** | To directly compare a documented finding against observed reality and explicitly address any gap between them. |

[↑ Back to index](#index)

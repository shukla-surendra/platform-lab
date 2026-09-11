# Case Study: Onshore Political Targeting of Offshore Contractors (Job-Security-Driven Elimination)

A thirteenth case study in this series, and a close relative of `07_case_study_managed_exit.md` and `12_case_study_whisper_campaign.md` — it shares the managed exit's use of individually-deniable steps and the whisper campaign's exploitation of asymmetric visibility, but runs on a structural engine the other two don't have: **budget-driven job security**. When headcount, cost, or renewal decisions are on the table, and an onshore employee perceives an offshore or contract engineer as the line item most likely to be cut *before* their own role, a specific and recurring pattern emerges — not because the onshore employee is unusually malicious, but because the org structure quietly rewards making someone else look like the safer cut. Read this alongside `../02_Thinking_Frameworks/13_conflict_management_in_projects.md` §6–7, which covers the ordinary structural friction this pattern hijacks and the diagnostic for telling the two apart.

## Index

1. [The Situation](#1-the-situation)
2. [Root-Cause Analysis](#2-root-cause-analysis)
3. [Why This Happens Even Without a "Villain"](#3-why-this-happens-even-without-a-villain)
4. [What the Individual Contributed](#4-what-the-individual-contributed)
5. [What the Organization Got Wrong](#5-what-the-organization-got-wrong)
6. [The Forward Protocol](#6-the-forward-protocol)
7. [Coaching Takeaway](#7-coaching-takeaway)
8. [Glossary — Vocabulary Used in This Chapter](#8-glossary--vocabulary-used-in-this-chapter)

---

## 1. The Situation

An offshore contractor joined a mixed onshore/offshore project team and, over several months, delivered solid, on-time work — nothing flagged, no complaints raised directly. As a budget review approached, an onshore team member began, in meetings the contractor wasn't part of, characterizing the contractor's work in subtly deflated terms: "still ramping up," "needs a lot of hand-holding," "I've had to redo some of what they sent over." None of this was said to the contractor directly, and none of it matched the actual git history, ticket record, or the direct feedback the contractor had been receiving in their own 1:1s with the delivery lead.

Separately, the contractor noticed being looped into fewer design discussions than before, occasionally finding out about decisions after they'd already been made, and once discovering that a piece of work they had, in fact, completed and demoed weeks earlier was described in a leadership update as "still in progress" — with no name attached, leaving the ambiguous impression that it might be stalled on the contractor's end. When the cost-review cycle arrived, the contractor's engagement was flagged as a "candidate for reduction," with the stated rationale citing "ramp-up concerns" that traced directly back to the earlier informal characterizations — now circulating as though they were an agreed team assessment rather than one person's unverified framing.

[↑ Back to index](#index)

## 2. Root-Cause Analysis

**Mechanism A — the cost line item makes the target legible in a way peers aren't.** A contractor's cost typically appears explicitly, on a schedule, in a document leadership reviews (`../02_Thinking_Frameworks/12_project_management_literacy_for_engineers.md` §5 — this is the RAID/status-report layer working exactly as designed, except now being aimed). An onshore FTE's fully-loaded cost almost never surfaces the same way in the same forum. When a budget conversation needs a name attached to "what could we cut," the contractor is structurally the easiest name to reach for — not because their work is weaker, but because their cost is the one already sitting in the spreadsheet.

**Mechanism B — asymmetric visibility does the framing for free.** Onshore staff share physical or synchronous-timezone proximity to decision-makers; the contractor's work is visible mainly through scheduled artifacts. This means an onshore voice characterizing the contractor's work reaches leadership *first and more often* than the contractor's own actual output does — the same visibility gap named structurally in `../02_Thinking_Frameworks/13_conflict_management_in_projects.md` §6, now being used adversarially rather than just navigated.

**Mechanism C — distributed, deniable seeding (shared with the whisper campaign).** Each individual comment — "still ramping up," "needed some rework" — is vague enough to be defensible as an honest, isolated impression. No single remark is provably false or provably malicious. The pattern only becomes visible in aggregate, and by the time it's dense enough to name, it has already shaped the cost-review outcome, exactly per `12_case_study_whisper_campaign.md` §2's mechanism.

**Mechanism D — an incentive that doesn't require intent to bite.** If the org signals, even implicitly, that a shrinking budget will be resolved by headcount reduction rather than reprioritization, every team member is quietly incentivized to not be the name on the list. Making someone else look like the safer cut is a locally rational response to that incentive — which is precisely why this pattern recurs across organizations that have never met each other: it's produced by the structure, not by a particular person's character.

[↑ Back to index](#index)

## 3. Why This Happens Even Without a "Villain"

It is tempting, and often wrong, to read this pattern as requiring a deliberately malicious actor. More often, the onshore employee is genuinely anxious about their own position, has partial and honestly-held (if inaccurate) impressions formed through the visibility gap in Mechanism B, and expresses those impressions in venues where a contractor's engagement happens to be adjudicated — without ever consciously framing it as "removing a competitor." The outcome is identical to a deliberate campaign either way, which is exactly why this case study focuses on **structural and pattern-level detection** rather than on proving anyone's intent — intent is usually unprovable and, for the purpose of protecting oneself, beside the point. (Where the pattern is closer to deliberate, the mechanism and countermeasures described here still apply — see the "good faith / bad faith" note in `07_case_study_managed_exit.md` §8's glossary.)

[↑ Back to index](#index)

## 4. What the Individual Contributed

- **Relying on direct 1:1 feedback as the full picture of standing**, when the actual decision-relevant conversations were happening in rooms and channels the contractor wasn't in. Positive feedback from a direct manager doesn't guarantee the same picture is reaching whoever owns the budget decision.
- **No artifact trail tying delivered work to dates and outcomes**, independent of what got said about it verbally afterward. The completed-but-reported-as-"in-progress" item had no contractor-owned record making its actual delivery date checkable by a third party.
- **Treating occasional exclusion from discussions as isolated scheduling noise** rather than logging it as a pattern from the first instance — the same underlying discipline `07_case_study_managed_exit.md` §6 recommends for scope-reduction signals, applicable here to visibility reduction.
- **Not building a second relationship with a sponsor beyond the immediate delivery lead** — the single-relationship exposure named directly in `12_case_study_whisper_campaign.md` §4, which applies with extra force to contractors, whose entire engagement typically routes through one or two relationships by default.

[↑ Back to index](#index)

## 5. What the Organization Got Wrong

- **Basing a cost-review decision on informal, unattributed characterization rather than the documented delivery record.** A "candidate for reduction" rationale citing "ramp-up concerns" should have been checked against tickets, delivery dates, and the contractor's own manager's assessment before being accepted into a formal review — and wasn't.
- **No norm of asking "has this been said to them directly?"** — the identical structural gap named in `12_case_study_whisper_campaign.md` §5, and just as load-bearing here: a leader who reflexively asks this question of any negative characterization removes most of this pattern's power, because it forces the concern into the open where it can be checked against reality.
- **Allowing cost visibility asymmetry to substitute for a fair comparison.** If contractor cost is scrutinized on a schedule and FTE cost isn't scrutinized with anything like the same rigor, "who's most replaceable" is being decided by *accounting convenience*, not by actual value delivered — a decision criterion no one would defend if stated plainly.
- **No requirement that budget-driven reduction decisions be checked against a documented performance record before being finalized.** The absence of this gate is what let an unverified informal narrative become the operative rationale.

[↑ Back to index](#index)

## 6. The Forward Protocol

1. **Keep a running, dated record of delivered work, independent of anyone else's summary of it** — commits, tickets closed, demos given, dates. This is the direct analogue of the dated log in `07_case_study_managed_exit.md` §6, aimed specifically at the artifact gap this pattern exploits: a contractor's own record is the thing that outlives and outranks a verbal mischaracterization.
2. **Send a brief, regular status update to the actual budget-owning stakeholder, not only the day-to-day delivery lead** (`../02_Thinking_Frameworks/11_role_clarity_and_expectation_contracts.md` §7, point 3 — the weekly three-line habit). This closes Mechanism B directly: it puts the contractor's own account of their work in front of the person who will eventually see the cost line, before anyone else's characterization gets there first.
3. **Build at least one relationship with a stakeholder beyond the immediate manager** — a skip-level, the economic buyer, or a peer lead who can independently vouch for delivered work. Single-relationship exposure is the same vulnerability named in `12_case_study_whisper_campaign.md` §4, and a contractor typically starts with fewer organic relationships than an FTE, making this a deliberate task rather than something that happens by default.
4. **If exclusion from discussions or decisions becomes noticeable, name it directly and factually, early** — "I noticed I wasn't looped into the caching design discussion last week — was that intentional, or should I be included going forward?" A specific, factual question, asked promptly, is far harder to wave off than a pattern raised only after the damage compounds.
5. **If a reduction rationale ever surfaces that cites vague performance language, ask for it in specific, checkable terms, in writing, and be prepared to answer it with the record from point 1.** "Ramp-up concerns" is not falsifiable as stated; "specifically which deliverables were late or needed rework, and when" is — and usually resolves in the contractor's favor once the actual record is compared against the vague claim.
6. **Treat renewal risk as continuous, not just a cost-review-season event**, per `../02_Thinking_Frameworks/11_role_clarity_and_expectation_contracts.md` §7 and §8 — the mitigations above (status visibility, multiple relationships, a clean delivery record) are cheapest maintained continuously and most expensive to assemble reactively once a reduction conversation has already started.

[↑ Back to index](#index)

## 7. Coaching Takeaway

This pattern is produced by structure — visible cost, asymmetric visibility, and a budget incentive that rewards not being the easiest name on the list — more often than by any individual's deliberate malice, which is exactly why it recurs so predictably across unrelated organizations. The countermeasure is not confrontation with whoever made the informal remarks (usually unprovable and often not even consciously adversarial) but **structural self-defense**: an independent, dated record of delivered work; direct visibility to the actual budget-owning stakeholder, not just the daily contact; and more than one relationship that can vouch for the work if a vague characterization ever needs to be checked against reality. A contractor who maintains all three going in is not paranoid — they are simply accounting for an incentive structure that is real, common, and worth taking seriously before a budget cycle forces the issue.

[↑ Back to index](#index)

## 8. Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Legible** | Easy for an outside observer (here, leadership) to read, identify, and act on |
| **Fully-loaded cost** | An employee's total cost to the organization, including salary, benefits, and overhead — not just visible line-item pay |
| **Distributed, deniable seeding** | Planting the same characterization with multiple people or in multiple settings so no single instance proves a coordinated pattern |
| **Locally rational** | Sensible from one party's own immediate incentives, even if the aggregate outcome is unfair or harmful |
| **Adjudicated** | Formally decided or judged, typically by a person or process with authority to do so |
| **Falsifiable** | Stated precisely enough that it could, in principle, be checked and shown to be false |
| **Economic buyer** | The person who controls the budget and makes the purchase or renewal decision |
| **Skip-level** | A manager one or more levels above one's direct manager |
| **Operative rationale** | The reason actually driving a decision, as opposed to the reason officially stated |
| **Structural self-defense** | Protective measures aimed at the underlying incentive structure itself, rather than at any one person's behavior |
| **Reactively (assembled)** | Put together only after a problem has already surfaced, rather than prepared in advance |

[↑ Back to index](#index)

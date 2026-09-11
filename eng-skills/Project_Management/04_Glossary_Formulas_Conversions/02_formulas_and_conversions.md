# PMI Formulas and Term Conversions — The Numbers and the Translation Layer

Two things engineers specifically asked to see in one place: the standard PMI/PMP formula sheet (EVM, PERT, critical path, communication channels) worked with real numbers, and a **PM-speak ↔ engineer-speak conversion table** — because the fastest way to become fluent in a second vocabulary is to see it mapped directly against a first one that's already native.

## Index

1. [Earned Value Management (EVM) — Full Formula Sheet](#1-earned-value-management-evm--full-formula-sheet)
2. [PERT / Three-Point Estimating](#2-pert--three-point-estimating)
3. [Critical Path and Float — Worked Calculation](#3-critical-path-and-float--worked-calculation)
4. [Communication Channels Formula](#4-communication-channels-formula)
5. [Other Common Formulas](#5-other-common-formulas)
6. [PM-Speak ↔ Engineer-Speak Conversion Table](#6-pm-speak--engineer-speak-conversion-table)
7. [Glossary — Vocabulary Used in This Chapter](#7-glossary--vocabulary-used-in-this-chapter)

---

## 1. Earned Value Management (EVM) — Full Formula Sheet

EVM is the technique PMs use to answer, with numbers, "are we actually on track" — introduced in `../02_Knowledge_Areas/02_cost_quality_resource_management.md` §1. Three base measures, taken at a specific point in time:

| Measure | Definition |
|---|---|
| **PV (Planned Value)** | The authorized budget for work scheduled to be done by this point |
| **EV (Earned Value)** | The value of work actually completed by this point, measured in budgeted terms |
| **AC (Actual Cost)** | The actual cost incurred for the work completed by this point |

### Worked scenario

A project has a total budget (**BAC**, Budget at Completion) of **$100,000**, scheduled to complete in 10 weeks ($10,000/week planned). At the end of week 4:
- **PV** = 4 weeks × $10,000 = **$40,000** (what should have been spent/done by now)
- Actual progress: only 35% of the total work is actually done → **EV** = 0.35 × $100,000 = **$35,000**
- Actual money spent so far: **AC** = **$42,000**

### Derived formulas

| Formula | Calculation | Result | Meaning |
|---|---|---|---|
| **CV (Cost Variance) = EV − AC** | $35,000 − $42,000 | **−$7,000** | Negative = over budget for the work actually completed |
| **SV (Schedule Variance) = EV − PV** | $35,000 − $40,000 | **−$5,000** | Negative = behind schedule |
| **CPI (Cost Performance Index) = EV / AC** | $35,000 / $42,000 | **0.83** | Getting $0.83 of value for every $1 spent — below 1.0 is unfavorable |
| **SPI (Schedule Performance Index) = EV / PV** | $35,000 / $40,000 | **0.875** | Completing work at 87.5% of the planned rate — below 1.0 is behind |
| **EAC (Estimate at Completion) = BAC / CPI** | $100,000 / 0.83 | **≈ $120,482** | If current cost efficiency holds, the project will actually cost this much |
| **ETC (Estimate to Complete) = EAC − AC** | $120,482 − $42,000 | **≈ $78,482** | How much more money is needed from here |
| **VAC (Variance at Completion) = BAC − EAC** | $100,000 − $120,482 | **≈ −$20,482** | The project is trending to be over budget by this amount at completion |
| **TCPI (To-Complete Performance Index) = (BAC − EV) / (BAC − AC)** | ($100,000 − $35,000) / ($100,000 − $42,000) | **1.12** | The cost efficiency now required for all *remaining* work to still hit the original budget — above 1.0 means the team must work more efficiently than it has so far, and a TCPI meaningfully above 1.2 is usually a signal the original budget is no longer realistically recoverable |

The single sentence that makes CPI and SPI immediately readable without recalculating anything: **below 1.0 is bad, above 1.0 is good, exactly 1.0 is on plan** — for both indices, in both directions (cost and schedule).

[↑ Back to index](#index)

## 2. PERT / Three-Point Estimating

Used when a single-point estimate is too uncertain to trust — combines an optimistic, most-likely, and pessimistic estimate into one weighted expected value:

> **Expected duration (TE) = (Optimistic + 4 × Most Likely + Pessimistic) / 6**

Worked example: a training-pipeline task estimated at **3 days optimistic**, **5 days most likely**, **14 days pessimistic** (accounting for a possible data-quality issue):

> TE = (3 + 4×5 + 14) / 6 = (3 + 20 + 14) / 6 = 37 / 6 ≈ **6.17 days**

Note how the heavily-weighted "most likely" term keeps the estimate from being dragged too far by the tail-risk pessimistic case, while still pulling it meaningfully above the naive average of the three ((3+5+14)/3 ≈ 7.3, actually higher here — a reminder that the weighting matters and shouldn't be assumed to always pull the estimate down). The companion formula for uncertainty itself:

> **Standard deviation (σ) = (Pessimistic − Optimistic) / 6**
> σ = (14 − 3) / 6 ≈ **1.83 days**

A wide spread between optimistic and pessimistic produces a large σ — itself useful, precise vocabulary for saying "this estimate is genuinely uncertain" instead of a vague verbal hedge, directly supporting the calibrated-estimation practice in `../../Communication-Mastery/02_Thinking_Frameworks/12_project_management_literacy_for_engineers.md` §6.

[↑ Back to index](#index)

## 3. Critical Path and Float — Worked Calculation

A small worked network, four activities feeding a milestone:

```
        A(3d) ──► C(4d) ──►
Start ─┤                    ├─► Finish
        B(2d) ──► D(6d) ──►
```

**Forward pass** (earliest start/finish): Path A→C = 3+4 = 7 days. Path B→D = 2+6 = 8 days.

**The critical path is B→D (8 days)** — the longer of the two, and therefore the path with zero float; the project cannot finish before day 8.

**Float on path A→C**: the critical path takes 8 days; A→C only needs 7, so A→C has **1 day of total float** — activity A or C (or both, distributed) could slip by up to 1 day combined without delaying the project's finish date.

This is the exact mechanical basis behind the "am I on the critical path?" question recommended in `../../Communication-Mastery/02_Thinking_Frameworks/12_project_management_literacy_for_engineers.md` §7 — a task with float genuinely can absorb a delay for free; a task with zero float cannot, and any slip there moves the entire project's end date one-for-one.

[↑ Back to index](#index)

## 4. Communication Channels Formula

Already introduced in `../02_Knowledge_Areas/03_communications_management.md` §3 — repeated here as part of the formula sheet for completeness:

> **Channels = n(n − 1) / 2**

| n | Channels | n | Channels |
|---|---|---|---|
| 5 | 10 | 12 | 66 |
| 6 | 15 | 15 | 105 |
| 8 | 28 | 20 | 190 |
| 10 | 45 | 25 | 300 |

[↑ Back to index](#index)

## 5. Other Common Formulas

| Formula | Use |
|---|---|
| **ROI = (Gain from Investment − Cost of Investment) / Cost of Investment** | Comparing the financial return of competing initiatives |
| **NPV = Σ [Cash flow at time t / (1 + discount rate)^t] − Initial investment** | Comparing projects with cash flows spread over different timeframes, in today's-dollar terms |
| **Payback period = Initial investment / Annual cash inflow** (for even cash flows) | Quick, rough comparison of how fast an investment recoups itself |
| **Present Value (PV, finance sense — not to be confused with EVM's Planned Value) = FV / (1 + r)^n** | The current worth of a future sum, discounted at rate r over n periods |
| **Cost of Quality = Cost of Conformance + Cost of Nonconformance** | Building the business case for investment in testing/monitoring infrastructure — `../02_Knowledge_Areas/02_cost_quality_resource_management.md` §2 |

[↑ Back to index](#index)

## 6. PM-Speak ↔ Engineer-Speak Conversion Table

The fastest route to fluency: mapping PMI terminology directly against the nearest native engineering concept.

| PM-speak | Nearest engineering equivalent | Note on the mapping |
|---|---|---|
| Baseline | A tagged release / a git commit hash frozen as a reference point | Both are "the version everything else gets diffed against" |
| Change control | A pull request / RFC review process | Both gate any modification to an agreed, frozen state |
| WBS | A task/epic decomposition tree, or a dependency graph of tickets | The WBS *is* the backlog's hierarchical structure, just named differently |
| Critical path | The longest chain in a build's dependency graph (like a critical path in a DAG scheduler) | Exactly the same graph-theory concept, borrowed vocabulary |
| RACI | CODEOWNERS + an on-call rotation, formalized | Both answer "who is actually responsible for this" |
| RAID log | An issue tracker's "risks" label + assumptions doc + blocked-tickets view, unified | PM formalizes what engineers often track informally and separately |
| Sprint | An iteration / release cycle | Nearly identical concept, same word difference as "ticket" vs. "work item" |
| Definition of Done | The CI/CD pipeline's required checks passing, plus review approval | Both are the explicit, checkable bar for "actually finished" |
| EVM (CPI/SPI) | Burn-rate dashboards, but formalized into a ratio comparable across projects | The engineering instinct ("are we burning budget/time faster than progress") formalized numerically |
| Stakeholder engagement plan | A "who to Slack/page for what" runbook, extended to include humans outside the on-call rotation | Same underlying need: route information to the right party |
| Risk register | A pre-mortem / known-issues backlog, made mandatory and reviewed on a cadence | Risk management is threat modeling, generalized beyond security |
| Procurement | Vendor selection / build-vs-buy decisions, formalized with contract types | The RFC process an engineering org runs before adopting a new managed service |
| Governance / steering committee | An architecture review board | Both are the body with authority to approve or block significant decisions |
| Lessons learned | A postmortem / retro doc | Nearly identical in function and intent |
| Milestone | A release tag / a phase-gate demo | A zero-duration marker of "this state has been reached" |
| Scope creep | Feature creep / ticket scope expanding mid-sprint | Same failure mode, same name almost verbatim in engineering culture already |

[↑ Back to index](#index)

## 7. Glossary — Vocabulary Used in This Chapter

| Term/Phrase | Meaning |
|---|---|
| BAC (Budget at Completion) | The total approved budget for all project work |
| PV (Planned Value) | The authorized budget for work scheduled to be done by a given point |
| EV (Earned Value) | The budgeted value of work actually completed by a given point |
| AC (Actual Cost) | The actual cost incurred for completed work |
| CV / SV | Cost Variance / Schedule Variance |
| CPI / SPI | Cost / Schedule Performance Index |
| EAC / ETC / VAC / TCPI | Estimate at Completion / to Complete; Variance at Completion; To-Complete Performance Index |
| TE (PERT expected duration) | The weighted expected duration from three-point estimating |
| Standard deviation (σ) | A measure of how spread out estimates or values are around their expected value |
| Forward pass | The critical-path-method calculation of earliest possible start/finish times |
| Total float | The amount a path can slip without delaying the project's overall finish date |
| Discount rate | The interest rate used to convert future cash flows into present-day value |
| Pre-mortem | An exercise imagining a project has already failed, to surface risks in advance |
| CODEOWNERS | A file convention assigning review responsibility for parts of a codebase |
| DAG (Directed Acyclic Graph) | A graph with directed edges and no cycles — the structure underlying most build/task schedulers |
| Verbatim | In exactly the same words, without paraphrase |

[↑ Back to index](#index)

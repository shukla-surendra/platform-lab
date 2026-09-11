# Integration, Scope, and Schedule Management

The three knowledge areas that define, respectively, *how the project stays coherent as one whole*, *what is and isn't included*, and *when things happen*. These three are grouped together because they share a single throughline: each manages a **baseline** — a fixed reference point — against which everything else is measured, and each is governed by a **formal change process** that protects that baseline from silent drift.

## Index

1. [Integration Management](#1-integration-management)
2. [Scope Management](#2-scope-management)
3. [Schedule Management](#3-schedule-management)
4. [How the Three Interlock](#4-how-the-three-interlock)
5. [Glossary — Vocabulary Used in This Chapter](#5-glossary--vocabulary-used-in-this-chapter)

---

## 1. Integration Management

### Definition

The knowledge area responsible for identifying, defining, combining, unifying, and coordinating the various processes and activities within the other nine knowledge areas. It is the "whole is more than the sum of parts" discipline — the reason a single person (the PM) exists to hold scope, schedule, cost, risk, and stakeholder concerns as one coherent picture rather than five disconnected streams.

### Key artifacts and concepts

| Term | Definition |
|---|---|
| **Project charter** | The document that formally authorizes a project (or phase) and gives the PM authority to apply resources. It states the business need, high-level scope, sponsor, and success criteria. This is the document worth actually reading in full — it is the ultimate arbiter of scope disputes, per `../../Communication-Mastery/02_Thinking_Frameworks/12_project_management_literacy_for_engineers.md` §3 |
| **Project management plan** | The master document — the approved, integrated collection of all subsidiary plans (scope, schedule, cost, risk, communications, etc.) |
| **Integrated Change Control** | The formal process by which any change to a baseline (scope, schedule, cost) is reviewed, approved or rejected, and incorporated — the process that stands between "an idea" and "an approved change" |
| **Change Control Board (CCB)** | The group (or individual) with authority to approve or reject formal change requests |
| **Configuration management** | The system for tracking and controlling changes to a product's specifications and documentation, distinct from but closely related to change control |
| **Lessons learned register** | A running record, ideally updated throughout the project (not just at the end), of what worked and what didn't, feeding the closing-phase retrospective |

### Why it matters to an engineer

Every technical change of any real size — a new dependency, a scope addition, a re-architected component — is, from the PM's side, a potential **integrated change control** event, not just an engineering decision. Framing a proposal as "here's a change request: here's what it affects in scope, schedule, and cost" gets it processed correctly and quickly; framing it only in technical terms and hoping it gets absorbed invisibly is what produces the "wait, why did the date move?" conversation two weeks later.

[↑ Back to index](#index)

## 2. Scope Management

### Definition

The processes required to ensure the project includes all the work required — and only the work required — to complete it successfully.

### Key artifacts and concepts

| Term | Definition |
|---|---|
| **Scope statement (project scope statement)** | A detailed description of the project's deliverables and the work required to create them, including explicit exclusions |
| **Requirements documentation** | The captured, traceable set of stakeholder needs and expectations the project must satisfy |
| **Requirements Traceability Matrix (RTM)** | A table linking each requirement to its source, to the design/component that satisfies it, and to the test that verifies it — the mechanism that lets anyone answer "why does this exist?" and "how do we know it works?" |
| **Work Breakdown Structure (WBS)** | A hierarchical decomposition of the total scope of work into smaller, more manageable components, down to **work packages** — the smallest unit typically assigned and tracked |
| **WBS dictionary** | The companion document defining exactly what each WBS element includes, its acceptance criteria, and who owns it |
| **Scope baseline** | The approved scope statement + WBS + WBS dictionary, together — the reference point scope creep is measured against |
| **Scope creep** | Uncontrolled expansion of scope without corresponding adjustments to time, cost, or resources — the informal, undocumented cousin of a legitimate scope change |
| **Gold plating** | Adding extra features or polish beyond what was requested or required — well-intentioned, but it consumes budget/time without authorization and without corresponding value, and it is scope creep's self-inflicted twin |
| **Decomposition** | The technique of subdividing project scope into smaller, more manageable pieces — the mechanism that produces the WBS |
| **Rolling wave planning** | Planning near-term work in detail while leaving distant work at a coarser level, refined as it approaches — the standard technique for planning under uncertainty, and the formal name for what most engineers already do instinctively when a full upfront plan isn't realistic |

### Why it matters to an engineer

The WBS is the artifact most engineers should actually want to shape, because it is the point where "what counts as this task being done" gets fixed. An engineer who reviews the WBS dictionary for their own work packages and pushes back on unclear acceptance criteria *before* execution starts is doing exactly the kind of upstream influence described in `../01_Foundations/01_what_is_project_management.md` §3 — cheap now, expensive as a dispute later. **Scope creep and gold plating are the two directions the same failure can run** — one imposed from outside, one self-inflicted from a desire to over-deliver — and both are corrosive to a schedule for the same reason: unauthorized, untracked work.

[↑ Back to index](#index)

## 3. Schedule Management

### Definition

The processes required to manage the timely completion of the project.

### Key artifacts and concepts

| Term | Definition |
|---|---|
| **Activity list** | The full set of scheduled activities required to produce the project's deliverables, derived from decomposing work packages further |
| **Activity sequencing** | Determining and documenting the relationships (dependencies) among activities |
| **Dependency types** | **Finish-to-Start (FS)** — most common: B can't start until A finishes. **Start-to-Start (SS)** — B can't start until A starts. **Finish-to-Finish (FF)** — B can't finish until A finishes. **Start-to-Finish (SF)** — rare: B can't finish until A starts |
| **Lead** | Time by which a successor activity can be *advanced* relative to a predecessor (overlap) |
| **Lag** | Time by which a successor activity must be *delayed* relative to a predecessor (waiting time) |
| **Network diagram** | A graphical representation of the logical relationships (dependencies) among schedule activities |
| **Critical Path Method (CPM)** | The technique for calculating the longest sequence of dependent activities, determining the shortest possible project duration — full formula walkthrough in `../04_Glossary_Formulas_Conversions/02_formulas_and_conversions.md` §3 |
| **Float / slack** | The amount of time an activity can be delayed without delaying the project end date (**total float**) or the next activity (**free float**) |
| **Schedule baseline** | The approved version of the schedule, used as the basis for comparing actual progress |
| **Schedule compression** | Techniques to shorten the schedule without reducing scope — **crashing** (adding resources, usually at increased cost) and **fast-tracking** (running normally sequential activities in parallel, usually at increased risk) |
| **Resource leveling** | Adjusting the schedule to resolve resource over-allocation, which can extend the critical path |
| **Three-point estimating (PERT)** | Estimating using optimistic, most-likely, and pessimistic values to produce a weighted expected duration — full formula in `../04_Glossary_Formulas_Conversions/02_formulas_and_conversions.md` §2 |

### Why it matters to an engineer

Fluency in **critical path vs. float** is the single highest-value piece of schedule vocabulary an engineer can own — it is the exact concept covered operationally in `../../Communication-Mastery/02_Thinking_Frameworks/12_project_management_literacy_for_engineers.md` §7, and it converts "is this delay a big deal?" from a guess into a checkable fact: ask the PM directly whether the task in question sits on the critical path or carries float. Understanding **crashing vs. fast-tracking** also supplies the correct vocabulary for a common negotiation: when asked to compress a timeline, naming which lever is being pulled ("that's fast-tracking — we'd run integration testing in parallel with development, which raises defect risk" vs. "that's crashing — it means adding a second engineer, at added cost and onboarding overhead") reframes a vague squeeze into a concrete, named trade-off.

[↑ Back to index](#index)

## 4. How the Three Interlock

```
Charter (Integration)
   → Scope Statement + WBS (Scope)
        → Activity List + Sequencing + Estimates (Schedule)
             → Schedule Baseline
                  → feeds Cost Baseline (../02_cost_quality_resource_management.md)
```

Every downward arrow is a **dependency of trust**: the schedule is only as reliable as the WBS it was built from, and the WBS is only as reliable as the scope statement it decomposed. When a schedule looks wrong, the most common root cause an engineer can usefully flag is not the schedule itself but a scope ambiguity one layer up — "the estimate looks off because work package 3.2 in the WBS doesn't actually specify whether it includes the migration script or not" is a far more actionable objection than "the schedule seems tight."

[↑ Back to index](#index)

## 5. Glossary — Vocabulary Used in This Chapter

| Term/Phrase | Meaning |
|---|---|
| Throughline | A connecting theme running through multiple distinct things |
| Charter | The document formally authorizing a project and granting the PM authority |
| Change Control Board (CCB) | The authority that approves or rejects formal change requests |
| Configuration management | The system for tracking and controlling changes to a product's specifications |
| WBS (Work Breakdown Structure) | A hierarchical decomposition of total project scope into manageable work packages |
| Work package | The smallest unit of a WBS, typically assigned and tracked as a single piece of work |
| Requirements Traceability Matrix | A table linking requirements to their source, implementation, and verifying test |
| Gold plating | Adding unrequested extra features or polish beyond what was actually required |
| Rolling wave planning | Planning near-term work in detail while leaving distant work coarse, refined as it approaches |
| Dependency (FS/SS/FF/SF) | A logical ordering relationship between two scheduled activities |
| Lead / lag | Overlap or required waiting time between a predecessor and successor activity |
| Critical path | The longest dependency chain in a schedule; delays on it delay the whole project |
| Float / slack | The amount an activity can slip without affecting the schedule |
| Crashing | Adding resources to shorten a schedule, usually at increased cost |
| Fast-tracking | Running normally sequential activities in parallel, usually at increased risk |
| Resource leveling | Adjusting a schedule to resolve over-allocated resources |
| PERT (three-point estimating) | Estimating using optimistic, most-likely, and pessimistic values |
| Arbiter | The authority whose decision settles a dispute |
| Coarse | Low in detail or granularity |

[↑ Back to index](#index)

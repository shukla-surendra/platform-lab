# Cost, Quality, and Resource Management

The knowledge areas that answer "with what money, to what standard, and with whom." Grouped together because they are the three constraints (alongside schedule) most directly traded against one another in real time — a resource shortage becomes a cost problem or a quality problem within days, and understanding the vocabulary of all three lets an engineer see which lever actually moved when a project's shape suddenly changes.

## Index

1. [Cost Management](#1-cost-management)
2. [Quality Management](#2-quality-management)
3. [Resource Management](#3-resource-management)
4. [How Cost, Quality, and Resource Interact](#4-how-cost-quality-and-resource-interact)
5. [Glossary — Vocabulary Used in This Chapter](#5-glossary--vocabulary-used-in-this-chapter)

---

## 1. Cost Management

### Definition

The processes involved in planning, estimating, budgeting, financing, funding, managing, and controlling costs so the project can be completed within the approved budget.

### Key artifacts and concepts

| Term | Definition |
|---|---|
| **Cost estimate** | A quantitative assessment of the likely costs of resources needed |
| **Analogous estimating** | Using historical data from a similar past project, scaled — fast, low-accuracy, useful early |
| **Parametric estimating** | Using a statistical relationship between historical data and other variables (e.g., cost per GPU-hour × estimated hours) — faster and more consistent than bottom-up, less precise |
| **Bottom-up estimating** | Estimating each work package individually and summing — slow, high-accuracy, used once scope is well understood |
| **Cost baseline** | The approved, time-phased budget, used as the basis for comparing actual spend — the reference EVM (below) measures against |
| **Contingency reserve** | Budget set aside for *known* risks (identified in the risk register) — owned and can be spent by the project team without escalation |
| **Management reserve** | Budget set aside for *unknown* risks (unforeseen work within scope) — requires sponsor/management approval to access, and is *not* part of the cost baseline |
| **Earned Value Management (EVM)** | The core technique for objectively measuring project performance by integrating scope, schedule, and cost — the terms PV, EV, AC, CV, SV, CPI, SPI, EAC, ETC, VAC, and TCPI are all EVM outputs, worked with formulas and examples in `../04_Glossary_Formulas_Conversions/02_formulas_and_conversions.md` §1 |
| **Life-cycle costing** | Considering the total cost of a deliverable over its full life — acquisition plus operating plus maintenance cost — critically relevant to MLOps, where the training cost is often a small fraction of the lifetime serving/monitoring cost |

### Why it matters to an engineer

**EVM is the language PMs use to say, with a number, whether a project is on track** — an engineer fluent in CPI/SPI can read a status dashboard in seconds instead of parsing prose, and can supply the *reason* behind a bad number (which the PM usually cannot, since the technical cause is invisible from the metric alone). The distinction between contingency reserve and management reserve also matters directly: a legitimate, previously-identified risk materializing is a contingency-reserve draw the team can often self-authorize; scope discovered mid-flight that was never anticipated is a management-reserve conversation that needs the sponsor — conflating the two in a request is a fast way to get the wrong answer.

[↑ Back to index](#index)

## 2. Quality Management

### Definition

The processes for incorporating an organization's quality policy regarding planning, managing, and controlling project and product quality requirements, in order to meet stakeholder expectations.

### Key artifacts and concepts

| Term | Definition |
|---|---|
| **Quality management plan** | Describes how the project will implement its quality policy — standards, metrics, acceptance criteria |
| **Quality metrics** | Specific, measurable attributes and their tolerances (e.g., "P99 inference latency < 200ms") |
| **Cost of quality (COQ)** | The total cost of *conformance* (prevention + appraisal — testing, review, training) plus the cost of *nonconformance* (internal failure + external failure — rework, incidents, reputational damage) |
| **Quality assurance (QA)** | Proactive, process-focused: are we following the process that should produce a quality outcome? |
| **Quality control (QC)** | Reactive, product-focused: does this specific deliverable meet the standard? |
| **Six Sigma / statistical process control** | Techniques for reducing variation and defects using statistical methods — borrowed from manufacturing, occasionally invoked in mature MLOps orgs for pipeline reliability targets |
| **Pareto principle (80/20 rule)** | The observation, used heavily in quality prioritization, that roughly 80% of problems stem from 20% of causes — the justification for tackling the highest-frequency defect category first |
| **Continuous improvement / Kaizen** | An ongoing, incremental approach to improving process quality, rather than one-off fixes |

### Why it matters to an engineer

The QA/QC distinction maps directly onto familiar territory: **QA is "do we have CI, code review, and a testing standard in place at all" — QC is "does this specific PR pass them."** An engineer objecting to a rushed release is usually making a QC argument (this specific thing isn't verified) but the more durable fix is often a QA argument (we don't have a gate that would have caught this class of problem generally) — and naming which one is being raised sharpens the conversation considerably. **Cost of quality** also supplies a genuinely persuasive framing for investing in testing/monitoring infrastructure: "the appraisal cost of building this validation step is $X; the failure cost we've already paid twice this year for the equivalent incident is $Y" turns an abstract quality argument into a budget one, in a PM's native currency.

[↑ Back to index](#index)

## 3. Resource Management

### Definition

The processes to identify, acquire, and manage the resources needed for the successful completion of the project — both the team and physical resources (equipment, materials, infrastructure).

### Key artifacts and concepts

| Term | Definition |
|---|---|
| **Resource management plan** | How project resources are estimated, acquired, managed, and released |
| **RACI matrix** | **R**esponsible, **A**ccountable, **C**onsulted, **I**nformed — assigns roles per activity; covered operationally in `../../Communication-Mastery/02_Thinking_Frameworks/12_project_management_literacy_for_engineers.md` §5 and `11_role_clarity_and_expectation_contracts.md` §4 |
| **Resource calendar** | Documents the time periods a specific resource (person, equipment) is available |
| **Resource breakdown structure** | A hierarchical representation of resources by category and type |
| **Resource leveling** | Adjusting a schedule to resolve over-allocation, often extending the timeline |
| **Resource smoothing** | Adjusting activities within their available float to avoid resource peaks and valleys, without changing the critical path |
| **Team charter** | Establishes team values, agreements, and operating guidelines — the informal social contract underneath the formal RACI |
| **Tuckman's stages (forming, storming, norming, performing, adjourning)** | The classic model of team development — useful for calibrating expectations about a new team's friction level; storming is normal, not a red flag on its own |
| **Conflict management** | Covered in full at `../../Communication-Mastery/02_Thinking_Frameworks/13_conflict_management_in_projects.md` |

### Why it matters to an engineer

The **resource leveling vs. resource smoothing** distinction is a precise, useful piece of vocabulary for a specific and common negotiation: when a PM says "we need to adjust the schedule because you're double-booked," ask which one they mean — leveling changes the end date (a real trade-off worth surfacing to the sponsor); smoothing doesn't (it's free, and there's no reason to resist it). Most PMs use "leveling" loosely for both, and the engineer who asks the precise question is the one who catches a real schedule impact before it becomes a surprise.

[↑ Back to index](#index)

## 4. How Cost, Quality, and Resource Interact

```
        Fewer / cheaper resources
                │
     ┌──────────┼──────────┐
     ▼          ▼          ▼
  Lower cost   Longer      Lower quality
  (intended)   schedule    (often unintended,
               (via         and silently absorbed
               leveling)    rather than decided)
```

The unintended, silent branch is the one worth naming explicitly and often: when resourcing is cut without a corresponding, *explicit* decision about schedule or quality, quality is usually the constraint that quietly gives — the same dynamic already covered generally in `../../Communication-Mastery/02_Thinking_Frameworks/12_project_management_literacy_for_engineers.md` §2. The engineer's protective habit is to force that branch into the open: "if we're reducing the team by one engineer, which are we choosing — a later date, or accepting less test coverage on this release? I don't want that to be an accident."

[↑ Back to index](#index)

## 5. Glossary — Vocabulary Used in This Chapter

| Term/Phrase | Meaning |
|---|---|
| Analogous estimating | Estimating by scaling a similar past project's actuals |
| Parametric estimating | Estimating via a statistical rate applied to a measurable variable |
| Bottom-up estimating | Estimating each component individually and summing |
| Contingency reserve | Budget for known risks, usually team-controlled |
| Management reserve | Budget for unknown risks, requiring sponsor approval to access |
| Earned Value Management (EVM) | The technique for measuring project performance by integrating scope, schedule, and cost |
| Life-cycle costing | Accounting for a deliverable's full cost across acquisition, operation, and maintenance |
| Cost of quality (COQ) | Total cost of conformance (prevention/appraisal) plus nonconformance (failure) |
| Quality assurance (QA) | Process-focused activity ensuring the right process is followed |
| Quality control (QC) | Product-focused activity verifying a specific deliverable meets the standard |
| Pareto principle | The observation that roughly 80% of effects come from 20% of causes |
| Kaizen | Japanese-origin term for continuous, incremental improvement |
| RACI matrix | Responsible/Accountable/Consulted/Informed role assignment table |
| Resource leveling | Adjusting a schedule to resolve resource over-allocation, potentially changing the end date |
| Resource smoothing | Adjusting activity timing within existing float to avoid resource peaks, without changing the end date |
| Tuckman's stages | The forming–storming–norming–performing–adjourning model of team development |
| Silently absorbed | A cost or consequence that occurs without anyone explicitly deciding to accept it |

[↑ Back to index](#index)

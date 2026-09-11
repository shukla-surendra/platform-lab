# PMI Glossary — The Working Term Set

A single-stop reference of PMI/PMBOK terminology, organized by category rather than strict A–Z (per this repo's structure-over-prose convention — a categorized table is more usable than one giant alphabetical wall). Terms already given full treatment in the knowledge-area chapters are included here too, in compressed form, so this file works as a genuine one-stop lookup — each links back to its deep-dive. This is a curated set of the terms an engineer will actually encounter, not a reproduction of PMI's full ~700-term lexicon (that volume exists in the PMBOK Guide itself and in the *PMI Lexicon of Project Management Terms*, and is not more useful reproduced here than referenced).

## Index

1. [General & Governance Terms](#1-general--governance-terms)
2. [Scope & Requirements Terms](#2-scope--requirements-terms)
3. [Schedule Terms](#3-schedule-terms)
4. [Cost & Finance Terms](#4-cost--finance-terms)
5. [Quality Terms](#5-quality-terms)
6. [Risk Terms](#6-risk-terms)
7. [Communications & Stakeholder Terms](#7-communications--stakeholder-terms)
8. [Procurement & Contract Terms](#8-procurement--contract-terms)
9. [Agile-Specific Terms](#9-agile-specific-terms)
10. [Role Titles Reference](#10-role-titles-reference)

---

## 1. General & Governance Terms

| Term | Definition |
|---|---|
| **Project** | A temporary endeavor to create a unique product, service, or result — `../01_Foundations/01_what_is_project_management.md` §1 |
| **Program** | A group of related projects managed together for coordinated benefit — §2 of the same file |
| **Portfolio** | A collection of projects/programs managed together for strategic fit |
| **PMO (Project Management Office)** | The organizational unit standardizing PM governance and tooling |
| **Governance** | The framework of authority, decision rights, and accountability under which a project operates |
| **Project charter** | The document authorizing a project and granting the PM authority — `../02_Knowledge_Areas/01_integration_scope_schedule_management.md` §1 |
| **Project management plan** | The master, integrated document combining all subsidiary plans |
| **Enterprise Environmental Factors (EEFs)** | Conditions not under the project team's control that influence the project — culture, market conditions, infrastructure, existing systems |
| **Organizational Process Assets (OPAs)** | An organization's existing plans, processes, policies, and knowledge bases the project can draw on |
| **Tailoring** | Deliberately adjusting standard PM processes to fit a specific project's context, rather than applying them rigidly |
| **Progressive elaboration** | Continuously improving and detailing a plan as more information becomes available |
| **Phase gate (stage gate)** | A review point at the end of a phase, deciding whether to continue, revise, or end the project |
| **Steering committee** | A group of senior stakeholders empowered to make project-level decisions |
| **Governance body / CCB** | The authority approving formal changes to the project baseline |

[↑ Back to index](#index)

## 2. Scope & Requirements Terms

| Term | Definition |
|---|---|
| **Scope statement** | Detailed description of deliverables and the work required, including explicit exclusions |
| **WBS (Work Breakdown Structure)** | Hierarchical decomposition of total project scope into work packages |
| **WBS dictionary** | Defines exactly what each WBS element includes and its acceptance criteria |
| **Work package** | The smallest unit of a WBS, typically assigned and tracked as one piece of work |
| **Scope baseline** | The approved scope statement + WBS + WBS dictionary |
| **Requirement** | A condition or capability needed to satisfy a contract, standard, or specification |
| **Requirements Traceability Matrix (RTM)** | Links requirements to their source, implementation, and verifying test |
| **Scope creep** | Uncontrolled, unauthorized expansion of scope |
| **Gold plating** | Unrequested extra work or polish added beyond what was required |
| **Decomposition** | Subdividing scope into smaller, more manageable pieces |
| **Rolling wave planning** | Planning near-term work in detail, distant work coarsely, refined as it approaches |
| **Product scope vs. project scope** | *Product scope* = features/functions of the deliverable itself; *project scope* = the work required to deliver it |
| **Acceptance criteria** | The conditions that must be met before deliverables are accepted |
| **Verified deliverable** | A deliverable checked for correctness by the project team, prior to formal validation by the customer |

[↑ Back to index](#index)

## 3. Schedule Terms

| Term | Definition |
|---|---|
| **Activity** | A distinct, scheduled portion of work performed during a project |
| **Milestone** | A significant, zero-duration point in a schedule |
| **Dependency (FS/SS/FF/SF)** | A logical ordering relationship between activities — `../02_Knowledge_Areas/01_integration_scope_schedule_management.md` §3 |
| **Lead / Lag** | Overlap / required wait time between a predecessor and successor |
| **Network diagram** | Graphical representation of activity dependencies |
| **Critical path** | The longest dependency chain; determines minimum project duration |
| **Critical Path Method (CPM)** | The technique for calculating the critical path — full formulas in `02_formulas_and_conversions.md` §3 |
| **Float / slack (total / free)** | Time an activity can be delayed without delaying the project / the next activity |
| **Schedule baseline** | The approved schedule, used to measure actual progress against |
| **Crashing** | Adding resources to shorten a schedule, at increased cost |
| **Fast-tracking** | Running normally sequential activities in parallel, at increased risk |
| **PERT (Program Evaluation and Review Technique)** | Three-point estimating using optimistic/most-likely/pessimistic values |
| **Gantt chart** | A bar-chart schedule showing tasks, durations, and dependencies on a calendar |
| **Rolling wave** | See Scope terms — applies equally to schedule detail |
| **Schedule compression** | Any technique (crashing, fast-tracking) used to shorten a schedule without reducing scope |
| **Schedule variance (SV)** | An EVM metric — see `02_formulas_and_conversions.md` §1 |

[↑ Back to index](#index)

## 4. Cost & Finance Terms

| Term | Definition |
|---|---|
| **Cost baseline** | The approved, time-phased budget |
| **Contingency reserve** | Budget for known risks, team-controlled |
| **Management reserve** | Budget for unknown risks, requiring sponsor approval |
| **Analogous / Parametric / Bottom-up estimating** | Three estimating techniques of increasing accuracy and effort — `../02_Knowledge_Areas/02_cost_quality_resource_management.md` §1 |
| **Life-cycle costing** | Total cost across acquisition, operation, and maintenance |
| **EVM (Earned Value Management)** | The technique integrating scope, schedule, and cost into objective performance metrics — full formula sheet: `02_formulas_and_conversions.md` §1 |
| **PV, EV, AC** | Planned Value, Earned Value, Actual Cost — the three EVM base measures |
| **CV, SV** | Cost Variance, Schedule Variance — EVM variance metrics |
| **CPI, SPI** | Cost Performance Index, Schedule Performance Index — EVM efficiency ratios |
| **EAC, ETC, VAC, TCPI** | Estimate at Completion, Estimate to Complete, Variance at Completion, To-Complete Performance Index — EVM forecasting metrics |
| **ROI (Return on Investment)** | The financial return relative to the cost of an investment |
| **NPV (Net Present Value)** | The value today of future cash flows, discounted — used to compare competing project proposals |
| **IRR (Internal Rate of Return)** | The discount rate at which a project's NPV equals zero — a project's "break-even" rate of return |
| **Payback period** | The time required to recover an investment's initial cost |
| **Sunk cost** | A cost already incurred and unrecoverable — should not, in principle, influence forward-looking decisions |
| **Opportunity cost** | The value of the next-best alternative forgone by choosing one option over another |

[↑ Back to index](#index)

## 5. Quality Terms

| Term | Definition |
|---|---|
| **Quality management plan** | Describes standards, metrics, and acceptance criteria for the project |
| **Cost of Quality (COQ)** | Conformance cost (prevention + appraisal) + nonconformance cost (internal + external failure) |
| **Quality assurance (QA)** | Proactive, process-focused — is the right process being followed |
| **Quality control (QC)** | Reactive, product-focused — does this specific deliverable meet the standard |
| **Pareto principle** | Roughly 80% of problems stem from 20% of causes |
| **Six Sigma** | A data-driven methodology for reducing defects and process variation |
| **Control chart** | A graph used to study how a process changes over time, with upper/lower control limits |
| **Benchmarking** | Comparing actual or planned practices to those of comparable organizations |
| **Kaizen** | Continuous, incremental process improvement |
| **DMAIC** | Define, Measure, Analyze, Improve, Control — the core Six Sigma improvement cycle |

[↑ Back to index](#index)

## 6. Risk Terms

| Term | Definition |
|---|---|
| **Risk** | An uncertain event or condition with a positive or negative effect on objectives |
| **Risk appetite / tolerance / threshold** | Degree of acceptable uncertainty, at organizational and per-objective levels — `../02_Knowledge_Areas/04_risk_management.md` §1 |
| **Risk register** | The document holding all identified risks and their analysis |
| **Risk owner** | The person responsible for monitoring and responding to a specific risk |
| **Probability-impact matrix** | A grid scoring risks by likelihood × severity to prioritize response |
| **EMV (Expected Monetary Value)** | Probability × financial impact — full walkthrough in `../02_Knowledge_Areas/04_risk_management.md` §4 |
| **Monte Carlo simulation** | Randomized-input modeling producing a distribution of possible outcomes |
| **Avoid / Mitigate / Transfer / Accept / Escalate** | The five threat-response strategies |
| **Exploit / Enhance / Share / Accept** | The four opportunity-response strategies |
| **RAID log** | Risks, Assumptions, Issues, Dependencies register — `../02_Knowledge_Areas/04_risk_management.md` §6 |
| **Issue** | A risk that has materialized and now requires active management |
| **Black swan** | A rare, unpredictable event with severe consequences, rationalized as predictable only in hindsight |
| **Residual risk** | The risk remaining after response strategies have been applied |
| **Secondary risk** | A new risk created as a direct result of implementing a risk response |

[↑ Back to index](#index)

## 7. Communications & Stakeholder Terms

Full deep-dive: `../02_Knowledge_Areas/03_communications_management.md` and `05_procurement_and_stakeholder_management.md` §4–5.

| Term | Definition |
|---|---|
| **Push / Pull / Interactive communication** | The three PMI communication method categories |
| **Communication channels formula** | n(n−1)/2 — coordination paths grow quadratically with team size |
| **Stakeholder** | Anyone who may affect, be affected by, or perceive themselves affected by the project |
| **Stakeholder register** | The document identifying and classifying all stakeholders |
| **Power/Interest grid** | A tool plotting stakeholders by influence and concern to prioritize engagement |
| **Engagement level** | A stakeholder's disposition, from Unaware through Resistant, Neutral, Supportive, to Leading |
| **RACI matrix** | Responsible/Accountable/Consulted/Informed role assignment table |
| **RAG status (Red/Amber/Green)** | Traffic-light project health reporting |
| **Escalation path** | The predefined route by which an issue or decision moves to higher authority |

[↑ Back to index](#index)

## 8. Procurement & Contract Terms

Full deep-dive: `../02_Knowledge_Areas/05_procurement_and_stakeholder_management.md` §1–3.

| Term | Definition |
|---|---|
| **SOW (Statement of Work)** | Describes the scope of products/services being procured |
| **Make-or-buy analysis** | Deciding whether to perform work internally or procure it externally |
| **RFI / RFQ / RFP** | Request for Information / Quotation / Proposal — bid solicitation documents |
| **Fixed-Price (FP) contract** | Set total price; seller bears cost-overrun risk |
| **Cost-Reimbursable (CR) contract** | Buyer reimburses actual costs plus a fee; buyer bears cost-overrun risk |
| **Time and Materials (T&M)** | Paid by hours worked plus materials; the common structure for individual contractor engagements |
| **SLA (Service Level Agreement)** | A contractual commitment to specific service performance levels |
| **Claims administration** | The formal process for managing contested, unresolved contract changes |
| **Procurement audit** | A structured review of the procurement process for lessons learned and compliance |

[↑ Back to index](#index)

## 9. Agile-Specific Terms

Full deep-dive: `../03_Methodologies/01_predictive_agile_and_hybrid_delivery.md`.

| Term | Definition |
|---|---|
| **Sprint** | A fixed-length iteration in Scrum, typically 1–4 weeks |
| **Backlog (Product / Sprint)** | The ordered list of work — for the whole product, or selected for the current sprint |
| **Definition of Done (DoD)** | The shared, explicit quality bar every increment must meet |
| **Velocity** | A team's measured throughput per sprint, used for forecasting |
| **Burndown / burnup chart** | Plots of remaining (burndown) or completed (burnup) work over time |
| **WIP limit** | A cap on simultaneous in-progress items in a Kanban system |
| **Lead time / Cycle time** | Total request-to-delivery time / actual work-start-to-delivery time |
| **Little's Law** | Average cycle time = average WIP / average throughput |
| **User story** | A short, plain-language description of a feature from the end user's perspective |
| **Epic** | A large body of work that can be broken down into multiple smaller user stories |
| **Story points** | A relative, unitless measure of effort/complexity used to estimate backlog items |
| **INVEST criteria** | Independent, Negotiable, Valuable, Estimable, Small, Testable — the standard for a well-formed user story |
| **Spike** | A timeboxed investigation used to answer a question or reduce uncertainty before estimating real work |
| **Program Increment (PI)** | A multi-sprint timebox in SAFe within which an Agile Release Train delivers value |

[↑ Back to index](#index)

## 10. Role Titles Reference

A quick-lookup table for role titles an engineer will encounter across predictive, agile, and hybrid organizations — useful because the *same* underlying responsibility often carries a different title depending on the methodology in use:

| Predictive title | Agile equivalent | What they actually own |
|---|---|---|
| Project Manager | Scrum Master / Delivery Lead | Process, schedule, removing impediments |
| Business Analyst / Product Manager | Product Owner | Requirements, backlog priority, business value |
| Functional Manager | Engineering Manager / Team Lead | People, skills, capacity |
| Sponsor | Executive Sponsor / Product Sponsor | Ultimate accountability and resourcing |
| Team Member | Developer (Scrum's generic term for all delivery roles) | Execution of assigned work |

[↑ Back to index](#index)

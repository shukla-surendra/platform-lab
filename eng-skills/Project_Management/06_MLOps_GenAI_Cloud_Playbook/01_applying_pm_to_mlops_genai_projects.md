# Applying Project Management to MLOps, GenAI, and Cloud Projects

Everything in this folder so far is general-purpose PMI knowledge. This chapter is the translation layer into the domain the reader actually works in — a worked, concrete application of charters, WBS, RAID logs, and communication plans to the specific shape of ML/GenAI/Cloud work, plus the friction points classical project management structurally mishandles in this domain and how to route around each one.

## Index

1. [Why This Domain Breaks Classical Planning Assumptions](#1-why-this-domain-breaks-classical-planning-assumptions)
2. [Worked Example: Charter for a GenAI Feature](#2-worked-example-charter-for-a-genai-feature)
3. [Worked Example: WBS for an MLOps Platform Migration](#3-worked-example-wbs-for-an-mlops-platform-migration)
4. [Worked Example: RAID Log for a Model-Serving Rollout](#4-worked-example-raid-log-for-a-model-serving-rollout)
5. [The Five Recurring Frictions, and the Fix for Each](#5-the-five-recurring-frictions-and-the-fix-for-each)
6. [A Communication Plan for a Mixed Data-Science/Platform Team](#6-a-communication-plan-for-a-mixed-data-scienceplatform-team)
7. [Glossary — Vocabulary Used in This Chapter](#7-glossary--vocabulary-used-in-this-chapter)

---

## 1. Why This Domain Breaks Classical Planning Assumptions

Classical project management (and the PMBOK it's built from) assumes construction-shaped work: decomposable scope, effort roughly proportional to outcome, and success defined by conformance to a spec written in advance. GenAI/MLOps work routinely violates all three — already flagged at a summary level in `../../Communication-Mastery/02_Thinking_Frameworks/12_project_management_literacy_for_engineers.md` §9. This chapter goes from that summary table to fully worked artifacts.

[↑ Back to index](#index)

## 2. Worked Example: Charter for a GenAI Feature

```markdown
# Charter: RAG-Based Internal Support Assistant

**Sponsor:** VP of Customer Success
**Owner:** [MLOps/Platform Architect]

## Business Need
Support ticket volume for common product questions is growing faster than headcount.
A retrieval-augmented assistant should deflect 30% of Tier-1 tickets within two quarters.

## Objectives / Success Criteria
- [ ] Deflection rate ≥ 30% on Tier-1 tickets, measured over a 4-week window post-launch
- [ ] P95 response latency < 3 seconds
- [ ] Hallucination rate < 2% on the internal eval set (500 curated Q&A pairs)
- [ ] Full audit trail of sources cited per answer (compliance requirement)

## In Scope
Retrieval pipeline over the existing knowledge base; a single supported LLM provider;
a feedback-capture mechanism for incorrect answers.

## Explicitly Out of Scope
Fine-tuning a custom model (revisit only if retrieval-only accuracy plateaus below target);
multi-language support (Phase 2); voice interface.

## Key Assumption Flagged at Charter Stage
The 30% deflection target is a HYPOTHESIS, not a committed deliverable — see §5.1 below for
why this line exists and what it protects against.

## Target Timeline
Week 1-2: Data/retrieval spike (timeboxed) → Week 3-6: Build → Week 7: Eval gate →
Week 8: Limited rollout → Week 12: Full rollout decision
```

Note the explicit "Key Assumption Flagged at Charter Stage" section — this is not a standard PMBOK charter field; it is a deliberate addition, and its presence is the single highest-leverage change an ML-flavored charter needs relative to a construction-shaped one (§5.1 explains the mechanism it defends against).

[↑ Back to index](#index)

## 3. Worked Example: WBS for an MLOps Platform Migration

A partial WBS (down to work-package level for one branch only, to keep the example readable) for "migrate the training orchestration platform":

```
1. Platform Migration
   1.1 Discovery & Design
       1.1.1 Current-state architecture audit
       1.1.2 Target-state design + ADR
       1.1.3 Migration runbook draft
   1.2 Data & Access Readiness          ← the workstream classical WBS templates omit
       1.2.1 IAM/access provisioning for new platform
       1.2.2 Data lineage validation across old/new systems
       1.2.3 PII/compliance review of migrated data paths
   1.3 Pipeline Migration
       1.3.1 Port pipeline A (batch feature computation)
       1.3.2 Port pipeline B (model training)
       1.3.3 Parallel-run validation (old vs. new output diff)
   1.4 Observability & Monitoring       ← the workstream classical WBS templates omit
       1.4.1 Metrics/alerting parity check
       1.4.2 Drift monitoring re-instrumentation
   1.5 Cutover & Handover
       1.5.1 Cutover runbook + rollback plan
       1.5.2 Operational handover doc + on-call transition
   1.6 Closure
       1.6.1 Decommission old platform
       1.6.2 Lessons learned
```

The two branches marked are the ones a generically-templated WBS most reliably omits, and both are covered as named frictions below (§5.2, §5.5) — putting them in the WBS as first-class, budgeted, staffed line items is the single concrete fix for both.

[↑ Back to index](#index)

## 4. Worked Example: RAID Log for a Model-Serving Rollout

```markdown
## Risks
| ID | Description | P | I | Score | Owner | Response |
|---|---|---|---|---|---|---|
| R1 | Model accuracy on production traffic may differ from eval-set accuracy | 3 | 5 | 15 | ML lead | Mitigate: shadow-mode traffic replay before full cutover |
| R2 | GPU capacity in target region insufficient at peak load | 2 | 4 | 8 | Cloud architect | Transfer: reserved-instance commitment with cloud provider |
| R3 | Prompt-injection / adversarial input on user-facing GenAI endpoint | 3 | 5 | 15 | Security | Mitigate: input sanitization + output filtering layer |

## Assumptions
| ID | Assumption | Impact if false |
|---|---|---|
| A1 | Eval-set distribution matches production traffic distribution | Accuracy claims in the charter don't hold in production |
| A2 | Upstream data contract with the ingestion team stays stable through rollout | Silent feature drift, undetected without monitoring |

## Issues
| ID | Description | Owner | Plan |
|---|---|---|---|
| I1 | (example, post-launch) Latency spike under real traffic exceeds P95 target | Platform eng | Add caching layer; revisit charter's latency criterion if unresolved in 1 week |

## Dependencies
| ID | Depends on | Owner | Needed by |
|---|---|---|---|
| D1 | Security review sign-off on the filtering layer | Security team | Before full rollout (week 12 gate) |
| D2 | Reserved GPU capacity provisioned | Cloud/infra team | Before shadow-mode traffic replay |
```

[↑ Back to index](#index)

## 5. The Five Recurring Frictions, and the Fix for Each

Expanded from the summary table in `../../Communication-Mastery/02_Thinking_Frameworks/12_project_management_literacy_for_engineers.md` §9:

### 5.1 Model performance is a discovery, not a deliverable

A metric target (accuracy, deflection rate, hallucination rate) cannot be *guaranteed* by effort the way a feature can — it's a property of the data and the problem, discovered through the work, not specified in advance and then executed against. Committing to it as a hard milestone in the schedule sets the project up to be "late" against something that was never actually a schedule item.

**Fix:** Split the charter into two layers — a **committed deliverable** (the trained-and-evaluated model plus a written evaluation report, by a fixed date) and a **discovered finding** (the actual metric value, reported honestly whatever it turns out to be). Pre-agree, at charter time, what happens at each outcome band: "if deflection ≥ 30%, ship; if 20–30%, ship with a stated improvement roadmap; if < 20%, the sponsor and team jointly decide whether to iterate or pivot." This is exactly what the charter's "Key Assumption Flagged" section in §2 exists to do.

### 5.2 Data readiness is the real critical path, and it's usually invisible

Classical WBS templates jump straight to "build pipeline" without a line item for the access requests, quality investigation, and compliance review that must happen first — yet these routinely consume more calendar time than the actual pipeline build.

**Fix:** Give data/access readiness its own first-class WBS branch with its own owner and dates (§3, branch 1.2), not a bullet buried inside "pipeline development."

### 5.3 The POC-to-production chasm

A working notebook or a slick demo is roughly 20% of a production system; the stakeholders who saw the demo anchor on "it's basically done." Productionizing — serving infrastructure, monitoring, retraining automation, security hardening — is the majority of the remaining effort, and is invisible in a demo.

**Fix:** Manage the anchor *at demo time*, out loud: "what you're seeing proves the approach works. Getting this to production-grade — reliability, monitoring, security — is most of what's left; here's roughly how that breaks down." One sentence at the demo is cheaper than a month of expectation-repair afterward.

### 5.4 Iterative experimentation reads as rework on a Gantt chart

"Retrain with a new feature set" or "try a different retrieval strategy" looks, to a traditional schedule view, identical to redoing already-completed work — i.e., to failure — even when it's the expected, designed shape of ML development.

**Fix:** Frame each iteration as a numbered **experiment cycle** with an explicit **decision gate** at the end (continue / pivot / ship), so the schedule visibly shows a designed loop with checkpoints, not unexplained backsliding.

### 5.5 Operational cost and ownership outlive the project

Projects have an end date; a shipped model has drift to monitor, retraining to schedule, and incidents to page someone for, indefinitely. Classical project closure (`../01_Foundations/01_what_is_project_management.md` §3) has no natural slot for "this now needs feeding forever" — it just... ends.

**Fix:** Raise the operational-ownership question at charter time, not at closure: "who owns this model in month six — retraining cadence, drift response, on-call?" is a staffing-plan line item, not a footnote, and belongs in the WBS's Observability & Monitoring branch (§3) with a named owner extending past the project's formal end date. For contractors specifically, this doubles as the exit-engineering discipline in `../../Communication-Mastery/02_Thinking_Frameworks/11_role_clarity_and_expectation_contracts.md` §7 point 5.

[↑ Back to index](#index)

## 6. A Communication Plan for a Mixed Data-Science/Platform Team

Applying `../02_Knowledge_Areas/03_communications_management.md` §5 to this specific domain's stakeholder mix:

| Audience | Info need | Method | Cadence |
|---|---|---|---|
| Data scientists (platform consumers) | Breaking changes, new capabilities, known limitations | Interactive (office hours) + push (changelog) | Weekly office hours; changelog per release |
| Product/business sponsor | Business-metric progress (deflection rate, cost per query), not technical detail | Push (1-page summary) | Biweekly |
| Security/compliance | Control implementation status, data handling changes | Push (ticket-linked doc) | Per milestone, plus immediately on any data-path change |
| Platform/infra team | Capacity needs, IaC changes touching shared infrastructure | Interactive (design review) | Before any change touching shared resources |
| On-call/SRE (post-launch) | Runbooks, alert thresholds, escalation paths | Pull (wiki) + push (handover doc) | Once, at handover, then pull-maintained |

[↑ Back to index](#index)

## 7. Glossary — Vocabulary Used in This Chapter

| Term/Phrase | Meaning |
|---|---|
| Shadow mode | Running a new model on production traffic without its outputs affecting real users, to validate before cutover |
| Cutover | The moment of switching production traffic from an old system to a new one |
| Drift (model/data) | Gradual degradation in model accuracy as production data diverges from training data |
| Eval set | A held-out, curated dataset used to measure model performance |
| Deflection rate | The proportion of support requests resolved without human escalation |
| Reserved instance | A cloud capacity commitment purchased in advance, often at a discount, to guarantee availability |
| Anchor / anchoring | The disproportionate influence of an initial number or impression on later judgment |
| Decision gate | A pre-agreed checkpoint where continue/pivot/stop is explicitly decided |
| Chasm | A deep gap; here, the distance between a working demo and a production system |
| First-class (line item) | Treated as a primary, explicitly planned element rather than an implicit afterthought |

[↑ Back to index](#index)

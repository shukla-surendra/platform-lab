# Ready-to-Use Templates

Fill-in-the-blank versions of the core PM artifacts referenced throughout this folder, sized for an individual engineer/architect to actually use — not the full enterprise-PMO version, but enough structure to produce something a PM or stakeholder will recognize instantly and take seriously.

## Index

1. [Project/Workstream Charter (Lightweight)](#1-projectworkstream-charter-lightweight)
2. [RACI Matrix](#2-raci-matrix)
3. [RAID Log](#3-raid-log)
4. [Weekly Status Report](#4-weekly-status-report)
5. [Risk Register Entry](#5-risk-register-entry)
6. [Communications Plan](#6-communications-plan)
7. [Change Request](#7-change-request)
8. [Glossary — Vocabulary Used in This Chapter](#8-glossary--vocabulary-used-in-this-chapter)

---

## 1. Project/Workstream Charter (Lightweight)

```markdown
# Charter: [Project/Workstream Name]

**Sponsor:** [name]
**Owner (this role):** [name]
**Date:** [date]

## Business Need
[Why does this exist? What problem does it solve?]

## Objectives / Success Criteria (must be checkable)
- [ ] [Specific, measurable outcome 1]
- [ ] [Specific, measurable outcome 2]

## In Scope
- [item]

## Explicitly Out of Scope
- [item]

## Key Stakeholders
| Name | Role | Interest |
|---|---|---|

## Constraints & Assumptions
- [constraint/assumption]

## Target Timeline
[Start] → [Key milestones] → [End/Go-live]

## Budget (if applicable)
[amount, and reserve type — contingency vs. management]
```

Cross-reference: `../../Communication-Mastery/02_Thinking_Frameworks/11_role_clarity_and_expectation_contracts.md` §5.1 for the conversation that populates this.

[↑ Back to index](#index)

## 2. RACI Matrix

```markdown
| Activity / Deliverable | [Person A] | [Person B] | [Person C] | [Sponsor] |
|---|---|---|---|---|
| Architecture decision      | A/R | C | C | I |
| Pipeline implementation    | I | R | C | I |
| Security review sign-off   | C | I | A/R | I |
| Go-live decision           | C | C | C | A |
```
*Every row must have exactly one **A**. Multiple R's are fine; multiple A's mean the ownership isn't actually resolved yet.*

[↑ Back to index](#index)

## 3. RAID Log

```markdown
## Risks
| ID | Description | Prob (1-5) | Impact (1-5) | Score | Owner | Response | Status |
|---|---|---|---|---|---|---|---|
| R1 | Upstream schema may change again | 4 | 4 | 16 | [name] | Mitigate: add validation | Open |

## Assumptions
| ID | Assumption | Impact if false | Owner |
|---|---|---|---|
| A1 | Training data schema is stable | Pipeline breaks silently | [name] |

## Issues
| ID | Description | Severity | Owner | Resolution plan | Target date |
|---|---|---|---|---|---|
| I1 | [materialized risk or new problem] | High | [name] | [plan] | [date] |

## Dependencies
| ID | Depends on | Owned by | Needed by | Status |
|---|---|---|---|---|
| D1 | Platform team's schema migration | [team] | [date] | On track / At risk |
```

Full field-level explanation: `../02_Knowledge_Areas/04_risk_management.md` §6.

[↑ Back to index](#index)

## 4. Weekly Status Report

```markdown
## Status: [Project/Workstream] — Week of [date]

**Overall status:** 🟢 Green / 🟡 Amber / 🔴 Red

**Delivered this week:**
- [item]

**In flight:**
- [item] — expected [date]

**Blocked:**
- [item] — blocked by [who/what] — impact if unresolved by [date]: [consequence]

**Risks/changes since last update:**
- [new or updated risk]

**Decisions needed:**
- [decision] — needed from [who] by [date]
```

The three-line minimal version (delivered / in-flight / blocked-by-whom) is covered operationally in `../../Communication-Mastery/02_Thinking_Frameworks/11_role_clarity_and_expectation_contracts.md` §8 and §7's contractor-specific framing.

[↑ Back to index](#index)

## 5. Risk Register Entry

```markdown
**Risk ID:** R-[number]
**Description:** [event] — [what happens if it occurs]
**Category:** [technical / schedule / cost / external / organizational]
**Probability:** [1-5] **Impact:** [1-5] **Score:** [P×I]
**Trigger condition:** [what signals this risk is materializing]
**Response strategy:** Avoid / Mitigate / Transfer / Accept / Escalate
**Response plan:** [specific action]
**Owner:** [name]
**Status:** Open / Monitoring / Closed / Materialized (→ moved to Issues)
```

[↑ Back to index](#index)

## 6. Communications Plan

```markdown
| Audience | Info Need | Purpose | Method | Format | Frequency | Owner |
|---|---|---|---|---|---|---|
| Sponsor | Overall health, decisions needed | Enable go/no-go calls | Push | 1-page email | Weekly | [name] |
| Data science team | Pipeline changes, breaking changes | Enable their own planning | Interactive | Standup + doc | Daily / as-needed | [name] |
| Security | Control implementation status | Compliance sign-off | Push | Ticket + doc | Per milestone | [name] |
| Steering committee | Budget/schedule variance, risks | Strategic decisions | Interactive | Slide deck | Monthly | [name] |
```

Full model: `../02_Knowledge_Areas/03_communications_management.md` §5.

[↑ Back to index](#index)

## 7. Change Request

```markdown
**Change Request:** CR-[number]
**Requested by:** [name] **Date:** [date]

**Description of change:**
[what is being proposed]

**Reason:**
[why — new requirement, risk discovered, technical constraint]

**Impact analysis:**
- Scope: [effect]
- Schedule: [effect, in days/weeks]
- Cost: [effect]
- Risk: [new or changed risks]

**Recommendation:** Approve / Reject / Approve with modification

**Decision:** [outcome] **Approved by:** [name/CCB] **Date:** [date]
```

Cross-reference: `../02_Knowledge_Areas/01_integration_scope_schedule_management.md` §1 (Integrated Change Control).

[↑ Back to index](#index)

## 8. Glossary — Vocabulary Used in This Chapter

| Term/Phrase | Meaning |
|---|---|
| RACI | Responsible/Accountable/Consulted/Informed role-assignment matrix |
| RAID log | Risks, Assumptions, Issues, Dependencies register |
| CCB | Change Control Board — the authority approving formal change requests |
| Go/no-go | A binary decision point on whether to proceed |
| In flight | Currently being worked on, not yet complete |
| Trigger condition | A signal indicating a risk is about to occur or has occurred |

[↑ Back to index](#index)

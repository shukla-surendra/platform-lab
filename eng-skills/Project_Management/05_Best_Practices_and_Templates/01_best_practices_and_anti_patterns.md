# Project Management Best Practices and Anti-Patterns

A condensed, opinionated field guide — not a restatement of PMBOK theory, but the practices that consistently separate well-run projects from troubled ones, paired with the anti-patterns that predict trouble early. Written for an engineer/architect who wants to recognize both quickly, whether operating inside someone else's project or informally shaping one's own workstream.

## Index

1. [Best Practices by Knowledge Area](#1-best-practices-by-knowledge-area)
2. [Universal Anti-Patterns](#2-universal-anti-patterns)
3. [Early Warning Signs a Project Is in Trouble](#3-early-warning-signs-a-project-is-in-trouble)
4. [The Engineer's Personal Best-Practice Checklist](#4-the-engineers-personal-best-practice-checklist)
5. [Glossary — Vocabulary Used in This Chapter](#5-glossary--vocabulary-used-in-this-chapter)

---

## 1. Best Practices by Knowledge Area

| Area | Best practice |
|---|---|
| **Integration** | Treat the project management plan as a living document, revisited at every phase gate — not written once and archived |
| **Scope** | Get the WBS reviewed by the people who will actually execute the work packages, before it's baselined — the people closest to the work catch ambiguity fastest |
| **Schedule** | Identify the critical path explicitly and communicate it — most teams have a schedule but never actually know which tasks are truly load-bearing |
| **Cost** | Track EVM metrics (or at minimum burn rate vs. plan) continuously, not just at milestone reviews — problems compound fastest between checkpoints |
| **Quality** | Define acceptance criteria and Definition of Done *before* work starts, not as a retrospective judgment call |
| **Resource** | Resolve over-allocation (resource leveling) explicitly and visibly, rather than letting individuals silently absorb double-booking |
| **Communications** | Build the communications plan around what each stakeholder needs to *decide or do*, not what's convenient to report |
| **Risk** | Run a dedicated risk identification session at kickoff and at every phase gate — risk identification that only happens reactively is not risk management |
| **Procurement** | Match the contract type to the actual scope certainty — fixed-price for well-understood work, cost-reimbursable or T&M for evolving work |
| **Stakeholder** | Map stakeholders explicitly (power/interest grid) and revisit the map when the team or org changes — stakeholder maps decay as fast as role charters |

[↑ Back to index](#index)

## 2. Universal Anti-Patterns

| Anti-pattern | What it looks like | Why it's costly |
|---|---|---|
| **Watermelon status** | Reports green on the outside, red on the inside — status is upbeat in the summary line but the underlying detail tells a different story | Erodes trust catastrophically once discovered; the "optimistic status update trap" already documented at `../../Communication-Mastery/13_Common_Mistakes/05_case_study_optimistic_status_update_trap.md` |
| **Analysis paralysis** | Planning extends indefinitely because "we need more certainty first" | The prerequisite-stacking pattern (`../../Communication-Mastery/02_Thinking_Frameworks/06_prerequisite_stacking_and_the_elsewhere_effect.md`) at the project level — a fixed planning-phase end date is the same structural fix |
| **Scope creep by a thousand cuts** | No single addition seems worth fighting; the aggregate quietly doubles the original scope | Each addition individually passes a low bar; nobody ever compares the aggregate against the original baseline |
| **Hero culture** | The project runs on one person's heroics (nights, weekends, tribal knowledge) rather than a sustainable process | A single point of failure wearing a project management hat — see `../../Communication-Mastery/13_Common_Mistakes/04_case_study_single_point_of_failure.md` |
| **Meeting sprawl** | Every coordination need spawns a recurring meeting; calendars fill until no focused work time remains | Confuses the *existence* of a meeting with the *resolution* of the coordination problem it was meant to solve |
| **Status theater** | Elaborate reporting rituals that consume real effort but don't change any decision | A report nobody acts on is pure overhead — if a report never changes a decision, it shouldn't exist in its current form |
| **Gold-plated scope** | Engineers add unrequested robustness/features "since we're already in there" | Consumes schedule and budget without authorization — the self-inflicted twin of scope creep, `../02_Knowledge_Areas/01_integration_scope_schedule_management.md` §2 |
| **The vanishing baseline** | The schedule/budget gets silently re-baselined so often that "on track" becomes meaningless | If the baseline moves every time reality threatens to miss it, variance metrics stop measuring anything real |
| **Risk register as paperwork** | A risk register exists, was filled out once at kickoff, and has not been touched since | A risk register that isn't revisited is a historical document, not a management tool |
| **Silent scope-owner ambiguity** | Nobody can say, on the spot, who actually owns a given decision | The role/boundary conflict source from `../../Communication-Mastery/02_Thinking_Frameworks/13_conflict_management_in_projects.md` §2 |

[↑ Back to index](#index)

## 3. Early Warning Signs a Project Is in Trouble

A project doesn't usually fail suddenly — it accumulates warning signs that are individually dismissible and collectively damning, the exact pattern already documented for interpersonal dynamics in `../../Communication-Mastery/13_Common_Mistakes/07_case_study_managed_exit.md` §2, applying equally to project health:

- **CPI or SPI trending below 0.9 and not recovering** across two or more reporting periods (§1 of `../04_Glossary_Formulas_Conversions/02_formulas_and_conversions.md`).
- **The risk register hasn't been updated in the last reporting cycle** — either the project has genuinely stopped facing new risk (rare) or risk management has quietly lapsed.
- **Status reports get vaguer, not more specific, as a deadline approaches** — specificity should increase as uncertainty resolves; the reverse is a tell.
- **Meetings about the plan start outnumbering work on the plan.**
- **The same blocker appears in three consecutive status updates** without a materially different mitigation each time.
- **Key decisions are being made in side conversations** rather than the sanctioned decision-making forum — a symptom of the governance body having lost effective authority.

[↑ Back to index](#index)

## 4. The Engineer's Personal Best-Practice Checklist

A distillation, restated as first-person habits rather than PM theory:

1. Read the charter. Know the sponsor, the success criteria, and what's explicitly out of scope.
2. Know whether your current task sits on the critical path or carries float — ask if it isn't obvious.
3. Give estimates as ranges with a named driver, not bare point numbers (`../../Communication-Mastery/02_Thinking_Frameworks/12_project_management_literacy_for_engineers.md` §6).
4. Log risks and assumptions the moment they occur to you, not when they've already become issues.
5. Report blockers within a day, in the routed form: what's blocking, what's been tried, what's needed, by when, and the impact if unresolved.
6. Push scope-affecting decisions through the change process, not around it.
7. Keep your own dated record of delivered work, independent of anyone else's summary of it.
8. Ask, explicitly, which knowledge-area constraint is being implicitly sacrificed whenever a request doesn't add corresponding time, budget, or scope relief.

[↑ Back to index](#index)

## 5. Glossary — Vocabulary Used in This Chapter

| Term/Phrase | Meaning |
|---|---|
| Watermelon status | A report that looks healthy (green) on the surface but is unhealthy (red) underneath |
| Analysis paralysis | Being unable to act because of excessive deliberation or desire for more certainty |
| By a thousand cuts | Damage accumulated through many small, individually minor actions |
| Hero culture | An organizational pattern relying on individual extraordinary effort rather than sustainable process |
| Meeting sprawl | The unchecked proliferation of recurring meetings |
| Status theater | Reporting activity that consumes effort without informing any actual decision |
| Gold-plated scope | Unrequested extra work added beyond what was actually required |
| Re-baselined | Having its approved reference point (schedule/budget) formally reset |
| Damning | Providing strong, incriminating evidence of a fault |
| Sanctioned (forum) | Officially approved or authorized |
| Distillation | A concentrated, simplified extraction of the essential points from something larger |

[↑ Back to index](#index)

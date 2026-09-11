# Project Management — A Literacy Curriculum for MLOps/GenAI/Cloud Engineers and Architects

A standalone, PMI-grounded project management curriculum, built for a specific and deliberately narrow goal: **understand project management well enough to speak it fluently, read its artifacts correctly, and communicate inside it with precision — not to become a project manager.** Everything here is written for someone who will keep being evaluated as an engineer/architect, whose relationship to PM is as an informed, articulate counterpart, not a practitioner.

## Core Premise

This folder is deliberately separate from `../Communication-Mastery/`. That repo teaches the transmission layer generally (how to explain, structure, and phrase). This one teaches a specific *subject-matter vocabulary* — PMI/PMBOK terminology, formulas, artifacts, and methodology — so that the transmission skills already covered in `Communication-Mastery/` have precise, correct PM vocabulary to work with. The two are meant to be used together: `../Communication-Mastery/02_Thinking_Frameworks/11_role_clarity_and_expectation_contracts.md`, `12_project_management_literacy_for_engineers.md`, and `13_conflict_management_in_projects.md` are the operational, communication-first companions to the fuller reference material built out here.

Per this repo's `CLAUDE.md`, the writing itself is part of the point — precise vocabulary and structure are used deliberately throughout, not as decoration, because reading and reviewing this material is part of how the fluency gets built.

## Folder Map

```
Project_Management/
│
├── 01_Foundations/                    What a project actually is, the PMBOK grid, life cycles,
│                                        constraints, organizational structures, key roles
├── 02_Knowledge_Areas/                The ten PMBOK knowledge areas in depth — Integration,
│                                        Scope, Schedule, Cost, Quality, Resource, Communications
│                                        (flagship chapter), Risk, Procurement, Stakeholder
├── 03_Methodologies/                  Predictive/Agile/Hybrid delivery — the Agile Manifesto,
│                                        Scrum roles/events/artifacts, Kanban flow metrics, SAFe
├── 04_Glossary_Formulas_Conversions/  The curated PMI term glossary, plus the full formula sheet
│                                        (EVM, PERT, critical path, comm channels) and a
│                                        PM-speak ↔ engineer-speak conversion table
├── 05_Best_Practices_and_Templates/   Best practices and anti-patterns by knowledge area, plus
│                                        ready-to-use fill-in templates (charter, RACI, RAID,
│                                        status report, risk register, comms plan, change request)
├── 06_MLOps_GenAI_Cloud_Playbook/     Worked examples applying all of the above to a GenAI
│                                        feature charter, an MLOps platform migration WBS, and
│                                        a model-serving RAID log — plus the five domain-specific
│                                        planning frictions and their fixes
├── 07_Communication_Toolkit/          A drillable PM phrase bank, organized by situation
│                                        (estimates, status, risk, scope, blockers, altitude,
│                                        contractor terms), ending in one fully worked status update
├── 08_Certifications_and_Further_Study/ PMP/CAPM/PMI-ACP/PRINCE2 mapped, and where to go
│                                        deeper if this folder's scope isn't enough
├── 09_Case_Studies/                   Real, sourced project case studies mapped to the
│                                        knowledge areas above — risk failures (Denver DIA,
│                                        Sydney Opera House, FBI Virtual Case File), conflict/
│                                        coordination failures (Airbus A380, Boston Big Dig),
│                                        and a risk-management success (Heathrow T5) as contrast
└── README.md                          This file
```

## Suggested Reading Path

| Stage | Goal | Read |
|---|---|---|
| **1. Orient** | Get the shape of the whole discipline | `01_Foundations/` (both files) |
| **2. Build the vocabulary core** | The ten knowledge areas, especially communications | `02_Knowledge_Areas/` — read `03_communications_management.md` first regardless of order, since it's this folder's center of gravity |
| **3. Place the methodology you actually work in** | Recognize Scrum/Kanban/SAFe/hybrid on sight | `03_Methodologies/01_predictive_agile_and_hybrid_delivery.md` |
| **4. Anchor the numbers** | Be able to read a CPI/SPI dashboard and a critical path without translating | `04_Glossary_Formulas_Conversions/` — work the EVM example in `02_formulas_and_conversions.md` §1 by hand once |
| **5. Get concrete** | See it all applied to your actual domain | `06_MLOps_GenAI_Cloud_Playbook/01_applying_pm_to_mlops_genai_projects.md` |
| **6. Drill the delivery** | Make the vocabulary come out fluently under pressure | `07_Communication_Toolkit/01_pm_phrase_bank_and_scripts.md` — read the worked status update in §8 aloud |
| **7. See the theory fail and succeed for real** | Ground everything above in real, high-stakes outcomes | `09_Case_Studies/` — read the failures first, then Heathrow T5 as the contrast |
| **8. Keep as reference** | Return to these as needed, not read cover to cover | `05_Best_Practices_and_Templates/`, `08_Certifications_and_Further_Study/` |

## Where the Deep Interpersonal/Political Material Lives

Role clarity, conflict management, and the onshore/offshore contractor political dynamic are covered with full depth in `../Communication-Mastery/`, not duplicated here:

- `../Communication-Mastery/02_Thinking_Frameworks/11_role_clarity_and_expectation_contracts.md` — owning your remit, the engineer/architect boundary, stakeholder expectation maps, contractor-specific dynamics
- `../Communication-Mastery/02_Thinking_Frameworks/12_project_management_literacy_for_engineers.md` — the operational companion to this whole folder, written before it and still the fastest single read for day-to-day PM interaction
- `../Communication-Mastery/02_Thinking_Frameworks/13_conflict_management_in_projects.md` — conflict sources, styles, escalation, and the onshore–offshore structural fault line
- `../Communication-Mastery/13_Common_Mistakes/13_case_study_onshore_political_targeting_of_offshore_contractors.md` — the specific case study on job-security-driven political targeting of offshore/contract engineers, with a forward protocol

This folder is the reference depth; those chapters are the applied, narrative depth. Read both directions as needed — a term encountered in the narrative chapters that isn't fully explained there almost certainly has its full definition here.

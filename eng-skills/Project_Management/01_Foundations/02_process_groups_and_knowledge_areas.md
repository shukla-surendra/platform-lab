# Process Groups and Knowledge Areas — The PMBOK Grid

PMI's PMBOK® Guide organizes all of project management along two independent axes: **five process groups** (categories of activity, recurring across the project) and **ten knowledge areas** (domains of subject matter). Where they intersect is a *process* — PMBOK's Sixth Edition names 49 of them. This chapter gives the grid, explains why it's shaped this way, and deliberately does not enumerate all 49 processes with their full inputs/tools/outputs (ITTO) — that level of detail belongs in a PMP study guide, not an engineer's working reference. What an engineer actually needs is the grid's *shape*, so PM vocabulary and PM artifacts can be placed correctly the moment they're encountered.

## Index

1. [The Grid](#1-the-grid)
2. [The Five Process Groups, Explained](#2-the-five-process-groups-explained)
3. [The Ten Knowledge Areas, Explained](#3-the-ten-knowledge-areas-explained)
4. [What "ITTO" Means and Why It's Not Worth Memorizing Whole](#4-what-itto-means-and-why-its-not-worth-memorizing-whole)
5. [Where This Repo Covers Each Knowledge Area in Depth](#5-where-this-repo-covers-each-knowledge-area-in-depth)
6. [Glossary — Vocabulary Used in This Chapter](#6-glossary--vocabulary-used-in-this-chapter)

---

## 1. The Grid

```
                          PROCESS GROUPS
              Initiating  Planning  Executing  M&C  Closing
Integration       ●          ●          ●       ●      ●
Scope                        ●                  ●
Schedule                     ●                  ●
Cost                         ●                  ●
Quality                      ●          ●       ●
Resource                     ●          ●       ●
Communications                ●          ●       ●
Risk                         ●                  ●
Procurement                  ●          ●       ●
Stakeholder       ●          ●          ●       ●
```
*(M&C = Monitoring & Controlling. Dot density is illustrative of typical concentration, not exhaustive — several knowledge areas touch every group at low intensity.)*

Two things this grid makes visible immediately:

1. **"Planning" is the dominant column** — most knowledge areas have their heaviest activity there, reinforcing the point already made in `01_what_is_project_management.md` §3: influence is cheapest early, and planning is where nearly all of it gets spent.
2. **Integration and Stakeholder management are the only rows active in every single column.** This is not incidental — they are the "connective tissue" knowledge areas, which is why a PM who seems to be constantly managing relationships and constantly reconciling changes against the whole plan is not being inefficient; that *is* the job description of those two rows.

[↑ Back to index](#index)

## 2. The Five Process Groups, Explained

| Process group | Purpose | Typical engineer-visible artifact |
|---|---|---|
| **Initiating** | Define a new project or phase; secure authorization to proceed | The project charter (`../02_Knowledge_Areas/01_integration_scope_schedule_management.md` §1) |
| **Planning** | Establish scope, refine objectives, define the course of action | WBS, schedule, budget, risk register, communication plan |
| **Executing** | Complete the work defined in the plan to satisfy requirements | Deliverables themselves; status updates; change requests |
| **Monitoring & Controlling** | Track, review, and regulate progress and performance; identify and act on necessary changes | Status reports, RAID log updates, EVM metrics (`../04_Glossary_Formulas_Conversions/02_formulas_and_conversions.md`) |
| **Closing** | Formally conclude the project or phase | Acceptance sign-off, lessons learned, handover documentation |

A common misconception worth correcting explicitly: **these are not sequential phases of the project — they are categories of activity that recur, often simultaneously, throughout it.** A project can be executing one work package while still planning another and closing out a completed one, all in the same week. Confusing process groups with life-cycle phases (`01_what_is_project_management.md` §3) is one of the more common vocabulary errors an otherwise-fluent engineer makes in a PM conversation.

[↑ Back to index](#index)

## 3. The Ten Knowledge Areas, Explained

| Knowledge area | What it governs | One-line engineer translation |
|---|---|---|
| **Integration Management** | Coordinating all the other pieces into a coherent whole; managing change | "Keeping the plan internally consistent as things change" |
| **Scope Management** | Defining and controlling what is, and is not, included | "Requirements and the fight against scope creep" |
| **Schedule Management** | Sequencing, estimating, and controlling the timeline | "The Gantt chart and whether the date holds" |
| **Cost Management** | Estimating, budgeting, and controlling spend | "The burn rate and whether it's on budget" |
| **Quality Management** | Determining quality standards and ensuring they're met | "Definition of done, at the project level" |
| **Resource Management** | Acquiring, developing, and managing the team and physical resources | "Staffing and capacity planning" |
| **Communications Management** | Ensuring timely, appropriate generation, distribution, and storage of project information | "Who needs to know what, how, and how often" (full treatment: `../02_Knowledge_Areas/03_communications_management.md`) |
| **Risk Management** | Identifying, analyzing, and responding to uncertainty | "The RAID log and what could still go wrong" |
| **Procurement Management** | Acquiring goods and services from outside the project team | "Vendor contracts, SOWs, and — from the other side — the contractor's own engagement" |
| **Stakeholder Management** | Identifying stakeholders and managing their engagement and expectations | "Who cares about this, how much, and what do they need from us" |

[↑ Back to index](#index)

## 4. What "ITTO" Means and Why It's Not Worth Memorizing Whole

**ITTO** stands for **Inputs, Tools & Techniques, Outputs** — the standard template PMBOK uses to describe each of the 49 processes: what feeds in, what method converts it, what comes out. Anyone pursuing the PMP certification memorizes dozens of these tables. For an engineer whose goal is *literacy, not certification* (per the operating premise of this whole folder — see `../README.md`), the useful takeaway is the pattern itself, applicable on the fly to any PM artifact encountered:

> Every PM artifact has an **input** it was built from, a **method** used to build it, and an **output** it feeds forward into the next process.

Applying this pattern to a schedule, for instance: input = the WBS and resource estimates; technique = critical path method (`../04_Glossary_Formulas_Conversions/02_formulas_and_conversions.md` §3); output = the schedule baseline, which then becomes an *input* to cost budgeting. Recognizing this input→technique→output shape on sight is what lets an engineer ask a sharp, well-placed question ("what's the schedule baseline this estimate is measured against?") without having memorized which of the 49 official processes produced it.

[↑ Back to index](#index)

## 5. Where This Repo Covers Each Knowledge Area in Depth

| Knowledge area | Deep-dive location |
|---|---|
| Integration, Scope, Schedule | `../02_Knowledge_Areas/01_integration_scope_schedule_management.md` |
| Cost, Quality, Resource | `../02_Knowledge_Areas/02_cost_quality_resource_management.md` |
| Communications | `../02_Knowledge_Areas/03_communications_management.md` |
| Risk | `../02_Knowledge_Areas/04_risk_management.md` |
| Procurement, Stakeholder | `../02_Knowledge_Areas/05_procurement_and_stakeholder_management.md` |

[↑ Back to index](#index)

## 6. Glossary — Vocabulary Used in This Chapter

| Term/Phrase | Meaning |
|---|---|
| Process group | One of five categories of PM activity: Initiating, Planning, Executing, Monitoring & Controlling, Closing |
| Knowledge area | One of ten subject-matter domains PM activity is organized around |
| ITTO | Inputs, Tools & Techniques, Outputs — the standard template describing any PMBOK process |
| Connective tissue | (figurative) Something that links and holds together otherwise-separate parts of a system |
| Burn rate | The rate at which a project consumes its budget over time |
| Definition of done | The agreed, explicit bar a piece of work must clear to count as complete |
| Scope creep | The gradual, unagreed expansion of what a project is expected to cover |
| Baseline | The approved version of scope/schedule/cost used as a fixed comparison point |
| On the fly | Done in the moment, without extensive prior preparation |

[↑ Back to index](#index)

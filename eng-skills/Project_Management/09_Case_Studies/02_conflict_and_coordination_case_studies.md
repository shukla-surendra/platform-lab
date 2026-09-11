# Conflict and Coordination Case Studies — Airbus A380 and the Boston Big Dig

Two cases illustrating the two distinct conflict categories named in `../../Communication-Mastery/02_Thinking_Frameworks/13_conflict_management_in_projects.md` §1: the Airbus A380 wiring-harness crisis is **task/coordination conflict** taken to an extreme — no single person did anything wrong, but a structural coordination failure between teams produced billions in cost; the Boston Big Dig is **stakeholder and political conflict** at megaproject scale — competing interests (federal government, state agencies, contractors, the public) actively pulling the project in different directions for over a decade. Same sourcing note as `01_risk_management_case_studies.md`: PMI's Learning Library papers are member-gated; the material below draws on PMI's public research plus extensively documented, widely-cited public case histories.

## Index

1. [Case: Airbus A380 Wiring Harness Crisis](#1-case-airbus-a380-wiring-harness-crisis)
2. [Case: The Boston Big Dig](#2-case-the-boston-big-dig)
3. [The Two Conflict Types, Contrasted](#3-the-two-conflict-types-contrasted)
4. [Glossary — Vocabulary Used in This Chapter](#4-glossary--vocabulary-used-in-this-chapter)

---

## 1. Case: Airbus A380 Wiring Harness Crisis

### The situation

The Airbus A380's design and manufacturing were split across multiple European sites — notably Hamburg (Germany) and Toulouse (France) — each responsible for different sections of the aircraft. The German and Spanish design teams continued working in an older version of the CAD software (CATIA V4), while the French and British teams had moved to a substantially rewritten newer version (CATIA V5) — not a simple upgrade, but effectively a different tool. The aircraft's roughly 100,000 wires and 40,000 connectors, designed across both versions, failed to integrate correctly: bend-radius calculations and other specifications didn't translate cleanly between the two software environments. The mismatch wasn't caught until physical wiring harnesses from different sites were brought together for final assembly — by which point more than 1,100 German engineers were reportedly dispatched to the Toulouse assembly site to manually rework the wiring. The resulting delay pushed the A380's delivery back roughly two years and is widely reported to have cost several billion euros.

### Root-cause analysis, mapped to knowledge areas

| Knowledge area | What went wrong |
|---|---|
| **Integration Management (`../02_Knowledge_Areas/01_integration_scope_schedule_management.md` §1)** | No effective **configuration management** existed across sites — the two design teams were, in effect, working from incompatible baselines without a shared, enforced standard, the exact failure mode configuration management exists to prevent |
| **Communications — the onshore/offshore-shaped fault line (`../02_Knowledge_Areas/03_communications_management.md` §8)** | Distributed, multi-site teams (Hamburg vs. Toulouse) with incomplete tooling alignment is structurally the same friction pattern documented for onshore/offshore teams — physical and organizational distance let an incompatibility persist undetected far longer than it would have inside one co-located team |
| **Risk** | A tooling-version mismatch across sites working on a single, physically integrated system is a foreseeable, nameable risk category — "did every site verify compatibility of their design tooling before divergent work proceeded" is exactly the kind of identify-risks question `../02_Knowledge_Areas/04_risk_management.md` §2 recommends asking at project start, and there's no public evidence it was asked with the seriousness the stakes warranted |
| **Quality (QA vs. QC, `../02_Knowledge_Areas/02_cost_quality_resource_management.md` §2)** | This was a QA failure, not a QC one — no individual wiring harness was necessarily built "wrong" by the standard it was designed to; the *process* allowing two incompatible standards to coexist across sites was the actual defect, and it went undetected until physical integration, far later than QA should have caught it |

### Lessons forward

1. **A shared toolchain across distributed teams working on one physically integrated system is not optional infrastructure — it is a top-tier project risk to actively manage**, not something to leave to individual sites' local preferences.
2. **Integration points between distributed teams need to happen far earlier and far more frequently than "final assembly."** The mismatch was structurally guaranteed to be found eventually — the failure was in how late it was found, when the cost of fixing it had already multiplied enormously.
3. **This is precisely why `../../Communication-Mastery/02_Thinking_Frameworks/13_conflict_management_in_projects.md` §6 treats onshore/offshore and multi-site distance as a structural risk category in its own right** — visibility gaps between distributed teams don't just create interpersonal friction, they can hide purely technical incompatibilities for years.

[↑ Back to index](#index)

## 2. Case: The Boston Big Dig

### The situation

The Central Artery/Tunnel Project — Boston's "Big Dig" — rerouted the city's central highway underground. Originally estimated at roughly $2.6 billion, the project's final cost is widely reported at around $14.8 billion (roughly 275% over the original budget in constant dollars), and it opened nine years later than planned. Beyond the raw overrun, the project is a canonical stakeholder-conflict case: the Federal Highway Administration pressured redesigns tied to future road-capacity demands; state agencies, contractors, and public interest groups pulled the project in different directions throughout construction; and continuous externally-driven redesigns compounded the original scope repeatedly. A 2006 ceiling panel collapse in one of the tunnels, which killed a motorist, was later traced to a specific epoxy-bolt failure — itself connected to disputes and shortcuts during construction.

### Root-cause analysis, mapped to knowledge areas

| Knowledge area | What went wrong |
|---|---|
| **Stakeholder Management (`../02_Knowledge_Areas/05_procurement_and_stakeholder_management.md` §4-5)** | An unusually large, high-power, high-interest stakeholder set (federal government, state government, dozens of contractors, the public) was never brought into a coherent power/interest-grid-style engagement plan — the project instead absorbed pressure reactively from whichever stakeholder pushed hardest at a given moment |
| **Scope/Integration** | "Constant redesigns" driven by external pressure (the Federal Highway Administration's funding threat over road-widening being a specific, documented example) were absorbed without the disciplined Integrated Change Control process (`../02_Knowledge_Areas/01_integration_scope_schedule_management.md` §1) that would have forced each redesign to be weighed explicitly against cost and schedule impact before being accepted |
| **Conflict Management (`../../Communication-Mastery/02_Thinking_Frameworks/13_conflict_management_in_projects.md` §2)** | This is squarely the taxonomy's **structural/positional conflict** category — federal funding leverage, state political accountability, and contractor commercial incentives were fundamentally different, locally rational interests colliding by design, not by any individual's misconduct |
| **Quality** | The fatal ceiling collapse traces back to a quality-control failure under schedule/cost pressure — the textbook illustration of `../02_Knowledge_Areas/02_cost_quality_resource_management.md` §4's warning that when resourcing or schedule pressure mounts without an explicit trade-off decision, quality is the constraint that silently gives, sometimes with severe consequences |

### Lessons forward

1. **A megaproject with this many high-power stakeholders needs its stakeholder engagement plan treated as seriously as its engineering plan** — the power/interest grid (`../02_Knowledge_Areas/05_procurement_and_stakeholder_management.md` §5) exists precisely to make "who needs to be managed closely, and starting when" an explicit, proactive decision rather than a reactive scramble.
2. **Externally-imposed scope changes still need to go through change control**, even when the party demanding them holds real power (here, federal funding leverage) — absorbing them informally is how a project's baseline quietly loses all meaning, the "vanishing baseline" anti-pattern named in `../05_Best_Practices_and_Templates/01_best_practices_and_anti_patterns.md` §2.
3. **When schedule or political pressure mounts, someone has to explicitly ask "which constraint is being sacrificed to relieve this pressure?"** — on the Big Dig, the evidence suggests quality was repeatedly the unstated answer, and the tunnel collapse is the clearest possible illustration of why that question needs to be asked out loud rather than allowed to resolve itself silently.

[↑ Back to index](#index)

## 3. The Two Conflict Types, Contrasted

| | Airbus A380 | Boston Big Dig |
|---|---|---|
| **Conflict category** | Task/coordination conflict (structural, not political) — `../../Communication-Mastery/02_Thinking_Frameworks/13_conflict_management_in_projects.md` §1 | Stakeholder/political conflict, with structural roots — §2's "structural/positional" row |
| **Who was in conflict** | No individuals — two engineering standards, silently incompatible | Federal government, state government, contractors, public interest groups — actively, visibly |
| **Detectability in advance** | High — a tooling audit would have caught it | Lower — political and funding pressures shift unpredictably over a decade-plus timeline |
| **The generalizable fix** | Configuration management + earlier, more frequent integration checkpoints | A proactive, continuously maintained stakeholder engagement plan, and disciplined change control even under high-power pressure |

Both cases converge on the same meta-lesson as `01_risk_management_case_studies.md` §5's cross-case pattern: **the eventual failure was rarely a mystery in hindsight — the mechanism was visible early, to anyone specifically looking for it, and the actual failure was that no formal process was assigned to look.**

[↑ Back to index](#index)

## 4. Glossary — Vocabulary Used in This Chapter

| Term/Phrase | Meaning |
|---|---|
| Configuration management | The system for tracking and controlling changes to a product's specifications and documentation |
| Bend radius | The minimum radius a wire or cable can be bent without damage — a real engineering constraint affected by the A380's CAD mismatch |
| Toolchain | The set of software tools used together across a workflow, here across engineering sites |
| Canonical (case) | Widely accepted as the standard, most-cited example of a pattern |
| Epoxy-bolt failure | A structural fastening failure — the specific technical cause identified in the Big Dig tunnel collapse |
| Squarely (fits a category) | Falls directly and unambiguously within that category |
| Meta-lesson | A lesson about the pattern itself, one level more general than either individual case |

## Sources

- [SimpleFlying — The Software Discrepancies That Caused A Multibillion-Euro Delay To The Airbus A380 Program](https://simpleflying.com/airbus-a380-program-software-discrepancies-delay-story/)
- [Calleam Consulting — Airbus A380: Why Do Projects Fail?](https://calleam.com/WTPF/?p=4700)
- [SimpleFlying — History: The Delays That Made The Airbus A380 Late To Market](https://simpleflying.com/airbus-a380-production-delays-history/)
- [PMI — Boston's Lessons Learned](https://www.pmi.org/learning/library/boston-lessons-learned-9950)
- [PMI — Big Dig: Best Practices for Mega-Project Cost Estimating](https://www.pmi.org/learning/library/practices-mega-project-cost-estimating-6668)
- [Wiley — Megaproject Management: Lessons on Risk and Project Management from the Big Dig](https://www.wiley.com/en-us/Megaproject+Management:+Lessons+on+Risk+and+Project+Management+from+the+Big+Dig-p-9781118418871)

[↑ Back to index](#index)

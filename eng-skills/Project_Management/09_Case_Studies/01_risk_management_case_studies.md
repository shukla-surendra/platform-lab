# Risk Management Case Studies — Denver Airport, Sydney Opera House, FBI Virtual Case File

A note on sourcing before the content: PMI's own Learning Library (the member-only paper archive referenced throughout `../` as "PMI Learning Library") sits behind a login wall and could not be fetched directly for this chapter. What follows instead draws on PMI's own **public** research (the *Pulse of the Profession* series) and three of the most extensively documented, widely-cited project failures in the project-management literature — cases PMI itself references in its academic case-study program and in *PM Network* coverage, and which appear repeatedly across PMP/CAPM training precisely because the failure mechanisms map so cleanly onto specific PMBOK knowledge areas. Figures below are the commonly-cited public figures; exact totals vary slightly by source depending on what's included (design cost vs. total cost, nominal vs. inflation-adjusted dollars), and that variance is noted where it matters.

## Index

1. [PMI's Own Data on Why Projects Fail](#1-pmis-own-data-on-why-projects-fail)
2. [Case: Denver International Airport Baggage System](#2-case-denver-international-airport-baggage-system)
3. [Case: Sydney Opera House](#3-case-sydney-opera-house)
4. [Case: FBI Virtual Case File](#4-case-fbi-virtual-case-file)
5. [Cross-Case Pattern](#5-cross-case-pattern)
6. [Glossary — Vocabulary Used in This Chapter](#6-glossary--vocabulary-used-in-this-chapter)

---

## 1. PMI's Own Data on Why Projects Fail

PMI's *Pulse of the Profession* research (an ongoing, publicly published PMI survey series, distinct from the member-gated Learning Library) consistently identifies communication as the single largest driver of project failure — a finding worth having as a number, not just an impression:

| Finding | Figure |
|---|---|
| Projects where poor communication is a contributing cause of failure | Cited at roughly one-third of failed projects, and a negative factor in over half |
| Money at risk per $1 billion spent, attributable to poor communication | Over half of the at-risk amount (roughly $75M of $135M at risk per $1B spent) |
| Projects meeting original goals — high project-management-maturity orgs vs. low | ~73% vs. ~53% meet original goals, respectively |

The practical takeaway, before even reaching the individual cases below: **root-cause narratives about "engineering failure" or "scope failure" very often turn out, on inspection, to be communication and risk-management failures wearing a technical costume** — a pattern that holds across all three cases in this chapter.

[↑ Back to index](#index)

## 2. Case: Denver International Airport Baggage System

### The situation

Denver International Airport's original design called for a single, fully automated, airport-wide baggage-handling system — an ambitious integration of roughly 100 computers, dozens of laser scanners, and thousands of motorized carts, intended to route bags automatically across the entire airport rather than relying on conventional tug-and-cart handling. The system was contractually committed to a fixed scope, schedule, and cost before its technical complexity was fully understood. Continuous scope changes from the airlines (the system's actual end users) compounded an already underestimated technical challenge. The airport's opening was delayed by 16 months specifically because of the baggage system's failure to work reliably; by 2005, United Airlines had abandoned the automated system entirely in favor of a conventional one — the same approach used at every other major airport.

### Root-cause analysis, mapped to knowledge areas

| Knowledge area | What went wrong |
|---|---|
| **Scope (`../02_Knowledge_Areas/01_integration_scope_schedule_management.md`)** | An extraordinarily ambitious scope was locked into a contract before feasibility was proven — the opposite of the "spike before estimating" discipline in `../../Communication-Mastery/02_Thinking_Frameworks/12_project_management_literacy_for_engineers.md` §6 |
| **Risk (`../02_Knowledge_Areas/04_risk_management.md`)** | No apparent formal risk register treating "first-of-its-kind, airport-wide automation" as the very-high-probability, very-high-impact risk it obviously was; the qualitative risk matrix (§3 of that chapter) would have scored this near the top of the grid on sight |
| **Stakeholder (`../02_Knowledge_Areas/05_procurement_and_stakeholder_management.md`)** | The airlines — the system's actual daily users — were not adequately engaged during design, and their subsequent stream of change requests reads, in hindsight, as exactly the scope-conflict pattern named in `../../Communication-Mastery/02_Thinking_Frameworks/13_conflict_management_in_projects.md` §2 (a role/boundary and goal conflict between the airport authority and its airline tenants) |
| **Integration/Change Control** | Continuous scope changes were absorbed into an already fragile technical plan without the schedule or budget baseline being formally revisited to match — the "silent absorption" failure mode named generally in `../02_Knowledge_Areas/02_cost_quality_resource_management.md` §4 |

### Lessons forward

1. **A first-of-its-kind technical approach is, by definition, a top-scoring qualitative risk** — it should never enter a fixed-scope, fixed-schedule contract without a de-risking phase first.
2. **The people who will actually use a system need a seat in its design process**, not just a change-request channel after the fact — engaging the airlines as genuine design stakeholders, not downstream requesters, would have surfaced the scope's true complexity far earlier.
3. **A fixed-price contract on unproven, novel technology puts the wrong party at risk** — `../02_Knowledge_Areas/05_procurement_and_stakeholder_management.md` §2's contract-type table exists precisely to prevent this mismatch.

[↑ Back to index](#index)

## 3. Case: Sydney Opera House

### The situation

Designed by Danish architect Jørn Utzon and constructed between 1959 and 1973, the Sydney Opera House is simultaneously an architectural triumph and one of the most-cited cost/schedule overrun cases in project management literature: an original budget near AU$7 million ballooned to over AU$100 million (commonly cited figures vary by source and currency-year), and construction ran roughly 15 years against an originally much shorter estimate — widely reported as several hundred percent over the original schedule. Construction began before the design was fully resolved; Utzon was later replaced mid-project by a government-appointed team that struggled to fully realize his original vision, particularly for the building's interiors.

### Root-cause analysis, mapped to knowledge areas

| Knowledge area | What went wrong |
|---|---|
| **Integration/Schedule** | Construction started (per widely reported accounts) before the design was complete — the exact inversion of the "planning is where influence is cheapest" principle in `../01_Foundations/01_what_is_project_management.md` §3; changes made after ground was broken were vastly more expensive than the same changes would have been on paper |
| **Cost** | No credible cost baseline existed early on to measure variance against — without one, there's no EVM-style signal (`../04_Glossary_Formulas_Conversions/02_formulas_and_conversions.md` §1) to catch drift while it's still small |
| **Governance/Stakeholder** | Replacing the original architect mid-project, and the reported communication breakdown between the incoming team and the original vision, is a governance and stakeholder-continuity failure — a change of this magnitude belongs to Integration Management's Integrated Change Control (`../02_Knowledge_Areas/01_integration_scope_schedule_management.md` §1), formally assessed for its downstream impact, not executed as an abrupt substitution |
| **Risk** | Ambitious, unproven structural engineering (the building's iconic shell roof required genuinely novel structural solutions) was treated more as an inspirational challenge than as a named, tracked risk with a mitigation plan |

### Lessons forward

1. **"Start building to create momentum" is a seductive but dangerous move when the design isn't finished** — the schedule gained by starting early is almost always smaller than the cost incurred by the resulting rework.
2. **A visionary, technically novel design needs its risk register to match its ambition** — the more original the engineering, the more formal (not less) the risk process needs to be, precisely because intuition about probability and impact is least reliable on genuinely new problems.
3. **Replacing a key stakeholder (here, the lead architect) is itself a major project risk event** deserving its own transition/handover plan, not treated as an administrative substitution.

[↑ Back to index](#index)

## 4. Case: FBI Virtual Case File

### The situation

Launched in the early 2000s, the FBI's Virtual Case File (VCF) project aimed to replace the Bureau's paper-based case management system with a modern digital one. After roughly $170 million and several years of development, the system was scrapped without ever being deployed. The most frequently cited causes: constantly shifting requirements (partly driven by post-9/11 security-mission changes), weak program oversight and governance, and inadequate progress tracking that let the project drift for a long time before its true state became visible to decision-makers. The FBI later launched a successor program, Sentinel, applying lessons from VCF's failure, which was completed successfully in 2012.

### Root-cause analysis, mapped to knowledge areas

| Knowledge area | What went wrong |
|---|---|
| **Scope** | Requirements were never stabilized into a real scope baseline (`../02_Knowledge_Areas/01_integration_scope_schedule_management.md` §2) — a textbook case for a phased or agile life cycle (`../03_Methodologies/01_predictive_agile_and_hybrid_delivery.md` §5) rather than the fixed, sequential approach reportedly used |
| **Governance** | Weak oversight meant no forcing function existed to catch drift early — the PMO/steering-committee role described in `../01_Foundations/01_what_is_project_management.md` §6 either didn't exist in practice or lacked real authority |
| **Communications/Monitoring & Controlling** | Inadequate progress tracking meant status reporting wasn't producing a signal decision-makers could act on — the "watermelon status" anti-pattern named in `../05_Best_Practices_and_Templates/01_best_practices_and_anti_patterns.md` §2, at government-program scale |
| **Risk** | Shifting external requirements (security-mission changes) were a foreseeable category of risk for any government IT program in that specific post-9/11 period, yet the program's rigid, sequential approach had no formal mechanism to absorb requirement churn without destabilizing the whole build |

### Lessons forward

1. **When the requirements themselves are genuinely unstable, a predictive (waterfall) life cycle is the wrong tool** — this is precisely the decision table in `../03_Methodologies/01_predictive_agile_and_hybrid_delivery.md` §5: low requirements clarity favors agile, and VCF's environment had about as much requirements instability as a project can have.
2. **Oversight has to be real, not nominal** — a governance body that exists on paper but doesn't actually track and act on variance is functionally the same as having none, and is worse in one respect: it creates false confidence that someone is watching.
3. **A program this large needed EVM-grade metrics (`../04_Glossary_Formulas_Conversions/02_formulas_and_conversions.md` §1) reported on a real cadence** — "we found out too late how bad it was" is nearly always, on inspection, "we weren't measuring the right thing frequently enough to find out early."

[↑ Back to index](#index)

## 5. Cross-Case Pattern

All three cases, despite spanning construction, aviation infrastructure, and government IT, converge on the same underlying mechanism:

> **A genuinely difficult technical or organizational challenge got treated as a scope/schedule/cost planning problem, when it should have been treated as a risk management problem first.**

| Case | The risk that should have driven the plan | What drove the plan instead |
|---|---|---|
| Denver DIA | "This is a first-of-its-kind automation system" | A fixed contract, as if the technology were proven |
| Sydney Opera House | "The design and the structural engineering aren't finished" | A start date, as if the design were finished |
| FBI VCF | "Requirements will keep shifting in this environment" | A sequential build plan, as if requirements were stable |

The forward-looking discipline this implies, restated as a single habit: **before committing to a schedule and budget, name the single hardest unknown in the project out loud, and ask whether the chosen methodology and contract type actually account for it** — not whether the plan looks complete on paper.

[↑ Back to index](#index)

## 6. Glossary — Vocabulary Used in This Chapter

| Term/Phrase | Meaning |
|---|---|
| Feasibility | Whether something is technically or practically achievable, ideally established before committing resources |
| Baseline | The approved version of scope/schedule/cost used as a fixed comparison point |
| De-risking | Taking early action to reduce or clarify a major uncertainty before committing further resources |
| Requirements churn | Frequent, ongoing change in what a system is required to do |
| Nominal forcing function | A mechanism intended to compel action or visibility, but which exists only formally and has no real effect |
| Momentum (as a project driver) | Continuing or starting work primarily to maintain a sense of progress, rather than because the underlying plan is sound |
| Textbook case | An example matching a known pattern so cleanly it's commonly used to teach that pattern |
| Converge (on a pattern) | Multiple independent cases arriving at the same underlying explanation |

## Sources

- [Denver Airport Baggage System — Calleam Consulting case study](https://www5.in.tum.de/~huckle/DIABaggage.pdf)
- [PEimpact — Lessons Learned: Denver International Airport Automated Baggage-Handling System](https://peimpact.com/the-denver-international-airport-automated-baggage-handling-system/)
- [PMI — Academic Project Management Case Studies program](https://www.pmi.org/learning/academic-programs/project-management-curriculum-and-resources/academic-project-management-case-studies)
- [Sydney Opera House Project Failures Analysis](https://www.scribd.com/document/727107079/B22414-V1)
- [Beyond Software — Sydney Opera House: Learning from Failed Projects](https://blog.beyondsoftware.com/learning-from-failed-projects-sydney-opera-house)
- [ResearchGate — Project Risk Management: Application in the Construction of the Sydney Opera House](https://www.researchgate.net/publication/394239334_Project_Risk_Management_Application_in_the_Construction_of_the_Sydney_Opera_House_SOH)
- [ScholarWorks CSUSB — The FBI Virtual Case File: A Case Study, Jack T. Marchewka](https://scholarworks.lib.csusb.edu/cgi/viewcontent.cgi?article=1132&context=ciima)
- [GenX Jamerican — Lessons Learned: The Failure of Virtual Case File](https://www.genxjamerican.com/2007/12/05/lessons-learned-the-failure-of-virtual-case-file/)
- [PMI — The High Cost of Low Performance (Pulse of the Profession)](https://www.pmi.org/learning/library/en-2013-pulse-high-cost-low-performance-13512)
- [Ascertra — PMI Study: Poor Communication Leads to Project Failure One Third of the Time](https://www.ascertra.com/blog/pmi-study-reveals-poor-communication-leads-to-project-failure-one-third-of-the-time)

[↑ Back to index](#index)

# Project Management Literacy for Engineers — Reading the Machinery Without Becoming Its Operator

An engineer does not need to *run* projects to be hurt by not understanding how they are run. Project management is the coordination layer that converts engineering effort into organizational outcomes — and an engineer who cannot read that layer is **flying blind** inside it: estimates get silently converted into commitments, risks raised in the wrong vocabulary get ignored, blockers reported too late get billed to the engineer's reputation, and beautifully engineered work gets marked late against a plan the engineer never saw. This chapter is **literacy, not certification**: the working knowledge a Cloud/MLOps developer or architect needs to be a credible counterpart to project managers — to feed their artifacts, speak their dialect, and protect the engineering work inside their machinery. It is the operational sibling of `11_role_clarity_and_expectation_contracts.md`: that chapter establishes *what the role owns*; this one covers *how owned work travels through a managed project*.

## Index

1. [Why PM Literacy Pays (Without the Job Title)](#1-why-pm-literacy-pays-without-the-job-title)
2. [The Core Mental Model: The Triple Constraint](#2-the-core-mental-model-the-triple-constraint)
3. [The Project Lifecycle — and Where the Engineer Plugs In](#3-the-project-lifecycle--and-where-the-engineer-plugs-in)
4. [Delivery Methodologies, Decoded](#4-delivery-methodologies-decoded)
5. [The PM's Artifacts: How to Read Them, How to Feed Them](#5-the-pms-artifacts-how-to-read-them-how-to-feed-them)
6. [Estimation — the Highest-Stakes Interface](#6-estimation--the-highest-stakes-interface)
7. [Dependencies, Blockers, and the Critical Path](#7-dependencies-blockers-and-the-critical-path)
8. [Speaking Risk Fluently](#8-speaking-risk-fluently)
9. [MLOps-Specific Friction With Project Plans](#9-mlops-specific-friction-with-project-plans)
10. [The Engineer–PM Working Contract](#10-the-engineerpm-working-contract)
11. [Glossary — Vocabulary Used in This Chapter](#11-glossary--vocabulary-used-in-this-chapter)

---

## 1. Why PM Literacy Pays (Without the Job Title)

Four concrete returns, each traceable to a specific failure it prevents:

| Return | Failure it prevents |
|---|---|
| **Estimates stop mutating into commitments.** Knowing how a number travels — from a hallway guess into a Gantt chart into an executive deck — teaches the engineer to attach ranges and assumptions *at the source*, the only point where they still can be attached. | The "you said two weeks" conversation, four weeks in. |
| **Risks raised in PM vocabulary actually land.** "This might be a problem" evaporates in a status meeting; "this is a high-probability, high-impact risk to the go-live date, and here is the mitigation" enters the RAID log and creates an accountable owner. | Being technically right, on the record nowhere, when the risk materializes. |
| **The plan becomes legible, and therefore contestable.** An engineer who can read a critical path can see *which* delays actually matter, argue sequencing intelligently, and spot when their task has been scheduled against a dependency that does not exist yet. | Discovering the plan's assumptions only by violating them. |
| **Architect-altitude credibility.** At architect level (`11_role_clarity_and_expectation_contracts.md` §3), delivery feasibility is part of the design conversation. An architect who shrugs at "how would this phase?" is only doing half the job. | Designs that are technically elegant and organizationally undeliverable. |

The point is emphatically **not** to annex the PM's job — a PM who feels second-guessed becomes an adversary, and the coordination work they do is genuinely a full-time discipline. The point is to be the counterpart PMs describe as "easy to plan around": legible, forthcoming, and fluent in their dialect. That reputation compounds.

[↑ Back to index](#index)

## 2. The Core Mental Model: The Triple Constraint

Nearly all project management reduces to managing one tension, classically drawn as a triangle:

```
            SCOPE (what gets built)
             /\
            /  \
           /    \
          /------\
   TIME           COST
 (by when)     (people, money)

   — with QUALITY as the invisible fourth
     dimension that silently absorbs the
     strain when the other three are fixed
```

**The load-bearing rule: the three corners cannot all be fixed simultaneously.** Compress the timeline and either scope shrinks, cost grows (more people — which, per **Brooks's law**, often backfires on late projects), or quality is quietly sacrificed. Every schedule negotiation an engineer will ever sit in is someone pulling one corner while pretending the others won't move.

Why this matters to an engineer specifically:

- **It supplies the trade-off sentence that ends unwinnable conversations.** When asked to absorb new scope with no new time: "We can do that — the triangle has to give somewhere. We drop feature X, move the date, or add a person. Which corner do you want to move?" This is the same tension-naming move as `11_role_clarity_and_expectation_contracts.md` §4, now with a shared diagram behind it. The alternative — silently absorbing the strain — is how quality becomes the sacrificial corner without anyone ever *deciding* that, and the engineer inherits the resulting incident.
- **It decodes PM behavior.** A PM pushing back on a refactor is not anti-quality; they are defending a corner they are accountable for. Framing the refactor *inside* the triangle ("two days now, or an estimated week of incident response before Q4") turns a standoff into a trade-off — the PM's native genre.

[↑ Back to index](#index)

## 3. The Project Lifecycle — and Where the Engineer Plugs In

Whatever the methodology, projects pass through recognizable phases. The engineer's leverage is wildly uneven across them — and concentrated at the front, where influence is cheap and mostly unexercised:

| Phase | What happens | Key artifacts | The engineer/architect's real role |
|---|---|---|---|
| **Initiation** | The project is justified and authorized: business case, sponsor, rough budget | Project charter, business case | Mostly upstream of the engineer — but *reading the charter* reveals what the sponsor actually bought, which is the ultimate arbiter of every later scope dispute |
| **Planning** | Scope is decomposed, estimated, sequenced, staffed | WBS, schedule/Gantt, RACI, risk register | **The window of maximum leverage.** Estimates, dependencies, and technical risks contributed here shape everything after. Feasibility silence here is consent — objections raised in execution arrive with interest |
| **Execution** | The work happens | Status reports, change requests | Deliver; surface change early; keep the status truthful (`../13_Common_Mistakes/05_case_study_optimistic_status_update_trap.md`) |
| **Monitoring & control** | Actuals vs. plan; risks tracked; scope guarded | RAID log, burndown, milestone reviews | Feed accurate signal. The PM's picture is only as good as engineer inputs — garbage in, Gantt out |
| **Closure** | Handover, acceptance, lessons learned | Acceptance sign-off, retrospective, handover docs | For MLOps: the operational handover (runbooks, monitoring, on-call) *is* the deliverable, not an appendix. For contractors, closure quality is the renewal pitch (`11_role_clarity_and_expectation_contracts.md` §7) |

The single most common engineer mistake against this lifecycle: **sleepwalking through planning, then fighting the plan during execution.** By execution, the plan has sponsors, dashboards, and inertia; changing it costs political capital. In planning, changing it costs a sentence.

[↑ Back to index](#index)

## 4. Delivery Methodologies, Decoded

An engineer meets these as the "operating system" of the project — the ceremonies attended, the units work is sliced into, the cadence of accountability:

| Methodology | Core mechanic | Where it fits | What the engineer must know |
|---|---|---|---|
| **Waterfall** | Phases in strict sequence: requirements → design → build → test → deploy; change is controlled via formal change requests | Fixed-scope, compliance-heavy, contract-driven work (common in enterprise/government cloud migrations) | Late change is *expensive by design* — get requirements objections in during the requirements phase or live with them; a signed-off spec is a **baseline**, and deviating from it needs a change request, not initiative |
| **Scrum** | Fixed-length **sprints** (1–4 weeks); a **product owner** ranks a **backlog**; the team commits to a sprint's worth and demos at the end | Product development with evolving requirements | The sprint commitment is the unit of trust — mid-sprint scope injection is legitimate to refuse ("bring it to planning"); the **daily standup** is a coordination broadcast, not a status interrogation (`../09_Meeting_Communication/01_standups_reviews_incidents_execs.md`); the **retrospective** is the sanctioned channel for process complaints — grievances aired nowhere else count for nothing |
| **Kanban** | No sprints; continuous flow through a board with **WIP limits**; optimize cycle time | Operations-shaped work: platform teams, support, incident-driven streams — often the natural fit for *run-side* MLOps | WIP limits are the whole point — starting a sixth task while five are in flight is a process violation, not enthusiasm |
| **Hybrid / scaled (e.g., SAFe)** | Agile teams inside waterfall-ish quarterly planning (**PI planning**); dependencies negotiated across many teams at once | Large enterprises — statistically, where most cloud/MLOps contractors land | The quarterly planning event is where cross-team dependencies get committed; missing it means other teams commit *on the engineer's behalf* |

Two literacy points that outrank any methodology detail:

1. **Ceremonies are interfaces — learn what each one is *for*, then supply that.** Standup wants blockers and coordination signals, not a work diary. Sprint review wants demonstrated outcomes. Retro wants process observations. Feeding the wrong content to a ceremony ("in the weeds" technical narration at a milestone review) is the engineering equivalent of returning the wrong type from a function.
2. **Most organizations run a dialect, not the textbook.** "We do agile" typically means "sprints plus a hard deadline someone already promised." Wasting energy on methodology purism misses the practical question: *where, in this org's actual process, do estimates, risks, and scope objections have to be lodged in order to count?* Find those three lodging points in week one.

[↑ Back to index](#index)

## 5. The PM's Artifacts: How to Read Them, How to Feed Them

Each artifact is an interface with an expected input from engineering. Feeding them well is most of what "great to work with" means in a PM's mouth:

| Artifact | What it is | What the PM needs from the engineer |
|---|---|---|
| **Project charter** | The one-pager authorizing the project: objective, sponsor, success criteria | Just read it. It names the sponsor (the real customer) and the success criteria that settle scope arguments |
| **WBS (work breakdown structure)** | The full scope decomposed into a tree of work packages | Decomposition help, and the flag on what's *missing* — in MLOps, chronically: data readiness, monitoring, security review, handover. Absent from the WBS ≈ absent from the budget ≈ done for free at the end |
| **Schedule / Gantt chart** | Tasks laid on a calendar with dependencies and milestones | Estimates with assumptions attached, dependency corrections ("D can't start before the security review — that link is missing"), early warning when a date is drifting |
| **RACI matrix** | Per activity: who is **R**esponsible, **A**ccountable, **C**onsulted, **I**nformed | Contest it at creation — this is the formal edition of the §4 stakeholder map in `11_role_clarity_and_expectation_contracts.md`. Being silently listed R for "model monitoring" *is* the scope creep, in matrix form |
| **RAID log** | Running register of **R**isks, **A**ssumptions, **I**ssues, **D**ependencies | A steady drip of entries. The RAID log is the engineer's institutional memory: a risk logged in March is cover in July; a risk mentioned verbally in March is folklore |
| **Status report (RAG: red/amber/green)** | Periodic rollup to stakeholders, usually traffic-light coded | Honest color-calibration. Amber means "needs attention to stay on track" — flagging amber early is competence; the melt from green straight to red is the classic trust-destroyer (`../13_Common_Mistakes/05_case_study_optimistic_status_update_trap.md`) |
| **Change request** | Formal proposal to alter the baseline (scope/time/cost) | Impact analysis: what the change touches, costs, and pushes. The engineer's `git diff`-shaped mind is genuinely good at this |
| **Burndown / velocity charts** | Work remaining over time; the team's historical throughput | Mostly: don't game them. Velocity is a planning input, not a performance score — inflating points to look productive corrupts the very forecast that protects the team from overcommitment |

**The unifying insight: PM artifacts are the project's write-ahead log.** What is written in them survives reorgs, vacations, and memory; what was said in a meeting does not. The engineer's protective habit is simple — *anything that matters gets an artifact entry*: risks into the RAID log, agreements into a follow-up message, scope changes into a change request. This is the same closing-the-loop discipline as `11_role_clarity_and_expectation_contracts.md` §5.1, applied to project mechanics.

[↑ Back to index](#index)

## 6. Estimation — the Highest-Stakes Interface

Estimation is where engineering and project management touch most often and injure each other most often. The mechanism of the injury:

> The engineer produces a **point estimate** ("about two weeks") intended as a rough central guess. The plan cannot hold a probability distribution, so the number is recorded *as a date*. The date is aggregated upward, promised outward, and returns as a **commitment** — with the original uncertainty amputated. When reality lands in the (always right-hand) tail, the engineer is "late" against a certainty they never expressed.

Nobody in this loop acted in bad faith; the artifact chain simply strips error bars by default. The countermeasures all amount to *re-attaching the uncertainty at the source*:

1. **Give ranges with drivers, not points.** "Five days if the VPC peering is already approved; ten if not — the approval is the swing factor, and it's outside my control." The driver is the crucial part: it converts the range from hedging into information, and it hands the PM a dependency to chase.
2. **State estimates with their confidence and assumptions.** "Two weeks at maybe 70% confidence, assuming the training data is in the shape the data team described. If that assumption breaks, all bets are off — I'll know within two days of getting access." An estimate with a stated assumption is self-updating: when the assumption dies, the re-estimate is expected rather than resented. `08_probabilistic_thinking_and_calibration.md` covers the underlying calibration skill.
3. **Distinguish effort from duration, out loud.** Three days of effort is not three days of elapsed time — reviews, approvals, environment waits, and the engineer's other commitments stretch it. PMs plan in duration; engineers instinctively answer in effort; the unstated conversion is a chronic silent slippage. "Three days of work, likely a calendar week given the security review in the middle."
4. **Buffer visibly, not secretly.** Silent padding corrodes trust when discovered and gets amputated by negotiation anyway ("surely we can shave a couple of days"). A visible risk buffer — "8 days of work plus 3 days of buffer against the flaky staging environment" — is defensible, adjustable, and honest.
5. **Refuse to estimate the unestimable — offer a spike instead.** For genuinely novel work (most model-performance questions), the professional answer is not a fabricated number: "I can't estimate that responsibly yet. Give me a three-day **timebox** to prototype, and I'll come back with a real estimate and the top two risks." A PM will nearly always trade three days for a number they can trust.

[↑ Back to index](#index)

## 7. Dependencies, Blockers, and the Critical Path

The **critical path** is the longest chain of dependent tasks in the plan — the sequence with zero **slack**, where any delay moves the end date one-for-one. Tasks off the critical path have **float**: they can slip, within limits, harmlessly. This one concept upgrades an engineer's judgment immediately:

- **Not all delays are equal, and the plan says which is which.** Two days lost on a critical-path task is a project-level event deserving immediate escalation; two days lost on a task with a week of float is a non-event. Engineers who treat these identically either cry wolf or stay quiet about the one that mattered.
- **"Am I on the critical path right now?" is a question worth asking the PM directly.** The answer calibrates everything: urgency, interruption tolerance, how loudly to escalate a blocker, whether a refactor detour is affordable this week.

On blockers, the norm engineers chronically get backwards: **reporting a blocker is not an admission of failure — sitting on one is.** The engineer's instinct is to quietly wrestle a blocker ("I should be able to solve this myself") while the critical path silently absorbs the delay. From the PM's side, a blocker raised on day one is a routing problem they are *paid to solve* — chasing the approval, escalating to the other team, re-sequencing around it. A blocker confessed on day four is a schedule slip plus a trust dent. The efficient form:

> "I'm blocked on [X]. I've tried [A, B]. I need [specific thing] from [specific party]. Until then I'm proceeding on [next-best task]. Impact if it takes more than [N] days: [consequence — say whether it's on the critical path]."

Blocked-with-a-plan, not helpless — and note the last clause does the PM's impact triage for them. This report belongs in the weekly three-line status from `11_role_clarity_and_expectation_contracts.md` §8 (delivered / in-flight / **blocked-and-by-whom**): the "by whom" is what converts a complaint into an actionable routing request.

[↑ Back to index](#index)

## 8. Speaking Risk Fluently

Engineers spot risks constantly and get them ignored constantly, because the raising is done in the wrong grammar. "This could be a problem" is, to a PM, unprocessable — it has no probability, no impact, no ask. PM risk grammar has four slots:

> **[Event] + [likelihood] + [impact if it happens] + [proposed response]**

Vocabulary that makes the response slot precise:

| Term | Meaning |
|---|---|
| **Mitigation** | Action taken *now* to reduce the risk's probability or impact ("load-test before go-live") |
| **Contingency** | The pre-agreed plan *if it happens anyway* ("if drift exceeds the threshold at launch, we fall back to the previous model version") |
| **Risk acceptance** | An explicit, named-owner decision to live with the risk — the honest form of doing nothing |
| **Issue** | A risk that has stopped being hypothetical; it is now happening and needs management, not probability estimates |

Worked example, MLOps-flavored:

> Weak: "The data quality worries me a bit."
> Fluent: "Risk for the log: the upstream events pipeline has changed schema twice this quarter. If it happens again post-launch — I'd put it at 30–40% within six months — the feature pipeline breaks silently and the model serves on stale features. Mitigation: schema validation at ingestion, about two days. Contingency: alerting plus auto-fallback to the last good snapshot. I'd like the two days in the current sprint."

The fluent version is not more alarmed — it is more *actionable*, and it ends with an ask. Two norms complete the fluency: **log it, don't just say it** (the RAID log is where risks accrue institutional weight — and it is also the engineer's protection when the risk materializes: the difference between "flagged in writing in March" and an unprovable "I mentioned it once"); and **never inflate to be heard**. Calibrated risk-raisers get believed on the occasion it really matters; habitual catastrophizers get discounted precisely then. This is reputation as a **crying-wolf budget** — spend it accurately.

[↑ Back to index](#index)

## 9. MLOps-Specific Friction With Project Plans

Classical project plans assume construction-shaped work: known scope, decomposable tasks, effort roughly proportional to output. ML work violates these assumptions in patterned, nameable ways — and naming them *to the PM, in advance* is the difference between "managed research risk" and "engineer who keeps missing dates":

| Friction | Why it happens | How to communicate it |
|---|---|---|
| **Model performance is a discovery, not a deliverable** | Whether 90% accuracy is achievable is a property of the data, unknowable in advance — no amount of effort *guarantees* it | Never let a metric target enter the plan as a committed milestone. Reframe: "The committed deliverable is the trained-and-evaluated model plus the evaluation report by [date]; the accuracy number is a *finding*, and we pre-agree now what we do at each outcome band." Timebox the science; commit the engineering |
| **Data readiness is the real schedule, and it's invisible** | Plans model "build pipeline: 2 weeks" but not the access requests, quality archaeology, and PII reviews that precede it — routinely the true critical path | Force data readiness into the WBS as first-class tasks with owners (§5). "Data acquisition and validation is a workstream, not a preamble — it needs its own line and its own dates" |
| **The POC-to-production chasm** | A notebook that works is 20% of a system that serves; stakeholders who saw the demo anchor on 90% | Manage the anchor *at demo time*, not after: "What you're seeing proves feasibility. Productionizing — serving, monitoring, retraining, security — is the majority of the remaining work; here's the breakdown." One sentence at the demo saves a month of expectation repair |
| **Iterative work reads as rework** | "Retraining with new features" sounds, to a Gantt chart, like doing the same task twice — i.e., like failure | Frame iteration as the unit of plan-visible progress: "experiment cycle 1/2/3," each with a decision gate ("continue / pivot / ship"), so the chart shows designed loops rather than slippage |
| **Ongoing costs outlive the project** | Projects end; models drift, pipelines rot, monitoring pages someone. Classical closure has no slot for "this now needs feeding forever" | Raise run-cost and operational ownership at *planning*, in the charter conversation: "Who owns this model in month six — retraining, drift response, on-call? That's a staffing line, not a footnote." (For contractors this doubles as the §7 exit-engineering from `11_role_clarity_and_expectation_contracts.md`) |

The meta-skill across all five rows: **translate ML uncertainty into PM-legible structures** — timeboxes, decision gates, workstreams, pre-agreed outcome bands — rather than either overpromising to fit the plan's shape or hand-waving that "ML is unpredictable" (which a PM can only hear as *unmanageable*, and unmanageable things get cut).

[↑ Back to index](#index)

## 10. The Engineer–PM Working Contract

The row that was deliberately deferred from the stakeholder map in `11_role_clarity_and_expectation_contracts.md` §4, expanded to a full mutual contract:

| The PM legitimately expects from the engineer | The engineer legitimately expects from the PM |
|---|---|
| Estimates with stated assumptions and confidence — and *prompt re-estimates* when assumptions break (§6) | Estimates transmitted onward with their assumptions attached, not stripped to bare dates |
| Blockers within a day, in the routed form (§7) | Blockers actually chased — escalation is their craft; that is the trade |
| Risks in four-slot grammar, logged not just voiced (§8) | Logged risks tracked to an owner and a decision, not filed into a write-only log |
| Truthful status colors, amber flagged early (§5) | Amber treated as a request for help, not punished as failure — a PM who shoots amber messengers manufactures the green-to-red melts they fear |
| Respect for the change process: scope changes surfaced, not freelanced | Protection *by* the change process: scope arriving through the front door, and air cover for "that's a change request" |
| Ceremony inputs in the expected shape (§4) | Ceremonies kept purposeful and engineering time defended from meeting sprawl |
| No end-runs: concerns raised with the PM before being escalated around them | No surprises in reverse: dates not promised upward on the engineer's behalf without the engineer's number |

Like every contract in this pair of chapters, this one works only if made explicit — and the engineer who *proposes* it ("here's how I like to work with PMs: early ambers, logged risks, ranges with assumptions — and here's what I'll ask of you in return") is doing in miniature exactly what §5 of the previous chapter prescribes: drafting the charter instead of divining it. PMs, whose working life is a procession of engineers who go quiet until the deadline, tend to receive this proposal like rain in a drought.

[↑ Back to index](#index)

## 11. Glossary — Vocabulary Used in This Chapter

| Term/Phrase | Meaning |
|---|---|
| Literacy | Working knowledge sufficient to read and participate, short of expert practice |
| Flying blind | Operating without the information or instruments needed to see where one is going |
| Triple constraint | The scope–time–cost triangle; fixing all three simultaneously is impossible |
| Brooks's law | "Adding manpower to a late software project makes it later" (Fred Brooks) |
| Sacrificial | Deliberately (or tacitly) given up so something else can survive |
| Standoff | A deadlock in which neither side will yield |
| Charter | The document formally authorizing a project: objective, sponsor, success criteria |
| WBS (work breakdown structure) | Hierarchical decomposition of the full project scope into work packages |
| Gantt chart | A bar-chart schedule showing tasks, durations, and dependencies on a calendar |
| Baseline | The approved version of scope/schedule/cost against which changes are measured |
| RACI | Matrix assigning Responsible / Accountable / Consulted / Informed per activity |
| RAID log | Running register of Risks, Assumptions, Issues, Dependencies |
| RAG status | Red/amber/green traffic-light health reporting |
| Change request | Formal proposal to alter the baseline, with impact analysis |
| Burndown chart | Plot of work remaining over time within a sprint or release |
| Velocity | A team's measured throughput per sprint, used for forecasting |
| Write-ahead log | (borrowed from databases) The durable record written before actions, from which truth is reconstructed |
| Sprint | A fixed-length iteration ending in a demonstrable increment |
| Backlog | The ranked queue of pending work |
| Product owner | The role that owns and ranks the backlog |
| Retrospective | End-of-sprint meeting to inspect and improve the process itself |
| WIP limit | A cap on simultaneous in-flight items in a kanban system |
| PI planning | (SAFe) The quarterly event where multiple teams plan and commit together |
| Dialect | A local variant of a language — here, an org's homegrown version of a methodology |
| In the weeds | Lost in low-level detail inappropriate to the audience or forum |
| Lodged | Formally submitted or registered (a complaint, an objection, a risk) |
| Point estimate | A single-number estimate, with the uncertainty stripped |
| Error bars | The expressed range of uncertainty around a number |
| Amputated | Cut off entirely (here: uncertainty removed from an estimate as it travels) |
| Swing factor | The variable that determines which end of a range materializes |
| All bets are off | Prior predictions become void because an assumption has broken |
| Effort vs. duration | Work-hours required vs. calendar time elapsed; conflating them causes silent slippage |
| Padding | Hidden inflation of an estimate as insurance |
| Buffer | Visible, declared schedule reserve held against named risks |
| Spike / timebox | A fixed-duration investigation bought to convert unknowns into an estimate |
| Critical path | The longest dependency chain; delays on it move the end date one-for-one |
| Slack / float | Schedule room by which a non-critical task can slip harmlessly |
| Cry wolf | Raise alarms so often that real ones get ignored (from Aesop's fable) |
| Sitting on | Withholding or delaying something one should pass along |
| Mitigation | Action now to reduce a risk's probability or impact |
| Contingency | The pre-agreed plan executed if the risk happens anyway |
| Risk acceptance | A named-owner decision to knowingly live with a risk |
| Issue | A risk that has materialized and now requires management, not forecasting |
| Catastrophizing | Habitually presenting outcomes as far worse than evidence supports |
| Anchor (anchoring) | The first number or impression seen, which disproportionately shapes later judgment |
| Chasm | A deep gap; here, the distance between a working demo and a production system |
| Archaeology | (figurative) Painstaking excavation of old, undocumented data or systems |
| Workstream | A named, parallel track of related work within a project |
| Decision gate | A pre-agreed checkpoint where continue/pivot/stop is explicitly decided — full mechanism, history, and vocabulary (Stage-Gate, gatekeeper, exit criteria, go/kill/hold/recycle) in `../../Project_Management/03_Methodologies/01_predictive_agile_and_hybrid_delivery.md` §5 |
| Freelanced | Done unilaterally, outside the agreed process |
| End-run | Bypassing the proper channel or person to get a decision elsewhere |
| Meeting sprawl | The unchecked expansion of meetings into time meant for focused work |
| Rain in a drought | Something scarce and badly needed, received with disproportionate gratitude |
| Procession | A long series of people or things arriving one after another |

[↑ Back to index](#index)

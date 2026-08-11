# AI-Based Development Lifecycles: A Field Guide (Aug 2026)

> **Scope.** The competing lifecycle models for building software *with* AI agents —
> vibe coding, spec-driven development (SDD), eval-driven, multi-agent role
> simulation, change-proposal, and orchestrated/governed agentic SDLC — with the
> honest trade-offs of each. Not a tool tutorial; a map of the process space.

---

## 1. The one idea that generates all of them

Every model below is an answer to the same question:

> **An LLM will happily produce plausible code. Where does the *intent* live, and
> who verifies the output against it?**

Classical SDLC answered this with documents and humans. Agents broke the answer in
three specific ways, and each named methodology is a patch for one of them:

| Failure mode | What it looks like | Patched by |
|---|---|---|
| **Intent drift** | "Add login" → model picks defaults nobody agreed to | Spec-first (SDD) |
| **Context evaporation** | Intent lives in a chat transcript that dies with the session | Durable specs, steering/memory files |
| **Unverifiable output** | Code compiles, reviewer rubber-stamps, defect ships | Eval/test-driven, governed SDLC |

**Mental model — a spectrum, not a menu.** The x-axis is *how much structure,
verification, and human judgment surround the generation step*. Moving right buys
reliability and pays in ceremony. Nothing on this axis is "correct"; the discipline
is matching position on the axis to the blast radius of the code.

```
 less structure ─────────────────────────────────────────────────► more structure
 ┌──────────┬──────────────┬──────────────┬─────────────┬──────────────┬───────────┐
 │  Vibe    │ AI-augmented │  Context-    │ Eval/Test-  │ Spec-driven  │ Governed  │
 │  coding  │ SDLC         │  engineered  │ driven      │ (3 grades)   │ agentic   │
 │          │ (copilot)    │              │             │              │ SDLC      │
 └──────────┴──────────────┴──────────────┴─────────────┴──────────────┴───────────┘
   throwaway    everyday        team           risky         product        regulated
   prototypes   feature work    codebases      changes       surfaces       / at scale
```

Two axes are actually in play, and conflating them is the most common mistake:

- **Structure** (how much is written down before generation) — the axis above.
- **Autonomy** (how long the agent runs unsupervised) — orthogonal.

High autonomy + low structure = the failure quadrant. High structure exists mainly
to *buy* safe autonomy.

---

## 2. The lifecycles

### 2.1 Vibe coding

**Loop:** prompt → look at result → prompt again. Intent lives only in chat.

Coined by Andrej Karpathy (Feb 2025) for "fully giving in to the vibes" — accepting
diffs without reading them.

| Pros | Cons |
|---|---|
| Fastest path from idea to running artifact | Intent is unrecoverable once the session ends |
| Zero process overhead; ideal for exploration | No traceability — nobody can say *why* the code is like this |
| Great for throwaway code, spikes, scripts, demos | Quality collapses as the codebase grows past a few files |
| Genuinely useful for learning an unfamiliar API | Review burden shifts entirely to a human reading generated code |

**Use when:** prototypes, hackathons, one-off scripts, personal tooling, anything you
would be happy to delete.
**Never when:** the code touches money, PII, auth, or anything on-call.

---

### 2.2 AI-augmented traditional SDLC (copilot mode)

**Loop:** the normal SDLC (ticket → design → code → PR → CI → deploy), with AI as an
accelerator *inside* each stage. No lifecycle change; a productivity change.

| Pros | Cons |
|---|---|
| Zero migration cost — existing process, review gates, CI unchanged | Gains are local and capped; the process is still human-paced |
| Existing quality gates (PR review, tests) still bind | Encourages "accept-and-move-on" review at higher diff volume |
| Easy to adopt org-wide; no retraining | Doesn't address intent drift at all — just produces drift faster |

**Use when:** an established team with real review culture wants a safe first step.

---

### 2.3 Context-engineered development

**Loop:** invest in durable, versioned context files the agent reads on every run —
`CLAUDE.md` / `AGENTS.md`, steering docs, architecture notes, conventions — then work
normally on top of them.

This is the cheapest high-leverage move on the whole spectrum, and it is a
*prerequisite* for everything to its right. Specs without shared conventions still
produce code that fights the codebase.

| Pros | Cons |
|---|---|
| Very high ratio of quality gain to ceremony added | Context files rot silently; stale guidance is worse than none |
| Repo-wide effect — every task benefits, not just the next one | Consumes context window on every request |
| Composes with every other model on this list | No mechanism forces the agent to actually obey them |

**Use when:** always. Treat it as table stakes, not a methodology choice.

---

### 2.4 Eval-driven / test-driven AI development

**Loop:** write the executable acceptance criteria (tests, evals, property checks,
golden files) *before* the agent generates → agent iterates until green → human
reviews the tests, not primarily the code.

The key inversion: **the human's scarce attention moves from reading generated code to
authoring the oracle that judges it.** This is the single highest-value adaptation for
an engineer whose job is reliability.

| Pros | Cons |
|---|---|
| Verification is machine-checkable, not vibes-based | Only as good as the test suite — untested dimensions drift freely |
| Scales with agent throughput; review isn't the bottleneck | Agents will overfit to tests (hardcode, special-case, weaken assertions) |
| Directly reusable in CI; no new tooling required | Hard for genuinely fuzzy outputs (UX, prose, ranking quality) |
| Natural fit for ML/LLM systems where evals already exist | Writing good oracles is a real skill and slower than writing prompts |

**Use when:** the correctness criteria are expressible. For ML/inference systems this
is usually the *right default*, since offline evals + regression suites already exist.

---

### 2.5 Spec-driven development (SDD) — the dominant 2026 model

**Loop (canonical):** `constitution/steering → specify → plan → tasks → implement → verify`

A durable, version-controlled specification — not the chat history — is the source of
truth. Emerged in 2025 as the direct answer to vibe coding; by 2026 every major tool
ships a flavor (GitHub Spec Kit, AWS Kiro, Claude Code, Cursor, OpenSpec, BMAD, Tessl,
Google Antigravity).

**Three grades of commitment** — the distinction most write-ups miss:

| Grade | Relationship of spec to code | Example |
|---|---|---|
| **Spec-first** | Spec drives the first generation, then code diverges freely | Kiro, Spec Kit (in practice) |
| **Spec-anchored** | Spec and code stay bidirectionally synced; drift is detected | Tessl (aspirational) |
| **Spec-as-source** | Code is *generated output*, marked "do not edit" | Tessl beta, `// GENERATED FROM SPEC` |

Grade 3 is Model-Driven Development wearing new clothes — and MDD's historical failure
mode (the abstraction gap, round-trip pain) has not been repealed by LLMs.

| Pros | Cons |
|---|---|
| Intent survives the session — reviewable, diffable, versioned | Ceremony is real: Spec Kit emits 8+ files per feature |
| Review shifts to the spec (small, human-language) before code exists | **Review overload just moves** — verbose markdown is still review burden |
| Same spec drives implementation, tests, and docs | Agents frequently *ignore* the spec; nothing enforces conformance |
| Enables safe delegation to longer-running agents | Functional vs. technical spec boundary confuses both humans and agents |
| Onboards humans and agents from the same artifact | Overkill for small changes — a one-line bug fix gets three user stories |
| Auditable trail for regulated / enterprise contexts | Specs rot; a stale spec is a confident lie |

> **The honest criticism** (Martin Fowler's team, after hands-on trials): these tools may
> *amplify* the problems they claim to solve — review overload and hallucination — rather
> than fix them, with the more elaborate frameworks the worst offenders. Treat SDD as a
> bet, not a settled result.

---

### 2.6 Change-proposal / delta-driven development

**Loop:** propose a change with explicit deltas against existing behavior
(`ADDED` / `MODIFIED` / `REMOVED`) → approve → implement → fold into the baseline spec.

The brownfield answer. Full-spec SDD assumes greenfield; real work is a 200k-line
system where "what changes" matters far more than "what exists." Represented by
OpenSpec.

| Pros | Cons |
|---|---|
| Fits existing systems, where most engineering actually happens | Requires a baseline spec to diff against, or you bootstrap forever |
| Deltas are small, reviewable, and map cleanly to PRs | Adds an approval gate — friction on a fast-moving team |
| Natural audit trail: every behavior change has a proposal | Baseline drifts from reality unless folding-in is disciplined |

**Use when:** a large existing codebase, multiple contributors, changes that need to be
explained to someone later.

---

### 2.7 Multi-agent role simulation

**Loop:** simulate an entire team. BMAD runs 12+ specialized agents — Analyst, PM,
Architect, UX, Scrum Master, Developer, QA, Tech Writer — each with a tightly scoped
context window, each producing a versioned artifact (PRD → architecture doc → sprint
stories) before handing off. ChatDev is the research ancestor.

| Pros | Cons |
|---|---|
| Context scoping is genuinely clever — each agent sees only its slice | Cargo-cults human org structure; Conway's Law applied to bots |
| Produces the artifact chain enterprises expect (PRD, arch doc, stories) | Compounding error: a bad PRD poisons everything downstream |
| Strong for greenfield, ambiguous, "figure out what to build" work | Expensive in tokens and wall-clock for modest features |
| Handoff points are natural human review gates | Ceremony can exceed the work; heaviest option in the category |

**Use when:** greenfield feature with genuine ambiguity, and you want the planning
artifacts anyway.

---

### 2.8 Orchestrated agentic SDLC

**Loop:** agents operate *across* the lifecycle — analysis, planning, design, build,
test, delivery — and are orchestrated together rather than invoked one at a time.
Agents interpret goals, plan, use tools, act across systems, evaluate results, and
**escalate to a human when judgment or accountability is required**.

This is where the industry is heading (Forrester's 2026 framing: "from code assistants
to orchestrated SDLC agents"), and it is a *systems* problem, not a prompting problem.

| Pros | Cons |
|---|---|
| Removes handoff latency between lifecycle stages | The bottleneck moves to review, governance, and architecture |
| Long-horizon work becomes tractable (migrations, sweeps, audits) | Failure modes become distributed-systems failure modes |
| Human time concentrates on escalations and judgment calls | Requires real observability into agent actions, or it's unauditable |
| Fits CI/CD naturally — agents as pipeline stages | Accountability is genuinely unresolved: who owns a bad agent decision? |

**Engineer's read:** everything you know about distributed systems applies — idempotency,
retries, partial failure, backpressure, blast radius, rollback. The interesting problems
are orchestration and observability, not prompt wording.

---

### 2.9 Autonomous SWE agents (background / issue-to-PR)

**Loop:** hand an agent a ticket; it works unsupervised in an isolated environment
(container/worktree) and returns a PR. SWE-agent is the research lineage; the practical
form is background/cloud agents.

| Pros | Cons |
|---|---|
| Parallelism: N tickets in flight with no human in the inner loop | Success rate falls off a cliff as task ambiguity rises |
| Isolation limits blast radius | PR review becomes the hard bottleneck, at higher volume |
| Excellent for mechanical, well-bounded work (deps, lint sweeps, migrations) | Silent wrong-but-plausible PRs are the dangerous output |
| Sandboxing makes the risk explicit and containable | Needs strong CI/evals or you're merging on faith |

**Use when:** the task is bounded, verifiable by CI, and cheap to throw away.

---

### 2.10 Governed AI SDLC (the emerging enterprise layer)

**Loop:** everything above, wrapped in policy-as-code — provenance tracking for
AI-generated code, mandatory human sign-off on defined risk classes, license and
security scanning of generated output, and audit trails from spec → commit → deploy.

The newest layer and the least mature. Driven by the *productivity–reliability paradox*:
throughput rose, defect escape rates did too, and the compensating control has to be
structural rather than cultural.

| Pros | Cons |
|---|---|
| Makes AI-generated code auditable and attributable | Immature tooling; mostly bespoke today |
| Risk-tiering lets low-risk work stay fast | Easy to devolve into compliance theater |
| Prerequisite for regulated industries to adopt agents at all | Adds latency exactly where teams feel most productive |

---

## 3. Tool landscape (as of mid-2026)

| Tool | Model | Weight | Distinctive property |
|---|---|---|---|
| **GitHub Spec Kit** | Spec-first | Heavy (8+ files/spec) | Most adopted OSS; 30+ agent support; `constitution → specify → plan → tasks` |
| **AWS Kiro** | Spec-first | Light (3 files) | Agentic IDE; EARS requirements syntax; hooks; AWS integration |
| **Tessl** | Spec-anchored → spec-as-source | Medium, ambitious | 1:1 spec↔code mapping; `// GENERATED FROM SPEC`; spec registry for OSS libs |
| **OpenSpec** | Change-proposal | Medium | Brownfield deltas (ADDED/MODIFIED/REMOVED); auditable approvals |
| **BMAD** | Multi-agent roles | Heaviest | 12+ role agents, versioned artifact chain, agile simulation |
| **GSD** | Context-engineering phase loop | Lightest | Solo-dev oriented |
| **Claude Code / Cursor / Antigravity** | Native SDD flavors + plan modes | Varies | Skills, subagents, plan mode, worktree isolation |

Practical shape of the trade-off: **Kiro is lightest, Spec Kit most customizable but
heaviest, Tessl most ambitious and least proven.**

---

## 4. Cross-cutting truths

1. **The bottleneck moved.** It is no longer code generation. It is review, verification,
   governance, and architecture. Any methodology that doesn't reduce *review* load is
   solving last year's problem.
2. **Ceremony must be earned.** Every artifact you require is a tax paid on every change.
   The right question is never "is this rigorous?" but "does this rigor pay for itself at
   this blast radius?"
3. **Written intent beats remembered intent.** This is the durable insight underneath SDD,
   and it survives even if every current SDD tool dies.
4. **Nothing here enforces conformance.** Specs are *guidance*; only tests, types,
   evals, and CI are *binding*. Pair any spec-driven process with an executable oracle
   or you have documentation, not verification.
5. **Structure buys autonomy.** You cannot safely lengthen an agent's leash without
   first lengthening the verification loop.

---

## 5. Choosing: a decision table

| Situation | Model |
|---|---|
| Throwaway script, spike, personal tool | Vibe coding |
| Everyday feature work, mature team, strong review | AI-augmented SDLC + context engineering |
| Any repo you'll touch more than twice | Context engineering (always-on baseline) |
| Change with real correctness criteria | Eval/test-driven |
| Greenfield feature, ambiguous requirements | Spec-driven (light: Kiro/GSD) or multi-agent (BMAD) |
| Large brownfield system, multiple contributors | Change-proposal (OpenSpec) |
| Mechanical, CI-verifiable, bounded task | Autonomous background agent |
| Regulated, audited, or safety-critical | Governed agentic SDLC + spec-driven + evals |

Default for an infra/ML platform engineer: **context engineering + eval-driven, reaching
for light spec-driven when the change spans services.** Heavy SDD frameworks rarely pay
for themselves on infrastructure work, where the hard part is the failure mode, not the
requirement.

---

## 6. Articulate it (interview framing)

Expect this as a "what's your take on AI in engineering" question at every 2026 loop.
Weak answers list tools. Strong answers show a model.

**60-second version:**
> "I think of it as one axis: how much structure and verification wraps the generation
> step. Vibe coding is zero structure — fine for throwaway code, fatal in production
> because intent dies with the chat session. Spec-driven development pushes intent into
> a versioned artifact so it survives and is reviewable before code exists. The catch is
> that a spec is guidance, not enforcement — agents ignore specs routinely. So the piece
> I actually weight most is eval-driven: the human's scarce attention should go into
> authoring the oracle, not reading generated diffs. Structure is what buys you the right
> to let an agent run unsupervised."

**Likely follow-ups, and what they're testing:**

| Follow-up | What they're probing |
|---|---|
| "Isn't SDD just waterfall again?" | Do you know specs are *iterative and executable*, and can you name the real MDD failure mode? |
| "How would you catch an agent that games the tests?" | Mutation testing, held-out evals, property-based tests, human spot-audit sampling |
| "How do you review 10x the diff volume?" | Shift the gate left (spec review) + make verification machine-checkable; admit review is the bottleneck |
| "Who's accountable when an agent ships a bug?" | The merging human. Provenance, risk-tiering, mandatory sign-off classes |
| "What breaks first at scale?" | Context rot, spec drift, and reviewer fatigue — in that order |
| "How does this change your on-call story?" | More code you didn't write → observability and rollback matter more, not less |

The trap: sounding like a vendor. Ground every claim in a failure mode you can name.

---

## 7. Sources

- [Understanding Spec-Driven Development: Kiro, spec-kit, and Tessl — Martin Fowler / Thoughtworks](https://www.martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)
- [Spec-Driven Development (SDD): The Definitive 2026 Guide — BCMS](https://www.thebcms.com/blog/spec-driven-development/)
- [Agentic Software Development Takes The Lead — Forrester](https://www.forrester.com/blogs/agentic-software-development-takes-the-lead-from-code-assistants-to-orchestrated-sdlc-agents/)
- [The New SDLC: From Vibe Coding to Agentic Engineering — workingsoftware.dev](https://www.workingsoftware.dev/the-new-software-development-lifecycle-sdlc-from-vibe-coding-to-agentic-engineering/)
- [From Prompt to Process: a Process Taxonomy of Frameworks Supporting AI Software Development Agents — arXiv 2606.04967](https://arxiv.org/pdf/2606.04967)
- [The Productivity-Reliability Paradox: Specification-Driven Governance — arXiv 2605.01160](https://arxiv.org/pdf/2605.01160)
- [BMAD vs Spec Kit vs OpenSpec — Reenbit](https://medium.com/@reenbit/bmad-vs-spec-kit-vs-openspec-choosing-your-spec-driven-ai-framework-in-2026-a6996b3ebb8d)
- [9 Best AI Tools for Spec-Driven Development in 2026 — MarkTechPost](https://www.marktechpost.com/2026/05/08/9-best-ai-tools-for-spec-driven-development-in-2026-kiro-bmad-gsd-and-more-compare/)
- [Spec-Driven Development: A Spec-First Approach to AI-Native Engineering — Microsoft](https://developer.microsoft.com/blog/spec-driven-development-ai-native-engineering/)
- [An AI-led SDLC with Azure and GitHub — Microsoft Community Hub](https://techcommunity.microsoft.com/blog/appsonazureblog/an-ai-led-sdlc-building-an-end-to-end-agentic-software-development-lifecycle-wit/4491896)
- [2026 AI Specification Frameworks Compared — BSWEN](https://docs.bswen.com/blog/2026-08-07-ai-spec-frameworks-compared/)

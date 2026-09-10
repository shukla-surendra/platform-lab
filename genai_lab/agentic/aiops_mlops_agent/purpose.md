# Purpose

## What this project is

A reference implementation of one coherent, production-shaped agent architecture, applied to a
realistic MLOps/AIOps incident-response use case. It exists to answer a specific question by
demonstration rather than by slideware: **what does it actually take to wire an LLM agent to
real tools and real grounding, safely, and to run the result somewhere other than a laptop
terminal?**

Three things are combined deliberately, because they're usually shown separately and the seams
between them are where most of the real engineering effort actually lives:

1. **An agentic control flow** (LangGraph) that routes three different incident domains through
   one pipeline instead of three bespoke scripts.
2. **Tool access via MCP** instead of in-process function calls — the agent's tools are a real,
   independently addressable service boundary, not Python functions imported into the same
   process.
3. **Grounding via RAG** — the agent's diagnoses cite specific runbooks and postmortems rather
   than reasoning from the model's parametric knowledge alone, and that grounding is retrieved
   through the same MCP mechanism as everything else, not bolted on separately.

## What it's for

**Primarily educational / reference-grade**, not a product to deploy against real infrastructure
as-is. It's meant to be read, run, broken, and extended — every file has enough in its docstring
or the README to explain *why* it's shaped the way it is, not just what it does. If you're
building something similar and want to see the decisions worked all the way through (dry-run
safety gates, structured-output failure handling, stdio-vs-network MCP transports, a knowledge
base an agent actually uses instead of ignoring), this project is meant to be that worked
example.

It is explicitly **not**:
- A real MLOps/AIOps platform. Nothing here talks to a real model registry, a real Prometheus, or
  a real CI system — `state.py`'s JSON file is the entire mock world, on purpose, so the focus
  stays on the agent architecture rather than on integration plumbing for any one vendor's API.
- Hardened for production traffic. The Docker Compose setup simulates a multi-service production
  *topology* (real network boundaries, a fixed server-side safety gate, independent containers)
  so the architectural seams are real — but there's no auth between services, no TLS, no
  multi-tenancy, and no load testing behind any of it.

## Why these specific design choices

- **Three domains, one graph, not three agents.** A model-drift incident, a host running hot, and
  a failed pipeline are different problems, but "gather context, ground it in institutional
  knowledge, diagnose, decide, act carefully, record" is the same shape every time. Routing three
  domains through one pipeline (rather than three separate agents) is the more honest
  demonstration of what actually varies (the tools and the knowledge base) versus what doesn't
  (the control flow).
- **Dry-run by default, everywhere.** Every mutating tool describes what it would do until
  explicitly told to act. This isn't a hedge against the demo breaking — it's the same posture a
  real on-call automation should default to, and the project treats "safe to run and see what an
  agent *would* do" as a first-class mode, not an afterthought flag.
- **Local-first, cloud-optional.** Ollama by default means the whole thing runs with no API key
  and no cost to try. Claude is a one-line config swap (`LLM_PROVIDER=claude`), not a rewrite —
  because the interesting parts of this project (the graph, the tools, the retrieval) shouldn't
  be coupled to which model is answering.
- **Reliability notes are part of the deliverable, not an appendix.** Local models occasionally
  fail structured output; MCP subprocess spawning has real per-call overhead; a runbook can be
  genuinely ambiguous and produce different-but-defensible decisions on different runs. The
  README documents these with real captured evidence, not hypotheticals, because pretending an
  agent never misbehaves is a worse teaching tool than showing what handling that actually looks
  like.

## Agent vs. rule-based pipeline: what's actually different

It's fair to ask whether any of this needed an LLM at all. `pl-daily-etl`, `pl-feature-refresh`,
and `pl-model-retrain` are the kind of thing a monitoring script has handled for years: read a
metric, compare it to a threshold, run the matching branch. `databricks_autopilot_agent`-style
rule dispatch (`if category == "oom": resize_cluster()`) is cheaper, faster, fully deterministic,
and has zero hallucination risk. None of that is a strawman — it's the right tool for a large
fraction of real on-call automation, and this project's own `decide_node` and `act_node` are
*themselves* plain deterministic Python, not LLM calls, for exactly that reason (see `graph.py`'s
docstring: "there's no reason to spend a model call deciding that too"). The question this
project actually answers isn't "agent good, rules bad" — it's **which specific part of the
problem is a rules engine bad at, and where exactly does that boundary sit in this codebase.**

**A rule engine encodes decisions as pre-enumerated cases.** Every branch it can take had to occur
to an engineer, in advance, in enough detail to write as an `if`. That works cleanly right up
until reality produces a combination nobody wrote a branch for — and then a rule engine doesn't
reason about the gap, it just falls through to `else` (usually "do nothing" or "alert generically"),
silently. It can't get *more* right the more context you hand it, because the mapping from context
to action is fixed at code-review time, not at run time.

**Where this project actually needed something else** — three concrete cases already captured
with real output in the README, not hypotheticals:

- **`knowledge_base/postmortems/postmortem_checkout_api_oom_2026_02.md` holds two true rules in
  tension**: "single host degraded, siblings healthy → just restart it" and "a traffic-driven
  spike hits every host on a service at once, even if only one has crossed the alert threshold
  first → don't restart, you'll cascade." A rule engine needs a human to pre-decide, for every
  possible combination of symptoms, which rule wins — and to encode that tie-break as more rules.
  The agent, given both passages and the live signal (`running_count: 1` against
  `desired_count: 3`, one sibling genuinely healthy), synthesized a specific, checkable judgment:
  escalate rather than restart, citing the cascade risk, even though the literal data showed only
  one host down. That's not "smarter than a rule" in the abstract — it's a real decision boundary
  where writing the rule *in advance* would have required anticipating this exact ambiguity.
- **`knowledge_base/pipeline_docs/schema_drift_playbook.md` explicitly says no automated action in
  this toolset resolves a schema-drift failure** — the correct behavior is to stop and hand it to
  a human with the specific column diff, not to retry or roll back. A rule engine can absolutely
  encode "if category == schema_drift: escalate" once someone has written that rule. What it can't
  do is *arrive* at "this needs a human" for a failure mode nobody pre-classified — the agent's
  `escalate: bool` output is a judgment made from reading the situation against the knowledge
  base's guidance, not a lookup against a pre-built table of failure categories.
- **The fraud-detection drift postmortem exists because a stale feature pipeline masqueraded as
  model drift** (see the postmortem in this same directory). Encoding "check the feature pipeline
  before blaming drift" as a rule is easy *after* you've had the incident and written the
  postmortem. What's harder for a rules engine: that lesson living as one new markdown file in
  `knowledge_base/`, picked up by every future `model_drift` diagnosis the moment
  `rag/ingest.py` re-runs — no code change, no redeploy, no engineer translating prose into a new
  `if` branch. The institutional knowledge and the decision logic are the same artifact here.

**What this costs, honestly** — the reason this project isn't "just use an agent for everything":
non-determinism (the README's Reliability notes section documents the *same* scenario getting
different, both-defensible recommendations on separate runs), real latency and compute cost per
decision, and a whole safety apparatus (dry-run gates, confidence thresholds, structured-output
fallbacks, audit logs) that exists specifically because "the model synthesized a judgment" is a
fundamentally less checkable claim than "rule 47 fired." A rule engine's worst failure mode is
*missing* a case it was never taught; an agent's worst failure mode is *confidently* handling a
case it was never taught, correctly-shaped output and all. That asymmetry is exactly why every
mutating action in this project is dry-run by default rather than trusted on the model's say-so.

**The actual dividing line**, and the one this project tries to draw honestly rather than
gesture at: deterministic branches for anything enumerable ahead of time (`decide_node`,
`act_node`, the domain routing in `gather_context_node` — all plain Python, zero LLM calls); an
LLM call only where the input space is genuinely open-ended and the right answer depends on
weighing prose guidance against live, messy context (`classify_node` on free text, `diagnose_node`
synthesizing root cause and action from context + retrieved knowledge). Everything in this
project that *could* be a rule, is one. The two LLM calls exist because "is this the case the
postmortem was warning about, or not" isn't a lookup — it's the one piece of the job an
if/else was never actually going to do well.

## Who this is for

Someone who already knows roughly what an LLM agent is and wants to see: a multi-domain LangGraph
pipeline that isn't a toy chatbot loop, MCP used as a real service boundary (including what
changes when you move it from stdio to a network transport), a RAG knowledge base an agent
demonstrably uses rather than decorates its output with, and a Docker Compose topology that makes
the "who owns the safety gate" question concrete instead of theoretical.

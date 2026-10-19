# 0. Agentic Concepts

Before writing any LangGraph code, it's worth being precise about what "agent" means — the word gets used
for everything from a single tool-calling LLM call to a fleet of cooperating specialists. This chapter is
framework-agnostic: the vocabulary here applies whether you build with LangGraph, a hand-rolled loop (like
this repo's `personal_assistant_demo.py`), or another SDK entirely. Later chapters ground each concept in
runnable code.

## What makes something an "agent"

A single LLM call that reads a prompt and returns text is not an agent — it's a function. Something becomes
agentic when it gains a **loop**: the ability to take an action, observe the result, and decide what to do
next *without a human choosing each step*.

```
perceive  →  reason  →  act  →  observe  →  (back to reason)
```

- **Perceive** — read the current state: the user's request, prior tool results, conversation history.
- **Reason** — decide what to do next (answer now? call a tool? ask a specialist?).
- **Act** — execute that decision: call a tool, call another agent, or produce a final answer.
- **Observe** — fold the result of that action back into state and loop.

The loop terminates when the reasoning step decides it has enough information to produce a final answer
(or when a safety limit — see [Guardrails](#guardrails-and-control) below — cuts it off). This is exactly
the **ReAct** pattern covered in depth in [Chapter 4](04-tools-and-agents.md).

## The building blocks

Every agentic system is some combination of five ingredients. This repo has a working example of each.

| Building block | What it does | Where in this repo |
|---|---|---|
| **Model** | Does the reasoning — decides actions from context | the Ollama call in `personal_assistant_demo.py`; any `llm` in the LangGraph chapters |
| **Tools** | Give the model ways to affect or query the world beyond text generation | `task_store.py` functions; `tasks_mcp_server.py` (Chapter 11) |
| **Memory** | Carries state across steps and across separate runs | `AgentState` (in-run); checkpointers (cross-run) — [Chapter 5](05-memory-and-persistence.md) |
| **Orchestration** | Decides *which* step runs next — routing, planning, delegation | `router` / `planner_agent` — [Chapter 3](03-conditional-routing.md), [Chapter 6](06-multi-agent-systems.md) |
| **Guardrails** | Bounds what the loop is allowed to do, and for how long | step caps, recursion limits — see below and [Chapter 10](10-best-practices.md) |

## Workflows vs. agents: a spectrum, not a binary

"Agentic" is a spectrum of how much control you hand to the model. This repo actually contains three points
on that spectrum:

| Pattern | Who decides the next step | Example in this repo |
|---|---|---|
| **Fixed pipeline** | The developer, at build time — the graph shape *is* the logic | `say_hello` in [Chapter 1](01-getting-started.md) |
| **Workflow (planner + router)** | The developer's code, at run time, from a rule-based plan | `planner_agent` → queue → `router` in `langgraph_agents_demo.py` ([Chapter 6](06-multi-agent-systems.md)) |
| **Agent (model-directed loop)** | The model itself, one decision at a time, based on tool results | The JSON tool-call loop in `personal_assistant_demo.py`; `create_react_agent` ([Chapter 4](04-tools-and-agents.md)) |

Neither end is "better" — it's a trade-off. Fixed pipelines and workflows are cheap, fast, and fully
testable, but only handle the cases you anticipated. Model-directed agents generalize to novel requests but
cost more, are slower, and are harder to make fully predictable. A well-designed system usually mixes
levels: this repo's `planner_agent` uses code-level routing to dispatch to specialists, any one of which
could internally be a full ReAct loop. [Chapter 6](06-multi-agent-systems.md) covers exactly that
composition.

## Guardrails and control

The same loop structure that makes agents powerful also makes them capable of running forever, calling the
wrong tool, or burning tokens on a task that should have stopped. Every production agent needs explicit
bounds:

- **Step/iteration limits** — `personal_assistant_demo.py`'s `run_assistant` caps itself at 6 loop
  iterations before giving up; LangGraph enforces a `recursion_limit` for the same reason.
- **Tool allow-lists** — an agent should only ever be offered the specific tools it needs for its role, not
  every tool available in the process (`TOOLS` in `personal_assistant_demo.py` is a closed, explicit set).
- **Input/argument validation** — never trust a model's tool arguments blindly; validate them the same way
  you'd validate user input, since from the tool's perspective that's exactly what they are.
- **Human-in-the-loop checkpoints** — for high-stakes actions, pause the loop and require approval before
  the "act" step executes. Covered with LangGraph's `interrupt` in
  [Chapter 5](05-memory-and-persistence.md).

## Interoperability: agents need to reach tools that outlive them

So far, "tools" have meant Python functions living in the same process as the agent. That works for a demo,
but breaks down once you want the *same* tool (say, this repo's task manager) usable from multiple agents,
or from a different host entirely (a chat UI, another team's agent, an IDE assistant). The **Model Context
Protocol (MCP)** exists to solve exactly that: a standard way for an agent to discover and call tools that
live in a separate process or server. This repo already ships an MCP server (`tasks_mcp_server.py`) —
[Chapter 11](11-mcp-agentic-capabilities.md) covers it in depth.

## How this tutorial maps to these concepts

| Concept | Chapter |
|---|---|
| The core loop, state, single agent | [1](01-getting-started.md)–[2](02-core-concepts.md) |
| Orchestration (routing) | [3](03-conditional-routing.md) |
| Tools, ReAct | [4](04-tools-and-agents.md) |
| Memory | [5](05-memory-and-persistence.md) |
| Multi-agent orchestration | [6](06-multi-agent-systems.md) |
| Observability of the loop | [7](07-streaming.md) |
| Guardrails, resilience | [8](08-advanced-patterns.md) |
| Shipping an agent | [9](09-deployment.md), [10](10-best-practices.md) |
| Interoperability (MCP) | [11](11-mcp-agentic-capabilities.md) |
| All of the above, combined | [12](12-real-world-example.md) |

Next: [Chapter 1 — Getting Started](01-getting-started.md).

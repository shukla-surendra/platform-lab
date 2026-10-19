# Agentic Development Tutorial: Beginner to Advanced

Welcome! This is a self-contained, beginner-to-advanced tutorial on building AI agents — covering the
underlying agentic concepts, [LangGraph](https://langchain-ai.github.io/langgraph/) (the graph-based
framework for building stateful, multi-step LLM applications), the
[Model Context Protocol](https://modelcontextprotocol.io) (MCP) for exposing tools across agents, and how it
all comes together in a real, deployable example.

It is written against the code in this repository — in particular `langgraph_agents_demo.py`
(planner → researcher/calculator → writer), `personal_assistant_demo.py` (a hand-rolled agent loop), and
`tasks_mcp_server.py` (an MCP server) — so every concept has a working example you can actually run.

## Who this is for

You should know basic Python and have used an LLM API before (OpenAI, Anthropic, Ollama, etc.). No prior
LangGraph or LangChain experience is assumed.

## How the tutorial is organized

The chapters build on each other. Each one introduces one or two new ideas and ends with a small runnable
example.

| # | Chapter | You'll learn |
|---|---------|---------------|
| 0 | [Agentic Concepts](00-agentic-concepts.md) | What makes something an "agent," the core loop, building blocks, guardrails — framework-agnostic |
| 1 | [Getting Started](01-getting-started.md) | Install LangGraph, build and run your first graph |
| 2 | [Core Concepts](02-core-concepts.md) | `State`, nodes, edges, reducers, `StateGraph`, compiling |
| 3 | [Conditional Routing](03-conditional-routing.md) | Branching logic, routers, loops — the "planner" pattern |
| 4 | [Tools & Agents](04-tools-and-agents.md) | Tool calling, `ToolNode`, the ReAct loop, `create_react_agent` |
| 5 | [Memory & Persistence](05-memory-and-persistence.md) | Checkpointers, threads, time travel, human-in-the-loop |
| 6 | [Multi-Agent Systems](06-multi-agent-systems.md) | Supervisor pattern, subgraphs, the repo's planner/researcher/calculator/writer graph |
| 7 | [Streaming](07-streaming.md) | Streaming state updates, LLM tokens, and custom events |
| 8 | [Advanced Patterns](08-advanced-patterns.md) | Fan-out/fan-in, custom reducers, retries, error handling |
| 9 | [Deployment](09-deployment.md) | Packaging a graph as a service, and deploying it with Bedrock AgentCore |
| 10 | [Best Practices](10-best-practices.md) | Testing, debugging, project structure, LangGraph Studio |
| 11 | [Model Context Protocol (MCP)](11-mcp-agentic-capabilities.md) | What MCP is, this repo's MCP server, consuming MCP tools from a LangGraph agent |
| 12 | [Real-World Example](12-real-world-example.md) | Combining agentic concepts, LangGraph, and MCP into one deployable personal assistant |

## Prerequisites for running the examples

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` in this repo already pins `langgraph`. Some tutorial snippets also use `langchain-openai`
or `langgraph-checkpoint-sqlite` — install those only if you want to run that specific snippet locally.

## Quick orientation: what is LangGraph?

LangGraph models an application as a **graph**:

- **State** — a shared, typed object that flows through the graph and gets updated as it goes.
- **Nodes** — plain Python functions (or callables) that receive the state and return a partial update.
- **Edges** — the connections between nodes, including conditional ("if/else") edges that pick the next
  node at runtime.

Compiling the graph produces a runnable object with the same interface as any LangChain `Runnable`:
`.invoke()`, `.stream()`, `.ainvoke()`, `.astream()`.

Ready? Start with [Chapter 0 — Agentic Concepts](00-agentic-concepts.md), or jump straight to
[Chapter 1 — Getting Started](01-getting-started.md) if you just want to write LangGraph code.

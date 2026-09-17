# 3. Agent Framework & Agent Bricks

Two sibling products answer "build an AI agent on Databricks" — not one replacing the other.
They solve different problems, not competing versions of the same one, and mixing them up is a
common source of confusion when reading Databricks material.

## Agent Framework — code-first

Author agents in Python, in whatever library you already know — LangGraph, LangChain, the OpenAI
SDK, and LlamaIndex are all explicitly supported, not just tolerated. Deploy via Databricks Apps,
or register as an "Agent Service" in Unity Catalog so other teams/systems can discover and govern
it the same way they'd discover a table or a model.

**Source:** [Use agents on Databricks](https://docs.databricks.com/aws/en/agents/agent-framework/build-agents).

This is the "give me full control of the tool-calling loop" path — the one to reach for when a
requirement doesn't fit inside a no-code product, e.g. non-SQL side effects, custom retry/approval
logic, or a graph shape (see [`Agentic_Concepts/06-multi-agent-systems.md`](../Agentic_Concepts/06-multi-agent-systems.md)
in this repo) that a low-code product can't express.

### Unity Catalog Functions as agent tools

The Databricks-native way to give a code-first agent a tool: write a SQL or Python function,
register it in Unity Catalog, and it inherits UC's governance (who can call it, audit logging)
automatically — same access-control story as a table.

Current recommended wiring is **MCP**, not direct SDK calls: Databricks exposes a managed MCP URL
per catalog/schema —

```
https://<workspace-hostname>/api/2.0/mcp/functions/{catalog}/{schema}
```

— which gives automatic tool discovery and built-in auth, instead of you hand-writing a tool
schema for every UC function. This repo's own [`fastmcp_auth_tools/`](../../fastmcp_auth_tools)
and [`official_mcp_tools/`](../../official_mcp_tools) projects, and [Agentic_Concepts Chapter
11](../Agentic_Concepts/11-mcp-agentic-capabilities.md), cover the MCP mechanics this endpoint
relies on — Databricks didn't invent a new protocol here, it exposed UC functions through the same
MCP shape you already know.

**Source:** [Create agent tools using Unity Catalog functions](https://docs.databricks.com/aws/en/agents/custom-agents/create-custom-tool),
[Integrate Unity Catalog tools with third-party frameworks](https://docs.databricks.com/aws/en/agents/agent-framework/unity-catalog-tool-integration).

## Agent Bricks — low-code

Pre-built, named building blocks for agents that don't require you to write the tool-calling loop
yourself:

- **Knowledge Assistant** — RAG/doc Q&A over your own documents (Chapter 4)
- **Custom Agents** — configurable agent behavior without a full code-first build
- **Intelligent Document Processing (IDP)** — parsing + classification + extraction pipeline
  (Chapter 4)
- **Supervisor Agent** — multi-agent orchestrator (below)

Databricks' own DAIS 2026 numbers for scale/momentum: 100k+ agents built, "1+ quadrillion
tokens/year" processed through Agent Bricks.

**Source:** [Agent Bricks: DAIS 2026](https://www.databricks.com/blog/agent-bricks-dais-2026),
[Agent Bricks product page](https://www.databricks.com/product/artificial-intelligence/agent-bricks).

## Supervisor Agent — the multi-agent orchestrator

This is the piece that ties Chapters 1, 3, and 4 together into one system rather than three
disconnected products. The Supervisor Agent explicitly orchestrates:

- Genie Agents (Chapter 1)
- Agent endpoints
- Unity Catalog functions
- MCP servers
- Custom agents

In practice: a Supervisor Agent is how you'd architect "one assistant that can answer a business
question over structured data (delegate to a Genie Agent), answer a question over a PDF policy
document (delegate to a Knowledge Assistant), and take an action (call a UC function)" — without
hand-rolling routing logic across three unrelated systems. This is the same supervisor pattern
covered generically in [`Agentic_Concepts/06-multi-agent-systems.md`](../Agentic_Concepts/06-multi-agent-systems.md);
Databricks' version is that pattern with Genie Agents and UC Functions as first-class node types.

**Source:** [Build agents on Databricks](https://docs.databricks.com/aws/en/agents/agent-framework/build-agents).

## Unity AI Gateway — the control plane underneath both

Whichever path you build with, traffic to models flows through **Unity AI Gateway** (renamed from
"Mosaic AI Gateway" in current material — both names still appear): a single control plane for
model access, cost governance, and runtime guardrails — PII exposure, prompt injection, jailbreak
attempts, unsafe content. Covered fully in Chapter 6 as part of the MLOps/governance story.

**Source:** [AI governance with Unity AI Gateway](https://docs.databricks.com/aws/en/ai-gateway/).

## Framework vs. Bricks — the decision an architect should be able to state crisply

| Signal | Choose |
|---|---|
| Requirement fits a named Agent Bricks block (doc Q&A, extraction, NL2SQL) and speed/governance-by-default matters more than custom control | **Agent Bricks** |
| Need custom tool-calling logic, non-SQL side effects, a specific agent graph shape, or a framework/library your team already standardizes on | **Agent Framework** |
| Need to combine several of the above into one assistant | **Supervisor Agent**, orchestrating whichever mix of Genie Agents / Bricks / Framework agents / UC functions the sub-tasks need |

This mirrors the same "when to use which" call as Chapter 7's NL2SQL walkthrough — it's the general
form of that specific decision.

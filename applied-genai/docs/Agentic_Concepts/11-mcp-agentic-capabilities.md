# 11. Model Context Protocol (MCP)

Every tool up to this point (`get_weather`, `calculator_agent`, `task_store.py`'s functions) has been a
plain Python function living in the same process as the agent that calls it. That's simple, but it means
the tool only exists for that one agent, in that one codebase. The **Model Context Protocol (MCP)** — an
open, JSON-RPC-based protocol — standardizes how an agent (the "client" or "host") discovers and calls
tools that live in a separate **server** process, so the same tool implementation can serve any number of
agents, chat UIs, or IDEs without being rewritten for each one. See
[modelcontextprotocol.io](https://modelcontextprotocol.io) for the full specification.

This repo ships a real MCP server, `tasks_mcp_server.py`, exposing the same task-management operations used
throughout this tutorial. This chapter walks through it, then shows how to consume it from a LangGraph
agent.

## The three things an MCP server can expose

| Primitive | What it is | Analogy |
|---|---|---|
| **Tools** | Callable actions with typed arguments — what most people mean by "MCP" | A `@tool`-decorated function ([Chapter 4](04-tools-and-agents.md)) |
| **Resources** | Read-only data the client can fetch for context | A file the agent can read, without calling a "read" tool |
| **Prompts** | Reusable, server-defined prompt templates | A shared prompt library, versioned outside the agent's own code |

`tasks_mcp_server.py` only implements tools, which covers the majority of real MCP servers you'll write.

## Walkthrough: `tasks_mcp_server.py`

```python
from mcp.server.fastmcp import FastMCP
from task_store import add_task, complete_task, list_tasks

mcp = FastMCP("local-tasks")


@mcp.tool()
def mcp_list_tasks() -> str:
    """Return all tasks and their completion state."""
    return list_tasks()


@mcp.tool()
def mcp_add_task(title: str) -> str:
    """Add a new task by title."""
    return add_task(title)


@mcp.tool()
def mcp_complete_task(task_id: int) -> str:
    """Mark a task as complete by id."""
    return complete_task(task_id)


if __name__ == "__main__":
    mcp.run()
```

A few things to notice:

- **`FastMCP`** is the high-level server SDK — it handles protocol plumbing (handshake, capability
  negotiation, JSON-RPC framing) so you only write plain Python functions.
- **`@mcp.tool()`** is the MCP equivalent of LangChain's `@tool` decorator from
  [Chapter 4](04-tools-and-agents.md): it derives the tool's JSON schema from the function's type hints, and
  its description from the docstring — the same "write the docstring for the model" rule applies.
- **The server has no idea who's calling it.** `mcp_add_task` delegates straight to `task_store.py`, the
  same plain data layer used by `personal_assistant_demo.py`. The server is a thin protocol adapter around
  logic that doesn't know or care that MCP exists — a good pattern to copy for your own tools.
- **`mcp.run()`** defaults to the **stdio transport**: the client launches the server as a subprocess and
  talks to it over stdin/stdout. MCP also supports an HTTP-based transport for servers that run
  independently and serve multiple clients over the network — reach for that once a server needs to run
  as a standalone, always-on service rather than being spawned per-agent.

## Running and inspecting the server

```bash
python tasks_mcp_server.py
```

On its own, this just starts the server and blocks, waiting for a client to speak MCP over stdio — there's
nothing to see interactively. To poke at it by hand, use the official **MCP Inspector**, a browser-based
debugging UI that speaks MCP for you:

```bash
npx @modelcontextprotocol/inspector python tasks_mcp_server.py
```

This launches a local web UI where you can list the server's tools, call `mcp_add_task` with a test title,
and see the raw JSON-RPC exchange — invaluable for verifying a server works *before* wiring an LLM in front
of it.

## Consuming MCP tools from a LangGraph agent

The point of MCP is that any client can use this server, not just a hand-rolled loop. The
[`langchain-mcp-adapters`](https://github.com/langchain-ai/langchain-mcp-adapters) package converts an MCP
server's tools into LangChain `Tool` objects, so they drop straight into
[Chapter 4](04-tools-and-agents.md)'s `create_react_agent`:

```python
# pip install langchain-mcp-adapters
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

client = MultiServerMCPClient(
    {
        "tasks": {
            "command": "python",
            "args": ["tasks_mcp_server.py"],
            "transport": "stdio",
        }
    }
)
tools = await client.get_tools()  # [mcp_list_tasks, mcp_add_task, mcp_complete_task] as LangChain tools

app = create_react_agent(llm, tools)
result = await app.ainvoke(
    {"messages": [("user", "Add a task to review the MCP chapter, then show my tasks.")]}
)
```

Everything from [Chapter 4](04-tools-and-agents.md) — `ToolNode`, `should_continue`, the ReAct loop — works
unmodified. The only difference from a locally-defined `@tool` is *where the function executes*: in a
separate process, reached over the MCP protocol, instead of inline in your graph.

## Where this fits in `personal_assistant_demo.py`

Today, `personal_assistant_demo.py` calls `task_store.py` functions directly — it doesn't go through
`tasks_mcp_server.py` at all, even though both exist in this repo. That's intentional for a minimal demo,
but it's worth naming the gap: converting the demo to call its tools through the MCP client shown above
(instead of the in-process `TOOLS` dict) is exactly the kind of protocol boundary that lets you later swap
in a *different* agent, or expose the *same* task tools to Claude Desktop or another MCP host, with zero
changes to `tasks_mcp_server.py` itself. [Chapter 12](12-real-world-example.md) builds that version.

## Direct call vs. in-process tool vs. MCP tool

| | Direct function call | `@tool` (Chapter 4) | MCP tool (this chapter) |
|---|---|---|---|
| Runs in | Same process | Same process | Separate process (or host) |
| Discoverable by other agents | No | No | Yes — any MCP client |
| Protocol overhead | None | None | JSON-RPC over stdio/HTTP |
| Best for | Internal helpers | Tools specific to one graph | Tools you want to reuse or expose beyond one codebase |

## Security note

An MCP server is a new trust boundary, not a free pass around one. `mcp_add_task` still receives arguments
chosen by an LLM, exactly like any tool in [Chapter 4](04-tools-and-agents.md) — validate and sanitize them
the same way you would for a directly-called tool. Because a server can be reused by any client that can
reach it, also be deliberate about *what* you expose: a tool that can execute arbitrary shell commands or
delete files is far riskier once it's reachable by every agent that speaks MCP, not just the one you wrote
it for.

Next: [Chapter 12 — Real-World Example](12-real-world-example.md).

# 10. Best Practices

## Test nodes as plain functions

Every node is `(state) -> partial_update`, so unit test them exactly like any other Python function — no
graph, no LLM, no mocking framework required:

```python
from langgraph_agents_demo import calculator_agent


def test_calculator_agent_evaluates_expression():
    state = {
        "question": "What is 17 * 9?",
        "remaining_agents": ["calculator"],
        "notes": [],
    }
    result = calculator_agent(state)
    assert result["math_result"] == "17 * 9 = 153"
```

Reserve full-graph `.invoke()` tests for a smaller number of end-to-end cases; push edge cases (empty
input, malformed expressions, unusual routing) down to node-level unit tests where they're cheap and fast.

## Keep routing logic pure and typed

Router functions (`(state) -> str`) should be pure — no side effects, no I/O — and their return type should
be a `Literal[...]` of every possible destination, as in `router` in `langgraph_agents_demo.py`:

```python
def router(state: AgentState) -> Literal["researcher", "calculator", "writer"]:
    ...
```

This lets your type checker catch a typo'd node name or a missing case before you ever run the graph.

## Separate deterministic logic from LLM calls

The clearest lesson from this repo's structure: `planner_agent`, `calculator_agent`, and the `router` are
all deterministic Python with zero LLM calls. Only reach for an LLM node where judgment is genuinely
required. Deterministic nodes are faster, free, fully testable, and don't need prompt engineering — prefer
them whenever the task allows.

## Debugging a graph

- **`app.get_graph().draw_mermaid()`** — confirm the graph is wired the way you think before debugging
  runtime behavior.
- **`stream_mode="updates"`** (see [Chapter 7](07-streaming.md)) — watch exactly which node ran and what it
  changed, one step at a time, instead of guessing from the final state.
- **`app.get_state_history(config)`** (requires a checkpointer, see [Chapter 5](05-memory-and-persistence.md))
  — replay exactly what happened on a specific run, including intermediate states you didn't explicitly log.
- **LangGraph Studio** — a visual debugger (part of the LangGraph Platform tooling) that lets you step
  through a running graph node by node, inspect state at each step, and edit-and-resume from any point. Most
  valuable once your graph has enough branches that reasoning about it from logs alone gets tedious.

## Project structure

For a small demo like this repo, one module per concern works well:

```
langgraph_agents_demo.py   # graph definition + nodes + run_demo() entrypoint
agentcore_app.py           # deployment glue (Chapter 9), imports run_demo
task_store.py              # plain data layer, no LangGraph/LLM dependency
```

As a project grows, the natural split is:

- `state.py` — `TypedDict`/`Pydantic` state schemas and reducers
- `nodes/` — one module per node or logical group of nodes
- `graph.py` — `build_graph()`, wiring only, no business logic
- `tools.py` — `@tool`-decorated functions, kept independent of any specific graph

Keeping node logic free of LangGraph imports where possible (plain functions that happen to match the
`(state) -> dict` signature) makes them trivially reusable outside the graph and easier to unit test.

## Common mistakes

- **Mutating state in place instead of returning an update.** Nodes should return a new dict; don't do
  `state["notes"].append(...)` and then `return state` — it can silently break checkpointing and reducer
  semantics. Prefer `return {"notes": [*state["notes"], new_note]}` (or better, use a reducer, see
  [Chapter 2](02-core-concepts.md#reducers-how-state-updates-merge)).
- **Forgetting a `path_map` / `Literal` case in a conditional edge**, causing a runtime error only on the
  input that hits the missing branch — see [Chapter 3](03-conditional-routing.md#common-pitfall-forgetting-a-path).
- **No recursion limit awareness in loops** — a router-driven loop or ReAct tool loop with a broken exit
  condition will hit `GraphRecursionError` in production if you never exercised the "never finishes" case in
  tests.
- **Reaching for an LLM node where plain code would do** — slower, costs money, and is harder to test than
  the deterministic alternative.

## Where to go from here

- Convert `personal_assistant_demo.py`'s hand-rolled Ollama tool loop into a proper `StateGraph` using
  [Chapter 4](04-tools-and-agents.md)'s `ToolNode` pattern, and add persistence with
  [Chapter 5](05-memory-and-persistence.md) so conversations survive across CLI invocations.
- Turn `planner_agent`'s regex-based routing decision into an LLM call using
  [Chapter 6](06-multi-agent-systems.md)'s supervisor pattern, and compare reliability/cost against the
  deterministic version.
- Add a `RetryPolicy` (Chapter 8) around any node that calls an external API.

That's the full tour of LangGraph itself — from a two-line `StateGraph` in Chapter 1 to a deployed,
multi-agent, persistent graph. Two chapters remain: exposing tools over a standard protocol, and combining
everything into one deployable system.

Next: [Chapter 11 — Model Context Protocol (MCP)](11-mcp-agentic-capabilities.md).

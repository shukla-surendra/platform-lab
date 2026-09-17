# 4. Tools & Agents

So far our nodes have been deterministic Python (regex, arithmetic). The next step is letting an LLM decide
what to do — including which tools to call — which is what most people mean by "agent."

## Anatomy of a tool-calling agent

The classic loop (often called **ReAct**) is:

1. Call the LLM with the conversation so far and a list of available tools.
2. If the LLM's response includes tool calls, execute them and append the results as `ToolMessage`s.
3. Go back to step 1.
4. If the LLM responds with plain text (no tool calls), stop and return it.

In LangGraph terms, that's a two-node graph with a conditional edge:

```python
from typing import Annotated
from langchain_core.messages import AnyMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


@tool
def get_weather(city: str) -> str:
    """Return a short weather report for a city."""
    return f"It's sunny in {city}."


tools = [get_weather]
llm_with_tools = llm.bind_tools(tools)


def call_model(state: State) -> State:
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def should_continue(state: State) -> str:
    last = state["messages"][-1]
    return "tools" if last.tool_calls else END


graph = StateGraph(State)
graph.add_node("agent", call_model)
graph.add_node("tools", ToolNode(tools))

graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
graph.add_edge("tools", "agent")

app = graph.compile()
```

Key pieces:

- **`llm.bind_tools(tools)`** tells the chat model which tools it may call and lets it emit structured
  `tool_calls` on its `AIMessage`.
- **`ToolNode(tools)`** is a prebuilt node that reads the last message's `tool_calls`, executes the matching
  Python functions, and returns the results as `ToolMessage`s — no manual dispatch loop required.
- **`should_continue`** is the conditional edge that ends the loop once the model stops calling tools.
- **The `tools -> agent` edge** sends control back to the model so it can read the tool results and decide
  what to do next (call another tool, or answer).

## The shortcut: `create_react_agent`

For the common case above, LangGraph ships a prebuilt constructor so you don't have to wire it by hand:

```python
from langgraph.prebuilt import create_react_agent

app = create_react_agent(llm, tools)
result = app.invoke({"messages": [("user", "What's the weather in Paris?")]})
```

`create_react_agent` builds exactly the `agent` / `tools` graph shown above (plus some extra plumbing for
system prompts, structured output, and pre/post-model hooks). Reach for the hand-built version when you
need custom control flow — e.g. validating a tool call before executing it, or the routing patterns from
[Chapter 3](03-conditional-routing.md).

## Tools without an LLM: the pattern this repo uses

Not every "tool" needs an LLM to invoke it. `langgraph_agents_demo.py`'s `calculator_agent` node *is* a
tool in spirit — it parses the question with `ast`, safely evaluates the arithmetic, and returns a result —
but it's called deterministically by the router rather than chosen by an LLM:

```python
def calculator_agent(state: AgentState) -> AgentState:
    expr = _extract_expression(state["question"])
    ...
    return {**state, "math_result": result, ...}
```

This is a perfectly valid and often *more reliable* pattern: use an LLM only where judgment is required
(the `planner_agent`'s routing decision could itself be swapped for an LLM call), and use plain code for
anything deterministic. Mixing LLM-driven and code-driven nodes in the same graph is normal — see
[Chapter 6](06-multi-agent-systems.md) for the full picture.

`personal_assistant_demo.py` in this repo shows a third style: a hand-rolled tool loop against a local
Ollama model that emits its tool calls as JSON (`{"action":"tool","name":"add_task",...}`) which is then
parsed and dispatched against `task_store.py`. It isn't built with `StateGraph`, but it's the same ReAct
loop conceptually — useful to compare against the `ToolNode` approach above.

## Structured tool definitions

The `@tool` decorator infers a JSON schema from your function's type hints and docstring — the docstring
*is* the tool description the LLM sees, so write it for the model, not for humans skimming the source:

```python
@tool
def add_task(title: str) -> str:
    """Add a new task with the given title and return a confirmation message."""
    ...
```

For tools with more complex arguments, use a Pydantic model as the `args_schema`, or decorate a class with
`langchain_core.tools.StructuredTool.from_function`.

Next: [Chapter 5 — Memory & Persistence](05-memory-and-persistence.md).

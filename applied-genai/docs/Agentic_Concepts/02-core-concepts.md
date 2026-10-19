# 2. Core Concepts

## State

State is the single object that flows through every node in the graph. It's usually a `TypedDict`, but can
also be a `dataclass` or a Pydantic `BaseModel`.

```python
from typing import TypedDict


class AgentState(TypedDict):
    question: str
    notes: list[str]
```

This mirrors `AgentState` in `langgraph_agents_demo.py`:

```python
class AgentState(TypedDict):
    question: str
    remaining_agents: list[str]
    notes: list[str]
    math_result: NotRequired[str]
    final_answer: NotRequired[str]
```

`NotRequired[...]` marks fields that may be absent from the initial state and get added later by a node —
useful when different nodes populate different parts of the state as the graph progresses.

## Nodes

A node is any callable with the signature `(state) -> partial_state_update`. Nodes do **not** return the
full state — they return a dict of the keys they want to change. LangGraph merges that dict into the
existing state for you.

```python
def researcher_agent(state: AgentState) -> AgentState:
    insight = _knowledge_lookup(state["question"])
    return {
        "notes": [*state["notes"], f"Researcher note: {insight}"],
    }
```

Returning only `{"notes": [...]}` here is enough — LangGraph updates just that key and leaves the rest of
the state untouched, *unless* the field has a custom reducer (see below).

## Edges

Edges connect nodes and determine execution order.

- **Normal edge**: `graph.add_edge("a", "b")` — always go from `a` to `b`.
- **Conditional edge**: `graph.add_conditional_edges("a", router_fn)` — call `router_fn(state)` to decide
  the next node dynamically. Covered in depth in [Chapter 3](03-conditional-routing.md).
- **`START`** and **`END`** are sentinel nodes marking the graph's entry and exit points.

## Reducers: how state updates merge

By default, a node's returned value for a key **overwrites** the previous value. Sometimes you want to
**accumulate** instead — for example, appending to a list of chat messages every turn instead of replacing
it. That's what reducers are for.

```python
from typing import Annotated
import operator


class State(TypedDict):
    notes: Annotated[list[str], operator.add]
```

With `Annotated[list[str], operator.add]`, when two nodes each return `{"notes": [...]}`, LangGraph
concatenates the lists instead of the second overwriting the first. This matters a lot once you have
parallel branches writing to the same key (see [fan-out/fan-in](08-advanced-patterns.md#fan-out-fan-in)).

The most common reducer you'll use is `langgraph.graph.message.add_messages`, purpose-built for chat
history:

```python
from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    messages: Annotated[list, add_messages]
```

`add_messages` appends new messages, and — usefully — updates a message in place if it shares an existing
message's `id`, which is how tool-call results get attached to the right `AIMessage`.

!!! tip "MessagesState"
    LangGraph ships a ready-made `MessagesState` (`from langgraph.graph import MessagesState`) that's just
    `{"messages": Annotated[list[AnyMessage], add_messages]}`. Use it instead of hand-rolling the above
    whenever your state is "just a chat".

## Building and compiling a `StateGraph`

```python
from langgraph.graph import StateGraph, START, END

graph = StateGraph(AgentState)

graph.add_node("planner", planner_agent)
graph.add_node("researcher", researcher_agent)

graph.add_edge(START, "planner")
graph.add_edge("planner", "researcher")
graph.add_edge("researcher", END)

app = graph.compile()
```

`compile()` validates the graph (e.g. checks every node is reachable) and returns a `CompiledStateGraph`,
which behaves like any LangChain `Runnable`: `.invoke()`, `.ainvoke()`, `.stream()`, `.astream()`,
`.batch()`.

## Execution model: it's still just Python functions

There's no hidden magic — a compiled graph does a breadth-first-ish traversal starting at `START`, calling
each node's function with the current state, merging the result, and following edges (static or
conditional) until it reaches `END`. Nodes are plain functions, so anything you already know about testing
and debugging Python applies directly — see [Chapter 10](10-best-practices.md) for testing patterns.

Next: [Chapter 3 — Conditional Routing](03-conditional-routing.md).

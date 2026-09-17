# 6. Multi-Agent Systems

A "multi-agent system" is just a graph where more than one node represents an independent area of
responsibility — often with its own prompt, tools, or (as in this repo) its own deterministic logic. This
chapter walks through `langgraph_agents_demo.py` end to end, then covers the two other common multi-agent
topologies: **supervisor** and **subgraphs**.

## Walkthrough: the planner/researcher/calculator/writer graph

### State

```python
class AgentState(TypedDict):
    question: str
    remaining_agents: list[str]
    notes: list[str]
    math_result: NotRequired[str]
    final_answer: NotRequired[str]
```

`remaining_agents` is a work queue, `notes` is a running trace every agent appends to, and `math_result` /
`final_answer` are populated by specific agents later in the run.

### The four nodes

| Node | Responsibility |
|------|-----------------|
| `planner_agent` | Inspects the question, decides which specialists are needed, fills `remaining_agents` |
| `researcher_agent` | Looks up a canned fact relevant to the question, pops itself from the queue |
| `calculator_agent` | Extracts and safely evaluates an arithmetic expression, pops itself from the queue |
| `writer_agent` | Reads `notes` and `math_result`, composes the final answer |

Each specialist agent (`researcher_agent`, `calculator_agent`) follows the same shape: do its job, append a
note describing what it did, and pop itself off `remaining_agents` so the router knows it's finished.

### Wiring

```python
graph = StateGraph(AgentState)
graph.add_node("planner", planner_agent)
graph.add_node("researcher", researcher_agent)
graph.add_node("calculator", calculator_agent)
graph.add_node("writer", writer_agent)

graph.add_edge(START, "planner")
graph.add_conditional_edges("planner", router)
graph.add_conditional_edges("researcher", router)
graph.add_conditional_edges("calculator", router)
graph.add_edge("writer", END)
```

This is the **planner/dispatcher** pattern: one node (`planner`) decides a plan up front (as a queue), and a
shared `router` function drains that queue one node at a time, looping back through itself after each
specialist runs (see [Chapter 3](03-conditional-routing.md) for the routing mechanics). It's a good fit when
the set of steps is decided once, early, and each step is independent of the others' output.

### Why `notes` accumulates without a reducer

Notice `notes` is a plain `list[str]`, not `Annotated[list[str], operator.add]`. Every node still appends
correctly because each node manually spreads the previous notes: `"notes": [*state["notes"], "new note"]`.
This works, but it means every node has to remember to do that spread — a custom reducer (see
[Chapter 2](02-core-concepts.md#reducers-how-state-updates-merge)) would enforce the accumulation
automatically and is the better default for any state you expect to *only* grow. Try refactoring
`AgentState.notes` to use a reducer as an exercise — the individual node bodies get simpler.

## Pattern: supervisor (LLM chooses the next agent)

The repo's example uses code to plan; a common variant lets an LLM act as the planner, choosing the next
worker dynamically instead of building a queue up front:

```python
from typing import Literal


class SupervisorState(MessagesState):
    next: str


def supervisor(state: SupervisorState) -> Command[Literal["researcher", "coder", "__end__"]]:
    response = supervisor_llm.invoke(state["messages"])
    goto = response["next"]  # e.g. structured output: {"next": "researcher"} or {"next": "FINISH"}
    if goto == "FINISH":
        goto = END
    return Command(goto=goto, update={"next": goto})
```

Here each worker node also returns a `Command(goto="supervisor", update={...})` after finishing, handing
control back to the supervisor so it can decide the *next* step based on what just happened — unlike the
repo's fixed queue, the plan can change mid-run based on intermediate results. `Command` lets a node
combine "update state" and "route to this node" in a single return value, which is often cleaner than
separate `add_conditional_edges` calls once routing logic lives inside the node itself rather than a
dedicated router function.

## Pattern: subgraphs (compose graphs like functions)

Once an individual agent gets complex enough to be its own multi-node graph (e.g. a full ReAct loop from
[Chapter 4](04-tools-and-agents.md)), compile it separately and use it as a node in a larger graph:

```python
research_subgraph = build_researcher_graph().compile()

parent = StateGraph(ParentState)
parent.add_node("researcher", research_subgraph)  # a compiled graph is a valid node
parent.add_node("writer", writer_agent)
parent.add_edge(START, "researcher")
parent.add_edge("researcher", "writer")
parent.add_edge("writer", END)
```

For this to work, the subgraph's state and the parent's state need overlapping keys (or you wrap the
subgraph in a small adapter function that translates between the two schemas). Subgraphs are how you keep a
large multi-agent system's individual graphs testable in isolation — exactly the same reason you'd factor a
large Python module into smaller ones.

## Choosing a topology

| Pattern | Use when |
|---|---|
| Fixed pipeline (Ch. 1–2 style) | Steps are always the same, in the same order |
| Planner + router queue (this repo) | The *set* of steps varies by input, but each step is independent and order doesn't depend on intermediate results |
| Supervisor (LLM-driven) | The *next* step depends on what previous steps discovered; you want an LLM making that call |
| Subgraphs | Any single agent is complex enough to deserve its own graph, tests, and state schema |

Next: [Chapter 7 — Streaming](07-streaming.md).

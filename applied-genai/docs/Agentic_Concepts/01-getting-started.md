# 1. Getting Started

## Install

From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

That installs `langgraph` along with the rest of this repo's dependencies. If you're starting a fresh
project instead, the minimum install is:

```bash
pip install langgraph langchain-core
```

Add `langchain-openai`, `langchain-anthropic`, or another chat-model integration if you want an LLM node.

## Your first graph

Every LangGraph app starts the same way: define a **state**, add **nodes**, wire up **edges**, then
**compile**.

```python
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    greeting: str


def say_hello(state: State) -> State:
    return {"greeting": f"Hello, {state['greeting']}!"}


graph = StateGraph(State)
graph.add_node("greet", say_hello)
graph.add_edge(START, "greet")
graph.add_edge("greet", END)

app = graph.compile()

print(app.invoke({"greeting": "world"}))
# {'greeting': 'Hello, world!'}
```

Walk through what happened:

1. `State` is a `TypedDict` describing the shape of data flowing through the graph.
2. `say_hello` is a **node**: a function that takes the current state and returns a dict with the fields it
   wants to update.
3. `graph.add_edge(START, "greet")` says "start execution at the `greet` node."
4. `graph.add_edge("greet", END)` says "after `greet` runs, the graph is done."
5. `graph.compile()` turns the graph definition into a runnable object.

## Running it against this repo's demo

This repo ships a complete, slightly larger example at `langgraph_agents_demo.py`. Try it now:

```bash
python langgraph_agents_demo.py "What is LangGraph and what is 17 * 9?"
```

You should see a multi-line answer with a "Workflow trace" showing which nodes ran. We'll dissect exactly
how that graph is built in [Chapter 6 — Multi-Agent Systems](06-multi-agent-systems.md). For now, just
notice the pattern: a `StateGraph`, some nodes, and edges that connect them — exactly like the toy example
above, just with more nodes and a conditional router.

## `invoke` vs `stream`

`app.invoke(state)` runs the whole graph and returns the final state. For long-running graphs (especially
ones with an LLM in the loop) you'll usually want to see intermediate steps as they happen:

```python
for step in app.stream({"greeting": "world"}):
    print(step)
```

Each item yielded is a dict keyed by node name, containing that node's output. We cover streaming in depth
in [Chapter 7](07-streaming.md).

## Visualizing a graph

Compiled graphs can render themselves as Mermaid diagrams, which is invaluable once graphs get bigger than
two or three nodes:

```python
print(app.get_graph().draw_mermaid())
```

Paste the output into any Mermaid renderer (including this documentation site — see the
[Advanced Patterns](08-advanced-patterns.md) chapter for an embedded example).

Next: [Chapter 2 — Core Concepts](02-core-concepts.md).

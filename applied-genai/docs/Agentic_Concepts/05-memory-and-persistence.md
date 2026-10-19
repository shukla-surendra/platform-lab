# 5. Memory & Persistence

Everything so far runs a graph start-to-finish in one `invoke()` call and forgets it happened. Real
applications need to:

- remember a conversation across multiple turns,
- survive a process restart,
- pause and wait for a human before continuing,
- or rewind to an earlier point and try again.

LangGraph handles all of this with **checkpointers**.

## Checkpointers

A checkpointer saves a snapshot of the graph's state after every step, keyed by a **thread ID**. Attach one
at compile time:

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer)
```

Now every call needs a `thread_id` in its config, identifying *which* conversation you're continuing:

```python
config = {"configurable": {"thread_id": "user-42"}}

app.invoke({"messages": [("user", "My name is Ada.")]}, config)
app.invoke({"messages": [("user", "What's my name?")]}, config)
# The second call still has access to the first message, because
# the checkpointer restored state for thread_id "user-42".
```

`MemorySaver` keeps everything in-process memory — great for development, gone on restart. For anything
that needs to survive a restart, swap in a persistent backend:

```python
from langgraph.checkpoint.sqlite import SqliteSaver

with SqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
    app = graph.compile(checkpointer=checkpointer)
```

(`pip install langgraph-checkpoint-sqlite` for the snippet above.) Postgres and other backends exist as
separate `langgraph-checkpoint-*` packages for production deployments.

## Threads vs. state

A **thread** is just an ID. The checkpointer stores a full history of state snapshots for that thread, which
gives you three things almost for free:

- **Resuming**: call `invoke`/`stream` again with the same `thread_id` and the graph picks up where it left
  off.
- **Inspecting history**: `app.get_state_history(config)` returns every checkpoint for a thread, oldest to
  newest.
- **Time travel**: pass a specific checkpoint's config back into `invoke` to "fork" execution from that
  point — useful for debugging or for "try a different answer" UX.

```python
for state in app.get_state_history(config):
    print(state.values, state.next)
```

## Human-in-the-loop with `interrupt`

Checkpointing is also what makes it possible to **pause a graph mid-run and wait for a human**. Use the
`interrupt` function inside a node:

```python
from langgraph.types import interrupt, Command


def ask_for_approval(state: State) -> State:
    decision = interrupt({"question": "Approve this action?", "action": state["proposed_action"]})
    return {"approved": decision == "yes"}
```

Calling `interrupt(...)` halts graph execution at that node and surfaces the payload to your calling code
(e.g. show it in a UI). To resume, invoke the graph again with a `Command(resume=...)`:

```python
app.invoke(Command(resume="yes"), config)
```

Because the checkpointer already saved state up to the interrupt point, execution resumes exactly where it
left off — the node re-runs, `interrupt()` now returns `"yes"` instead of pausing again, and the graph
continues.

This is the modern replacement for the older `interrupt_before=[...]` / `interrupt_after=[...]` compile-time
options, which still work but only support pausing *before or after* a whole node rather than at an
arbitrary point inside one.

## Updating state manually

You can also inject state changes from outside the graph — for example, to let a human edit a proposed
answer before the graph continues:

```python
app.update_state(config, {"proposed_action": "revised text"})
```

## Why this matters for the repo's demos

`langgraph_agents_demo.py` is intentionally stateless — one `invoke()` per question, no checkpointer,
because it's a single-shot CLI demo. `personal_assistant_demo.py`, by contrast, persists task data across
runs, but does it with a plain JSON file (`tasks.json`, via `task_store.py`) rather than LangGraph
checkpointing, since it isn't built on `StateGraph`. If you converted that assistant into a `StateGraph`
(a good exercise!), a `SqliteSaver` keyed by a per-user `thread_id` is exactly how you'd give it multi-turn
conversational memory instead of re-parsing one prompt at a time.

Next: [Chapter 6 — Multi-Agent Systems](06-multi-agent-systems.md).

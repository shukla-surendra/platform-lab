# 7. Streaming

Waiting for `.invoke()` to return the full final state is fine for a CLI demo like this repo's
`langgraph_agents_demo.py`. For anything with a UI, users expect to see progress as it happens. LangGraph
supports several streaming modes, each answering a different question.

## `stream_mode="updates"` — what changed at each step

```python
for chunk in app.stream({"question": "What is LangGraph?"}, stream_mode="updates"):
    print(chunk)
# {'planner': {'remaining_agents': ['researcher'], 'notes': [...]}}
# {'researcher': {'remaining_agents': [], 'notes': [...]}}
# {'writer': {'final_answer': '...'}}
```

Each item is `{node_name: partial_state_returned_by_that_node}` — perfect for driving a "workflow trace" UI
like the one `langgraph_agents_demo.py` prints at the end, but live instead of after the fact.

## `stream_mode="values"` — the full state after each step

```python
for state in app.stream({"question": "..."}, stream_mode="values"):
    print(state)  # entire AgentState, snapshotted after each node
```

Use this when downstream code wants the whole picture each time rather than a diff.

## `stream_mode="messages"` — token-by-token LLM output

For a chat-style graph with an LLM node, `"messages"` streams individual tokens as the model generates
them, tagged with which node/LLM call they came from:

```python
for message_chunk, metadata in app.stream({"messages": [...]}, stream_mode="messages"):
    print(message_chunk.content, end="", flush=True)
```

This is what you want for a typical "typing" chat UI.

## `astream_events` — everything, as fine-grained events

For full observability (tool calls starting/finishing, retriever calls, nested chain steps — not just
node-level and token-level events), use the async event stream:

```python
async for event in app.astream_events({"messages": [...]}, version="v2"):
    if event["event"] == "on_chat_model_stream":
        print(event["data"]["chunk"].content, end="")
    elif event["event"] == "on_tool_start":
        print(f"\n[calling tool: {event['name']}]")
```

This is the same event schema used by plain LangChain `Runnable`s, so if you've streamed a LangChain chain
before, it transfers directly.

## Combining stream modes

You can request multiple modes at once and distinguish them by a tag in each yielded item:

```python
for stream_mode, chunk in app.stream(
    {"messages": [...]}, stream_mode=["updates", "messages"]
):
    ...
```

## Streaming a graph that has an interrupt

Streaming and the human-in-the-loop `interrupt()` from [Chapter 5](05-memory-and-persistence.md) compose
naturally: the stream simply ends (without hitting `END`) when the graph pauses, and resumes producing
chunks once you call `.stream(Command(resume=...), config)`.

## Try it against this repo's graph

`langgraph_agents_demo.py`'s `run_demo` function currently calls `app.invoke(...)`. As an exercise, change
it to `app.stream(initial_state, stream_mode="updates")` and print each chunk — you'll see the planner's
decision, then each specialist agent's note, arrive one at a time instead of all at once at the end.

Next: [Chapter 8 — Advanced Patterns](08-advanced-patterns.md).

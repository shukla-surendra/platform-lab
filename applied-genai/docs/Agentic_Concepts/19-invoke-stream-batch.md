# Appendix: invoke(), ainvoke(), stream(), astream(), batch()

All five are methods on the **same object**: a LangChain `Runnable`. That can be a chat model, a prompt, a chain, or a compiled LangGraph graph. They all run the same thing and differ only in **how you get the result back**. Two questions decide which one to use:

1. **Do I want the whole answer at once, or piece by piece?** → `invoke` vs. `stream`
2. **Is my code sync or async?** → no prefix vs. the `a` prefix

## Quick table

| Method | Input | Returns | Waits? | Use when |
|---|---|---|---|---|
| `.invoke(x)` | one input | the full result | blocks until done | Scripts, tests, simple backend calls |
| `.ainvoke(x)` | one input | full result (awaitable) | `await`, doesn't block other tasks | FastAPI / async web servers |
| `.stream(x)` | one input | an iterator of chunks | yields pieces as they come | Showing output live in a CLI |
| `.astream(x)` | one input | an async iterator of chunks | `async for`, non-blocking | Live output in a web app (SSE / WebSocket) |
| `.batch([x1, x2, ...])` | a **list** of inputs | a list of results, same order | runs them in parallel (threads) | Processing many inputs, e.g. evals, bulk classification |

(There is also `.abatch()`, the async version of `batch`.)

## Same model, five ways

```python
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-sonnet-5-5")

# 1. invoke: wait, then get everything
msg = llm.invoke("Explain Kubernetes in one line")
print(msg.content)

# 2. ainvoke: same, but inside async code
msg = await llm.ainvoke("Explain Kubernetes in one line")

# 3. stream: print tokens as they arrive
for chunk in llm.stream("Explain Kubernetes in one line"):
    print(chunk.content, end="", flush=True)

# 4. astream: same, async (e.g. inside a FastAPI endpoint)
async for chunk in llm.astream("Explain Kubernetes in one line"):
    await websocket.send_text(chunk.content)

# 5. batch: many inputs in parallel
results = llm.batch(["What is a pod?", "What is a node?", "What is a service?"],
                    config={"max_concurrency": 3})
```

## Sync vs. async, plain language

- **Sync (`invoke`, `stream`, `batch`)**: your program **waits** while the LLM thinks, and nothing else runs on that thread. Fine for scripts.
- **Async (`ainvoke`, `astream`, `abatch`)**: while waiting on the LLM, the server can **handle other users' requests**. Use these in FastAPI or any `async def` code. Calling the sync `invoke` inside an async server blocks the whole event loop, so every user waits. That's a common mistake.

## invoke vs. stream, plain language

The total time is the same. The difference is **when the user sees the first word**:

- `invoke`: blank screen for 8 seconds, then the full answer appears.
- `stream`: the first words show up after about 0.5 seconds and the rest types out. It feels much faster.

## In LangGraph it means a bit more

On a compiled graph (`app = graph.compile()`), the same methods exist, but `stream` streams **graph steps**, not just tokens. You pick what to stream with `stream_mode`:

```python
# final state only
result = app.invoke({"messages": [("user", "hi")]})

# stream: one event per node that finishes
for event in app.stream(inputs, stream_mode="updates"):
    print(event)            # {'agent': {...}}, then {'tools': {...}}, ...

# full state after each step
for state in app.stream(inputs, stream_mode="values"):
    ...

# LLM tokens from inside the nodes
for token, metadata in app.stream(inputs, stream_mode="messages"):
    print(token.content, end="")
```

So `invoke` gives you the **final state**, and `stream` lets you watch the agent work: "classifying... calling a tool... writing the answer".

## How to choose

- Script or test → `invoke`
- Async web API → `ainvoke`
- User watching a chat UI → `astream` (or `stream` in a CLI)
- Many inputs at once → `batch` / `abatch`
- Showing agent progress in LangGraph → `stream` with `stream_mode="updates"` or `"messages"`

See also: [Chapter 7: Streaming](07-streaming.md).

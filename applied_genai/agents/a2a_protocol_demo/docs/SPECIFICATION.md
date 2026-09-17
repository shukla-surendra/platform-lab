# A2A Protocol — Specification, Packages, and the LangChain/LangGraph Bridge

Companion to [`../README.md`](../README.md). That file explains *this project*; this
one documents the *protocol* and *ecosystem* underneath it, sourced from the protocol's
own spec ([a2a-protocol.org](https://a2a-protocol.org/latest/specification/)) and the
SDK's official `helloworld` sample
([github.com/a2aproject/a2a-samples](https://github.com/a2aproject/a2a-samples)) —
fetched directly while building this project, not recalled from memory.

## 1. The specification, in five parts

### Agent Card — discovery

A JSON document every A2A server publishes describing itself, fetched by a client
*before* it ever sends a real message:

| Field | Holds | Used in this project? |
|---|---|---|
| Identity | `name`, `description`, `version`, `provider` | Yes — every `AgentCard(...)` in `../weather_agent/__main__.py` / `../coordinator_agent/__main__.py` |
| Capabilities | `streaming`, `pushNotifications`, `extendedAgentCard` flags | Partially — we declare `streaming=False` and stop there |
| Skills | `AgentSkill` objects: id, name, description, input/output modes, examples | Yes — one skill per agent |
| Interfaces | Transport(s) + URL(s) this agent answers on | Yes — `AgentInterface(protocol_binding="JSONRPC", ...)` |
| Security schemes | API key / OAuth2 / OIDC / mTLS requirements | No — this demo is unauthenticated, localhost only |
| Extensions | Vendor/use-case-specific additions beyond core spec | No |

### Core RPC methods

| Method | Purpose | Used here? |
|---|---|---|
| `SendMessage` | Client sends a message; server returns a `Task` or `Message` | **Yes** — the entire demo runs on this one |
| `SendStreamingMessage` | Same, but streams updates live | No |
| `GetTask` / `ListTasks` | Poll/query task state after the fact | No — `send_message` blocks until done |
| `CancelTask` | Request cancellation | No — both executors' `cancel()` raise `NotImplementedError` |
| `SubscribeToTask` | Stream updates for an already-created task | No |
| `*TaskPushNotificationConfig` (Create/Get/List/Delete) | Register a webhook instead of polling | No |
| `GetExtendedAgentCard` | Fetch a fuller card, for authenticated clients | No |

### Task lifecycle

```
SUBMITTED → WORKING → COMPLETED   (or FAILED / CANCELED / REJECTED)
                    ↘ INPUT_REQUIRED / AUTH_REQUIRED   (paused, waiting on the client)
```

Both executors here only ever walk `WORKING → COMPLETED` — the simplest path. A `Task`
carries `id`, `contextId` (groups related tasks — think "conversation"), `status`,
`artifacts` (output), `history` (messages), `metadata`.

### Transport and auth

Three normatively-equivalent bindings: **JSON-RPC 2.0** over HTTP, **gRPC**,
**HTTP/REST** — this project uses JSON-RPC (`create_jsonrpc_routes`, the SDK's default
and what the official sample uses). Auth schemes (API key, Bearer, OAuth2, OIDC, mTLS)
are declared per-agent in the Agent Card; this demo declares none.

### Messages, Artifacts, Parts

A **Message** is one conversational turn (`role`: `user`/`agent`) built from one or
more **Parts** (text, a file reference, or structured JSON — this project only ever
uses `text/plain`). An **Artifact** is a task's *output*, also built from Parts — the
spec is explicit that results belong in artifacts, not messages, which is why both
executors call `add_artifact(...)` for the real answer, separately from the
`update_status(message=...)` calls that just narrate progress.

## 2. Package requirements

From [`../pyproject.toml`](../pyproject.toml):

| Package | What it's for | Could you drop it? |
|---|---|---|
| `a2a-sdk` | The protocol itself — `AgentCard`, `AgentExecutor`, `TaskUpdater`, the JSON-RPC route builders, the client (`A2ACardResolver`, `create_client`) | No — this is the whole point |
| `uvicorn` | ASGI server that actually runs the app and listens on a port | No — something has to serve the Starlette app |
| `starlette` | The lightweight ASGI framework `create_agent_card_routes`/`create_jsonrpc_routes` return routes for | Could swap for FastAPI (the SDK samples note this explicitly) — Starlette is just the simplest choice |
| `httpx` | Async HTTP client — what `A2ACardResolver` uses to fetch a remote Agent Card | No — needed for the client side of any A2A call |
| `langchain-ollama` | This project's own choice for the coordinator's LLM (`ChatOllama`) | Yes — swap for any other LangChain chat model, or drop LangChain entirely and call Ollama's REST API directly; A2A doesn't care what's inside `execute()` |
| `python-dotenv` | Loads `.env` for `config.py` | Convenience only |

**Why `requires-python = ">=3.13"`**: the SDK's own constraint, not something this
project added. `uv run` (see `../README.md`'s Makefile) provisions a 3.13 interpreter
automatically via `uv python install` the first time you run it — no separate manual
install needed, even though this repo's system Python is 3.12.

**A packaging option not used here**: [`a2a-langchain-adapters`](https://pypi.org/project/a2a-langchain-adapters/)
on PyPI — a community package that provides a more turnkey LangChain/LangGraph↔A2A
bridge (stateful conversations, streaming, multi-turn context, tool binding handled for
you). This project hand-rolls that bridge instead (see part 3) specifically so the
mechanism stays visible — same reasoning
[`../../langgraph_ollama_agent/graph.py`](../../langgraph_ollama_agent/graph.py) gives
for using raw `StateGraph` instead of LangGraph's `create_react_agent` helper.

## 3. How this works with LangChain (and LangGraph)

**The core idea: A2A and LangChain solve different layers, and one wraps the other.**
LangChain/LangGraph is the *agent's internal brain* — how it reasons, calls tools,
manages state. A2A is the *wire protocol* — how that agent gets exposed to, and talked
to by, something outside its own process. `AgentExecutor` is the adapter between them:
its `execute()` method is where you call into your LangChain/LangGraph code, then
translate whatever comes back into A2A's vocabulary (`TaskUpdater` calls, artifacts).

### The pattern, at its simplest — what `coordinator_agent/agent_executor.py` actually does

```python
class CoordinatorAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.llm = ChatOllama(...)          # <-- the LangChain object

    async def execute(self, context, event_queue):
        ...
        response = self.llm.invoke(query)    # <-- LangChain does the actual thinking
        result = response.content            # <-- unwrap LangChain's AIMessage
        await updater.add_artifact(parts=[new_text_part(text=result, ...)])  # <-- hand
        await updater.update_status(state=TaskState.TASK_STATE_COMPLETED, ...)  # off to A2A
```

Nothing more sophisticated than: call the LangChain object, take its `.content`, wrap
it in an A2A artifact. This is deliberately the simplest version — `self.llm` here is
one bare `ChatOllama` call, not a full agent loop.

### The fuller version — wrapping an actual LangGraph agent

Real-world examples (e.g. the community "Currency Agent" tutorial referenced above)
follow the same shape with a compiled LangGraph app instead of a single LLM call:

```python
class SomeAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.graph = build_graph()           # <-- e.g. this repo's own
                                              #     ../../langgraph_ollama_agent/graph.py

    async def execute(self, context, event_queue):
        query = get_message_text(context.message)
        result = self.graph.invoke({"messages": [("user", query)]})
        final_message = result["messages"][-1].content
        await updater.add_artifact(parts=[new_text_part(text=final_message, ...)])
        await updater.update_status(state=TaskState.TASK_STATE_COMPLETED, ...)
```

Same bridge, same three moves (call the graph, unwrap the result, emit an A2A
artifact) — just calling `graph.invoke(...)` instead of `llm.invoke(...)`. Nothing
about `AgentExecutor` changes; LangGraph's `StateGraph` and A2A's `Task` are two
independent state machines that happen to be composed here, not merged into one.

### Streaming maps state-updates to state-updates

If the agent uses `graph.stream(...)` instead of `.invoke(...)` (per
[`../../langgraph_ollama_agent/agent.py`](../../langgraph_ollama_agent/agent.py)'s own
`--stream` mode), each yielded LangGraph state update gets translated into an A2A
`TaskStatusUpdateEvent` or `TaskArtifactUpdateEvent` as it happens, instead of one
single artifact at the end. This project's `AgentCapabilities(streaming=False)` opts
out of that entirely — every call here is invoke-then-wait, the same simplification
made throughout `../README.md`.

### The one thing that *doesn't* change no matter which side you're on

Whether `execute()` calls a bare LLM, a full LangGraph graph, or delegates to another
A2A agent entirely (as `coordinator_agent` does for weather questions), the *outside*
of the box — the Agent Card, the skill declaration, the Task lifecycle, the JSON-RPC
transport — is identical. That's the actual value of the protocol: it doesn't care what
framework, if any, lives inside `execute()`.

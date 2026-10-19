# A2A Protocol Demo — Two Agents Talking to Each Other

Two real, independently-running agents, communicating over the actual
[A2A (Agent2Agent) protocol](https://a2a-protocol.org/) — not a shared Python process,
not a function call between them. Sits next to
[`../langgraph_ollama_agent/`](../langgraph_ollama_agent/) as a genuinely different
concern: that project is about *how one agent's internal loop works*
(`StateGraph`, tool-calling); this one is about *how two separate agents find and talk
to each other* — a different protocol for a different problem, and worth being precise
about which is which (see [`../../docs/Agentic_Concepts/13-trusted-tools-landscape.md`](../../docs/Agentic_Concepts/13-trusted-tools-landscape.md),
which covers [MCP](https://modelcontextprotocol.io/) for agent↔tool but didn't yet cover
agent↔agent — this project is that missing piece).

## The two agents

- **`weather_agent/`** — deliberately the simplest possible agent: a static lookup
  table, no LLM at all. Its only job is to have a real, independent, discoverable
  **Agent Card** and answer one **skill** (`weather_lookup`).
- **`coordinator_agent/`** — a real agent backed by a local Ollama LLM. For a general
  question, it answers directly. For a weather question, it **delegates** —
  discovers `weather_agent`'s Agent Card, opens a real A2A client connection to it,
  sends it the request, and relays the result back.
- **`client.py`** — the human's entry point. It only ever talks to `coordinator_agent`
  — never to `weather_agent` directly. Whether your question gets answered locally or
  silently routed to a second agent is invisible from here, which is the actual point
  of the protocol: a client only needs one Agent Card to talk to, no matter how many
  agents that agent delegates to behind the scenes.

```
you ──(A2A)──> coordinator_agent ──(A2A, only for weather questions)──> weather_agent
                     │                                                       │
                     └───────────────────── result relayed back ─────────────┘
```

## Why this needs a real protocol at all

Two options exist for "one agent uses another agent": (a) import the second agent's
code directly and call a function, or (b) treat it as a genuinely separate service and
talk to it over the network. Option (a) only works when both agents live in the same
codebase, the same process, the same language, deployed together. A2A is for option
(b) — the same reason HTTP/REST exists between two unrelated web services instead of
everyone importing everyone else's code: `weather_agent` could be written in a
different language, maintained by a different team, running on a different machine,
and `coordinator_agent` would still be able to use it, as long as it can fetch that
agent's **Agent Card** (a JSON document describing what it can do and how to reach it)
and speak the same wire protocol (JSON-RPC 2.0 over HTTP, in this project).

## Core concepts, from the actual code here

- **Agent Card** — published at a well-known path; describes identity, skills, and
  the URL/protocol to reach the agent at. See the `AgentCard(...)` construction in
  either `__main__.py` — this is the *discovery* mechanism: a client resolves the card
  first, before ever sending a real message.
- **Skill** — one declared capability an agent has (`weather_lookup`,
  `general_qa_with_weather_delegation`). A card can list several; a client (or another
  agent) can inspect these before deciding whether this agent is even the right one to
  talk to.
- **`AgentExecutor`** — the interface every agent implements regardless of what's
  inside it (a lookup table, an LLM, another delegation chain). One required method,
  `execute(context, event_queue)` — receives the incoming message, does whatever work,
  emits status updates and a final artifact.
- **Task lifecycle** — `TASK_STATE_WORKING` → `TASK_STATE_COMPLETED` (or `_FAILED`,
  `_CANCELED`, ...), visible in both executors' `update_status` calls. A long-running
  agent can report progress mid-task instead of the client just waiting on a black box.
- **Artifacts vs. Messages** — the *result* of a task is an **artifact**
  (`add_artifact`), not just another chat message — a deliberate distinction the spec
  makes: messages are conversation turns, artifacts are what the task actually produced.

**Full writeup**: see [`docs/SPECIFICATION.md`](docs/SPECIFICATION.md) for the complete
A2A spec (Agent Card, RPC methods, Task lifecycle, transport/auth), what each package in
`pyproject.toml` is actually for, and exactly how `AgentExecutor` bridges to
LangChain/LangGraph (this project's simple `ChatOllama.invoke()` case, and the fuller
"wrap a real `StateGraph`" case).

## Running it

Needs Python **3.13+** (the SDK's own requirement) — `uv run` provisions this
automatically if you don't have it installed globally, so nothing extra to set up:

```bash
# Terminal 1 — the worker agent, must be up before the coordinator ever gets a
# weather question
make weather

# Terminal 2 — the coordinator, delegates to weather_agent when needed
make coordinator

# Terminal 3 — talk to it
make ask Q="What's the weather in Tokyo?"      # -> delegated to weather_agent
make ask Q="What is the capital of France?"    # -> answered directly, no delegation
make chat                                       # interactive REPL instead
```

Needs a local Ollama model pulled and tool-calling-capable: `make pull` (or set
`OLLAMA_MODEL` in `.env` to whatever you already have — see `config.py`).

## One thing to know before running this for real

`coordinator_agent/agent_executor.py`'s `extract_response_text()` function — which
parses the response chunks `client.send_message()` streams back — was written against
the official SDK samples' documented shapes, but **not run against a live install
while writing it** (this environment doesn't have Python 3.13 or `a2a-sdk` installed).
If it doesn't parse cleanly the first time you run this, add
`print(repr(chunk))` inside its loop, look at what actually comes back, and adjust the
attribute path — the function's docstring flags exactly this. Everything else here
(Agent Card/Skill construction, the server routes, the executor interface) was copied
from the SDK's own current `helloworld` sample, not guessed.

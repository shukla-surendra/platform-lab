# Agent Types, and Ways to Access an Agent

Two related questions this doc answers: **what kind of agent is this**, positioned against the
broader landscape of agent designs, and **how does a user (or another system) actually reach
it** — which turns out to have more real answers than "type a prompt into a chat box."

## Part 1: Types of agents

"Agent" gets used for a wide range of designs. Roughly, from simplest to most autonomous:

| Type | How it decides what to do next | Example shape |
|---|---|---|
| **Reflex / rule-based** | Fixed if/else or lookup-table logic, no model in the loop | A monitoring alert that pages on-call when a metric crosses a threshold |
| **Single-shot LLM call** | One prompt in, one completion out, no tools, no loop | A summarization or classification endpoint |
| **Tool-using / ReAct loop** | Model sees a list of tools, decides per-turn whether to call one, loops until it produces a final answer | A general-purpose assistant with `bind_tools` and an open-ended `while` loop |
| **Planning / explicit-graph agent** | Control flow (which step follows which) is fixed by the developer; the model only fills in specific decision points | This project — see below |
| **Multi-agent / handoff systems** | Several specialized agents, each with their own tools/instructions, that can transfer control to each other mid-task | A triage agent that hands off to a specialist and back |
| **Autonomous / event-driven agents** | No human prompts each run; the agent reacts continuously to an external event stream | This project's `daemon.py` automode |
| **RAG-augmented agents** | Any of the above, plus a retrieval step that grounds generation in an external knowledge source instead of relying solely on parametric knowledge | This project's `retrieve_knowledge` node |

These aren't mutually exclusive categories — they're independent axes (control-flow style,
autonomy, grounding) that a real agent mixes and matches. This project's position on each axis:

- **Control flow**: explicit-graph, not a free-form ReAct loop. `graph.py`'s `StateGraph` fixes
  the sequence (`classify → gather_context → retrieve_knowledge → diagnose → decide → act →
  notify → record`) ahead of time. The two LLM calls (`classify`, `diagnose`) only fill in
  specific decisions *within* that fixed shape — which domain a query is about, what the root
  cause and recommended action are — they never decide what step runs next. This trades some
  flexibility for something a ReAct loop doesn't reliably give you: every run takes a
  predictable, auditable path, which matters a lot more for an agent that's allowed to touch
  infrastructure than for one that's just answering questions.
- **Autonomy**: both. `agent_cli.py` is reactive (a human asks a question, gets an answer).
  `daemon.py` is autonomous (it reacts to whatever lands in `events/inbox/` with nobody prompting
  it), running the *same graph* either way — autonomy here is a property of what triggers a run,
  not a different agent design.
- **Grounding**: RAG-augmented. `retrieve_knowledge` is a real step in the graph, not a
  side-channel — see the README's Reliability notes for how to verify the retrieved passages are
  actually influencing `diagnose`'s output rather than being fetched and ignored.
- **Multi-agent**: deliberately not used here. Three domains share one set of nodes because the
  *shape* of triage (gather → ground → diagnose → decide → act → record) doesn't change between
  them — only the tools and knowledge each domain reaches for does. A handoff design would be the
  right call if the domains needed genuinely different reasoning strategies, not just different
  tools; they don't, so one graph is the more honest design here, not a shortcut.

## Part 2: Ways a user can access an agent

An agent's *reasoning* (the graph) is separate from its *access surface* (how something outside
the process reaches it). The same graph can sit behind several different access surfaces at
once — this project actually does, today:

| Access surface | What it looks like | This project's implementation |
|---|---|---|
| **Interactive CLI** | A human types a request, waits, reads a response, in a terminal | `python agent_cli.py "why is fraud-detection degraded?"` |
| **Autonomous / event-driven** | No human in the loop per run; the agent reacts to an external event stream (a webhook, a queue, a watched directory) | `python daemon.py` polling `events/inbox/` |
| **Direct tool access (bypassing the agent's reasoning)** | A human or another program calls the underlying tools directly, without going through the LLM's diagnosis at all | Any MCP client (Claude Desktop, the MCP Inspector, another agent) pointed at `mcp_servers/ops_server.py` or `knowledge_server.py` — useful for inspecting/debugging the tools independent of whether the model reasons about them well |
| **Programmatic / embedded** | Another Python process imports and drives the graph directly, no subprocess or network hop | `from graph import build_graph; app = await build_graph(); await app.ainvoke(...)` — this is literally what `agent_cli.py` and `daemon.py` themselves do |
| **Network service (Docker Compose)** | The agent and its tools run as independently addressable containers on a real network, reachable by hostname:port instead of only by local process/filesystem | `docker compose up` — see `docker-compose.yml` and the README's Docker section; `ops-server`/`knowledge-server` become MCP endpoints anything on the network can reach, not just this project's own agent |
| **One-off exec against a running stack** | A short-lived command runs against services that are already up, without starting or owning them | `docker compose run --rm cli python agent_cli.py "..."` — the `cli` service shares the running stack's network and volumes but isn't part of `docker compose up` itself (`profiles: ["tools"]`) |

Access surfaces this project **doesn't** implement, listed because they're the natural next step
for a real deployment and worth knowing the shape of:

- **Chat UI / Slack-Teams bot** — a thin adapter that takes a message from a chat platform,
  calls `agent_cli.py`'s `run()` (or the graph directly) with the message text as `input_query`,
  and posts the result back. No graph changes needed — this is purely a new access surface on
  top of the same `build_graph()`/`ainvoke()` call `agent_cli.py` already makes.
- **REST/webhook API** — wrap `graph.py`'s `build_graph()` in a small FastAPI app; a `POST
  /investigate {"query": "..."}` endpoint calling `ainvoke({"input_query": ...})` is a few lines,
  since the graph itself is already async. A real monitoring system's webhook (PagerDuty,
  Datadog, a model-monitoring platform) would land here instead of in `events/inbox/`.
- **Scheduled/cron trigger** — instead of `daemon.py` polling a directory, a scheduler (cron,
  Airflow, a Kubernetes CronJob) invokes the graph on a fixed interval to proactively check for
  drift/anomalies rather than waiting for an event to arrive.
- **SDK / library** — packaging `graph.py` behind a small public function (`investigate(query:
  str) -> Result`) so another Python service can depend on this project as a library rather than
  shelling out to `agent_cli.py` or hitting it over HTTP.

The point of listing these: **the access surface and the agent's reasoning are separable
concerns**. Every one of the surfaces above — implemented or not — calls the same
`build_graph()`/`ainvoke()` pair. Adding a new way to reach this agent should never require
touching `graph.py`; if it does, that's a sign the access layer and the reasoning layer have
become coupled somewhere they shouldn't be.

# Appendix: Trusted Tools for Agentic Development

[Chapter 12](12-real-world-example.md) closed with "go build something real." Before the next
build, it's worth surveying the ecosystem this repo's examples sit inside — so that architecture
decisions (which orchestration model, how to persist memory, how to observe a running agent, how
to keep it safe) are made deliberately, not by whatever happened to come up first in a search.

This is a reference, not a tutorial — skim the tables, follow a link when a category becomes
relevant to what you're building. Every tool listed is either already used somewhere in this
repo, or is a widely-adopted, actively-maintained option in its category as of 2026. "Trusted"
here means: open-source or backed by an organization with a track record, has a real community or
production adoption (not a weekend project), and has a stable-enough API that building on it
today won't be a rewrite in three months.

## Orchestration frameworks (the agent loop itself)

| Tool | What it is | Reach for it when |
|---|---|---|
| **[LangGraph](https://github.com/langchain-ai/langgraph)** | Graph-based agent orchestration: explicit nodes/edges, built-in checkpointing, streaming, subgraphs | You want the control flow visible and testable as a graph, or need durable multi-step/cyclical chains — used throughout [Chapters 1–12](00-agentic-concepts.md) and in `../langgraph_ollama_agent` |
| **[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)** | Lightweight agent/handoff primitive: agents-as-tools transferring control to each other | You want multi-agent delegation without hand-wiring a graph, and the model itself should decide when to hand off — used in `../devops_sre_agent`; works against any OpenAI-compatible endpoint, including local Ollama |
| **[CrewAI](https://github.com/crewAIInc/crewAI)** | Role-based multi-agent "crews" (Researcher, Writer, ...) with a task pipeline | You're modeling a team of role-specialized agents and want that abstraction built in, rather than composing it yourself |
| **[AutoGen / AG2](https://github.com/ag2ai/ag2)** | Conversable multi-agent framework from Microsoft, strong at agent-to-agent dialogue and code execution | You need agents that converse with each other (not just hand off) or sandboxed code-execution agents |
| **[LlamaIndex Workflows](https://docs.llamaindex.ai/en/stable/module_guides/workflow/)** | Event-driven step orchestration, originally RAG-focused, now general agent workflows | You're already on LlamaIndex for retrieval and want orchestration in the same ecosystem |
| **[Pydantic AI](https://github.com/pydantic/pydantic-ai)** | Thin, type-safe agent framework from the Pydantic team; validated structured output by construction | You want strict input/output typing on every agent call with minimal framework overhead |
| **[Google ADK](https://github.com/google/adk-python)** | Google's Agent Development Kit; strong multi-agent + Gemini integration, deployable to Vertex AI | You're targeting Gemini/Vertex specifically |
| **[AWS Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/)** | Managed runtime + deployment for agent code (framework-agnostic) | You've built the agent (in LangGraph, Agents SDK, or anything else) and need a managed way to run and deploy it — used in `../agentcore_app.py`, see [Chapter 9](09-deployment.md) |
| **Hand-rolled loop** | No framework, just a `while` loop parsing model output | The simplest possible case, or when you want the mechanics fully visible with zero dependencies — see `../personal_assistant_demo.py` and [Chapter 0](00-agentic-concepts.md) |

None of these are mutually exclusive with each other in a larger system — e.g. AgentCore can host
a LangGraph or Agents SDK agent; MCP (below) supplies tools to any of them.

## Durable / event-driven orchestration

Relevant specifically when an agent needs to run continuously, react to external events, or
survive a process restart mid-task — not just answer one request and exit.

| Tool | What it is | Reach for it when |
|---|---|---|
| **[Temporal](https://temporal.io/)** | Durable execution engine: workflows resume exactly where they left off after a crash, with built-in retries and long-running state | The workflow must survive process/machine failure and run for hours-to-days (e.g. a multi-day approval-gated agent task) |
| **[Prefect](https://www.prefect.io/)** / **[Dagster](https://dagster.io/)** | Data/task orchestration with scheduling, retries, observability UIs | The agent's "events" are really pipeline runs (ETL, ML training) and you want a scheduler-native view of them |
| **[Apache Airflow](https://airflow.apache.org/)** | The long-standing DAG scheduler | You're already standardized on Airflow for data pipelines and want agent steps as tasks in that DAG |
| **Message queues** (Kafka/Redpanda, SQS, Redis Streams) | Durable event transport between producers and consumers | Events come from (or need to fan out to) other systems, not just a single process |
| **Lightweight polling loop** | A plain Python loop watching a queue/directory/table for new work | The event volume and reliability requirements are modest and a heavyweight scheduler would be pure overhead — this is the approach `../databricks_autopilot_agent` uses (a watched directory standing in for a real event source), deliberately choosing simplicity over Temporal/Kafka for a repo example |

The trade-off to actually reason about: Temporal/Kafka buy you crash-recovery and horizontal
scale at the cost of real operational complexity (a cluster to run, a new mental model). A polling
loop over a durable queue (even just a database table with a `status` column) is often the right
starting point, and the durable-store step (below) is where the real reliability comes from either
way — the loop itself is disposable and safe to restart.

## Tool-exposure standard

| Tool | What it is | Reach for it when |
|---|---|---|
| **[Model Context Protocol (MCP)](https://modelcontextprotocol.io/)** | An open standard (Anthropic-originated, now broadly adopted) for exposing tools/resources to any compatible client over a common protocol | You want tools reachable by more than one agent/client, not hardcoded into a single script — see [Chapter 11](11-mcp-agentic-capabilities.md) and `../tasks_mcp_server.py` |

## Agent-to-agent standard

The complement to the row above: MCP standardizes agent↔**tool**; this standardizes
agent↔**agent** — a genuinely different problem (discovering and delegating to another
independent agent, possibly on a different machine/team/language, not just calling a
function-shaped tool).

| Tool | What it is | Reach for it when |
|---|---|---|
| **[A2A (Agent2Agent) protocol](https://a2a-protocol.org/)** | An open standard (Google-originated, now Linux Foundation) for one agent to discover another's capabilities (its published **Agent Card**) and delegate work to it over JSON-RPC/gRPC/REST, as an independent service rather than an in-process call | Two agents need to talk across a real process/team/language boundary — not just one agent calling its own tools — see `../../agents/a2a_protocol_demo/` for a real two-agent example (a coordinator delegating weather questions to a separate worker agent) |

## Local & self-hosted model serving

| Tool | What it is | Reach for it when |
|---|---|---|
| **[Ollama](https://ollama.com)** | The simplest way to run open-weight models locally, with an OpenAI-compatible API | Local development, no GPU cluster to manage, need to iterate fast — used throughout this repo's local demos |
| **[vLLM](https://github.com/vllm-project/vllm)** | High-throughput inference server (PagedAttention, continuous batching) | Self-hosting at production scale/concurrency, not just single-user local dev |
| **[llama.cpp](https://github.com/ggml-org/llama.cpp)** | The underlying C++ inference engine many local tools (including Ollama) build on | You need maximum control over quantization/hardware targeting, or an embedded/edge deployment |
| **[LM Studio](https://lmstudio.ai/)** | GUI-first local model runner | Non-CLI users who want a model picker and chat UI over local inference |
| **[Text Generation Inference (TGI)](https://github.com/huggingface/text-generation-inference)** | Hugging Face's production inference server | Self-hosting Hugging Face models specifically, at scale |

Whichever server you pick, verify tool-calling support per model before building an agent on it —
`ollama show <model>` and check for `tools` under Capabilities, as this repo's projects do; not
every model (notably most Gemma variants in Ollama) supports it.

## Memory and vector storage

| Tool | What it is | Reach for it when |
|---|---|---|
| **[FAISS](https://github.com/facebookresearch/faiss)** | In-process similarity search library, no server | Single-process, no need for a shared/remote store — see `../faiss_vector_db` |
| **[Qdrant](https://qdrant.tech)** | Purpose-built vector database with a real server, native payload storage, filtered search | You need a real database (multi-client access, native metadata filtering, upsert-by-id) — see `../qdrant_vector_db` |
| **[pgvector](https://github.com/pgvector/pgvector)** | Vector type + index bolted onto Postgres | You already run Postgres and want vectors alongside relational data in one system — see `../rag_pgvector_local` |
| **[Chroma](https://www.trychroma.com/)** | Developer-friendly embedded/server vector store | Fast prototyping with minimal setup, similar niche to FAISS/Qdrant but optimized for ease of use |
| **[Redis (with vector search)](https://redis.io/docs/latest/develop/interact/search-and-query/advanced-concepts/vectors/)** | In-memory store with vector search as one of many features | Vectors are one part of a system already built on Redis for caching/sessions |
| **[Pinecone](https://www.pinecone.io/)** / **[Weaviate](https://weaviate.io/)** | Managed (Pinecone) or open-source-with-managed-option (Weaviate) vector databases | You want a managed service instead of operating Qdrant/pgvector yourself |
| **[mem0](https://github.com/mem0ai/mem0)** | A memory layer purpose-built for agents (facts extracted and retrieved across sessions, not raw chat logs) | You want structured long-term agent memory (user facts/preferences) rather than raw vector similarity over conversation text |

See [Chapter 5](05-memory-and-persistence.md) for the distinction this repo draws between
*conversation memory* (checkpointer/session, keyed by thread) and *data memory* (facts a tool
explicitly persisted) — most of the confusion in "which memory tool do I need" traces back to
conflating those two.

## Observability, tracing, and evaluation

| Tool | What it is | Reach for it when |
|---|---|---|
| **[LangSmith](https://www.langchain.com/langsmith)** | Tracing/eval/monitoring for LangChain/LangGraph apps (also works framework-agnostic via OpenTelemetry) | You're on LangGraph and want first-party trace visualization, dataset-based evals, and prompt versioning |
| **[Langfuse](https://langfuse.com/)** | Open-source LLM observability (self-hostable), tracing + evals + prompt management | You want tracing without a vendor lock-in to one framework, or need to self-host for data residency |
| **[Arize Phoenix](https://github.com/Arize-ai/phoenix)** | Open-source LLM tracing/eval, strong on embedding/retrieval debugging | RAG-heavy systems where you need to inspect retrieval quality, not just the final answer |
| **[OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)** | The emerging vendor-neutral standard for tracing LLM calls | You want traces portable across observability backends instead of tied to one vendor's SDK |
| **[Weights & Biases Weave](https://wandb.ai/site/weave/)** | Tracing + eval, integrated with W&B's broader ML experiment tracking | You're already using W&B for model training/experiment tracking |
| **[promptfoo](https://github.com/promptfoo/promptfoo)** | CLI-first prompt/output testing and red-teaming | You want CI-friendly regression tests over prompts, or automated adversarial testing |
| **[RAGAS](https://github.com/explodinggraph/ragas)** | RAG-specific evaluation metrics (faithfulness, answer relevance, context precision) | Scoring retrieval-augmented generation quality specifically |
| **[DeepEval](https://github.com/confident-ai/deepeval)** | Pytest-style LLM evaluation framework | You want agent/LLM evals to run as part of a normal test suite |

For a local-model project without a hosted account, the practical minimum bar (used in this
repo's `--trace`/`--stream` flags) is: **log every tool call and its raw output, separately from
the model's final prose summary.** `../devops_sre_agent/README.md#reliability-notes-read-this`
documents a concrete case — a local model's final answer claimed an action it never actually took
— that only tool-call-level logging caught. That's the one practice worth adopting before any of
the fancier platforms above.

## Guardrails and safety

| Tool | What it is | Reach for it when |
|---|---|---|
| **[Guardrails AI](https://github.com/guardrails-ai/guardrails)** | Validators for structured LLM output (schema, format, content rules), with retry-on-failure | You need to enforce output structure/content rules beyond what a Pydantic schema alone catches |
| **[NVIDIA NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails)** | Programmable conversational rails (topic limits, jailbreak resistance) | Consumer/public-facing conversational agents needing topic and safety boundaries |
| **[LLM Guard](https://github.com/protectai/llm-guard)** | Input/output scanners (PII, prompt injection, toxicity, secrets leakage) | You want a scanning layer around any LLM call, framework-agnostic |
| **[Microsoft Presidio](https://github.com/microsoft/presidio)** | PII detection and redaction | Any agent that might see or log user PII and needs it redacted before storage/forwarding |
| **[OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)** | Not a tool — the standard vulnerability checklist (prompt injection, insecure output handling, excessive agency, ...) | Reviewing any agent design, especially one with tools that can take real-world action — read this before an agent gets `--apply`-style mutating capability, as in `../devops_sre_agent` |

The pattern already used twice in this repo — dry-run by default, mutating tools gated behind an
explicit `--apply` flag (`../langgraph_ollama_agent`, `../devops_sre_agent`) — is a manual,
lightweight version of what Guardrails/NeMo Guardrails formalize. Reach for the dedicated tooling
once "check a flag before mutating" isn't enough (e.g. you need policy rules the agent can't talk
its way around, or output scanning at the token level).

## Deployment and serving

| Tool | What it is | Reach for it when |
|---|---|---|
| **[AWS Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/)** | Managed agent runtime + gateway + memory, framework-agnostic | Deploying to AWS specifically — see [Chapter 9](09-deployment.md), `../agentcore_app.py` |
| **[LangGraph Platform](https://www.langchain.com/langgraph-platform)** | Managed hosting purpose-built for LangGraph graphs, with built-in Studio debugging | You're committed to LangGraph and want managed hosting + the visual debugger from [Chapter 10](10-best-practices.md#debugging-a-graph) |
| **FastAPI + Uvicorn behind Docker** | Plain HTTP service, full control | You want no managed-platform lock-in and are comfortable owning the deployment |
| **[Ray Serve](https://docs.ray.io/en/latest/serve/index.html)** / **[Modal](https://modal.com/)** | Scalable Python serving with GPU support | Serving your own fine-tuned/self-hosted model alongside the agent code, at scale |

## How this maps onto the next project

`../databricks_autopilot_agent` (the complex, continuously-running chain built after this
appendix) draws directly on this landscape:

- **Orchestration**: LangGraph, for the same reason as [Chapters 1–12](00-agentic-concepts.md) —
  the chain has enough branches (failure-category routing, recurrence overrides) that an explicit
  graph is easier to reason about and test than an implicit agent loop.
- **Event-driven / automode**: a lightweight polling loop over a watched directory, not
  Temporal/Kafka — per the trade-off above, the right choice for a repo example's event volume,
  while keeping the durable state (job history, open tickets) in a real store so the loop itself
  stays disposable.
- **Observability**: every event, tool call, and decision is logged structuredly and separately
  from the model's summary — the one practice called out above as worth adopting regardless of
  which platform you eventually add on top.
- **Safety**: mutating actions (cluster resize, job retry) follow the same dry-run-by-default
  pattern as `../devops_sre_agent`.

Next: [`../databricks_autopilot_agent/README.md`](../../databricks_autopilot_agent/README.md).

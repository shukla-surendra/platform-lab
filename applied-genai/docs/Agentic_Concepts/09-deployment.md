# 9. Deployment

A compiled LangGraph graph is just a Python object with `.invoke()`. That means "deployment" is really
"put this behind an HTTP endpoint" — you have a few options, from generic to LangGraph-specific.

## Option A: wrap it yourself (any web framework)

Since a compiled graph is a plain callable, the simplest deployment is a thin FastAPI/Flask wrapper:

```python
from fastapi import FastAPI
from langgraph_agents_demo import run_demo

api = FastAPI()


@api.post("/invoke")
def invoke(payload: dict):
    return {"result": run_demo(payload["prompt"])}
```

This gives you full control but means you own scaling, request queuing, and (if you add checkpointing)
picking a production-grade checkpointer backend yourself.

## Option B: this repo's approach — Amazon Bedrock AgentCore

This repo deploys `langgraph_agents_demo.py` using **Bedrock AgentCore**, which packages the same idea
(wrap your graph in an HTTP entrypoint) with managed hosting on AWS. The entrypoint is
`agentcore_app.py`:

```python
from bedrock_agentcore import BedrockAgentCoreApp
from langgraph_agents_demo import run_demo

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(request):
    prompt = request.get("prompt", "What is LangGraph and what is 17 * 9?")
    return {"result": run_demo(prompt)}
```

`@app.entrypoint` is the only AgentCore-specific piece — everything else is the LangGraph graph you already
built in earlier chapters. This is the general shape for productionizing *any* graph: keep your LangGraph
code (`build_graph`, `run_demo`, etc.) free of deployment-framework imports, and put the framework glue in a
separate, thin entrypoint module.

### Running it locally

```bash
agentcore configure -e agentcore_app.py
agentcore dev
```

Then, in another terminal:

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What is LangGraph and what is 17 * 9?"}'
```

### Deploying and invoking

```bash
agentcore launch
agentcore invoke '{"prompt":"What is LangGraph and what is 17 * 9?"}'
```

And tearing it down when you're done:

```bash
agentcore destroy
```

See this repo's top-level `README.md` for the exact setup steps and troubleshooting (the `uv` and `chardet`
notes there are AgentCore/tooling quirks, not LangGraph itself).

## Option C: LangGraph Platform / LangGraph Server

For teams that want a purpose-built hosting layer (built-in persistence, streaming, human-in-the-loop
endpoints, and a visual debugger), LangChain offers **LangGraph Platform**, which runs a graph defined in a
`langgraph.json` config via `langgraph up` (self-hosted) or through their managed cloud offering. It's worth
evaluating once you outgrow a hand-rolled FastAPI wrapper and need multi-tenant persistence and streaming
out of the box — but it's a separate product from the open-source `langgraph` library used throughout this
tutorial, so treat it as an optional next step rather than a requirement.

## Choosing

| Approach | Best when |
|---|---|
| Roll your own (FastAPI, etc.) | You already have deployment infra and want minimal new dependencies |
| Bedrock AgentCore (this repo) | You're already on AWS and want managed hosting with minimal glue code |
| LangGraph Platform | You want built-in persistence/streaming/human-in-the-loop infra without building it yourself |

Next: [Chapter 10 — Best Practices](10-best-practices.md).

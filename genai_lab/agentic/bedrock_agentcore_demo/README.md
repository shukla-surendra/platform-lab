# LangGraph Agents Demo

A small, runnable LangGraph example with multiple agents:

- `planner` decides which specialist agents are needed
- `researcher` adds context notes
- `calculator` evaluates arithmetic expressions
- `writer` composes the final response

There is also a minimal local personal-assistant demo that uses:

- one local Ollama model
- shared local task tools
- an optional MCP server for the same task store

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python langgraph_agents_demo.py "What is LangGraph and what is 17 * 9?"
```

You can also run with no argument to use the default sample question.

## Run Minimal Personal Assistant Demo

Install and start Ollama:

```bash
brew install ollama
ollama serve
ollama pull llama3.1:8b
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the assistant:

```bash
python personal_assistant_demo.py "Add a task to buy milk and then show my tasks"
```

Useful test prompts:

```bash
python personal_assistant_demo.py "Add a task to review MCP docs"
python personal_assistant_demo.py "What are my tasks?"
python personal_assistant_demo.py "Complete task 1 and show my tasks"
```

The local MCP server stores tasks in `tasks.json`.

## Run with AgentCore Locally

```bash
agentcore configure -e agentcore_app.py
agentcore dev
```

If you see `No such file or directory: 'uv'`, reinstall dependencies in your venv:

```bash
pip install -r requirements.txt
```

In another terminal:

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What is LangGraph and what is 17 * 9?"}'
```

## Deploy with AgentCore

```bash
agentcore launch
agentcore invoke '{"prompt":"What is LangGraph and what is 17 * 9?"}'
```

When you are done:

```bash
agentcore destroy
```

## Documentation

A full beginner-to-advanced agentic development tutorial lives in [`../docs/`](../docs/index.md) (one level
up, at the repo root), built around the examples in this repo — covering agentic concepts, LangGraph, the
Model Context Protocol (MCP), and a real-world deployable example. Build and preview it locally from the
repo root with:

```bash
cd ..
make docs         # strict build, then serves at http://127.0.0.1:8000 (live-reloading)
make docs-build    # strict static build into site/ only, no server
```

## Troubleshooting

- `Failed to start development server: [Errno 2] No such file or directory: 'uv'`
  - `agentcore dev` uses `uv` internally for Python projects.
  - Fix:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

- `RequestsDependencyWarning: urllib3 ... or chardet ... doesn't match a supported version`
  - This is usually caused by an incompatible `chardet` version.
  - Fix:

```bash
source .venv/bin/activate
pip install "chardet<6"
```

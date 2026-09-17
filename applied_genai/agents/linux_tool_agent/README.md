# Local Ops Agent

A small LangGraph + OpenAI tool-calling agent that answers real questions about *this
machine* — disk space, memory, whether a process is running — by actually calling shell
commands, not just chatting. Same graph shape as
[`../langgraph_ollama_agent/`](../langgraph_ollama_agent/) (`StateGraph`, `MessagesState`,
`tools_condition`, `ToolNode`), swapped to OpenAI instead of local Ollama.

## Files

| File | Role |
|---|---|
| [`tools.py`](tools.py) | The three tools: `check_disk_usage`, `check_memory`, `check_process_running` — each a plain function decorated with `@tool`, wrapping a shell command |
| [`graph.py`](graph.py) | Wires the tools into the actual `StateGraph` (`START → agent → tools → agent → END`) |
| [`config.py`](config.py) | `OPENAI_MODEL` / `MODEL_TEMPERATURE`, loaded from `.env` |
| [`main.py`](main.py) | The CLI — single-shot, multi-turn REPL, or `--stream` |

## Setup

Needs an OpenAI API key. Create `.env` in this folder (see `.env.example`):

```
OPENAI_API_KEY=sk-your-real-key
```

Install dependencies (into whatever venv you're using — this repo's shared one lives at
`../../.venv`):

```bash
uv pip install --python ../../.venv/bin/python \
  langgraph langchain-openai langchain-core python-dotenv langgraph-checkpoint-sqlite
```

(`langgraph-checkpoint-sqlite` is a separate package from `langgraph` itself — easy to
miss, caught only by actually running this the first time.)

## Running it

```bash
# Single-shot
python main.py "How much free disk space do I have?"

# Multi-turn REPL -- conversation persists across process restarts, keyed by --thread
python main.py
python main.py --thread checks

# Streaming -- print each tool call/result as it happens, not just the final answer
python main.py --stream "Is api_server.py running, and do I have enough RAM for a 1.7B model?"
```

If you're not using the shared venv directly, run via its interpreter instead:

```bash
/home/surendra/projects/platform-lab/applied_genai/.venv/bin/python main.py "..."
```

## Real, actually-observed output

```
$ python main.py "How much free disk space do I have?"
You have 869 GB of free disk space available on your root filesystem.

$ python main.py "Is there a process called api_server.py running right now?"
Yes, there are processes related to `api_server.py` currently running.

$ python main.py "Do I have enough free RAM to load a 1.7B parameter model in float32?"
To determine if you have enough free RAM to load a 1.7 billion parameter model in
float32, we can calculate the memory requirement:
- Each float32 parameter requires 4 bytes.
- Therefore: 1.7 billion x 4 bytes = 6.8 billion bytes ~ 6.8 GB
You currently have approximately 1.8 GB of free RAM available. Since 6.8 GB is
required to load the model, you do not have enough free RAM to load the model.
```

That last one is the real test: the agent called `check_memory()`, read the actual
free-RAM number back, and reasoned over it correctly — not a guess, an answer grounded
in a real tool call.

## Notes

- `agent_memory.sqlite` (created on first run) is the conversation checkpoint database,
  keyed by `--thread` — gitignored, safe to delete to reset all conversation history.
- `check_process_running(name)` matches against the full command line via `pgrep -fl`,
  not just the process's own binary name — so `"api_server.py"` works even though the
  actual binary running is `python`.

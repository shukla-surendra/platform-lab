# Local Ops Agent

A small LangGraph + OpenAI tool-calling agent that answers real questions about *this
machine* — disk space, memory, running processes, directory contents, file contents —
and can run arbitrary shell commands, gated by a human-approval step for anything not
pre-approved as safe. Same graph shape as
[`../langgraph_ollama_agent/`](../langgraph_ollama_agent/) (`StateGraph`, `MessagesState`,
`tools_condition`, `ToolNode`), swapped to OpenAI instead of local Ollama.

## Files

| File | Role |
|---|---|
| [`tools.py`](tools.py) | The six tools (see below) — each a plain function decorated with `@tool`, wrapping a shell command |
| [`graph.py`](graph.py) | Wires the tools into the actual `StateGraph` (`START → agent → tools → agent → END`) |
| [`config.py`](config.py) | `OPENAI_MODEL` / `MODEL_TEMPERATURE`, loaded from `.env` |
| [`main.py`](main.py) | The CLI — single-shot, multi-turn REPL, or `--stream` — including the approval prompt loop |

## Tools

| Tool | What it does | Needs approval? |
|---|---|---|
| `check_disk_usage` | `df -h /` | No |
| `check_memory` | `free -h` | No |
| `check_process_running(name)` | `pgrep -fl <name>` | No |
| `list_directory(path=".")` | `ls -la <path>` | No |
| `read_file(path, max_lines=200)` | Reads up to `max_lines` of a text file | No |
| `run_command(command, cwd=".")` | Runs **any** shell command, in directory `cwd` | **Only if not on the safe list** — see below |

## Human approval for `run_command`

`run_command` checks the command's leading tokens against a small allowlist of
known-safe, read-only prefixes (`ls`, `cat`, `df`, `free`, `git status`, `kubectl get`,
...) in `tools.py`'s `SAFE_COMMAND_PREFIXES`. Anything **not** on that list — most
notably infrastructure-mutating commands like `terraform apply` or `terraform plan` —
calls LangGraph's `interrupt()`, which **pauses the entire graph mid-tool-call** and
returns control to `main.py`, which prints the pending command and asks for approval.
Answering blocks until you respond; `y`/`yes`/`approve`/`approved` resumes the graph
with `Command(resume=answer)` and the command actually runs; anything else resumes with
the command reported back to the agent as declined, never executed.

This is an **allowlist, not a denylist** — deliberately: an unrecognized command fails
closed into "ask a human" rather than silently running. Extend `SAFE_COMMAND_PREFIXES`
in `tools.py` as you find more commands that are genuinely safe to auto-run.

`run_command` never uses `shell=True` (`shlex.split` instead) — no `cd path && ...`,
pipes, or `$()` substitution work. Run one command per call, using the `cwd` argument
to target a specific directory (e.g. a Terraform project) instead.

## Getting the agent to actually *act*, not just describe

**Real bug, found and fixed**: asked to *"deploy this /path/to/terraform-project"*,
the first version of this agent responded with a 5-step manual guide (`cd`, `terraform
init`, `terraform plan`, `terraform apply`, ...) instead of ever calling `run_command`.
Nothing was wrong with the tool — the model just had no system prompt telling it to use
its own tools proactively, so it defaulted to "explain how a human would do this."

Fixed with a `SystemMessage` in `graph.py`'s `agent_node` (re-added fresh on every call,
not stored in the checkpointed conversation), explicitly telling the model: you have
real tools, call them directly for action requests; `run_command`'s own approval gate
already handles anything risky, so don't ask for confirmation in chat first — just call
the tool.

## Real, actually-observed output

## Setup

Needs an OpenAI API key. Create `.env` in this folder (see `.env.example`):

```
OPENAI_API_KEY=sk-your-real-key
```

`uv run` manages its own isolated `.venv` right here from `pyproject.toml` — no manual
install step needed, it resolves and installs on first run:

```bash
uv run python main.py "How much free disk space do I have?"
```

## Running it

```bash
# Single-shot
uv run python main.py "How much free disk space do I have?"

# Multi-turn REPL -- conversation persists across process restarts, keyed by --thread
uv run python main.py
uv run python main.py --thread checks

# Streaming -- print each tool call/result as it happens, not just the final answer
uv run python main.py --stream "Is api_server.py running, and do I have enough RAM for a 1.7B model?"

# Triggers the approval gate (run_command isn't on the safe list for this one)
uv run python main.py --stream "Run 'terraform plan' in the current directory"
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

**The full approval gate, verified against a real Terraform project and real Azure
credentials** (`cloud-practice/azure/terraform/storage-account`, a different project in
this repo) — approving `init` and `plan` (both safe, read-only) but explicitly
*declining* `apply`, to confirm nothing real actually gets touched without consent:

```
$ uv run python main.py --stream --thread deploy-test \
    "Can you deploy this /home/surendra/.../cloud-practice/azure/terraform/storage-account"

  [agent] -> call run_command({'command': 'terraform init', 'cwd': '.../storage-account'})
⚠  Approval needed: terraform init
   In directory: .../storage-account
   Approve? [y/N] y
  [tools] <- run_command: Terraform has been successfully initialized!

  [agent] -> call run_command({'command': 'terraform plan', 'cwd': '.../storage-account'})
⚠  Approval needed: terraform plan
   In directory: .../storage-account
   Approve? [y/N] y
  [tools] <- run_command: Plan: 4 to add, 0 to change, 0 to destroy.
              (real Azure plan output: a resource group, storage account, container, random_string)

  [agent] -> call run_command({'command': 'terraform apply -auto-approve', 'cwd': '.../storage-account'})
⚠  Approval needed: terraform apply -auto-approve
   In directory: .../storage-account
   Approve? [y/N] n
  [tools] <- run_command: Command NOT approved by a human -- not executed: terraform apply -auto-approve
The `terraform apply` command requires human approval before execution...
```

Confirmed afterward with `az group exists --name rg-storage-demo` → `false` — nothing
was actually created. Three things worth noting from this one real run:

- The system-prompt fix worked: it called `run_command` directly for a "deploy this"
  request instead of printing manual steps, and correctly used `cwd` to target the
  right project directory instead of trying (and failing) to `cd` there.
- It ran all three steps (`init`, `plan`, `apply`) in order without being told the exact
  sequence — that's the system prompt's "call once per step, report each result"
  instruction working as intended.
- It added `-auto-approve` to the `apply` call on its own (reasonable: this subprocess
  has no terminal for Terraform's own interactive "yes" prompt to work) — **and it made
  no difference**, because our approval gate is a completely separate mechanism from
  Terraform's own confirmation prompt. `-auto-approve` skips Terraform asking; it does
  nothing to `run_command`'s own `interrupt()` check, which still fired and still
  blocked until a human answered.

## Notes

- `agent_memory.sqlite` (created on first run) is the conversation checkpoint database,
  keyed by `--thread` — gitignored, safe to delete to reset all conversation history.
- `check_process_running(name)` matches against the full command line via `pgrep -fl`,
  not just the process's own binary name — so `"api_server.py"` works even though the
  actual binary running is `python`.
- `run_command` parses with `shlex.split`, not `shell=True` — deliberately: no pipes,
  `&&`, `;`, or `$()` command substitution work, which also means those can't be used
  to smuggle a second, unapproved command alongside an approved-looking one.
- `interrupt()` requires a checkpointer to work at all (it's what persists the paused
  state across the pause) — this project already had `SqliteSaver` wired in for
  conversation memory, which is exactly what makes the approval gate possible with no
  other structural change to `graph.py`.

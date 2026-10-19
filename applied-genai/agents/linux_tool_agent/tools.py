"""Tools for the Local Ops Agent.

Same `@tool` pattern as `../langgraph_ollama_agent/tools.py`: a plain Python function,
type-hinted, with a docstring -- LangChain turns the docstring into the description the
LLM actually sees when deciding whether to call this tool, so it has to be accurate,
not just a comment for humans. `graph.py` wires these into the actual StateGraph.
"""

from __future__ import annotations

import os
import shlex
import subprocess

from langchain_core.tools import tool
from langgraph.types import interrupt

# Command prefixes considered safe enough to run without asking a human first -- all
# read-only, nothing here can change state. Matched by leading tokens, e.g. ("git",
# "status") only matches "git status ...", not "git commit ...". Anything NOT matching
# one of these prefixes is treated as unsafe by default (allowlist, not a denylist --
# safer, since an unlisted command fails closed into "ask a human" instead of silently
# running).
SAFE_COMMAND_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("ls",), ("cat",), ("head",), ("tail",), ("df",), ("free",),
    ("pgrep",), ("ps",), ("whoami",), ("uname",), ("date",), ("pwd",), ("echo",),
    ("git", "status"), ("git", "log"), ("git", "diff"),
    ("docker", "ps"), ("kubectl", "get"),
)


def _is_safe(tokens: list[str]) -> bool:
    return any(tuple(tokens[: len(prefix)]) == prefix for prefix in SAFE_COMMAND_PREFIXES)


@tool
def create_plan(steps: list[str]) -> str:
    """Write out a short, numbered plan for a task that will need more than one tool
    call, BEFORE executing any of it, so the human can see what you intend to do.
    Call this once at the start of any multi-step task, then actually execute each
    step in order using the other tools -- this tool only records the plan, it doesn't
    do anything itself."""
    numbered = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(steps))
    return f"Plan ({len(steps)} steps):\n{numbered}"


@tool
def check_disk_usage() -> str:
    """Check free disk space on the root filesystem. Use this when asked about disk
    space, storage, or how full the disk is."""
    result = subprocess.run(
        ["df", "-h", "/"], capture_output=True, text=True, timeout=5,
    )
    if result.returncode != 0:
        return f"Failed to check disk usage: {result.stderr.strip()}"
    return result.stdout.strip()


@tool
def check_memory() -> str:
    """Check available and free RAM on this machine. Use this when asked about memory,
    RAM, or whether there's enough memory free to do something."""
    result = subprocess.run(
        ["free", "-h"], capture_output=True, text=True, timeout=5,
    )
    if result.returncode != 0:
        return f"Failed to check memory: {result.stderr.strip()}"
    return result.stdout.strip()


@tool
def check_process_running(name: str) -> str:
    """Check whether a process matching `name` is currently running on this machine.
    `name` is matched against the full command line (e.g. "api_server.py", "ollama"),
    not just the process's own binary name. Use this when asked if something is
    running, up, or still alive."""
    result = subprocess.run(
        ["pgrep", "-fl", name], capture_output=True, text=True, timeout=5,
    )
    if result.returncode != 0:
        return f"No process matching '{name}' is currently running."
    return f"Process(es) matching '{name}':\n{result.stdout.strip()}"


@tool
def list_directory(path: str = ".") -> str:
    """List files and subdirectories at `path` (defaults to the current directory),
    like `ls -la`. Use this to see what's inside a directory before deciding to read a
    specific file."""
    result = subprocess.run(
        ["ls", "-la", path], capture_output=True, text=True, timeout=5,
    )
    if result.returncode != 0:
        return f"Failed to list '{path}': {result.stderr.strip()}"
    return result.stdout.strip()


@tool
def read_file(path: str, max_lines: int = 200) -> str:
    """Read and return up to `max_lines` (default 200) lines from the text file at
    `path`. Use this to review a file's contents -- a config file, a script, a log.
    Refuses directories (use list_directory instead)."""
    try:
        with open(path, "r", errors="replace") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append(f"... (truncated at {max_lines} lines)")
                    break
                lines.append(line)
    except FileNotFoundError:
        return f"File not found: '{path}'"
    except IsADirectoryError:
        return f"'{path}' is a directory, not a file -- use list_directory instead."
    except OSError as exc:
        return f"Failed to read '{path}': {exc}"
    return "".join(lines).strip() or "(file is empty)"


@tool
def create_directory(path: str) -> str:
    """Create a new directory at `path`, including any missing parent directories
    (like `mkdir -p`). Refuses if `path` already exists as a file. Creating a
    directory changes the filesystem, so it requires human approval, same as
    run_command's approval gate."""
    if os.path.isdir(path):
        return f"'{path}' already exists as a directory -- nothing to do."
    if os.path.exists(path):
        return f"'{path}' already exists as a file, not a directory -- refusing."

    decision = interrupt(
        {
            "reason": "Creating a directory changes the filesystem and needs human approval.",
            "command": f"create_directory({path})",
        }
    )
    if str(decision).strip().lower() not in {"y", "yes", "approve", "approved"}:
        return f"Directory creation NOT approved by a human -- not created: {path}"

    try:
        os.makedirs(path, exist_ok=True)
    except OSError as exc:
        return f"Failed to create directory '{path}': {exc}"
    return f"Created directory: {path}"


@tool
def write_file(path: str, content: str, overwrite: bool = False) -> str:
    """Write `content` to a new text file at `path`. Refuses to overwrite an existing
    file unless `overwrite=True` is explicitly set. Writing a file changes the
    filesystem, so it requires human approval, same as run_command's approval gate."""
    if os.path.isdir(path):
        return f"'{path}' is a directory, not a file -- cannot write to it."
    if os.path.exists(path) and not overwrite:
        return f"'{path}' already exists -- refusing to overwrite (pass overwrite=True to force)."

    decision = interrupt(
        {
            "reason": "Writing a file changes the filesystem and needs human approval.",
            "command": f"write_file({path}, {len(content)} chars, overwrite={overwrite})",
        }
    )
    if str(decision).strip().lower() not in {"y", "yes", "approve", "approved"}:
        return f"File write NOT approved by a human -- not written: {path}"

    try:
        with open(path, "w") as f:
            f.write(content)
    except OSError as exc:
        return f"Failed to write '{path}': {exc}"
    return f"Wrote {len(content)} characters to {path}"


@tool
def run_command(command: str, cwd: str = ".") -> str:
    """Run an arbitrary shell command in directory `cwd` (defaults to this agent's own
    working directory -- pass an absolute path to run somewhere else, e.g. a Terraform
    project directory) and return its combined output. Known safe, read-only commands
    (ls, cat, df, free, git status, kubectl get, ...) run immediately. Anything else --
    especially anything that changes state, like `terraform apply` or `terraform plan`
    -- pauses this tool call and requires explicit human approval before it actually
    runs. If a human declines, the command is not executed and that fact is reported
    back, not treated as an error to retry. No shell operators (&&, ;, |, $()) work --
    run one command per call, using `cwd` instead of `cd path && ...`."""
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        return f"Could not parse command: {exc}"
    if not tokens:
        return "Empty command."
    if not os.path.isdir(cwd):
        return f"cwd '{cwd}' is not a directory."

    if not _is_safe(tokens):
        decision = interrupt(
            {
                "reason": "This command is not on the pre-approved safe list and needs human approval before running.",
                "command": command,
                "cwd": cwd,
            }
        )
        if str(decision).strip().lower() not in {"y", "yes", "approve", "approved"}:
            return f"Command NOT approved by a human -- not executed: {command} (cwd={cwd})"

    result = subprocess.run(tokens, cwd=cwd, capture_output=True, text=True, timeout=120)
    output = result.stdout.strip() or "(no output)"
    if result.returncode != 0:
        return f"Command exited with code {result.returncode}:\n{output}\n{result.stderr.strip()}".strip()
    return output


ALL_TOOLS = [
    create_plan,
    check_disk_usage,
    check_memory,
    check_process_running,
    list_directory,
    read_file,
    create_directory,
    write_file,
    run_command,
]

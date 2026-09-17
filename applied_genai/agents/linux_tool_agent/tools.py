"""Tools for the Local Ops Agent.

Same `@tool` pattern as `../langgraph_ollama_agent/tools.py`: a plain Python function,
type-hinted, with a docstring -- LangChain turns the docstring into the description the
LLM actually sees when deciding whether to call this tool, so it has to be accurate,
not just a comment for humans. `graph.py` wires these into the actual StateGraph.
"""

from __future__ import annotations

import subprocess

from langchain_core.tools import tool


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


ALL_TOOLS = [check_disk_usage, check_memory, check_process_running]

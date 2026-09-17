#!/usr/bin/env python3
"""Minimal local MCP server for personal task management."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from task_store import add_task, complete_task, list_tasks

mcp = FastMCP("local-tasks")


@mcp.tool()
def mcp_list_tasks() -> str:
    """Return all tasks and their completion state."""
    return list_tasks()


@mcp.tool()
def mcp_add_task(title: str) -> str:
    """Add a new task by title."""
    return add_task(title)


@mcp.tool()
def mcp_complete_task(task_id: int) -> str:
    """Mark a task as complete by id."""
    return complete_task(task_id)


if __name__ == "__main__":
    mcp.run()

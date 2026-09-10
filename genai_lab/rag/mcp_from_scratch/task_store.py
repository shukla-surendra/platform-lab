"""A tiny standalone task store, mirroring ../bedrock_agentcore_demo/task_store.py's shape so the tool set here matches
../bedrock_agentcore_demo/tasks_mcp_server.py's exactly (list_tasks, add_task, complete_task) -- same tools, same
behavior, different protocol implementation underneath. This copy is deliberately independent
(its own tasks.json) so this project stays self-contained like every other project in this repo.
"""

from __future__ import annotations

import json
from pathlib import Path

TASKS_FILE = Path(__file__).with_name("tasks.json")


def load_tasks() -> list[dict[str, object]]:
    if not TASKS_FILE.exists():
        return []
    try:
        data = json.loads(TASKS_FILE.read_text())
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def save_tasks(tasks: list[dict[str, object]]) -> None:
    TASKS_FILE.write_text(json.dumps(tasks, indent=2))


def list_tasks() -> str:
    tasks = load_tasks()
    if not tasks:
        return "No tasks yet."
    lines = []
    for task in tasks:
        status = "done" if task.get("done") else "open"
        lines.append(f"{task['id']}. [{status}] {task['title']}")
    return "\n".join(lines)


def add_task(title: str) -> str:
    tasks = load_tasks()
    next_id = max((int(task["id"]) for task in tasks), default=0) + 1
    task = {"id": next_id, "title": title.strip(), "done": False}
    tasks.append(task)
    save_tasks(tasks)
    return f"Added task {next_id}: {task['title']}"


def complete_task(task_id: int) -> str:
    tasks = load_tasks()
    for task in tasks:
        if int(task["id"]) == task_id:
            task["done"] = True
            save_tasks(tasks)
            return f"Completed task {task_id}: {task['title']}"
    return f"Task {task_id} not found."

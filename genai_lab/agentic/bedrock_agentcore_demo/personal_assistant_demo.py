#!/usr/bin/env python3
"""Minimal local personal assistant demo backed by Ollama."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from json import JSONDecoder

from task_store import add_task, complete_task, list_tasks

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"

TOOLS = {
    "list_tasks": lambda args: list_tasks(),
    "add_task": lambda args: add_task(str(args["title"])),
    "complete_task": lambda args: complete_task(int(args["task_id"])),
}


def call_ollama(prompt: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Could not reach Ollama at http://127.0.0.1:11434. "
            "Make sure `ollama serve` is running."
        ) from exc
    return str(body.get("response", "")).strip()


def build_prompt(user_prompt: str, scratchpad: list[str]) -> str:
    tool_guide = """
You are a concise personal assistant.

You can use these tools:
- list_tasks()
- add_task(title: string)
- complete_task(task_id: integer)

When you want to use a tool, respond with JSON only in this exact format:
{"action":"tool","name":"add_task","arguments":{"title":"buy milk"}}

When you are done, respond with JSON only in this exact format:
{"action":"final","answer":"your reply here"}

You may emit multiple JSON objects, one per line, if several tool calls are needed.
Do not wrap JSON in markdown.
""".strip()
    history = "\n".join(scratchpad) if scratchpad else "No previous tool calls."
    return f"{tool_guide}\n\nTool history:\n{history}\n\nUser request: {user_prompt}"


def parse_actions(raw: str) -> list[dict[str, object]]:
    decoder = JSONDecoder()
    idx = 0
    actions: list[dict[str, object]] = []

    while idx < len(raw):
        while idx < len(raw) and raw[idx] != "{":
            idx += 1
        if idx >= len(raw):
            break
        try:
            obj, next_idx = decoder.raw_decode(raw, idx)
        except json.JSONDecodeError:
            idx += 1
            continue
        if isinstance(obj, dict) and obj.get("action") in {"tool", "final"}:
            actions.append(obj)
        idx = next_idx

    return actions


def normalize_action(action: dict[str, object]) -> dict[str, object] | None:
    kind = action.get("action")
    if kind in {"tool", "final"}:
        return action

    if isinstance(kind, str) and kind in TOOLS:
        return {
            "action": "tool",
            "name": kind,
            "arguments": action.get("arguments", {}),
        }

    return None


def run_assistant(prompt: str) -> str:
    scratchpad: list[str] = []
    last_tool_result = ""

    for _ in range(6):
        raw = call_ollama(build_prompt(prompt, scratchpad))
        actions = parse_actions(raw)
        if not actions:
            return raw.strip() or last_tool_result or "I could not produce a valid response."

        normalized_actions = [
            normalized
            for action in actions
            if (normalized := normalize_action(action)) is not None
        ]
        if not normalized_actions:
            return raw.strip() or last_tool_result or "I could not produce a valid response."

        for action in normalized_actions:
            if action.get("action") == "final":
                return str(action.get("answer", "")).strip()

            if action.get("action") != "tool":
                return raw

            tool_name = action.get("name")
            tool_args = action.get("arguments", {})
            tool = TOOLS.get(str(tool_name))
            if tool is None:
                scratchpad.append(f"Tool error: unknown tool '{tool_name}'.")
                continue

            try:
                result = tool(tool_args)
            except Exception as exc:
                result = f"Tool error: {exc}"

            last_tool_result = result
            scratchpad.append(
                f"Called {tool_name} with {json.dumps(tool_args)} -> {result}"
            )

    return last_tool_result or "I stopped after too many tool steps. Please try a simpler request."


def main() -> int:
    prompt = (
        " ".join(sys.argv[1:]).strip()
        if len(sys.argv) > 1
        else "Add a task to review LangGraph, then show my tasks."
    )
    try:
        print(run_assistant(prompt))
    except RuntimeError as exc:
        print(exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Tools the agent can call. Each is a plain Python function exposed via LangChain's
`@tool` decorator, which turns the type hints and docstring into the JSON schema the
model sees. Keeping the implementations plain (no framework calls inside) makes them
easy to unit-test on their own.
"""

from __future__ import annotations

import ast
import json
import operator
from datetime import datetime, timezone

from langchain_core.tools import tool

import genai_lab.agentic.langgraph_ollama_agent.config as config

_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


@tool
def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression, e.g. "17 * 9" or "(4 + 2) / 3".

    Supports + - * / // % ** and parentheses. No variables or functions.
    """
    try:
        parsed = ast.parse(expression, mode="eval")
        return f"{expression} = {_safe_eval(parsed.body):g}"
    except Exception as exc:
        return f"Could not evaluate '{expression}': {exc}"


def _load_notes() -> list[dict[str, object]]:
    if not config.NOTES_FILE.exists():
        return []
    try:
        data = json.loads(config.NOTES_FILE.read_text())
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _save_notes(notes: list[dict[str, object]]) -> None:
    config.NOTES_FILE.write_text(json.dumps(notes, indent=2))


@tool
def add_note(text: str) -> str:
    """Save a short note to persistent local storage, for facts to remember across sessions."""
    notes = _load_notes()
    next_id = max((int(n["id"]) for n in notes), default=0) + 1
    notes.append({"id": next_id, "text": text.strip(), "created": datetime.now(timezone.utc).isoformat()})
    _save_notes(notes)
    return f"Saved note {next_id}."


@tool
def list_notes() -> str:
    """List all previously saved notes, most recent last."""
    notes = _load_notes()
    if not notes:
        return "No notes saved yet."
    return "\n".join(f"{n['id']}. {n['text']}" for n in notes)


@tool
def search_notes(query: str) -> str:
    """Search saved notes for a keyword and return matching ones."""
    query_lower = query.lower()
    matches = [n for n in _load_notes() if query_lower in str(n["text"]).lower()]
    if not matches:
        return f"No notes matching '{query}'."
    return "\n".join(f"{n['id']}. {n['text']}" for n in matches)


@tool
def search_knowledge(query: str) -> str:
    """Search the local knowledge base (markdown files in knowledge/) for a keyword and
    return matching lines with their source file, for grounding answers in local documents.
    """
    if not config.KNOWLEDGE_DIR.exists():
        return "Knowledge directory does not exist."

    query_lower = query.lower()
    hits: list[str] = []
    for path in sorted(config.KNOWLEDGE_DIR.glob("*.md")):
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if query_lower in line.lower():
                hits.append(f"{path.name}:{lineno}: {line.strip()}")
        if len(hits) >= 8:
            break

    if not hits:
        return f"No matches for '{query}' in {config.KNOWLEDGE_DIR.name}/."
    return "\n".join(hits[:8])


@tool
def current_datetime() -> str:
    """Return the current UTC date and time, for questions that depend on "today"."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


ALL_TOOLS = [calculator, add_note, list_notes, search_notes, search_knowledge, current_datetime]

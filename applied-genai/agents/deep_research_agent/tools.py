"""Read-only tools over the notes corpus (config.NOTES_ROOT).

These are the agent's only window onto the real disk. Everything the agent *writes* goes to
deepagents' virtual filesystem (graph state), which agent.py saves to output/ at the end.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from langchain_core.tools import tool

import config

TEXT_SUFFIXES = {".md", ".py", ".txt", ".yaml", ".yml", ".toml", ".tf", ".sh", ".go", ".rs"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "site", "__pycache__", ".ipynb_checkpoints", "output"}
MAX_FILE_BYTES = 300_000


def _iter_files():
    for dirpath, dirnames, filenames in os.walk(config.NOTES_ROOT):  # doesn't follow symlinks
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix in TEXT_SUFFIXES and path.stat().st_size <= MAX_FILE_BYTES:
                yield path


def _resolve(rel_path: str) -> Path:
    path = (config.NOTES_ROOT / rel_path).resolve()
    if not path.is_relative_to(config.NOTES_ROOT):
        raise ValueError(f"{rel_path!r} is outside the notes root")
    return path


@tool
def search_notes(query: str, max_results: int = 8) -> str:
    """Keyword-search the user's notes and code. Returns matching file paths (relative to the
    notes root), a relevance score, and a few matching lines. Use short, specific keywords,
    e.g. "event loop threadpool" rather than full questions."""
    terms = [t for t in re.findall(r"\w+", query.lower()) if len(t) > 2]
    if not terms:
        return "Query has no usable keywords."
    hits = []
    for path in _iter_files():
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        lower = text.lower()
        # Count each term, and require most terms to appear so one common word can't dominate.
        counts = [lower.count(t) for t in terms]
        if sum(c > 0 for c in counts) < max(1, (len(terms) + 1) // 2):
            continue
        score = sum(counts) + 5 * sum(t in path.name.lower() for t in terms)
        lines = [ln.strip() for ln in text.splitlines() if any(t in ln.lower() for t in terms)][:3]
        hits.append((score, path.relative_to(config.NOTES_ROOT), lines))
    if not hits:
        return f"No matches for {query!r}."
    hits.sort(key=lambda h: h[0], reverse=True)
    out = []
    for score, rel, lines in hits[:max_results]:
        snippet = "\n".join(f"    {ln[:160]}" for ln in lines)
        out.append(f"{rel}  (score {score})\n{snippet}")
    return "\n".join(out)


@tool
def read_note(path: str, offset: int = 0, limit: int = 200) -> str:
    """Read a file from the notes, by the relative path that search_notes returned. Returns
    `limit` lines starting at line `offset` (0-based), each prefixed with its line number."""
    try:
        file = _resolve(path)
        lines = file.read_text(errors="ignore").splitlines()
    except (OSError, ValueError) as exc:
        return f"Error: {exc}"
    chunk = lines[offset : offset + limit]
    body = "\n".join(f"{offset + i + 1:5}| {ln}" for i, ln in enumerate(chunk))
    more = f"\n... {len(lines) - offset - limit} more lines" if offset + limit < len(lines) else ""
    return f"{path} ({len(lines)} lines)\n{body}{more}"

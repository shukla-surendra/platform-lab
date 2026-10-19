"""The deep agent: a planner/writer that delegates research to subagents.

`create_deep_agent` builds a LangGraph graph (an agent loop with middleware) and adds four things
a plain ReAct agent lacks. These are what make it "deep":

  1. Planning:    a `write_todos` tool; the plan lives in graph state as `todos`.
                  (Opt-in since deepagents 0.7: we add TodoListMiddleware ourselves below.)
  2. Filesystem:  `ls` / `read_file` / `write_file` / `edit_file` / `glob` / `grep` over a
                  *virtual* filesystem stored in graph state as `files` (nothing touches disk).
  3. Subagents:   a `task` tool that runs a subagent in its own fresh context window and returns
                  only its final answer. This keeps the main agent's context small.
  4. A long system prompt teaching the model to use all of the above.

Our own tools (search_notes / read_note) are the only access to the real disk, and they're
read-only.
"""

from __future__ import annotations

from deepagents import SubAgent, create_deep_agent
from langchain.agents.middleware import TodoListMiddleware

import config
from llm import get_chat_model
from tools import read_note, search_notes

RESEARCHER_PROMPT = """You are a researcher working over the user's personal engineering notes and code.

You get ONE focused research question. Use search_notes with a few different keyword sets, then
read_note on the most promising files (read only the relevant parts). Prefer the user's own
explanations and observed results over general knowledge.

Reply with concise findings (bullet points, max ~250 words). Cite every claim with the source
path in backticks, e.g. `fastapi_practice/client_disconnect_lab/README.md`. If the notes don't
cover something, say so explicitly instead of filling the gap from memory."""

CRITIC_PROMPT = """You are a strict technical reviewer. Read /report.md with read_file.
The cited source paths are real files in the user's notes: verify the important claims with
read_note (they are NOT in the virtual filesystem, so don't grep for them there).

Check it for: claims without a source path, contradictions, vague statements, missing pieces of
the original question (given to you in the task), and anything that sounds made up.
Do NOT edit the file. Reply with a short numbered list of concrete fixes, most important first,
or "LGTM" if there's nothing worth fixing."""

MAIN_PROMPT = f"""You write study guides from the user's own engineering notes.
The notes live in a repo at {config.NOTES_ROOT.name}/ and you can only reach them through
subagents and your search_notes/read_note tools.

Workflow:
1. Your FIRST tool call must be write_todos with a short plan (3-6 items). Call write_todos
   again to mark items in_progress/completed as you go. Don't put the plan in a file.
2. Split the question into 2-4 independent subtopics. Delegate each one to the `researcher`
   subagent with the `task` tool. Launch independent research tasks in parallel (several `task`
   calls in one turn).
3. Save the raw findings to /research_notes.md with write_file.
4. Write the study guide to /report.md: a TL;DR, then sections, with source paths in backticks
   for each claim, ending with a "Gaps in the notes" section.
5. Ask the `critic` subagent to review /report.md. Apply its fixes with edit_file.
6. Final answer: 3-5 sentences summarising the guide. The user reads the full file separately."""


def build_agent():
    subagents: list[SubAgent] = [
        {
            "name": "researcher",
            "description": "Researches ONE focused question in the user's notes/code and returns cited findings. Give it a self-contained question.",
            "system_prompt": RESEARCHER_PROMPT,
            "tools": [search_notes, read_note],
            "model": get_chat_model(config.SUBAGENT_MODEL),
        },
        {
            "name": "critic",
            "description": "Reviews /report.md against the original question and returns a list of fixes. Include the original question in the task.",
            "system_prompt": CRITIC_PROMPT,
            # Also gets the built-in filesystem tools, so it can read /report.md from shared state.
            "tools": [search_notes, read_note],
            "model": get_chat_model(config.SUBAGENT_MODEL),
        },
    ]
    return create_deep_agent(
        model=get_chat_model(),
        tools=[search_notes, read_note],
        system_prompt=MAIN_PROMPT,
        subagents=subagents,
        middleware=[TodoListMiddleware()],
        name="deep-research-agent",
    )

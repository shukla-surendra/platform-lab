"""The agent graph: same two-node ReAct loop as
`../langgraph_ollama_agent/graph.py`:

    START -> agent -> (tools_condition) -> tools -> agent -> ... -> END

`agent` is an OpenAI chat model with the three ops tools bound via `bind_tools`, so it
decides on its own, per turn, whether to call a tool or answer directly. `tools`
executes whatever tool calls the model requested and feeds the results back as
messages. Same graph shape as the Ollama version -- only which chat model class gets
built changes; `bind_tools`/`.invoke` work identically across LangChain chat models,
which is the whole point of that common interface.
"""

from __future__ import annotations

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

import config
from tools import ALL_TOOLS

# Without this, the model either describes shell steps in prose instead of calling
# tools (observed live: asked to "deploy" a Terraform config, it wrote a 5-step manual
# guide instead of calling run_command), or stops after one tool call to ask "should I
# continue?" instead of autonomously working through a whole multi-step task the way a
# real coding agent does. The model isn't wrong to be cautious, it just doesn't know
# run_command *already has* a human-approval gate built in (tools.py's interrupt() on
# anything not in SAFE_COMMAND_PREFIXES) -- so asking again in chat first, or stopping
# between steps, is redundant caution, not extra safety. This prompt exists to close
# both gaps: call tools directly, plan multi-step work with create_plan, then execute
# the whole plan without stopping.
SYSTEM_PROMPT = (
    "You are a Local Ops Agent with real, working tools that act directly on this "
    "machine: create_plan, check_disk_usage, check_memory, check_process_running, "
    "list_directory, read_file, create_directory, write_file, and run_command (runs "
    "any shell command). Prefer create_directory/write_file over run_command for "
    "making a directory or writing file content -- run_command has no shell "
    "redirection, so it cannot write file contents at all.\n\n"
    "When asked to run, deploy, apply, check, or investigate something, CALL THE "
    "TOOLS DIRECTLY -- do not respond with a list of shell commands for the human to "
    "type themselves; you have real access, use it.\n\n"
    "For ANY task that will need more than one tool call: first call create_plan with "
    "a short numbered list of the steps, then execute every step yourself, in order, "
    "one tool call at a time, reporting each result before moving to the next. Do NOT "
    "stop partway through to ask 'should I continue?' or 'do you want me to proceed?' "
    "-- keep going autonomously until the whole task is actually done. The ONLY thing "
    "that should ever pause you mid-task is run_command's own approval gate (below) -- "
    "that is a separate, real mechanism the human is prompted for directly. Only stop "
    "and ask the human yourself if you are genuinely blocked on missing information no "
    "tool can give you.\n\n"
    "run_command already pauses for explicit human approval automatically before "
    "running anything not on its own pre-approved safe list (e.g. `terraform apply`) "
    "-- you do not need to ask for confirmation in chat before calling it; call it, "
    "and let its own approval gate handle anything that needs one.\n\n"
    "Pass a target directory as run_command's `cwd` argument (not `cd path && ...` -- "
    "shell operators like && don't work; one command per call, run in `cwd`)."
)


def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=config.OPENAI_MODEL,
        temperature=config.MODEL_TEMPERATURE,
    ).bind_tools(ALL_TOOLS)


def agent_node(state: MessagesState, llm: ChatOpenAI) -> MessagesState:
    messages = state["messages"]
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT), *messages]
    response = llm.invoke(messages)
    return {"messages": [response]}


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    llm = build_llm()

    graph = StateGraph(MessagesState)
    graph.add_node("agent", lambda state: agent_node(state, llm))
    graph.add_node("tools", ToolNode(ALL_TOOLS))

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile(checkpointer=checkpointer)

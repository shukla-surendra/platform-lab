"""The agent graph: two nodes wired into the standard LangGraph ReAct loop.

    START -> agent -> (tools_condition) -> tools -> agent -> ... -> END

Identical shape to `../langgraph_ollama_agent/graph.py` - same StateGraph, same
tools_condition routing. Only `tools.py`'s contents differ (real Kubernetes API calls
instead of local JSON/knowledge-base tools).
"""

from __future__ import annotations

from langchain_ollama import ChatOllama
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

import config
from tools import ALL_TOOLS

SYSTEM_PROMPT = (
    "You are a Kubernetes on-call assistant. You investigate real cluster state using the "
    "tools available - you do not guess at status, restart counts, or log contents; always "
    "call a tool to check. Work like a careful SRE: check what's unhealthy first, then look at "
    "events and logs to find root cause before proposing or taking any remediation action. "
    "Only call restart_deployment once you can state a specific reason it will help."
)


def build_llm() -> ChatOllama:
    return ChatOllama(
        model=config.OLLAMA_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        temperature=config.MODEL_TEMPERATURE,
    ).bind_tools(ALL_TOOLS)


def agent_node(state: MessagesState, llm: ChatOllama) -> MessagesState:
    messages = state["messages"]
    if not messages or messages[0].type != "system":
        messages = [("system", SYSTEM_PROMPT), *messages]
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

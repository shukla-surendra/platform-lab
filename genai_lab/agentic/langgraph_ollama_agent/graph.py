"""The agent graph: two nodes wired into the standard LangGraph ReAct loop.

    START -> agent -> (tools_condition) -> tools -> agent -> ... -> END

`agent` is a local Ollama chat model with tools bound via `bind_tools`, so it decides
on its own, per turn, whether to call a tool or answer directly. `tools` executes
whatever tool calls the model requested and feeds the results back as messages. This
is built explicitly with `StateGraph` rather than `create_react_agent` so the loop is
visible instead of hidden behind a helper.
"""

from __future__ import annotations

from langchain_ollama import ChatOllama
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

import genai_lab.agentic.langgraph_ollama_agent.config as config
from genai_lab.agentic.langgraph_ollama_agent.tools import ALL_TOOLS


def build_llm() -> ChatOllama:
    return ChatOllama(
        model=config.OLLAMA_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        temperature=config.MODEL_TEMPERATURE,
    ).bind_tools(ALL_TOOLS)


def agent_node(state: MessagesState, llm: ChatOllama) -> MessagesState:
    response = llm.invoke(state["messages"])
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

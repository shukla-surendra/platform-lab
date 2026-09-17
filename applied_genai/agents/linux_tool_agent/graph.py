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

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

import config
from tools import ALL_TOOLS


def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=config.OPENAI_MODEL,
        temperature=config.MODEL_TEMPERATURE,
    ).bind_tools(ALL_TOOLS)


def agent_node(state: MessagesState, llm: ChatOpenAI) -> MessagesState:
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

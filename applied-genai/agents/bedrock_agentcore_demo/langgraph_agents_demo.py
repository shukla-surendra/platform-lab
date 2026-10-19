#!/usr/bin/env python3
"""Sample LangGraph multi-agent demo.

This example wires together four simple "agents":
- planner: decides which specialist agents should run
- researcher: provides lightweight factual context
- calculator: solves arithmetic expressions found in the question
- writer: synthesizes the final answer

Run:
  python langgraph_agents_demo.py "What is LangGraph and what is 17 * 9?"
"""

from __future__ import annotations

import ast
import operator
import re
import sys
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from typing_extensions import NotRequired


class AgentState(TypedDict):
    question: str
    remaining_agents: list[str]
    notes: list[str]
    math_result: NotRequired[str]
    final_answer: NotRequired[str]


def planner_agent(state: AgentState) -> AgentState:
    question = state["question"].lower()

    needs_math = bool(re.search(r"\d+\s*[+\-*/]\s*\d+", question))
    needs_research = any(
        token in question
        for token in [
            "what",
            "who",
            "when",
            "where",
            "why",
            "how",
            "explain",
            "tell me",
            "langgraph",
            "agent",
        ]
    )

    queue: list[str] = []
    if needs_research:
        queue.append("researcher")
    if needs_math:
        queue.append("calculator")
    if not queue:
        queue = ["researcher"]

    return {
        **state,
        "remaining_agents": queue,
        "notes": [
            *state.get("notes", []),
            f"Planner selected: {', '.join(queue)}",
        ],
    }


def router(state: AgentState) -> Literal["researcher", "calculator", "writer"]:
    if not state["remaining_agents"]:
        return "writer"
    return state["remaining_agents"][0]  # type: ignore[return-value]


def _knowledge_lookup(question: str) -> str:
    q = question.lower()

    if "langgraph" in q:
        return (
            "LangGraph is a framework for building stateful, multi-step agent workflows "
            "as graphs where nodes are actions/agents and edges define control flow."
        )
    if "agent" in q:
        return (
            "An AI agent is a system that can decide actions, use tools, and iterate "
            "toward a goal instead of producing only one-shot text."
        )
    return "No specific lookup hit. I will answer from general context."


def researcher_agent(state: AgentState) -> AgentState:
    insight = _knowledge_lookup(state["question"])
    remaining = state["remaining_agents"][1:] if state["remaining_agents"] else []
    return {
        **state,
        "remaining_agents": remaining,
        "notes": [*state["notes"], f"Researcher note: {insight}"],
    }


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
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _ALLOWED_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Unsupported expression")


def _extract_expression(question: str) -> str | None:
    match = re.search(r"(\d+(?:\s*[+\-*/]\s*\d+)+)", question)
    if match:
        return match.group(1)
    return None


def calculator_agent(state: AgentState) -> AgentState:
    expr = _extract_expression(state["question"])
    remaining = state["remaining_agents"][1:] if state["remaining_agents"] else []

    if not expr:
        result = "No arithmetic expression detected."
    else:
        try:
            parsed = ast.parse(expr, mode="eval")
            value = _safe_eval(parsed.body)
            result = f"{expr} = {value:g}"
        except Exception as exc:  # pragma: no cover - demo safety path
            result = f"Could not evaluate expression '{expr}': {exc}"

    return {
        **state,
        "remaining_agents": remaining,
        "math_result": result,
        "notes": [*state["notes"], f"Calculator note: {result}"],
    }


def writer_agent(state: AgentState) -> AgentState:
    lines = [f"Question: {state['question']}"]

    research_lines = [n for n in state["notes"] if n.startswith("Researcher note:")]
    if research_lines:
        lines.append(research_lines[-1].replace("Researcher note: ", "Context: "))

    if state.get("math_result"):
        lines.append(f"Math: {state['math_result']}")

    lines.append("Workflow trace:")
    lines.extend(f"- {note}" for note in state["notes"])

    final = "\n".join(lines)
    return {**state, "final_answer": final}


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_agent)
    graph.add_node("researcher", researcher_agent)
    graph.add_node("calculator", calculator_agent)
    graph.add_node("writer", writer_agent)

    graph.add_edge(START, "planner")
    graph.add_conditional_edges("planner", router)
    graph.add_conditional_edges("researcher", router)
    graph.add_conditional_edges("calculator", router)
    graph.add_edge("writer", END)

    return graph.compile()


def run_demo(question: str) -> str:
    app = build_graph()
    initial_state: AgentState = {
        "question": question,
        "remaining_agents": [],
        "notes": [],
    }
    result = app.invoke(initial_state)
    return result["final_answer"]


def main() -> int:
    question = (
        " ".join(sys.argv[1:]).strip()
        if len(sys.argv) > 1
        else "What is LangGraph and what is 17 * 9?"
    )
    print(run_demo(question))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

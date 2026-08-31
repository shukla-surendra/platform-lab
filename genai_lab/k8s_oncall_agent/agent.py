#!/usr/bin/env python3
"""CLI for the local LangGraph + Ollama Kubernetes on-call agent.

Single-shot:
  python agent.py "What's unhealthy in the checkout namespace?"

Multi-turn REPL (conversation persists across process restarts, keyed by --thread -
this is the memory: ask a follow-up in a new process and it still remembers what it
already found):
  python agent.py
  python agent.py --thread incident-42

Streaming (print each tool call/result as it happens, instead of just the final answer):
  python agent.py --stream "Investigate the checkout namespace"
"""

from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.sqlite import SqliteSaver

import config
from graph import build_graph


@contextmanager
def get_app():
    with SqliteSaver.from_conn_string(config.CHECKPOINT_DB) as checkpointer:
        yield build_graph(checkpointer=checkpointer)


def _run_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": config.RECURSION_LIMIT}


def ask(app, prompt: str, thread_id: str, stream: bool) -> str:
    run_config = _run_config(thread_id)
    inputs = {"messages": [("user", prompt)]}

    if not stream:
        result = app.invoke(inputs, config=run_config)
        return result["messages"][-1].content

    final_answer = ""
    for update in app.stream(inputs, config=run_config, stream_mode="updates"):
        for node, payload in update.items():
            for message in payload.get("messages", []):
                if isinstance(message, AIMessage) and message.tool_calls:
                    for call in message.tool_calls:
                        print(f"  [{node}] -> call {call['name']}({call['args']})")
                elif isinstance(message, ToolMessage):
                    print(f"  [{node}] <- {message.name}: {message.content}")
                elif isinstance(message, AIMessage) and message.content:
                    final_answer = message.content
    return final_answer


def repl(app, thread_id: str, stream: bool) -> None:
    print(f"K8s on-call agent ({config.OLLAMA_MODEL}). Thread: '{thread_id}'. Ctrl-D to exit.")
    while True:
        try:
            prompt = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not prompt:
            continue
        answer = ask(app, prompt, thread_id, stream)
        print(f"agent> {answer}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Local LangGraph + Ollama K8s on-call agent")
    parser.add_argument("prompt", nargs="*", help="One-shot prompt. Omit to start a REPL.")
    parser.add_argument("--thread", default="default", help="Conversation thread id (default: 'default')")
    parser.add_argument("--stream", action="store_true", help="Print tool calls/results as they happen")
    args = parser.parse_args()

    try:
        with get_app() as app:
            if args.prompt:
                print(ask(app, " ".join(args.prompt), args.thread, args.stream))
            else:
                repl(app, args.thread, args.stream)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(
            "Make sure `ollama serve` is running, the model in .env / config.py is pulled "
            f"(`ollama pull {config.OLLAMA_MODEL}`), and `kubectl get nodes` works against "
            "the cluster you want this agent to investigate.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

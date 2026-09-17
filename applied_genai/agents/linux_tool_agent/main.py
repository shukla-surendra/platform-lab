#!/usr/bin/env python3
"""CLI for the Local Ops Agent.

Single-shot:
  python main.py "How much free disk space do I have?"

Multi-turn REPL (conversation persists across process restarts, keyed by --thread):
  python main.py
  python main.py --thread checks

Streaming (print each tool call/result as it happens, instead of just the final answer):
  python main.py --stream "Is api_server.py running, and do I have enough RAM for a 1.7B model?"
"""

from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from graph import build_graph

CHECKPOINT_DB = "agent_memory.sqlite"
RECURSION_LIMIT = 25


@contextmanager
def get_app():
    with SqliteSaver.from_conn_string(CHECKPOINT_DB) as checkpointer:
        yield build_graph(checkpointer=checkpointer)


def _run_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": RECURSION_LIMIT}


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
    print(f"Local Ops Agent. Thread: '{thread_id}'. Ctrl-D to exit.")
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
    parser = argparse.ArgumentParser(description="Local Ops Agent")
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
        print("Make sure OPENAI_API_KEY is set in your .env (or environment).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

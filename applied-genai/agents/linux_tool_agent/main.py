#!/usr/bin/env python3
"""CLI for the Local Ops Agent.

Single-shot:
  python main.py "How much free disk space do I have?"

Multi-turn REPL (conversation persists across process restarts, keyed by --thread):
  python main.py
  python main.py --thread checks

Streaming (print each tool call/result as it happens, instead of just the final answer):
  python main.py --stream "Is api_server.py running, and do I have enough RAM for a 1.7B model?"

Human-approval gate: `run_command` (tools.py) pauses via LangGraph's `interrupt()` for
any command not on its pre-approved safe list -- try:
  python main.py "List the files in the current directory"          # list_directory, no approval
  python main.py "Run 'terraform plan' in the current directory"    # run_command, PAUSES for approval
"""

from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from graph import build_graph

CHECKPOINT_DB = "agent_memory.sqlite"
# Each "step" (one tool call + the agent reading its result) is 2 loop iterations, plus
# 1 for create_plan itself -- 50 gives headroom for a genuinely long multi-step task
# without raising it so high a truly stuck loop runs 50 times before hitting the cap.
RECURSION_LIMIT = 50


@contextmanager
def get_app():
    with SqliteSaver.from_conn_string(CHECKPOINT_DB) as checkpointer:
        yield build_graph(checkpointer=checkpointer)


def _run_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": RECURSION_LIMIT}


def _prompt_for_approval(interrupt_value: dict) -> str:
    print(f"\n⚠  Approval needed: {interrupt_value.get('command')}")
    cwd = interrupt_value.get("cwd")
    if cwd and cwd != ".":
        print(f"   In directory: {cwd}")
    print(f"   Reason: {interrupt_value.get('reason')}")
    return input("   Approve? [y/N] ").strip()


def ask(app, prompt: str, thread_id: str, stream: bool) -> str:
    run_config = _run_config(thread_id)
    inputs = {"messages": [("user", prompt)]}

    if not stream:
        result = app.invoke(inputs, config=run_config)
        while "__interrupt__" in result:
            answer = _prompt_for_approval(result["__interrupt__"][0].value)
            result = app.invoke(Command(resume=answer), config=run_config)
        return result["messages"][-1].content

    final_answer = ""
    next_input = inputs
    while True:
        interrupted = False
        for update in app.stream(next_input, config=run_config, stream_mode="updates"):
            if "__interrupt__" in update:
                answer = _prompt_for_approval(update["__interrupt__"][0].value)
                next_input = Command(resume=answer)
                interrupted = True
                break
            for node, payload in update.items():
                for message in payload.get("messages", []):
                    if isinstance(message, AIMessage) and message.tool_calls:
                        for call in message.tool_calls:
                            print(f"  [{node}] -> call {call['name']}({call['args']})")
                    elif isinstance(message, ToolMessage):
                        print(f"  [{node}] <- {message.name}: {message.content}")
                    elif isinstance(message, AIMessage) and message.content:
                        final_answer = message.content
        if not interrupted:
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

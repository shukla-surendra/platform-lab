"""CLI: run the deep agent on a question, stream what it does, trace it to Langfuse.

    python agent.py "How does FastAPI behave when a client disconnects?"
"""

from __future__ import annotations

import argparse
import uuid
from contextlib import ExitStack

import config
from graph import build_agent

TODO_ICON = {"pending": "[ ]", "in_progress": "[~]", "completed": "[x]"}


def short(value, n: int = 140) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= n else text[: n - 3] + "..."


def print_update(namespace: tuple, update: dict) -> None:
    """Print one node's state update. `namespace` is empty for the main agent and names the
    subagent graph otherwise. That's what `subgraphs=True` gives you."""
    who = "main" if not namespace else "  sub"
    for node_update in update.values():
        if not isinstance(node_update, dict):
            continue
        if node_update.get("todos"):
            print(f"{who} | plan:")
            for todo in node_update["todos"]:
                print(f"{who} |   {TODO_ICON.get(todo['status'], '[?]')} {todo['content']}")
        for msg in node_update.get("messages") or []:
            if getattr(msg, "tool_calls", None):
                for call in msg.tool_calls:
                    args = call["args"]
                    if call["name"] == "task":
                        print(f"{who} | -> task[{args.get('subagent_type')}]: {short(args.get('description'), 110)}")
                    else:
                        print(f"{who} | -> {call['name']}({short(args, 100)})")
            elif msg.type == "tool":
                print(f"{who} | <- {msg.name}: {short(msg.content, 100)}")


def run(question: str, thread_id: str) -> None:
    agent = build_agent()
    callbacks, langfuse = [], None

    with ExitStack() as stack:
        if config.LANGFUSE_ENABLED:
            from langfuse import get_client, propagate_attributes
            from langfuse.langchain import CallbackHandler

            langfuse = get_client()
            # One root "agent" observation per run. The LangChain callback nests every LLM call,
            # tool call and subagent run under it, so one run = one trace in Langfuse.
            root = stack.enter_context(
                langfuse.start_as_current_observation(as_type="agent", name="deep-research", input={"question": question})
            )
            # session_id groups runs of the same thread in Langfuse's Sessions view.
            stack.enter_context(propagate_attributes(session_id=thread_id, tags=["deep-agent", config.OPENAI_MODEL]))
            callbacks.append(CallbackHandler())
        else:
            print("(Langfuse keys not set: running without tracing)")

        final_state = None
        for namespace, mode, data in agent.stream(
            {"messages": [{"role": "user", "content": question}]},
            config={"callbacks": callbacks, "configurable": {"thread_id": thread_id}, "recursion_limit": 150},
            stream_mode=["updates", "values"],
            subgraphs=True,
        ):
            if mode == "updates":
                print_update(namespace, data)
            elif not namespace:
                final_state = data  # the main graph's full state after each step

        answer = final_state["messages"][-1].content if final_state else ""
        if langfuse:
            root.update(output={"answer": answer, "files": sorted((final_state or {}).get("files", {}))})
            trace_id = langfuse.get_current_trace_id()
            try:  # needs an API call (project id); don't fail a finished run if Langfuse is down
                trace_url = langfuse.get_trace_url(trace_id=trace_id)
            except Exception:
                trace_url = f"(Langfuse unreachable) trace id {trace_id}"

    save_files(final_state or {})
    print("\n=== answer ===\n" + str(answer))
    if langfuse:
        langfuse.flush()  # spans are exported in the background, so flush before exiting
        print(f"\nLangfuse trace: {trace_url}")


def save_files(state: dict) -> None:
    """Copy the agent's virtual filesystem (graph state) to output/<file> on real disk."""
    files = state.get("files") or {}
    for path, data in files.items():
        content = data.get("content", "") if isinstance(data, dict) else data
        if isinstance(content, list):  # older deepagents versions store a list of lines
            content = "\n".join(content)
        target = config.OUTPUT_DIR / path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(content))
        print(f"saved {target.relative_to(config.BASE_DIR)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("question")
    parser.add_argument("--thread", default=None, help="Langfuse session id (default: random)")
    args = parser.parse_args()
    run(args.question, args.thread or f"run-{uuid.uuid4().hex[:8]}")


if __name__ == "__main__":
    main()

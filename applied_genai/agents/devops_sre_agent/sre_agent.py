#!/usr/bin/env python3
"""CLI for the local multi-agent SRE assistant (OpenAI Agents SDK + local Ollama).

Investigate only (default — mutating tools report DRY RUN instead of acting):
  python sre_agent.py "checkout-service is throwing errors, can you look into it?"

Investigate and actually remediate:
  python sre_agent.py --apply "checkout-service is throwing errors, can you look into it?"

Multi-turn session (conversation persists across process runs, keyed by --session):
  python sre_agent.py --session oncall-2026-07-22 "any active alarms right now?"
  python sre_agent.py --session oncall-2026-07-22 "go ahead and fix it"

Print each tool call / handoff as it happens:
  python sre_agent.py --trace "..."
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from agents import Runner, SQLiteSession, set_tracing_disabled
from agents.items import HandoffOutputItem, ToolCallItem, ToolCallOutputItem

import config
from agents_setup import build_triage_agent

set_tracing_disabled(True)  # no OpenAI account/API key involved; nothing to send traces to


def _print_trace(new_items) -> None:
    for item in new_items:
        if isinstance(item, HandoffOutputItem):
            print(f"  [handoff] {item.source_agent.name} -> {item.target_agent.name}")
        elif isinstance(item, ToolCallItem):
            raw = item.raw_item
            name = getattr(raw, "name", "?")
            args = getattr(raw, "arguments", "")
            print(f"  [{item.agent.name}] -> call {name}({args})")
        elif isinstance(item, ToolCallOutputItem):
            print(f"  [{item.agent.name}] <- {item.output}")


async def run(prompt: str, session_id: str, trace: bool) -> str:
    agent = build_triage_agent()
    session = SQLiteSession(session_id, config.SESSION_DB)

    result = await Runner.run(agent, prompt, session=session, max_turns=config.MAX_TURNS)
    if trace:
        _print_trace(result.new_items)
    return result.final_output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("prompt", nargs="*", help="What to ask the on-call agent.")
    parser.add_argument("--apply", action="store_true", help="Let mutating tools actually execute (default: dry-run).")
    parser.add_argument("--session", default="default", help="Conversation session id (default: 'default').")
    parser.add_argument("--trace", action="store_true", help="Print each tool call/handoff as it happens.")
    args = parser.parse_args()

    if not args.prompt:
        parser.print_help()
        return 1

    config.APPLY_CHANGES = args.apply
    prompt = " ".join(args.prompt)

    try:
        answer = asyncio.run(run(prompt, args.session, args.trace))
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(
            "Make sure `ollama serve` is running and the model in .env / config.py is pulled "
            f"(`ollama pull {config.OLLAMA_MODEL}`).",
            file=sys.stderr,
        )
        return 1

    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

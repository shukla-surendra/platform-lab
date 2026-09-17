#!/usr/bin/env python3
"""One-shot interactive entry point: ask the agent a free-text on-call question and watch it
classify, gather context, retrieve knowledge, diagnose, decide, and act.

    python agent_cli.py "why is fraud-detection showing degraded predictions?"
    python agent_cli.py --apply "checkout-api is throwing 503s, can you fix it?"
"""

from __future__ import annotations

import argparse
import asyncio
import json

from graph import build_graph


async def run(query: str, apply_changes: bool) -> None:
    app = await build_graph(apply_changes=apply_changes)
    result = await app.ainvoke({"input_query": query})

    diagnosis = result["diagnosis"]
    print(f"\nDomain: {result['domain']}    Entity: {result['entity']}    Severity: {result['severity']}")
    print(f"\nRoot cause:\n  {diagnosis['root_cause']}")
    print(f"\nReasoning:\n  {diagnosis['reasoning']}")
    print(f"\nRecommended action: {diagnosis['recommended_action']} "
          f"(confidence {diagnosis['confidence']}, escalate={diagnosis['escalate']})")
    print(f"Auto-remediated: {result['auto_remediate']}")
    print(f"\nAction result:\n  {result['action_result']}")
    print(f"\nKnowledge sources used: {[k['source'] for k in result['knowledge']]}")
    ticket = result["ticket"]
    print(f"\nTicket: {ticket['ticket_id']} ({ticket['status']}, {ticket['severity']})")
    print(f"  {ticket['summary']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("query", help="free-text on-call question")
    parser.add_argument("--apply", action="store_true", help="actually execute the recommended remediation")
    parser.add_argument("--json", action="store_true", help="print raw final state as JSON instead of the formatted summary")
    args = parser.parse_args()

    if args.json:
        async def run_json() -> None:
            app = await build_graph(apply_changes=args.apply)
            result = await app.ainvoke({"input_query": args.query})
            print(json.dumps(result, indent=2, default=str))
        asyncio.run(run_json())
    else:
        asyncio.run(run(args.query, args.apply))


if __name__ == "__main__":
    main()

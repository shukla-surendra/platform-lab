#!/usr/bin/env python3
"""Automode: polls events/inbox/ for event files, runs the agent graph on each one without a
human prompting it, and files the event under processed/ or failed/ when done. This is the
"AIOps" half of the project -- it keeps reacting to whatever shows up for as long as it runs.

    python daemon.py                 # dry-run, poll forever (Ctrl-C to stop)
    python daemon.py --apply         # remediation actions actually mutate world_state.json
    python daemon.py --once          # drain whatever's queued right now and exit
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time

import config
from graph import build_graph


async def process_one(app, path) -> None:
    event = json.loads(path.read_text())
    print(f"\n=== processing {path.name}: {event['domain']}/{event['entity']} -- {event['description']} ===")
    try:
        result = await app.ainvoke({"input_event": event})
        print(f"    diagnosis: {result['diagnosis']['root_cause']}")
        print(f"    action: {result['action_result']}")
        print(f"    ticket: {result['ticket']['ticket_id']} ({result['ticket']['status']})")
        path.rename(config.PROCESSED_DIR / path.name)
    except Exception as exc:  # noqa: BLE001 -- route any failure to failed/ rather than crash the daemon
        print(f"    FAILED: {exc}")
        path.rename(config.FAILED_DIR / path.name)


async def run(apply_changes: bool, once: bool) -> None:
    app = await build_graph(apply_changes=apply_changes)
    print(f"Daemon started (apply_changes={apply_changes}). Watching {config.INBOX_DIR} ...")
    while True:
        pending = sorted(config.INBOX_DIR.glob("*.json"))
        for path in pending:
            await process_one(app, path)
        if once:
            if not pending:
                print("Nothing queued.")
            return
        time.sleep(config.POLL_INTERVAL_SECONDS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="actually execute remediation actions")
    parser.add_argument("--once", action="store_true", help="drain the inbox once and exit instead of polling forever")
    args = parser.parse_args()
    asyncio.run(run(apply_changes=args.apply, once=args.once))


if __name__ == "__main__":
    main()

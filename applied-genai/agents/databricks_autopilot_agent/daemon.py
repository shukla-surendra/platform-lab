#!/usr/bin/env python3
"""Automode: watches events/inbox/ for new event files and runs the graph on each one, forever
(or until Ctrl-C). This is what "keeps responding to events" means concretely — no human prompt
per event, just a loop that polls a queue and reacts.

Usage:
  python daemon.py                 # dry-run: mutating actions (cluster resize, retries) are proposed, not applied
  python daemon.py --apply         # actually apply them
  python daemon.py --once          # drain whatever's currently in the inbox, then exit (useful for testing)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

import config
from graph import build_graph


def _pending_events() -> list[Path]:
    return sorted(config.INBOX_DIR.glob("*.json"))


def process_one(app, path: Path) -> None:
    try:
        event = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        print(f"[daemon] SKIP {path.name}: invalid JSON ({exc})", file=sys.stderr)
        shutil.move(str(path), config.FAILED_DIR / path.name)
        return

    print(f"\n[daemon] processing {event['type']} for {event['job_id']} (run {event['run_id']})")
    try:
        result = app.invoke({"event": event, "log": []})
        for line in result["log"]:
            print(f"  - {line}")
    except Exception as exc:
        print(f"[daemon] ERROR handling {path.name}: {exc}", file=sys.stderr)
        shutil.move(str(path), config.FAILED_DIR / path.name)
        return

    shutil.move(str(path), config.PROCESSED_DIR / path.name)


def run(once: bool) -> None:
    for d in (config.INBOX_DIR, config.PROCESSED_DIR, config.FAILED_DIR):
        d.mkdir(parents=True, exist_ok=True)

    app = build_graph()
    mode = "APPLY" if config.APPLY_CHANGES else "DRY RUN"
    print(f"[daemon] watching {config.INBOX_DIR} every {config.POLL_INTERVAL_SECONDS}s ({mode} mode). Ctrl-C to stop.")

    try:
        while True:
            pending = _pending_events()
            if not pending:
                if once:
                    print("[daemon] inbox empty, --once was set, exiting.")
                    return
                time.sleep(config.POLL_INTERVAL_SECONDS)
                continue

            for path in pending:
                process_one(app, path)

            if once:
                return
    except KeyboardInterrupt:
        print("\n[daemon] stopped.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Let mutating actions (cluster resize, retries) actually execute.")
    parser.add_argument("--once", action="store_true", help="Drain the current inbox once, then exit, instead of polling forever.")
    args = parser.parse_args()

    config.APPLY_CHANGES = args.apply

    try:
        run(once=args.once)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Reset pipeline_state.json to a clean baseline (3 jobs, 2 clusters, no run history, no
tickets) and clear the audit log. Unlike ../devops_sre_agent, incidents here aren't pre-seeded —
they arrive as events from event_simulator.py while the daemon is running.
"""

from __future__ import annotations

from pipeline_state import reset_state


def main() -> int:
    reset_state()
    print("Reset pipeline_state.json to a clean baseline and cleared audit_log.jsonl.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Reset the mock fleet in infra_state.json, optionally injecting a realistic incident.

Usage:
  python seed_incident.py              # healthy baseline fleet, nothing to investigate
  python seed_incident.py --incident   # baseline + a correlated checkout-service incident
"""

from __future__ import annotations

import argparse

from infra_state import reset_state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--incident",
        action="store_true",
        help="Inject a CPU-starved, OOM-ing web-01 instance that trips two alarms and degrades checkout-service.",
    )
    args = parser.parse_args()

    reset_state(inject_incident=args.incident)
    if args.incident:
        print(
            "Seeded fleet with an active incident: web-01 CPU/memory pressure, "
            "2 CloudWatch alarms in ALARM, checkout-service running below desired count."
        )
    else:
        print("Seeded a healthy baseline fleet. Nothing currently needs investigation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

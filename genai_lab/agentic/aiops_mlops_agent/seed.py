#!/usr/bin/env python3
"""Reset the mock world to a clean baseline, optionally seeding one incident scenario.

    python seed.py                                          # clean baseline, nothing wrong
    python seed.py --model-drift fraud-detection             # inject drift/error-rate spike
    python seed.py --infra-incident host-infer-01             # CPU/mem pressure on a host
    python seed.py --pipeline-failure pl-daily-etl --reason schema_drift
"""

from __future__ import annotations

import argparse

import state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model-drift", metavar="MODEL_NAME")
    parser.add_argument("--infra-incident", metavar="HOST_ID")
    parser.add_argument("--pipeline-failure", metavar="PIPELINE_ID")
    parser.add_argument(
        "--reason",
        default="upstream_stale",
        choices=["upstream_stale", "schema_drift", "oom", "transient"],
        help="failure reason for --pipeline-failure",
    )
    args = parser.parse_args()

    state.reset()
    print(f"World state reset -> {state.config.STATE_FILE}")

    if args.model_drift:
        model = state.seed_model_drift(args.model_drift)
        print(f"Seeded drift on {args.model_drift}: error_rate={model['error_rate']}, "
              f"latency_p95_ms={model['latency_p95_ms']}")
    if args.infra_incident:
        host = state.seed_infra_incident(args.infra_incident)
        print(f"Seeded infra incident on {args.infra_incident}: cpu={host['cpu_percent']}%, "
              f"mem={host['mem_percent']}%, status={host['status']}")
    if args.pipeline_failure:
        pipeline = state.seed_pipeline_failure(args.pipeline_failure, args.reason)
        print(f"Seeded pipeline failure on {args.pipeline_failure} ({args.reason}): "
              f"{pipeline['last_logs']}")


if __name__ == "__main__":
    main()

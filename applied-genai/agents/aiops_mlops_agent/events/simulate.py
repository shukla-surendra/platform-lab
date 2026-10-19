#!/usr/bin/env python3
"""Stand in for a real event source (a model-monitoring webhook, a CloudWatch alarm, a CI
failure notification) by (1) actually mutating the mock world into an incident state via
`state.py`, and (2) dropping a matching event file into `events/inbox/` for `daemon.py` to pick
up. Run this in one terminal and `daemon.py` in another to watch the agent react live.

    python events/simulate.py --scenario model-drift --model fraud-detection
    python events/simulate.py --scenario infra-incident --host host-web-01
    python events/simulate.py --scenario pipeline-failure --pipeline pl-daily-etl --reason schema_drift
    python events/simulate.py --scenario mixed
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
import state  # noqa: E402


def _write_event(domain: str, entity: str, description: str) -> None:
    event = {
        "event_id": f"evt-{uuid.uuid4().hex[:8]}",
        "domain": domain,
        "entity": entity,
        "description": description,
    }
    path = config.INBOX_DIR / f"{event['event_id']}.json"
    path.write_text(json.dumps(event, indent=2))
    print(f"-> wrote {path.name}: {domain}/{entity} -- {description}")


def model_drift(model_name: str) -> None:
    model = state.seed_model_drift(model_name)
    _write_event("model_drift", model_name, f"AUC/error-rate monitor fired: error_rate={model['error_rate']}")


def infra_incident(host_id: str) -> None:
    host = state.seed_infra_incident(host_id)
    _write_event("infra_anomaly", host["service"], f"Host {host_id} degraded: cpu={host['cpu_percent']}% mem={host['mem_percent']}%")


def pipeline_failure(pipeline_id: str, reason: str) -> None:
    state.seed_pipeline_failure(pipeline_id, reason)
    _write_event("pipeline_failure", pipeline_id, f"Run failed ({reason})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", required=True,
                         choices=["model-drift", "infra-incident", "pipeline-failure", "mixed"])
    parser.add_argument("--model", default="fraud-detection")
    parser.add_argument("--host", default="host-web-01")
    parser.add_argument("--pipeline", default="pl-daily-etl")
    parser.add_argument("--reason", default="schema_drift",
                         choices=["upstream_stale", "schema_drift", "oom", "transient"])
    args = parser.parse_args()

    if not config.STATE_FILE.exists():
        state.reset()

    if args.scenario == "model-drift":
        model_drift(args.model)
    elif args.scenario == "infra-incident":
        infra_incident(args.host)
    elif args.scenario == "pipeline-failure":
        pipeline_failure(args.pipeline, args.reason)
    elif args.scenario == "mixed":
        model_drift("fraud-detection")
        infra_incident("host-infer-01")
        pipeline_failure("pl-feature-refresh", "upstream_stale")


if __name__ == "__main__":
    main()

"""A mock AWS-shaped fleet: EC2 instances, ECS services, CloudWatch alarms, S3 buckets, service
logs, and incident tickets — all just JSON on disk. No boto3, no credentials, no network calls to
AWS. This exists purely to give the agent something realistic to investigate and (optionally)
remediate, in the same spirit as ../task_store.py backing the other local demos in this repo.

Run `python seed_incident.py` to (re)create the state file before using the agent.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from typing import Any

import config

_BASELINE: dict[str, Any] = {
    "ec2_instances": [
        {
            "id": "i-0a1b2c3d",
            "name": "web-01",
            "service": "checkout-service",
            "state": "running",
            "cpu_percent": 22,
            "status_checks_passed": 2,
            "status_checks_total": 2,
        },
        {
            "id": "i-0e5f6g7h",
            "name": "web-02",
            "service": "checkout-service",
            "state": "running",
            "cpu_percent": 19,
            "status_checks_passed": 2,
            "status_checks_total": 2,
        },
        {
            "id": "i-0i9j8k7l",
            "name": "worker-01",
            "service": "payments-worker",
            "state": "running",
            "cpu_percent": 15,
            "status_checks_passed": 2,
            "status_checks_total": 2,
        },
    ],
    "ecs_services": [
        {"name": "checkout-service", "cluster": "prod", "desired_count": 4, "running_count": 4},
        {"name": "payments-worker", "cluster": "prod", "desired_count": 2, "running_count": 2},
    ],
    "cloudwatch_alarms": [
        {
            "id": "alarm-cpu-web01",
            "name": "HighCPUUtilization",
            "resource_id": "i-0a1b2c3d",
            "metric": "CPUUtilization",
            "threshold": 85,
            "state": "OK",
        },
        {
            "id": "alarm-5xx-checkout",
            "name": "Elevated5xxRate",
            "resource_id": "checkout-service",
            "metric": "HTTP5xxCount",
            "threshold": 20,
            "state": "OK",
        },
        {
            "id": "alarm-disk-worker01",
            "name": "DiskSpaceLow",
            "resource_id": "i-0i9j8k7l",
            "metric": "DiskFreePercent",
            "threshold": 15,
            "state": "OK",
        },
    ],
    "s3_buckets": [
        {"name": "prod-checkout-assets", "size_gb": 128.4, "last_backup": "2026-07-21T02:00:00Z"},
        {"name": "prod-payments-audit-logs", "size_gb": 512.7, "last_backup": "2026-07-21T02:00:00Z"},
    ],
    "service_logs": {
        "checkout-service": [
            "INFO  checkout-service started, 4/4 tasks healthy",
            "INFO  handled GET /cart 200 in 42ms",
            "INFO  handled POST /checkout 200 in 118ms",
        ],
        "payments-worker": [
            "INFO  payments-worker started, 2/2 tasks healthy",
            "INFO  processed batch of 40 payments",
        ],
    },
    "tickets": [],
}

_INCIDENT_LOG_LINES = [
    "WARN  task 3f9a on web-01 memory usage 91%",
    "ERROR OutOfMemoryError in checkout-service task on web-01",
    "ERROR connection pool exhausted: payments-db max_connections reached",
    "WARN  task marked unhealthy by ELB, deregistering and restarting",
    "ERROR handled POST /checkout 503 in 30012ms",
]


def _baseline() -> dict[str, Any]:
    return copy.deepcopy(_BASELINE)


def _apply_incident(state: dict[str, Any]) -> dict[str, Any]:
    """Mutate a fresh baseline into a realistic, correlated incident: web-01 is CPU-starved and
    OOM-ing, which trips a CPU alarm and a 5xx-rate alarm, and drags the checkout-service ECS
    service below its desired task count.
    """
    for instance in state["ec2_instances"]:
        if instance["id"] == "i-0a1b2c3d":
            instance["cpu_percent"] = 96
            instance["status_checks_passed"] = 1

    for service in state["ecs_services"]:
        if service["name"] == "checkout-service":
            service["running_count"] = 2

    for alarm in state["cloudwatch_alarms"]:
        if alarm["id"] in {"alarm-cpu-web01", "alarm-5xx-checkout"}:
            alarm["state"] = "ALARM"

    state["service_logs"]["checkout-service"].extend(_INCIDENT_LOG_LINES)
    return state


def reset_state(inject_incident: bool = False) -> dict[str, Any]:
    state = _baseline()
    if inject_incident:
        state = _apply_incident(state)
    save_state(state)
    return state


def load_state() -> dict[str, Any]:
    if not config.STATE_FILE.exists():
        raise FileNotFoundError(
            f"{config.STATE_FILE.name} does not exist yet. Run `python seed_incident.py` first."
        )
    return json.loads(config.STATE_FILE.read_text())


def save_state(state: dict[str, Any]) -> None:
    config.STATE_FILE.write_text(json.dumps(state, indent=2))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

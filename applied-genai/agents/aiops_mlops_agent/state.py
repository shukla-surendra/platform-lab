"""Mock world state for three MLOps/AIOps domains -- models, infra hosts/services, and CI/CD
pipelines -- persisted as one JSON file (`world_state.json`) so the two MCP server subprocesses
(`mcp_servers/ops_server.py` and the seed/reset scripts) all read and write the same source of
truth without a real database.

No real MLflow, Prometheus, or CI system is involved anywhere in this project.
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timezone
from typing import Any

import config

_BASELINE: dict[str, Any] = {
    "models": {
        "fraud-detection": {
            "versions": [1, 2, 3],
            "deployed_version": 3,
            "previous_version": 2,
            "latency_p95_ms": 42,
            "error_rate": 0.004,
            "qps": 310,
        },
        "churn-prediction": {
            "versions": [1, 2],
            "deployed_version": 2,
            "previous_version": 1,
            "latency_p95_ms": 61,
            "error_rate": 0.006,
            "qps": 85,
        },
        "recsys-ranker": {
            "versions": [1, 2, 3, 4],
            "deployed_version": 4,
            "previous_version": 3,
            "latency_p95_ms": 118,
            "error_rate": 0.011,
            "qps": 940,
        },
    },
    "hosts": {
        "host-web-01": {
            "service": "checkout-api",
            "cpu_percent": 22,
            "mem_percent": 38,
            "disk_percent": 41,
            "status": "healthy",
            "desired_count": 3,
            "running_count": 3,
        },
        "host-web-02": {
            "service": "checkout-api",
            "cpu_percent": 24,
            "mem_percent": 40,
            "disk_percent": 39,
            "status": "healthy",
            "desired_count": 3,
            "running_count": 3,
        },
        "host-infer-01": {
            "service": "model-serving",
            "cpu_percent": 31,
            "mem_percent": 44,
            "disk_percent": 55,
            "status": "healthy",
            "desired_count": 4,
            "running_count": 4,
        },
    },
    "pipelines": {
        "pl-daily-etl": {
            "last_run_id": "run-0001",
            "last_status": "succeeded",
            "history": ["succeeded", "succeeded", "succeeded"],
            "last_logs": "Extracted 4.2M rows, loaded to warehouse.sales_fact. Duration: 14m02s.",
        },
        "pl-feature-refresh": {
            "last_run_id": "run-0001",
            "last_status": "succeeded",
            "history": ["succeeded", "succeeded"],
            "last_logs": "Refreshed 18 feature tables for fraud-detection, churn-prediction.",
        },
        "pl-model-retrain": {
            "last_run_id": "run-0001",
            "last_status": "succeeded",
            "history": ["succeeded"],
            "last_logs": "Retrained recsys-ranker v4 on 90-day window. AUC 0.902.",
        },
    },
    "tickets": {},
    "notifications": [],
}


def reset() -> None:
    config.STATE_FILE.write_text(json.dumps(_BASELINE, indent=2))


def load() -> dict[str, Any]:
    if not config.STATE_FILE.exists():
        raise FileNotFoundError(
            f"{config.STATE_FILE} does not exist yet -- run `python seed.py` first."
        )
    return json.loads(config.STATE_FILE.read_text())


def save(state: dict[str, Any]) -> None:
    config.STATE_FILE.write_text(json.dumps(state, indent=2))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Scenario seeding --------------------------------------------------------------------------
# Each function mutates one entity into a specific, reproducible "incident" state so a run of the
# agent has something real to diagnose. Deterministic per entity name via a seeded RNG, same
# pattern used for drift scores below -- re-running a scenario against the same entity reproduces
# the same numbers.

def seed_model_drift(model_name: str) -> dict[str, Any]:
    state = load()
    model = state["models"][model_name]
    model["error_rate"] = round(model["error_rate"] * random.uniform(4, 9), 4)
    model["latency_p95_ms"] = int(model["latency_p95_ms"] * random.uniform(1.1, 1.4))
    save(state)
    return model


def seed_infra_incident(host_id: str) -> dict[str, Any]:
    state = load()
    host = state["hosts"][host_id]
    host["cpu_percent"] = random.randint(88, 99)
    host["mem_percent"] = random.randint(85, 97)
    host["status"] = "degraded"
    host["running_count"] = max(0, host["running_count"] - random.randint(1, 2))
    save(state)
    return host


def seed_pipeline_failure(pipeline_id: str, reason: str = "upstream_stale") -> dict[str, Any]:
    state = load()
    pipeline = state["pipelines"][pipeline_id]
    run_id = f"run-{uuid.uuid4().hex[:6]}"
    pipeline["last_run_id"] = run_id
    pipeline["last_status"] = "failed"
    pipeline["history"] = (pipeline["history"] + ["failed"])[-10:]
    logs_by_reason = {
        "upstream_stale": "ERROR: source table warehouse.raw_events last modified 26h ago, "
        "exceeds 24h freshness SLA. Aborting run to avoid processing stale data.",
        "schema_drift": "ERROR: column 'customer_segment' not found in source schema. "
        "Expected 14 columns, found 13. Upstream schema likely changed.",
        "oom": "ERROR: Java heap space. Executor lost during shuffle stage 4 of 7. "
        "Container killed by YARN for exceeding memory limits.",
        "transient": "ERROR: connection reset by peer while reading from warehouse.raw_events. "
        "Network blip, no data changes detected.",
    }
    pipeline["last_logs"] = logs_by_reason.get(reason, logs_by_reason["transient"])
    save(state)
    return pipeline


def add_notification(text: str, severity: str) -> None:
    state = load()
    state["notifications"].append({"ts": now(), "severity": severity, "text": text})
    save(state)


def create_ticket(title: str, severity: str, domain: str, summary: str) -> dict[str, Any]:
    state = load()
    ticket_id = f"INC-{len(state['tickets']) + 1:04d}"
    ticket = {
        "ticket_id": ticket_id,
        "title": title,
        "severity": severity,
        "domain": domain,
        "summary": summary,
        "status": "open",
        "created_at": now(),
    }
    state["tickets"][ticket_id] = ticket
    save(state)
    return ticket


def resolve_ticket(ticket_id: str, resolution: str) -> dict[str, Any]:
    state = load()
    ticket = state["tickets"][ticket_id]
    ticket["status"] = "resolved"
    ticket["resolution"] = resolution
    ticket["resolved_at"] = now()
    save(state)
    return ticket

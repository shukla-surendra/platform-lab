"""A mock Databricks-shaped world: jobs, clusters, upstream table freshness, run history,
incident tickets, and notifications — all just JSON/JSONL on disk. No Databricks SDK, no
workspace credentials, no real cluster ever resized. This exists to give the agent something
realistic and stateful to react to across a stream of events, the same way ../devops_sre_agent's
infra_state.py mocks AWS.

Run `python reset_state.py` to (re)create pipeline_state.json before using the agent.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from typing import Any

import config

_BASELINE: dict[str, Any] = {
    "jobs": {
        "job-daily-sales-etl": {
            "name": "daily_sales_etl",
            "owner": "data-eng",
            "cluster_id": "cluster-prod-etl",
            "upstream_tables": ["raw.sales_transactions"],
            "runs": [],
        },
        "job-churn-features": {
            "name": "customer_churn_features",
            "owner": "ml-platform",
            "cluster_id": "cluster-prod-ml",
            "upstream_tables": ["curated.customer_events"],
            "runs": [],
        },
        "job-inventory-sync": {
            "name": "inventory_sync",
            "owner": "data-eng",
            "cluster_id": "cluster-prod-etl",
            "upstream_tables": ["raw.warehouse_feed"],
            "runs": [],
        },
    },
    "clusters": {
        "cluster-prod-etl": {
            "node_type": "i3.xlarge",
            "num_workers": 4,
            "min_workers": 2,
            "max_workers": 8,
        },
        "cluster-prod-ml": {
            "node_type": "g5.2xlarge",
            "num_workers": 2,
            "min_workers": 1,
            "max_workers": 4,
        },
    },
    "upstream_tables": {
        "raw.sales_transactions": {"last_updated_minutes_ago": 12, "expected_freshness_minutes": 60},
        "curated.customer_events": {"last_updated_minutes_ago": 20, "expected_freshness_minutes": 120},
        "raw.warehouse_feed": {"last_updated_minutes_ago": 8, "expected_freshness_minutes": 30},
    },
    "tickets": [],
    "notifications": [],
}


def _baseline() -> dict[str, Any]:
    return copy.deepcopy(_BASELINE)


def reset_state() -> dict[str, Any]:
    state = _baseline()
    save_state(state)
    if config.AUDIT_LOG_FILE.exists():
        config.AUDIT_LOG_FILE.unlink()
    return state


def load_state() -> dict[str, Any]:
    if not config.STATE_FILE.exists():
        raise FileNotFoundError(
            f"{config.STATE_FILE.name} does not exist yet. Run `python reset_state.py` first."
        )
    return json.loads(config.STATE_FILE.read_text())


def save_state(state: dict[str, Any]) -> None:
    config.STATE_FILE.write_text(json.dumps(state, indent=2))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Job runs -----------------------------------------------------------------------------------


def record_run(job_id: str, run_id: str, status: str, error_message: str | None = None) -> dict:
    state = load_state()
    job = state["jobs"][job_id]
    run = {"run_id": run_id, "status": status, "timestamp": now_iso(), "error_message": error_message}
    job["runs"].append(run)
    save_state(state)
    return run


def get_job(job_id: str) -> dict:
    return load_state()["jobs"][job_id]


def get_recent_runs(job_id: str, limit: int) -> list[dict]:
    return load_state()["jobs"][job_id]["runs"][-limit:]


def count_recent_failures(job_id: str, window: int) -> int:
    recent = get_recent_runs(job_id, window)
    return sum(1 for run in recent if run["status"] == "failed")


# --- Clusters -------------------------------------------------------------------------------------


def get_cluster(cluster_id: str) -> dict:
    return load_state()["clusters"][cluster_id]


def resize_cluster(cluster_id: str, new_num_workers: int) -> dict:
    state = load_state()
    cluster = state["clusters"][cluster_id]
    cluster["num_workers"] = new_num_workers
    save_state(state)
    return cluster


# --- Upstream freshness ------------------------------------------------------------------------


def get_upstream_freshness(table_name: str) -> dict | None:
    return load_state()["upstream_tables"].get(table_name)


# --- Tickets --------------------------------------------------------------------------------------


def get_open_ticket_for_job(job_id: str) -> dict | None:
    tickets = load_state()["tickets"]
    return next((t for t in tickets if t["job_id"] == job_id and t["status"] == "open"), None)


def create_ticket(job_id: str, title: str, summary: str, severity: str) -> dict:
    state = load_state()
    next_id = f"INC-{len(state['tickets']) + 1:04d}"
    ticket = {
        "id": next_id,
        "job_id": job_id,
        "title": title,
        "summary": summary,
        "severity": severity,
        "status": "open",
        "created": now_iso(),
        "resolution": None,
    }
    state["tickets"].append(ticket)
    save_state(state)
    return ticket


def resolve_ticket(ticket_id: str, resolution: str) -> dict | None:
    state = load_state()
    ticket = next((t for t in state["tickets"] if t["id"] == ticket_id), None)
    if ticket is None:
        return None
    ticket["status"] = "resolved"
    ticket["resolution"] = resolution
    save_state(state)
    return ticket


# --- Notifications ----------------------------------------------------------------------------


def send_notification(channel: str, message: str) -> dict:
    """Mocked notification: prints, and records to state + the audit log. Stands in for a real
    Slack/PagerDuty/email integration.
    """
    state = load_state()
    entry = {"channel": channel, "message": message, "timestamp": now_iso()}
    state["notifications"].append(entry)
    save_state(state)
    print(f"  [notify:{channel}] {message}")
    return entry


# --- Audit log --------------------------------------------------------------------------------


def append_audit(entry: dict[str, Any]) -> None:
    """Append-only structured log of every event the agent processed and what it decided —
    separate from pipeline_state.json so it's safe to tail while the daemon is running.
    """
    entry = {"timestamp": now_iso(), **entry}
    with config.AUDIT_LOG_FILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")

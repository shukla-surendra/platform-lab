"""MCP server exposing mock MLOps + AIOps tools across three domains: model registry/drift,
infra hosts/services, and CI/CD pipelines. Built on FastMCP, runs over stdio, spawned as a
subprocess by `mcp_client.py` -- there's no real MLflow, Prometheus, or CI backend here, only
`state.py`'s JSON-backed mock world.

Safety model: read tools are always live. The six *mutating* tools (rollback_model,
trigger_retrain, restart_service, scale_service, retry_pipeline, rollback_deployment) check
`APPLY_CHANGES` -- read from the environment once at import time -- before touching state:

- unset / "false" (default): return a `DRY RUN: would ...` description, world_state.json unchanged.
- "true" (set by mcp_client.py when the agent is invoked with --apply): actually mutate state.

This process is spawned fresh per agent run with `APPLY_CHANGES` baked into its environment, so
unlike a single-process project there's no in-process flag to flip -- the gate is decided once,
at spawn time, by whoever launched the agent.
"""

from __future__ import annotations

import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
import state  # noqa: E402
from fastmcp import FastMCP  # noqa: E402

APPLY_CHANGES = os.getenv("APPLY_CHANGES", "false").lower() == "true"

mcp = FastMCP("AIOps/MLOps Tools")


def _dry_run_or(description: str, mutate) -> str:
    """Shared gate for every mutating tool: describe-only unless APPLY_CHANGES is set."""
    if not APPLY_CHANGES:
        return f"DRY RUN: would {description}. Re-run the agent with --apply to execute."
    mutate()
    return f"APPLIED: {description}."


# --- Model registry / drift ---------------------------------------------------------------------

@mcp.tool()
def list_models() -> list[str]:
    """List all deployed model names."""
    return list(state.load()["models"].keys())


@mcp.tool()
def get_model_status(model_name: str) -> dict:
    """Get the deployed version, latency, error rate, and QPS for a model."""
    models = state.load()["models"]
    if model_name not in models:
        raise ValueError(f"unknown model: {model_name}")
    return {"model_name": model_name, **models[model_name]}


@mcp.tool()
def check_data_drift(model_name: str, version: int) -> dict:
    """Get per-feature input data drift scores (0-1) for a model version, deterministic per
    model+version via a seeded RNG so re-checking the same version returns the same report."""
    random.seed(f"{model_name}-{version}-data")
    features = ["age", "income", "transaction_amount", "session_length", "device_type"]
    scores = {f: round(random.uniform(0.0, 0.6), 3) for f in features}
    drifted = {f: s for f, s in scores.items() if s > 0.3}
    return {
        "model_name": model_name,
        "version": version,
        "feature_drift_scores": scores,
        "drifted_features": list(drifted.keys()),
        "drift_detected": bool(drifted),
    }


@mcp.tool()
def check_model_drift(model_name: str, version: int) -> dict:
    """Get performance drift (AUC over a 30-day window) for a model version, deterministic per
    model+version."""
    random.seed(f"{model_name}-{version}-perf")
    baseline_auc = round(random.uniform(0.85, 0.93), 3)
    current_auc = round(baseline_auc - random.uniform(0.0, 0.18), 3)
    delta = round(current_auc - baseline_auc, 3)
    return {
        "model_name": model_name,
        "version": version,
        "baseline_auc": baseline_auc,
        "current_auc": current_auc,
        "auc_delta": delta,
        "degraded": delta < -0.05,
        "window_days": 30,
    }


@mcp.tool()
def rollback_model(model_name: str) -> str:
    """Roll the deployed model version back to its previous version. Mutating -- dry-run unless
    the agent was started with --apply."""
    models = state.load()["models"]
    if model_name not in models:
        raise ValueError(f"unknown model: {model_name}")
    prev = models[model_name]["previous_version"]
    cur = models[model_name]["deployed_version"]

    def mutate() -> None:
        s = state.load()
        m = s["models"][model_name]
        m["previous_version"], m["deployed_version"] = m["deployed_version"], m["previous_version"]
        m["error_rate"] = round(m["error_rate"] / random.uniform(4, 9), 4)
        m["latency_p95_ms"] = int(m["latency_p95_ms"] / random.uniform(1.1, 1.4))
        state.save(s)

    return _dry_run_or(f"roll back {model_name} from v{cur} to v{prev}", mutate)


@mcp.tool()
def trigger_retrain(model_name: str) -> str:
    """Kick off a retraining job for a model. Mutating -- dry-run unless --apply."""
    models = state.load()["models"]
    if model_name not in models:
        raise ValueError(f"unknown model: {model_name}")

    def mutate() -> None:
        s = state.load()
        s["pipelines"]["pl-model-retrain"]["last_status"] = "running"
        s["pipelines"]["pl-model-retrain"]["last_logs"] = f"Retraining {model_name} triggered manually."
        state.save(s)

    return _dry_run_or(f"trigger a retraining run for {model_name}", mutate)


# --- Infra hosts / services ---------------------------------------------------------------------

@mcp.tool()
def list_hosts() -> list[str]:
    """List all infra host IDs."""
    return list(state.load()["hosts"].keys())


@mcp.tool()
def get_host_metrics(host_id: str) -> dict:
    """Get CPU/memory/disk utilization and running/desired task counts for a host."""
    hosts = state.load()["hosts"]
    if host_id not in hosts:
        raise ValueError(f"unknown host: {host_id}")
    return {"host_id": host_id, **hosts[host_id]}


@mcp.tool()
def tail_service_logs(service_name: str, lines: int = 50) -> str:
    """Get the last N lines of application logs for a service (mocked, correlates with the
    host's current status)."""
    hosts = state.load()["hosts"]
    matches = [h for h in hosts.values() if h["service"] == service_name]
    if not matches:
        raise ValueError(f"unknown service: {service_name}")
    if any(h["status"] == "degraded" for h in matches):
        return (
            f"ERROR OutOfMemoryError in {service_name} worker process\n"
            f"ERROR connection pool exhausted: max_connections reached\n"
            f"WARN  health check latency p99 4200ms, exceeds 2000ms threshold\n"
            f"ERROR handled request 503 in 4021ms"
        )
    return f"INFO  {service_name} healthy, handling requests normally (last {lines} lines)"


@mcp.tool()
def restart_service(service_name: str) -> str:
    """Restart all hosts running a service. Mutating -- dry-run unless --apply."""
    hosts = state.load()["hosts"]
    if not any(h["service"] == service_name for h in hosts.values()):
        raise ValueError(f"unknown service: {service_name}")

    def mutate() -> None:
        s = state.load()
        for h in s["hosts"].values():
            if h["service"] == service_name:
                h["cpu_percent"] = random.randint(15, 30)
                h["mem_percent"] = random.randint(25, 45)
                h["status"] = "healthy"
                h["running_count"] = h["desired_count"]
        state.save(s)

    return _dry_run_or(f"restart all hosts running {service_name}", mutate)


@mcp.tool()
def scale_service(service_name: str, desired_count: int) -> str:
    """Change the desired task count for a service. Mutating -- dry-run unless --apply."""
    hosts = state.load()["hosts"]
    if not any(h["service"] == service_name for h in hosts.values()):
        raise ValueError(f"unknown service: {service_name}")

    def mutate() -> None:
        s = state.load()
        for h in s["hosts"].values():
            if h["service"] == service_name:
                h["desired_count"] = desired_count
                h["running_count"] = desired_count
        state.save(s)

    return _dry_run_or(f"scale {service_name} to desired_count={desired_count}", mutate)


# --- CI/CD pipelines -----------------------------------------------------------------------------

@mcp.tool()
def list_pipelines() -> list[str]:
    """List all pipeline IDs."""
    return list(state.load()["pipelines"].keys())


@mcp.tool()
def get_pipeline_run(pipeline_id: str) -> dict:
    """Get the last run's status, logs, and recent run history for a pipeline."""
    pipelines = state.load()["pipelines"]
    if pipeline_id not in pipelines:
        raise ValueError(f"unknown pipeline: {pipeline_id}")
    return {"pipeline_id": pipeline_id, **pipelines[pipeline_id]}


@mcp.tool()
def retry_pipeline(pipeline_id: str) -> str:
    """Retry the last failed run of a pipeline. Mutating -- dry-run unless --apply."""
    pipelines = state.load()["pipelines"]
    if pipeline_id not in pipelines:
        raise ValueError(f"unknown pipeline: {pipeline_id}")

    def mutate() -> None:
        s = state.load()
        p = s["pipelines"][pipeline_id]
        p["last_status"] = "succeeded"
        p["history"] = (p["history"] + ["succeeded"])[-10:]
        p["last_logs"] = "Retry succeeded on second attempt."
        state.save(s)

    return _dry_run_or(f"retry the last failed run of {pipeline_id}", mutate)


@mcp.tool()
def rollback_deployment(pipeline_id: str) -> str:
    """Roll back to the last known-good artifact/config for a pipeline. Mutating -- dry-run
    unless --apply."""
    pipelines = state.load()["pipelines"]
    if pipeline_id not in pipelines:
        raise ValueError(f"unknown pipeline: {pipeline_id}")

    def mutate() -> None:
        s = state.load()
        p = s["pipelines"][pipeline_id]
        p["last_status"] = "succeeded"
        p["history"] = (p["history"] + ["succeeded"])[-10:]
        p["last_logs"] = "Rolled back to last known-good config/artifact."
        state.save(s)

    return _dry_run_or(f"roll back {pipeline_id} to its last known-good deployment", mutate)


# --- Incident tickets (informational -- not gated, same as notifications in most on-call tooling) --

@mcp.tool()
def create_incident_ticket(title: str, severity: str, domain: str, summary: str) -> dict:
    """File an incident ticket. Not gated by --apply -- filing a ticket is a record, not a
    change to production systems."""
    return state.create_ticket(title, severity, domain, summary)


@mcp.tool()
def resolve_incident_ticket(ticket_id: str, resolution: str) -> dict:
    """Mark an incident ticket resolved with a resolution note."""
    return state.resolve_ticket(ticket_id, resolution)


@mcp.tool()
def list_incident_tickets(status: str = "open") -> list[dict]:
    """List incident tickets, filtered by status ('open', 'resolved', or 'all')."""
    tickets = list(state.load()["tickets"].values())
    if status == "all":
        return tickets
    return [t for t in tickets if t["status"] == status]


if __name__ == "__main__":
    if config.MCP_TRANSPORT == "http":
        # Production-simulation mode: a long-lived network service, one per docker-compose
        # container. APPLY_CHANGES is fixed for this process's whole lifetime -- there's no
        # per-request client flag that could grant a shared service write access to itself.
        print(f"ops_server: http transport, APPLY_CHANGES={APPLY_CHANGES}", file=sys.stderr)
        mcp.run(transport="http", host=config.OPS_SERVER_HOST, port=config.OPS_SERVER_PORT)
    else:
        mcp.run()

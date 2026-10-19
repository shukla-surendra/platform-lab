import random
import uuid
from datetime import datetime, timedelta

from fastmcp import FastMCP

mcp = FastMCP("MLOps Tools")

# In-memory mock state so a session can register/approve/inspect models
# without any real MLflow or registry backend.
_EXPERIMENTS = {
    "fraud-detection": ["run-a1b2", "run-c3d4"],
    "churn-prediction": ["run-e5f6"],
}

_RUNS = {
    "run-a1b2": {
        "experiment": "fraud-detection",
        "params": {"n_estimators": "200", "max_depth": "8"},
        "metrics": {"auc": 0.912, "f1": 0.847},
        "status": "FINISHED",
    },
    "run-c3d4": {
        "experiment": "fraud-detection",
        "params": {"n_estimators": "400", "max_depth": "12"},
        "metrics": {"auc": 0.928, "f1": 0.861},
        "status": "FINISHED",
    },
    "run-e5f6": {
        "experiment": "churn-prediction",
        "params": {"learning_rate": "0.05", "n_estimators": "300"},
        "metrics": {"auc": 0.874, "f1": 0.803},
        "status": "FINISHED",
    },
}

_MODEL_VERSIONS: dict[str, list[dict]] = {}
_PENDING_APPROVALS: dict[str, dict] = {}


@mcp.tool()
def list_experiments() -> list[str]:
    """List all MLflow experiment names."""
    return list(_EXPERIMENTS.keys())


@mcp.tool()
def list_runs(experiment_name: str) -> list[dict]:
    """List runs for an experiment, with their status and headline metrics."""
    run_ids = _EXPERIMENTS.get(experiment_name)
    if run_ids is None:
        raise ValueError(f"unknown experiment: {experiment_name}")
    return [{"run_id": rid, **_RUNS[rid]} for rid in run_ids]


@mcp.tool()
def get_run_details(run_id: str) -> dict:
    """Get full params, metrics, and status for a single run."""
    run = _RUNS.get(run_id)
    if run is None:
        raise ValueError(f"unknown run_id: {run_id}")
    return {"run_id": run_id, **run}


@mcp.tool()
def register_model(model_name: str, run_id: str) -> dict:
    """Register a run as a new version of a model in the model registry."""
    if run_id not in _RUNS:
        raise ValueError(f"unknown run_id: {run_id}")
    versions = _MODEL_VERSIONS.setdefault(model_name, [])
    version = len(versions) + 1
    entry = {
        "version": version,
        "run_id": run_id,
        "stage": "None",
        "registered_at": datetime.utcnow().isoformat(),
    }
    versions.append(entry)
    return {"model_name": model_name, **entry}


@mcp.tool()
def list_model_versions(model_name: str) -> list[dict]:
    """List all registered versions of a model and their current stage."""
    versions = _MODEL_VERSIONS.get(model_name)
    if versions is None:
        raise ValueError(f"unknown model: {model_name}")
    return versions


@mcp.tool()
def request_stage_transition(model_name: str, version: int, target_stage: str) -> dict:
    """Request a model version move to a new stage (e.g. Staging, Production, Archived). Creates a pending approval."""
    valid_stages = {"Staging", "Production", "Archived"}
    if target_stage not in valid_stages:
        raise ValueError(f"target_stage must be one of {sorted(valid_stages)}")
    versions = _MODEL_VERSIONS.get(model_name)
    if versions is None or not any(v["version"] == version for v in versions):
        raise ValueError(f"unknown model version: {model_name} v{version}")

    request_id = str(uuid.uuid4())[:8]
    request = {
        "request_id": request_id,
        "model_name": model_name,
        "version": version,
        "target_stage": target_stage,
        "status": "PENDING",
    }
    _PENDING_APPROVALS[request_id] = request
    return request


@mcp.tool()
def list_pending_approvals() -> list[dict]:
    """List all model stage-transition requests awaiting approval."""
    return [r for r in _PENDING_APPROVALS.values() if r["status"] == "PENDING"]


@mcp.tool()
def approve_transition(request_id: str) -> dict:
    """Approve a pending stage-transition request and move the model version to its target stage."""
    request = _PENDING_APPROVALS.get(request_id)
    if request is None:
        raise ValueError(f"unknown request_id: {request_id}")
    request["status"] = "APPROVED"
    versions = _MODEL_VERSIONS[request["model_name"]]
    for v in versions:
        if v["version"] == request["version"]:
            v["stage"] = request["target_stage"]
    return request


@mcp.tool()
def reject_transition(request_id: str, reason: str) -> dict:
    """Reject a pending stage-transition request with a reason."""
    request = _PENDING_APPROVALS.get(request_id)
    if request is None:
        raise ValueError(f"unknown request_id: {request_id}")
    request["status"] = "REJECTED"
    request["reason"] = reason
    return request


@mcp.tool()
def check_data_drift(model_name: str, version: int) -> dict:
    """Get a mocked data drift report (per-feature drift scores) for a model version."""
    random.seed(f"{model_name}-{version}-data")
    features = ["age", "income", "transaction_amount", "account_tenure_days"]
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
    """Get a mocked performance/prediction drift report for a model version over the last 30 days."""
    random.seed(f"{model_name}-{version}-perf")
    baseline_auc = round(random.uniform(0.85, 0.93), 3)
    current_auc = round(baseline_auc - random.uniform(0.0, 0.15), 3)
    delta = round(current_auc - baseline_auc, 3)
    return {
        "model_name": model_name,
        "version": version,
        "baseline_auc": baseline_auc,
        "current_auc": current_auc,
        "auc_delta": delta,
        "degraded": delta < -0.05,
        "window": {
            "start": (datetime.utcnow() - timedelta(days=30)).date().isoformat(),
            "end": datetime.utcnow().date().isoformat(),
        },
    }


@mcp.tool()
def get_drift_report(model_name: str, version: int) -> dict:
    """Get a combined data + performance drift report with a retrain recommendation."""
    data = check_data_drift(model_name, version)
    perf = check_model_drift(model_name, version)
    recommend_retrain = data["drift_detected"] or perf["degraded"]
    return {
        "model_name": model_name,
        "version": version,
        "data_drift": data,
        "performance_drift": perf,
        "recommend_retrain": recommend_retrain,
    }


if __name__ == "__main__":
    mcp.run()

# Run directly:      python app.py
# Run with Inspector: fastmcp dev app.py

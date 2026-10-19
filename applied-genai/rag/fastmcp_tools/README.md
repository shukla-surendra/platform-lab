# fastmcp_tools

MLOps tooling exposed as MCP tools via the standalone [`fastmcp`](https://gofastmcp.com) package (not the `mcp.server.fastmcp` bundled in the official `mcp` SDK — see `../official_mcp_tools` for that variant).

All tools are mocked: there's no real MLflow, model registry, or drift-detection backend. State (registered models, pending approvals) lives in memory for the life of the server process and resets on restart.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py                # run the server directly (stdio)
fastmcp dev inspector app.py  # run with the MCP Inspector UI for interactive testing
```

If you're also running `official_mcp_tools`'s Inspector at the same time, its proxy/UI already hold ports 6277/6274. Use different ports for this one:

```bash
fastmcp dev inspector app.py --ui-port 6280 --server-port 6281
```

## Tools

**Tracking**
- `list_experiments` — list experiment names
- `list_runs(experiment_name)` — runs in an experiment with status/metrics
- `get_run_details(run_id)` — full params/metrics for a run

**Model registry**
- `register_model(model_name, run_id)` — register a run as a new model version
- `list_model_versions(model_name)` — versions and their current stage
- `request_stage_transition(model_name, version, target_stage)` — request a move to Staging/Production/Archived; creates a pending approval
- `list_pending_approvals()` — approvals awaiting a decision
- `approve_transition(request_id)` — approve and apply the stage change
- `reject_transition(request_id, reason)` — reject with a reason

**Drift**
- `check_data_drift(model_name, version)` — per-feature drift scores (deterministic per model/version via a seeded RNG)
- `check_model_drift(model_name, version)` — AUC drift over a 30-day window
- `get_drift_report(model_name, version)` — combined data + performance drift with a retrain recommendation

## Seed data

Two mock experiments are preloaded: `fraud-detection` (runs `run-a1b2`, `run-c3d4`) and `churn-prediction` (run `run-e5f6`). Use these run IDs with `register_model` to try the registry/approval/drift flow end to end.

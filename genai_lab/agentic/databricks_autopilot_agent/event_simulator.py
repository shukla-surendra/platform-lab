#!/usr/bin/env python3
"""Drops realistic Databricks job-run event files into events/inbox/, standing in for a real
event source (Databricks job webhooks / EventBridge / a Kafka topic). The daemon (daemon.py)
watches that directory and reacts as files land — this script is what makes "automode" visible:
run it in one terminal and the daemon in another to watch the agent respond live.

Usage:
  python event_simulator.py                        # plays the "mixed" scripted scenario once
  python event_simulator.py --scenario recurring-oom
  python event_simulator.py --forever               # keeps emitting random events until Ctrl-C
  python event_simulator.py --list-scenarios
"""

from __future__ import annotations

import argparse
import json
import random
import time
import uuid
from pathlib import Path

import config

ERROR_MESSAGES = {
    "oom": [
        "Driver OOM: java.lang.OutOfMemoryError: Java heap space during shuffle stage 42",
        "ExecutorLostFailure: executor 3 exited with OutOfMemoryError, container killed by YARN",
    ],
    "schema_drift": [
        "AnalysisException: cannot resolve column 'discount_pct' given input columns: "
        "[id, sku, qty, price]. Schema mismatch detected.",
        "org.apache.spark.sql.AnalysisException: Column 'region_code' is not defined in "
        "upstream schema, source table was altered",
    ],
    "upstream_stale": [
        "Source table {table} has not been updated in {minutes} minutes, expected freshness "
        "{expected} minutes",
    ],
    "transient": [
        "com.databricks.NetworkException: Connection reset by peer while reading from DBFS "
        "mount, retrying",
        "java.net.SocketTimeoutException: Read timed out while writing checkpoint to cloud storage",
    ],
    "unknown": [
        "Job failed with exit code 1: unspecified worker task failure",
    ],
}

JOBS = ["job-daily-sales-etl", "job-churn-features", "job-inventory-sync"]
UPSTREAM_TABLE_BY_JOB = {
    "job-daily-sales-etl": ("raw.sales_transactions", 340, 60),
    "job-churn-features": ("curated.customer_events", 260, 120),
    "job-inventory-sync": ("raw.warehouse_feed", 90, 30),
}


def _error_message(category: str, job_id: str) -> str:
    template = random.choice(ERROR_MESSAGES[category])
    if category == "upstream_stale":
        table, minutes, expected = UPSTREAM_TABLE_BY_JOB[job_id]
        return template.format(table=table, minutes=minutes, expected=expected)
    return template


def emit(event_type: str, job_id: str, category: str | None = None) -> Path:
    event_id = uuid.uuid4().hex[:8]
    run_id = f"run-{uuid.uuid4().hex[:6]}"
    event = {
        "event_id": event_id,
        "type": event_type,
        "job_id": job_id,
        "run_id": run_id,
    }
    if event_type == "job_run_failed":
        event["error_message"] = _error_message(category or "unknown", job_id)
        event["_seeded_category"] = category  # for the README's expected-vs-actual comparison only

    # Filename is timestamp-sortable so the daemon processes events in emission order.
    filename = f"{time.time():020.6f}_{event_id}.json"
    path = config.INBOX_DIR / filename
    path.write_text(json.dumps(event, indent=2))
    label = f"{event_type}" + (f" ({category})" if category else "")
    print(f"[simulator] {job_id}: {label}")
    return path


# Each scenario is a list of (event_type, category_or_None). job_id is chosen once per scenario
# unless the scenario explicitly varies it.
SCENARIOS: dict[str, list[tuple[str, str | None]]] = {
    "recurring-oom": [
        ("job_run_started", None),
        ("job_run_failed", "oom"),
        ("job_run_started", None),
        ("job_run_failed", "oom"),
        ("job_run_started", None),
        ("job_run_failed", "oom"),  # 3rd consecutive failure -> should trip the recurrence override
    ],
    "schema-drift": [
        ("job_run_started", None),
        ("job_run_failed", "schema_drift"),
    ],
    "upstream-delay": [
        ("job_run_started", None),
        ("job_run_failed", "upstream_stale"),
    ],
    "transient-then-recover": [
        ("job_run_started", None),
        ("job_run_failed", "transient"),
        ("job_run_started", None),
        ("job_run_succeeded", None),  # recovered on its own after the agent's auto-retry
    ],
    "mixed": [
        ("job_run_started", None),
        ("job_run_succeeded", None),
        ("job_run_started", None),
        ("job_run_failed", "transient"),
        ("job_run_started", None),
        ("job_run_succeeded", None),
        ("job_run_started", None),
        ("job_run_failed", "oom"),
        ("job_run_started", None),
        ("job_run_failed", "schema_drift"),
        ("job_run_started", None),
        ("job_run_failed", "upstream_stale"),
    ],
}


def play_scenario(name: str, job_id: str | None, min_interval: float, max_interval: float) -> None:
    steps = SCENARIOS[name]
    chosen_job = job_id or random.choice(JOBS)
    for i, (event_type, category) in enumerate(steps):
        # "mixed" rotates jobs each started/succeeded pair to touch all three; single-incident
        # scenarios stay on one job so the recurrence count is meaningful.
        step_job = JOBS[i % len(JOBS)] if name == "mixed" and job_id is None else chosen_job
        emit(event_type, step_job, category)
        if i < len(steps) - 1:
            time.sleep(random.uniform(min_interval, max_interval))


def play_forever(min_interval: float, max_interval: float) -> None:
    print("Emitting random events until Ctrl-C ...")
    try:
        while True:
            job_id = random.choice(JOBS)
            emit("job_run_started", job_id)
            time.sleep(random.uniform(min_interval, max_interval))
            if random.random() < 0.35:
                category = random.choice(list(ERROR_MESSAGES))
                emit("job_run_failed", job_id, category)
            else:
                emit("job_run_succeeded", job_id)
            time.sleep(random.uniform(min_interval, max_interval))
    except KeyboardInterrupt:
        print("\nStopped.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", default="mixed", choices=list(SCENARIOS), help="Scripted scenario to play.")
    parser.add_argument("--job", default=None, choices=JOBS, help="Pin the scenario to one job (default: scenario-dependent).")
    parser.add_argument("--forever", action="store_true", help="Ignore --scenario; emit random events until Ctrl-C.")
    parser.add_argument("--min-interval", type=float, default=1.0, help="Minimum seconds between events.")
    parser.add_argument("--max-interval", type=float, default=3.0, help="Maximum seconds between events.")
    parser.add_argument("--list-scenarios", action="store_true", help="List available --scenario values and exit.")
    args = parser.parse_args()

    config.INBOX_DIR.mkdir(parents=True, exist_ok=True)

    if args.list_scenarios:
        for name, steps in SCENARIOS.items():
            print(f"{name}: {len(steps)} events")
        return 0

    if args.forever:
        play_forever(args.min_interval, args.max_interval)
    else:
        play_scenario(args.scenario, args.job, args.min_interval, args.max_interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Batch drift check — CronJob entrypoint.

Consumes a fixed-duration window of events straight off Kafka (not through
02-feature-store — batch mode is comparing a bulk window against history,
not serving anything online, so it skips the Feast push step streaming mode
does), compares it to the fixed reference distribution via Evidently, emits
drift_score/drift_detected over OTLP, and exits. One run = one Evidently
`Report`, same as ../../../k8s_mlops/evidently_stack/'s notebook demo, just
triggered on a schedule instead of by hand.
"""

import json
import os
import sys
import time

import pandas as pd
from evidently import Dataset, DataDefinition, Report
from evidently.metrics import ValueDrift
from kafka import KafkaConsumer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "common"))
from otel_metrics import init_meter, record  # noqa: E402
from reference_data import load_reference  # noqa: E402

BOOTSTRAP_SERVERS = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
TOPIC = os.environ.get("TOPIC", "events")
WINDOW_SECONDS = int(os.environ.get("WINDOW_SECONDS", "60"))
OTEL_ENDPOINT = os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"]
DRIFT_THRESHOLD = float(os.environ.get("DRIFT_THRESHOLD", "0.5"))


def collect_window() -> pd.DataFrame:
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        auto_offset_reset="latest",
        consumer_timeout_ms=WINDOW_SECONDS * 1000,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    rows = [msg.value for msg in consumer]
    consumer.close()
    return pd.DataFrame(rows)


def extract_drift_score(snapshot) -> float:
    # NOT YET VERIFIED against a real Evidently run (see ../README.md) —
    # confirm this is where ValueDrift's score actually lands in
    # snapshot.dict() before trusting a real alert on it.
    result = snapshot.dict()
    metrics_list = result.get("metrics", [])
    if not metrics_list:
        raise ValueError(f"no metrics in snapshot: {result}")
    return float(metrics_list[0]["value"])


def main() -> None:
    init_meter(OTEL_ENDPOINT)
    reference = load_reference()

    print(f"collecting a {WINDOW_SECONDS}s window from {TOPIC}...", flush=True)
    current = collect_window()
    print(f"collected {len(current)} events", flush=True)

    if current.empty:
        print("empty window, nothing to compare, exiting", flush=True)
        return

    definition = DataDefinition()
    reference_dataset = Dataset.from_pandas(reference, data_definition=definition)
    current_dataset = Dataset.from_pandas(current[["amount", "category"]], data_definition=definition)

    report = Report([ValueDrift(column="amount")])
    snapshot = report.run(current_dataset, reference_dataset)

    drift_score = extract_drift_score(snapshot)
    drift_detected = drift_score > DRIFT_THRESHOLD
    print(f"amount drift_score={drift_score} drift_detected={drift_detected}", flush=True)
    record("amount", "batch", drift_score, drift_detected)

    # PeriodicExportingMetricReader exports on its own 5s timer; give it one
    # cycle to flush before the CronJob's pod exits, or this run's numbers
    # never leave the pod.
    time.sleep(6)


if __name__ == "__main__":
    main()

"""Streaming (live) drift check — long-running Deployment entrypoint.

Consumes Kafka continuously, pushes each event into 02-feature-store's
online store via the feature server's /push endpoint (so a real serving
system reading through Feast sees the same events this drift check does —
the train/serve consistency point of having a feature store at all), keeps
a sliding in-memory window, and re-runs the Evidently comparison against the
same fixed reference distribution batch mode uses every CHECK_INTERVAL_SECONDS.
Same metric names/labels as batch mode, `mode="streaming"` is the only
difference — see ../README.md.
"""

import json
import os
import sys
import time
from collections import deque

import pandas as pd
import requests
from evidently import Dataset, DataDefinition, Report
from evidently.metrics import ValueDrift
from kafka import KafkaConsumer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "common"))
from otel_metrics import init_meter, record  # noqa: E402
from reference_data import load_reference  # noqa: E402

BOOTSTRAP_SERVERS = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
TOPIC = os.environ.get("TOPIC", "events")
FEATURE_SERVER_URL = os.environ["FEATURE_SERVER_URL"]
OTEL_ENDPOINT = os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"]
WINDOW_SIZE = int(os.environ.get("WINDOW_SIZE", "200"))
MIN_WINDOW_SIZE = int(os.environ.get("MIN_WINDOW_SIZE", "50"))
CHECK_INTERVAL_SECONDS = int(os.environ.get("CHECK_INTERVAL_SECONDS", "15"))
DRIFT_THRESHOLD = float(os.environ.get("DRIFT_THRESHOLD", "0.5"))


def push_to_feast(event: dict) -> None:
    # NOT YET VERIFIED against a live feature server — confirm this request
    # body against a real `feast serve` instance (see
    # ../../02-feature-store/README.md) before relying on it. Failures are
    # logged, not raised: a feature-store hiccup shouldn't take the drift
    # check itself down.
    body = {
        "push_source_name": "amount_push_source",
        "df": {
            "producer_id": [event["producer_id"]],
            "amount": [event["amount"]],
            "category": [event["category"]],
            "event_timestamp": [pd.Timestamp.utcnow().isoformat()],
        },
        "to": "online",
    }
    try:
        resp = requests.post(f"{FEATURE_SERVER_URL}/push", json=body, timeout=5)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"feast push failed (continuing anyway): {exc}", flush=True)


def extract_drift_score(snapshot) -> float:
    result = snapshot.dict()
    metrics_list = result.get("metrics", [])
    if not metrics_list:
        raise ValueError(f"no metrics in snapshot: {result}")
    return float(metrics_list[0]["value"])


def check_drift(window: deque, reference: pd.DataFrame) -> None:
    if len(window) < MIN_WINDOW_SIZE:
        return
    current = pd.DataFrame(list(window))[["amount", "category"]]
    definition = DataDefinition()
    reference_dataset = Dataset.from_pandas(reference, data_definition=definition)
    current_dataset = Dataset.from_pandas(current, data_definition=definition)

    report = Report([ValueDrift(column="amount")])
    snapshot = report.run(current_dataset, reference_dataset)
    drift_score = extract_drift_score(snapshot)
    drift_detected = drift_score > DRIFT_THRESHOLD
    print(f"[streaming] amount drift_score={drift_score} drift_detected={drift_detected} (n={len(window)})", flush=True)
    record("amount", "streaming", drift_score, drift_detected)


def main() -> None:
    init_meter(OTEL_ENDPOINT)
    reference = load_reference()
    window: deque = deque(maxlen=WINDOW_SIZE)

    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id="drift-engine-streaming",
        auto_offset_reset="latest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )

    print(f"streaming drift check: {TOPIC} @ {BOOTSTRAP_SERVERS}, window={WINDOW_SIZE}, check every {CHECK_INTERVAL_SECONDS}s", flush=True)
    last_check = time.monotonic()
    for message in consumer:
        event = message.value
        window.append(event)
        push_to_feast(event)

        now = time.monotonic()
        if now - last_check >= CHECK_INTERVAL_SECONDS:
            check_drift(window, reference)
            last_check = now


if __name__ == "__main__":
    main()

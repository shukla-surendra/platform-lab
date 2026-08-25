"""Synthetic production-event producer for streaming-drift-detection.

Emits JSON events onto a Kafka topic at a steady rate. Each event carries one
numeric feature (`amount`) drawn from a normal distribution whose mean shifts
partway through the run — the injected drift that 03-drift-engine's batch and
streaming checks are meant to catch.
"""

import json
import os
import random
import time

from kafka import KafkaProducer

BOOTSTRAP_SERVERS = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
TOPIC = os.environ.get("TOPIC", "events")
EVENTS_PER_SECOND = float(os.environ.get("EVENTS_PER_SECOND", "5"))
DRIFT_SHIFT_AFTER_EVENTS = int(os.environ.get("DRIFT_SHIFT_AFTER_EVENTS", "2000"))
DRIFT_BASELINE_MEAN = float(os.environ.get("DRIFT_BASELINE_MEAN", "50.0"))
DRIFT_SHIFTED_MEAN = float(os.environ.get("DRIFT_SHIFTED_MEAN", "90.0"))
STDDEV = 10.0


def make_event(seq: int) -> dict:
    mean = DRIFT_BASELINE_MEAN
    if DRIFT_SHIFT_AFTER_EVENTS > 0 and seq >= DRIFT_SHIFT_AFTER_EVENTS:
        mean = DRIFT_SHIFTED_MEAN
    return {
        "event_id": seq,
        "producer_id": f"producer-{seq % 100}",
        "amount": round(random.gauss(mean, STDDEV), 2),
        "category": random.choice(["a", "b", "c"]),
        "timestamp": time.time(),
    }


def main() -> None:
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    delay = 1.0 / EVENTS_PER_SECOND
    seq = 0
    print(
        f"producing to {TOPIC} @ {BOOTSTRAP_SERVERS}, "
        f"{EVENTS_PER_SECOND}/s, drift shift after {DRIFT_SHIFT_AFTER_EVENTS} events "
        f"({DRIFT_BASELINE_MEAN} -> {DRIFT_SHIFTED_MEAN})",
        flush=True,
    )
    while True:
        event = make_event(seq)
        producer.send(TOPIC, event)
        seq += 1
        if seq % 500 == 0:
            producer.flush()
            print(f"produced {seq} events", flush=True)
        time.sleep(delay)


if __name__ == "__main__":
    main()

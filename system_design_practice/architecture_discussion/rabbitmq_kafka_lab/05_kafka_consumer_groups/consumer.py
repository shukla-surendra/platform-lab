# /// script
# requires-python = ">=3.12"
# dependencies = ["confluent-kafka>=2.6"]
# ///
"""Consume 'orders' as NAME in consumer group GROUP. Prints which partitions it owns. Ctrl+C to stop."""
import sys
from confluent_kafka import Consumer

name = sys.argv[1] if len(sys.argv) > 1 else "c1"
group = sys.argv[2] if len(sys.argv) > 2 else "shop"

def on_assign(consumer, partitions):
    owned = [p.partition for p in partitions]
    print(f"[{name}] rebalance: I now own partitions {owned or 'none (more consumers than partitions)'}", flush=True)

consumer = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": group,
    "auto.offset.reset": "earliest",
})
consumer.subscribe(["orders"], on_assign=on_assign)
print(f"[{name}] joining group '{group}'...", flush=True)

try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None or msg.error():
            continue
        print(f"[{name}] partition {msg.partition()} offset {msg.offset()}: {msg.value().decode()}", flush=True)
except KeyboardInterrupt:
    pass
finally:
    consumer.close()     # leave the group cleanly, which triggers a rebalance for the others

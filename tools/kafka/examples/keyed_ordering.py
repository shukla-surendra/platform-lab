"""
Kafka only guarantees ordering *within a partition*, never across an entire topic. The
producer's default partitioner hashes the message key to pick a partition — same key,
same partition, every time — which is the actual mechanism behind "all events for order
#42 arrive in order." No key means round-robin scattering across partitions instead: fine
for throughput, useless for ordering.

Run:
    pip install confluent-kafka
    export KAFKA_BOOTSTRAP_SERVERS=localhost:19092,localhost:19093,localhost:19094
    python3 keyed_ordering.py
"""
import os
from collections import defaultdict

from confluent_kafka import Consumer, Producer

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092,localhost:19093,localhost:19094")
TOPIC = "orders"
GROUP_ID = "keyed-ordering-demo-group"


def produce_keyed_events():
    producer = Producer({"bootstrap.servers": BOOTSTRAP})

    # Three "orders," each with several events. Same order_id -> same key -> same
    # partition -> that order's events arrive in the exact sequence they were produced.
    # Different order_ids can (and here, do) land on different partitions.
    events = [
        ("order-A", "created"), ("order-B", "created"), ("order-A", "paid"),
        ("order-C", "created"), ("order-A", "shipped"), ("order-B", "paid"),
        ("order-C", "paid"), ("order-B", "shipped"), ("order-C", "shipped"),
    ]
    for key, value in events:
        producer.produce(TOPIC, key=key, value=value)
    producer.flush(10)
    print(f"[producer] sent {len(events)} events for 3 order keys")


def consume_and_show_per_partition_order():
    consumer = Consumer({
        "bootstrap.servers": BOOTSTRAP,
        "group.id": GROUP_ID,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    consumer.subscribe([TOPIC])

    by_partition = defaultdict(list)
    by_key = defaultdict(list)
    empty_polls = 0
    while empty_polls < 3:
        msg = consumer.poll(timeout=2)
        if msg is None:
            empty_polls += 1
            continue
        if msg.error():
            continue
        by_partition[msg.partition()].append((msg.key().decode(), msg.value().decode()))
        by_key[msg.key().decode()].append(msg.value().decode())

    consumer.close()

    print("\n[consumer] events grouped by PARTITION (arrival order within each):")
    for partition in sorted(by_partition):
        print(f"  partition {partition}: {by_partition[partition]}")

    print("\n[consumer] events grouped by KEY — every key's events are in the order they")
    print("were produced, because every key always landed on the same partition:")
    for key in sorted(by_key):
        print(f"  {key}: {by_key[key]}")


if __name__ == "__main__":
    produce_keyed_events()
    consume_and_show_per_partition_order()

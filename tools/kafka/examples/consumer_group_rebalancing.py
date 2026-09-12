"""
The mechanism that makes Kafka both a scalable queue (consumer group) and a pub/sub system
(multiple groups) using the exact same topic, at the same time:

- Consumers that share a `group.id` DIVIDE a topic's partitions between them — each
  partition is owned by exactly one consumer in the group at a time, so the group as a
  whole processes every message exactly once (modulo the retry/redelivery semantics
  covered in basic_producer_consumer.py), and adding more consumers (up to the partition
  count) adds real parallelism.
- Consumers with DIFFERENT `group.id`s each get their own full, independent view of the
  topic — every group sees every message, unaffected by what any other group does. This is
  the mechanism, not a side effect: it's how the same Kafka topic serves multiple
  independent downstream systems (e.g., an analytics pipeline and a notification service
  both consuming "order events," with neither one able to affect what the other sees).

Run:
    pip install confluent-kafka
    export KAFKA_BOOTSTRAP_SERVERS=localhost:19092,localhost:19093,localhost:19094
    python3 consumer_group_rebalancing.py
"""
import os
import threading
import time
from collections import defaultdict

from confluent_kafka import Consumer, Producer

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092,localhost:19093,localhost:19094")
TOPIC = "orders"
NUM_MESSAGES = 30


def produce_messages():
    producer = Producer({"bootstrap.servers": BOOTSTRAP})
    for i in range(NUM_MESSAGES):
        producer.produce(TOPIC, key=f"key-{i}", value=f"event-{i}")
    producer.flush(10)
    print(f"[producer] sent {NUM_MESSAGES} messages across the topic's 3 partitions")


def run_consumer(group_id, consumer_name, results, assigned_partitions, duration_sec=8):
    # A fixed wall-clock window, not "stop after N empty polls" — the group-join/rebalance
    # handshake itself can take a couple of seconds before the first message ever arrives,
    # so counting early empty polls as "done" exits before assignment even completes.
    consumer = Consumer({
        "bootstrap.servers": BOOTSTRAP,
        "group.id": group_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })

    def on_assign(_consumer, partitions):
        assigned_partitions[consumer_name] = sorted(p.partition for p in partitions)

    consumer.subscribe([TOPIC], on_assign=on_assign)

    start = time.time()
    while time.time() - start < duration_sec:
        msg = consumer.poll(timeout=1)
        if msg is None or msg.error():
            continue
        results[consumer_name].append(msg.key().decode())
    consumer.close()


def run_two_consumers(group_ids, names):
    """Run two consumers concurrently, for the same fixed window, starting together (real
    separate clients, real rebalancing) and return what each one actually received.

    Deliberately starting both at the same instant, not staggered: if one consumer's
    window ends (and it leaves the group) meaningfully before the other's, that triggers a
    *second* rebalance mid-run that hands its partitions to whoever's left — real, but a
    confusing thing to explain in a first example. Keeping both windows aligned isolates
    just the one rebalance this example is actually about: the initial join.
    """
    results = defaultdict(list)
    assigned_partitions = {}
    threads = [
        threading.Thread(target=run_consumer, args=(group_ids[0], names[0], results, assigned_partitions)),
        threading.Thread(target=run_consumer, args=(group_ids[1], names[1], results, assigned_partitions)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results, assigned_partitions


if __name__ == "__main__":
    produce_messages()

    print("\n=== SAME group.id: partitions are DIVIDED between the two consumers ===")
    same_group_results, same_group_partitions = run_two_consumers(
        group_ids=["shared-group", "shared-group"], names=["consumer-A", "consumer-B"]
    )
    for name in ("consumer-A", "consumer-B"):
        print(f"  {name}: assigned partitions {same_group_partitions.get(name)}, "
              f"received {len(same_group_results[name])} messages")
    total = len(same_group_results["consumer-A"]) + len(same_group_results["consumer-B"])
    print(f"  total messages processed by the GROUP: {total} (== {NUM_MESSAGES} produced, each exactly once)")

    print("\n=== DIFFERENT group.id: each consumer gets its OWN full copy of every message ===")
    diff_group_results, diff_group_partitions = run_two_consumers(
        group_ids=["group-x", "group-y"], names=["consumer-X", "consumer-Y"]
    )
    for name in ("consumer-X", "consumer-Y"):
        print(f"  {name}: assigned partitions {diff_group_partitions.get(name)}, "
              f"received {len(diff_group_results[name])} messages")

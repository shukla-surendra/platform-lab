"""
A single malformed ("poison") message can't be allowed to block an entire partition.
Kafka only lets a consumer commit offsets *in order* — there's no "skip just this one
message" primitive — so if a consumer's processing logic throws on message N and just
retries forever, every message after N on that partition is stuck behind it too, even
though they're perfectly fine.

The standard fix: catch the processing failure, republish the poison message (plus why it
failed) to a separate dead-letter topic, then commit past it on the original topic anyway.
The partition keeps moving; the failed message isn't silently dropped, it's parked
somewhere a human (or a separate retry/inspection process) can look at it later.

Run:
    pip install confluent-kafka
    export KAFKA_BOOTSTRAP_SERVERS=localhost:19092,localhost:19093,localhost:19094
    python3 dead_letter_queue.py
"""
import json
import os
import time

from confluent_kafka import Consumer, Producer

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092,localhost:19093,localhost:19094")
TOPIC = "orders"
DLQ_TOPIC = "orders-dlq"
GROUP_ID = "dlq-demo-group"


def produce_batch_with_one_poison_message():
    producer = Producer({"bootstrap.servers": BOOTSTRAP})
    # Valid messages: a JSON object with a numeric "amount". One message (order-4) has a
    # non-numeric amount on purpose — this is the "poison" message: it'll parse as valid
    # JSON but fail during processing, the realistic failure mode (malformed *data*, not a
    # malformed *message*, which is the harder, more common case to handle well).
    orders = [
        {"order_id": "order-1", "amount": 42.50},
        {"order_id": "order-2", "amount": 17.00},
        {"order_id": "order-3", "amount": 99.99},
        {"order_id": "order-4", "amount": "not-a-number"},   # <- poison
        {"order_id": "order-5", "amount": 5.25},
    ]
    for order in orders:
        producer.produce(TOPIC, key=order["order_id"], value=json.dumps(order))
    producer.flush(10)
    print(f"[producer] sent {len(orders)} orders (1 deliberately malformed)")


def process_order(order: dict) -> float:
    """The 'business logic' — deliberately strict, so the poison message throws here."""
    return float(order["amount"]) * 1.08   # apply tax; raises ValueError on bad amount


def run_consumer_with_dlq():
    consumer = Consumer({
        "bootstrap.servers": BOOTSTRAP,
        "group.id": GROUP_ID,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    dlq_producer = Producer({"bootstrap.servers": BOOTSTRAP})
    consumer.subscribe([TOPIC])

    processed, sent_to_dlq = [], []
    start = time.time()
    while time.time() - start < 8:
        msg = consumer.poll(timeout=1)
        if msg is None or msg.error():
            continue

        order = json.loads(msg.value())
        try:
            total = process_order(order)
            processed.append((order["order_id"], total))
            print(f"[consumer] processed {order['order_id']}: total={total:.2f}")
        except (ValueError, TypeError) as exc:
            # The whole point: catch it, route it, and STILL commit past it below —
            # exactly what keeps this partition from getting stuck on order-4 forever.
            dlq_producer.produce(
                DLQ_TOPIC,
                key=msg.key(),
                value=msg.value(),
                headers={
                    "error": str(exc).encode(),
                    "original_topic": TOPIC.encode(),
                    "original_partition": str(msg.partition()).encode(),
                    "original_offset": str(msg.offset()).encode(),
                },
            )
            dlq_producer.flush(10)
            sent_to_dlq.append(order["order_id"])
            print(f"[consumer] {order['order_id']} FAILED ({exc}) -> routed to {DLQ_TOPIC}")

        # Commit unconditionally — whether this message succeeded or was DLQ'd, either way
        # this offset is "handled" and the partition should move past it.
        consumer.commit(msg)

    consumer.close()
    print(f"\n[summary] processed successfully: {[o for o, _ in processed]}")
    print(f"[summary] routed to DLQ: {sent_to_dlq}")


def show_dlq_contents():
    consumer = Consumer({
        "bootstrap.servers": BOOTSTRAP,
        "group.id": "dlq-inspector",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    consumer.subscribe([DLQ_TOPIC])
    print(f"\n[dlq inspector] contents of {DLQ_TOPIC}:")
    start = time.time()
    while time.time() - start < 5:
        msg = consumer.poll(timeout=1)
        if msg is None or msg.error():
            continue
        headers = dict(msg.headers() or [])
        print(f"  key={msg.key().decode()} value={msg.value().decode()} "
              f"error={headers.get('error', b'').decode()} "
              f"original_offset={headers.get('original_offset', b'').decode()}")
    consumer.close()


if __name__ == "__main__":
    produce_batch_with_one_poison_message()
    run_consumer_with_dlq()
    show_dlq_contents()

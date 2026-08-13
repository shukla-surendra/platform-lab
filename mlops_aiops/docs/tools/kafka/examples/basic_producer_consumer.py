"""
The minimal real round trip: produce a message, confirm delivery via callback, consume it
back with manual offset commit. Every other example in this folder builds on this pattern.

Run:
    pip install confluent-kafka
    export KAFKA_BOOTSTRAP_SERVERS=localhost:19092,localhost:19093,localhost:19094
    python3 basic_producer_consumer.py
"""
import os

from confluent_kafka import Consumer, KafkaError, Producer

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092,localhost:19093,localhost:19094")
TOPIC = "orders"
GROUP_ID = "basic-demo-group"


def produce_one():
    # acks="all": the broker only sends the delivery callback once every in-sync replica
    # has the write, not just the partition leader — the durability half of the trade
    # (see docs/README.md's "Delivery guarantees" section for what this actually buys you
    # on a single-broker lab setup vs. a real multi-broker cluster).
    #
    # enable.idempotence=True: the producer tags each batch with a sequence number: if a
    # network blip causes the producer to retry a send the broker actually already
    # received, the broker recognizes the duplicate sequence number and drops it instead
    # of writing the message twice. This turns Kafka's default *at-least-once* producer
    # behavior (retries can duplicate) into *effectively-once* on the producer side alone
    # — still not the same as end-to-end exactly-once (that also needs the consumer side
    # to be idempotent or transactional, see dead_letter_queue.py's commit-after-process
    # ordering).
    producer = Producer({
        "bootstrap.servers": BOOTSTRAP,
        "acks": "all",
        "enable.idempotence": True,
    })

    delivered = {}

    def on_delivery(err, msg):
        if err is not None:
            delivered["error"] = err
        else:
            delivered["topic"] = msg.topic()
            delivered["partition"] = msg.partition()
            delivered["offset"] = msg.offset()

    producer.produce(TOPIC, key="order-1", value="basic round trip", callback=on_delivery)
    # produce() is async — it queues the message and returns immediately. flush() blocks
    # until every queued message's delivery callback has actually fired (or times out).
    # Skipping flush() is a real, common bug: the process can exit before anything is
    # actually sent, and there's no exception to warn you — produce() succeeding only
    # means "queued," never "delivered."
    remaining = producer.flush(10)
    print(f"[producer] {remaining} messages still in queue after flush (should be 0)")
    print(f"[producer] delivery report: {delivered}")
    return delivered


def consume_one():
    consumer = Consumer({
        "bootstrap.servers": BOOTSTRAP,
        "group.id": GROUP_ID,
        "auto.offset.reset": "earliest",   # only matters the FIRST time this group.id reads this topic
        "enable.auto.commit": False,        # commit manually, after processing succeeds — see below
    })
    consumer.subscribe([TOPIC])

    msg = consumer.poll(timeout=10)
    if msg is None:
        print("[consumer] no message received within timeout")
    elif msg.error():
        if msg.error().code() == KafkaError._PARTITION_EOF:
            print("[consumer] reached end of partition")
        else:
            print("[consumer] error:", msg.error())
    else:
        print(f"[consumer] key={msg.key()} value={msg.value()} "
              f"partition={msg.partition()} offset={msg.offset()}")
        # Commit AFTER successfully handling the message, not before. If the process
        # crashed between poll() and this line, the next poll (after restart) would
        # re-deliver the same message — at-least-once, the mechanism, not a bug.
        consumer.commit(msg)
        print("[consumer] offset committed")

    consumer.close()


if __name__ == "__main__":
    produce_one()
    consume_one()

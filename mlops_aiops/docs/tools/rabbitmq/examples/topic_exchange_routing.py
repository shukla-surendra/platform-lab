"""
Topic exchange: routing decided by pattern-matching the message's routing key, not just a
hash-to-shard the way Kafka's partition key is. `*` matches exactly one dot-separated
segment; `#` matches zero or more. This is genuinely more expressive per-message routing
than Kafka has any equivalent for.

Run:
    pip install pika
    export RABBITMQ_HOST=localhost RABBITMQ_PORT=5672 RABBITMQ_USER=labuser RABBITMQ_PASSWORD=labpass
    python3 topic_exchange_routing.py
"""
import os

import pika

HOST = os.environ.get("RABBITMQ_HOST", "localhost")
PORT = int(os.environ.get("RABBITMQ_PORT", 5672))
USER = os.environ.get("RABBITMQ_USER", "labuser")
PASSWORD = os.environ.get("RABBITMQ_PASSWORD", "labpass")

EXCHANGE = "orders-topic"
# queue -> binding pattern
BINDINGS = {
    "all-orders": "orders.#",             # every order event, any country, any tier
    "us-orders-only": "orders.us.*",      # only US orders, any tier
    "high-priority-only": "*.*.priority",  # any country, priority tier only
}


def connect():
    creds = pika.PlainCredentials(USER, PASSWORD)
    return pika.BlockingConnection(pika.ConnectionParameters(host=HOST, port=PORT, credentials=creds))


def setup():
    conn = connect()
    ch = conn.channel()
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    for queue, pattern in BINDINGS.items():
        ch.queue_declare(queue=queue, durable=True)
        ch.queue_bind(exchange=EXCHANGE, queue=queue, routing_key=pattern)
        ch.queue_purge(queue=queue)
    conn.close()


def publish_events():
    conn = connect()
    ch = conn.channel()
    events = [
        ("orders.us.standard", "US standard order"),
        ("orders.eu.standard", "EU standard order"),
        ("orders.us.priority", "US priority order"),
    ]
    for routing_key, body in events:
        ch.basic_publish(exchange=EXCHANGE, routing_key=routing_key, body=body.encode())
        print(f"[publisher] routing_key={routing_key!r} -> {body}")
    conn.close()


def show_what_each_queue_received():
    conn = connect()
    ch = conn.channel()
    print()
    for queue, pattern in BINDINGS.items():
        received = []
        while True:
            method, props, body = ch.basic_get(queue=queue, auto_ack=True)
            if method is None:
                break
            received.append(body.decode())
        print(f"[{queue}] bound to {pattern!r}: {received}")
    conn.close()


if __name__ == "__main__":
    setup()
    publish_events()
    show_what_each_queue_received()

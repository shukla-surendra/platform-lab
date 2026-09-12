"""
Two different ways a message ends up dead-lettered, both broker-native (no manual
"republish to another topic" code needed the way Kafka's DLQ pattern requires):

1. TTL expiry — the broker itself expires the message and routes it to the configured
   dead-letter exchange, entirely without consumer involvement.
2. A consumer explicitly rejecting a message it can't process (`basic_nack`, requeue=False)
   — this is the direct analog of Kafka's dead_letter_queue.py, except here the routing to
   the DLQ topic happens automatically via the queue's `x-dead-letter-exchange` argument,
   not via a manual re-publish in the except block.

Either way, the dead-lettered message carries an `x-death` header recording exactly why.

Run:
    pip install pika
    export RABBITMQ_HOST=localhost RABBITMQ_PORT=5672 RABBITMQ_USER=labuser RABBITMQ_PASSWORD=labpass
    python3 dead_letter_exchange.py
"""
import json
import os
import time

import pika

HOST = os.environ.get("RABBITMQ_HOST", "localhost")
PORT = int(os.environ.get("RABBITMQ_PORT", 5672))
USER = os.environ.get("RABBITMQ_USER", "labuser")
PASSWORD = os.environ.get("RABBITMQ_PASSWORD", "labpass")

DLX = "dlx"
DLQ = "dead-letters"


def connect():
    creds = pika.PlainCredentials(USER, PASSWORD)
    return pika.BlockingConnection(pika.ConnectionParameters(host=HOST, port=PORT, credentials=creds))


def setup():
    conn = connect()
    ch = conn.channel()
    ch.exchange_declare(exchange=DLX, exchange_type="fanout", durable=True)
    ch.queue_declare(queue=DLQ, durable=True)
    ch.queue_bind(exchange=DLX, queue=DLQ)
    ch.queue_purge(queue=DLQ)

    # Path 1: TTL-based expiry
    ch.queue_declare(queue="ttl-demo", durable=True, arguments={
        "x-message-ttl": 2000,
        "x-dead-letter-exchange": DLX,
    })
    ch.queue_purge(queue="ttl-demo")

    # Path 2: consumer-rejected poison message
    ch.queue_declare(queue="orders", durable=True, arguments={
        "x-dead-letter-exchange": DLX,
    })
    ch.queue_purge(queue="orders")
    conn.close()


def demo_ttl_expiry():
    conn = connect()
    ch = conn.channel()
    ch.basic_publish(exchange="", routing_key="ttl-demo", body=b"this will expire in 2s")
    print("[ttl] published a message with a 2s TTL, waiting...")
    conn.close()
    time.sleep(3)


def demo_poison_message():
    conn = connect()
    ch = conn.channel()
    orders = [
        {"order_id": "order-1", "amount": 42.50},
        {"order_id": "order-2", "amount": "not-a-number"},   # <- poison
        {"order_id": "order-3", "amount": 17.00},
    ]
    for order in orders:
        ch.basic_publish(exchange="", routing_key="orders", body=json.dumps(order).encode())
    print(f"[poison] published {len(orders)} orders (1 deliberately malformed)")

    processed = []
    for _ in range(len(orders)):
        method, props, body = ch.basic_get(queue="orders", auto_ack=False)
        order = json.loads(body)
        try:
            total = float(order["amount"]) * 1.08
            ch.basic_ack(method.delivery_tag)
            processed.append((order["order_id"], total))
        except (ValueError, TypeError) as exc:
            # requeue=False is what routes it to the DLX instead of just putting it back
            # at the front of the same queue for another consumer to immediately fail on.
            ch.basic_nack(method.delivery_tag, requeue=False)
            print(f"[poison] {order['order_id']} rejected ({exc}) -> dead-lettered")
    conn.close()
    print(f"[poison] processed successfully: {processed}")


def show_dlq_contents():
    conn = connect()
    ch = conn.channel()
    print(f"\n[dlq inspector] contents of '{DLQ}':")
    while True:
        method, props, body = ch.basic_get(queue=DLQ, auto_ack=True)
        if method is None:
            break
        death = dict(props.headers or {}).get("x-death", [{}])
        reason = death[0].get("reason") if death else None
        origin_queue = death[0].get("queue") if death else None
        print(f"  body={body} reason={reason!r} original_queue={origin_queue!r}")
    conn.close()


if __name__ == "__main__":
    setup()
    demo_ttl_expiry()
    demo_poison_message()
    show_dlq_contents()

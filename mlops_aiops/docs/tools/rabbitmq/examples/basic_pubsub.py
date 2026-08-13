"""
Fanout exchange: one publish, every bound queue gets its own independent copy — no routing
key needed, no coordination between the queues required. The RabbitMQ equivalent of "every
Kafka consumer group gets its own full copy of the topic," except decided by exchange
bindings (set up once, by whoever owns the topology) rather than by how many independent
consumer groups happen to subscribe at read time.

Run:
    pip install pika
    export RABBITMQ_HOST=localhost RABBITMQ_PORT=5672 RABBITMQ_USER=labuser RABBITMQ_PASSWORD=labpass
    python3 basic_pubsub.py
"""
import os

import pika

HOST = os.environ.get("RABBITMQ_HOST", "localhost")
PORT = int(os.environ.get("RABBITMQ_PORT", 5672))
USER = os.environ.get("RABBITMQ_USER", "labuser")
PASSWORD = os.environ.get("RABBITMQ_PASSWORD", "labpass")

EXCHANGE = "notifications"
QUEUES = ["email-service", "sms-service", "push-service"]


def connect():
    creds = pika.PlainCredentials(USER, PASSWORD)
    return pika.BlockingConnection(pika.ConnectionParameters(host=HOST, port=PORT, credentials=creds))


def setup():
    conn = connect()
    ch = conn.channel()
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="fanout", durable=True)
    for q in QUEUES:
        ch.queue_declare(queue=q, durable=True)
        ch.queue_bind(exchange=EXCHANGE, queue=q)
        ch.queue_purge(queue=q)   # start clean each run
    conn.close()


def publish_one_event():
    conn = connect()
    ch = conn.channel()
    ch.basic_publish(exchange=EXCHANGE, routing_key="", body=b"user signed up")
    print(f"[publisher] published to '{EXCHANGE}' (fanout, routing_key ignored)")
    conn.close()


def show_each_queue_got_its_own_copy():
    conn = connect()
    ch = conn.channel()
    for q in QUEUES:
        method, props, body = ch.basic_get(queue=q, auto_ack=True)
        print(f"[{q}] received: {body}")
    conn.close()


if __name__ == "__main__":
    setup()
    publish_one_event()
    show_each_queue_got_its_own_copy()

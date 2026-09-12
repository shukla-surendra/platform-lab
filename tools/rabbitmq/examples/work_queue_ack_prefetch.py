"""
Manual acknowledgment + prefetch_count: what actually makes competing consumers share work
fairly. The counter-intuitive part, demonstrated directly: with UNLIMITED prefetch (the
easy default to leave in place), a slow consumer can end up hoarding almost the entire
backlog while a fast consumer sits idle — the opposite of "the queue evens things out."
prefetch_count=1 is what turns this into real, speed-proportional work-stealing.

Run:
    pip install pika
    export RABBITMQ_HOST=localhost RABBITMQ_PORT=5672 RABBITMQ_USER=labuser RABBITMQ_PASSWORD=labpass
    python3 work_queue_ack_prefetch.py
"""
import os
import threading
import time

import pika

HOST = os.environ.get("RABBITMQ_HOST", "localhost")
PORT = int(os.environ.get("RABBITMQ_PORT", 5672))
USER = os.environ.get("RABBITMQ_USER", "labuser")
PASSWORD = os.environ.get("RABBITMQ_PASSWORD", "labpass")

QUEUE = "work-queue"
NUM_TASKS = 20
DURATION_SEC = 6


def connect():
    creds = pika.PlainCredentials(USER, PASSWORD)
    return pika.BlockingConnection(pika.ConnectionParameters(host=HOST, port=PORT, credentials=creds))


def seed_queue():
    conn = connect()
    ch = conn.channel()
    ch.queue_declare(queue=QUEUE, durable=True)
    ch.queue_purge(queue=QUEUE)
    for i in range(NUM_TASKS):
        ch.basic_publish(exchange="", routing_key=QUEUE, body=f"task-{i}".encode(),
                          properties=pika.BasicProperties(delivery_mode=2))
    conn.close()
    print(f"[setup] seeded {NUM_TASKS} tasks onto '{QUEUE}'")


def consume(name, per_task_delay, prefetch_count, results):
    """One consumer: acks each message only after `per_task_delay` seconds of 'processing'."""
    conn = connect()
    ch = conn.channel()
    ch.basic_qos(prefetch_count=prefetch_count)
    count = 0
    start = time.time()
    for method, props, body in ch.consume(QUEUE, auto_ack=False, inactivity_timeout=1):
        if time.time() - start > DURATION_SEC:
            break
        if method is None:
            continue
        time.sleep(per_task_delay)
        ch.basic_ack(method.delivery_tag)
        count += 1
    results[name] = count
    conn.close()


def run_trial(prefetch_count):
    seed_queue()
    results = {}
    threads = [
        threading.Thread(target=consume, args=("slow (0.5s/task)", 0.5, prefetch_count, results)),
        threading.Thread(target=consume, args=("fast (0s/task)", 0.0, prefetch_count, results)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


if __name__ == "__main__":
    print(f"\n=== prefetch_count=0 (UNLIMITED) ===")
    print(run_trial(prefetch_count=0))

    print(f"\n=== prefetch_count=1 (fair, speed-proportional dispatch) ===")
    print(run_trial(prefetch_count=1))

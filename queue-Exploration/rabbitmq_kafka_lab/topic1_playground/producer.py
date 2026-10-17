# /// script
# requires-python = ">=3.12"
# dependencies = ["confluent-kafka>=2.6"]
# ///
"""Send a batch of N JSON events (default 15) to TOPIC (default 'topic1'), keyed by user, and print where each one landed."""
import json
import random
import sys
import time

from confluent_kafka import Producer

count = int(sys.argv[1]) if len(sys.argv) > 1 else 15
TOPIC = sys.argv[2] if len(sys.argv) > 2 else "topic1"
USERS = ["user-1", "user-2", "user-3", "user-4"]
EVENTS = ["signup", "login", "view_item", "add_to_cart", "purchase", "logout"]

producer = Producer({"bootstrap.servers": "localhost:9092"})

def delivered(err, msg):
    if err:
        print("FAILED", err)
    else:
        print(f"key={msg.key().decode():<7} partition {msg.partition()} offset {msg.offset():<3} {msg.value().decode()}")

for i in range(1, count + 1):
    user = random.choice(USERS)
    event = {"id": i, "user": user, "event": random.choice(EVENTS), "sent_at": time.strftime("%X")}
    if event["event"] == "purchase":
        event["amount"] = random.randint(100, 5000)
    # Same key -> same partition, so each user's events stay in order
    producer.produce(TOPIC, key=user, value=json.dumps(event), on_delivery=delivered)
producer.flush()     # wait until Kafka has confirmed every message
print(f"sent {count} message(s) to {TOPIC}")

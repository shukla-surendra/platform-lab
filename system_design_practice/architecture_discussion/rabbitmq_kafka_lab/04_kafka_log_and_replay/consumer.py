# /// script
# requires-python = ">=3.12"
# dependencies = ["confluent-kafka>=2.6"]
# ///
"""Read 'events' as consumer group GROUP. Stops after 5 seconds with nothing new."""
import sys
from confluent_kafka import Consumer

group = sys.argv[1] if len(sys.argv) > 1 else "A"

consumer = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": group,                  # Kafka stores a bookmark (committed offset) per group
    "auto.offset.reset": "earliest",    # a brand-new group starts from the oldest message
    "enable.auto.commit": False,        # we commit ourselves, after handling each message
})
consumer.subscribe(["events"])

read = 0
idle = 0.0
while idle < 5:
    msg = consumer.poll(1.0)
    if msg is None:
        idle += 1
        continue
    if msg.error():
        print("error:", msg.error())
        continue
    idle = 0
    read += 1
    print(f"[group {group}] offset {msg.offset()}: {msg.value().decode()}")
    consumer.commit(message=msg, asynchronous=False)   # move this group's bookmark past this message

print(f"[group {group}] read {read} new message(s); nothing more for 5s, stopping")
consumer.close()

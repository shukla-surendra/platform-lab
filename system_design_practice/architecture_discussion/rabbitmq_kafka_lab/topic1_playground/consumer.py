# /// script
# requires-python = ">=3.12"
# dependencies = ["confluent-kafka>=2.6"]
# ///
"""Read TOPIC (default 'topic1') as consumer group GROUP (default 'topic1-readers'), printed as NAME. Stops after 5 seconds with nothing new."""
import json
import sys

from confluent_kafka import Consumer

group = sys.argv[1] if len(sys.argv) > 1 else "topic1-readers"
topic = sys.argv[2] if len(sys.argv) > 2 else "topic1"

consumer = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": group,                  # Kafka stores a bookmark (committed offset) per group
    "auto.offset.reset": "earliest",    # a brand-new group starts from the oldest message
    "enable.auto.commit": False,        # we commit ourselves, after handling each message
})
name = sys.argv[3] if len(sys.argv) > 3 else group

def assigned(consumer, partitions):
    # Called after every rebalance: shows which partitions this consumer now owns
    print(f"[{name}] assigned partitions {[p.partition for p in partitions] or 'none (idle)'}")

consumer.subscribe([topic], on_assign=assigned)

read = 0
idle = 0
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
    key = msg.key().decode() if msg.key() else None
    try:
        value = json.loads(msg.value())
    except ValueError:                  # messages typed by hand in the console producer may not be JSON
        value = msg.value().decode()
    print(f"[{name}] partition {msg.partition()} offset {msg.offset():<3} key={key}  {value}")
    consumer.commit(message=msg, asynchronous=False)   # move this group's bookmark past this message

print(f"[{name}] read {read} new message(s); nothing more for 5s, stopping")
consumer.close()

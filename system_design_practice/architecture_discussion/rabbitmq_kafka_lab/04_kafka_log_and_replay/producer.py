# /// script
# requires-python = ">=3.12"
# dependencies = ["confluent-kafka>=2.6"]
# ///
"""Append N messages to the 'events' topic (1 partition) and print the offset each one got."""
import sys
import time

from confluent_kafka import KafkaError, KafkaException, Producer
from confluent_kafka.admin import AdminClient, NewTopic

count = int(sys.argv[1]) if len(sys.argv) > 1 else 5
BOOTSTRAP = "localhost:9092"


def ensure_topic(name, partitions):
    """Create the topic and wait for it. Without waiting, the first message would auto-create
    the topic with the broker's default of 1 partition."""
    admin = AdminClient({"bootstrap.servers": BOOTSTRAP})   # keep a reference until the result arrives
    future = admin.create_topics([NewTopic(name, num_partitions=partitions)])[name]
    try:
        future.result()
    except KafkaException as e:
        if e.args[0].code() != KafkaError.TOPIC_ALREADY_EXISTS:
            raise


ensure_topic("events", partitions=1)   # 1 partition keeps the offsets easy to follow

producer = Producer({"bootstrap.servers": BOOTSTRAP})

def delivered(err, msg):
    if err:
        print("FAILED", err)
    else:
        print(f"appended '{msg.value().decode()}' at partition {msg.partition()} offset {msg.offset()}")

for i in range(1, count + 1):
    producer.produce("events", value=f"event {i} sent at {time.strftime('%X')}", on_delivery=delivered)
producer.flush()     # wait until Kafka has confirmed every message

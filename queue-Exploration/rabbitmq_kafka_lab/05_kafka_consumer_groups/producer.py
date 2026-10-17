# /// script
# requires-python = ">=3.12"
# dependencies = ["confluent-kafka>=2.6"]
# ///
"""Send 12 orders for 4 customers to the 'orders' topic (3 partitions), keyed by customer."""

from confluent_kafka import KafkaError, KafkaException, Producer
from confluent_kafka.admin import AdminClient, NewTopic

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


ensure_topic("orders", partitions=3)

producer = Producer({"bootstrap.servers": BOOTSTRAP})

def delivered(err, msg):
    print(f"key={msg.key().decode():6} -> partition {msg.partition()}  '{msg.value().decode()}'")

customers = ["alice", "bob", "erin", "mallory"]   # chosen so they spread over all 3 partitions
for n in range(1, 4):
    for c in customers:
        # Same key -> same partition, every time. That's how Kafka keeps per-customer order.
        producer.produce("orders", key=c, value=f"{c} order #{n}", on_delivery=delivered)
producer.flush()

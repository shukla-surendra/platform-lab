# /// script
# requires-python = ">=3.12"
# dependencies = ["confluent-kafka>=2.6"]
# ///
"""Send 1 slow task followed by 4 fast ones to the 'tasks' topic (1 partition)."""

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


ensure_topic("tasks", partitions=1)

producer = Producer({"bootstrap.servers": BOOTSTRAP})
for task in ["task-1 slow:15", "task-2 fast:1", "task-3 fast:1", "task-4 fast:1", "task-5 fast:1"]:
    producer.produce("tasks", value=task)
    print("sent", task)
producer.flush()

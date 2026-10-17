# /// script
# requires-python = ">=3.12"
# dependencies = ["confluent-kafka>=2.6"]
# ///
"""Work through 'tasks' as NAME in group 'task-workers'.

  uv run consumer.py A           normal settings (poll deadline: 5 minutes)
  uv run consumer.py A --strict  poll deadline of 10 seconds, shorter than the 15-second slow task
"""
import sys
import time
from confluent_kafka import Consumer, KafkaException

name = sys.argv[1] if len(sys.argv) > 1 else "A"
strict = "--strict" in sys.argv

config = {
    "bootstrap.servers": "localhost:9092",
    "group.id": "task-workers",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,                 # commit only after a task is finished
}
if strict:
    config["session.timeout.ms"] = 6000          # heartbeat deadline (the broker's minimum)
    config["max.poll.interval.ms"] = 10000       # must call poll() again within 10s, or be kicked out

def on_assign(consumer, partitions):
    print(f"[{name}] {time.strftime('%X')} owns partitions {[p.partition for p in partitions] or 'none'}", flush=True)

consumer = Consumer(config)
consumer.subscribe(["tasks"], on_assign=on_assign)
print(f"[{name}] joining group 'task-workers'{' (strict poll deadline)' if strict else ''}...", flush=True)

try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print(f"[{name}] {time.strftime('%X')} {msg.error()}", flush=True)
            continue
        task = msg.value().decode()
        waited = time.time() - msg.timestamp()[1] / 1000
        print(f"[{name}] {time.strftime('%X')} start {task}  (waited {waited:.0f}s in Kafka)", flush=True)
        time.sleep(int(task.split(":")[1]))      # the work. poll() is NOT called during this
        try:
            consumer.commit(message=msg, asynchronous=False)
            print(f"[{name}] {time.strftime('%X')} done  {task}, committed", flush=True)
        except KafkaException as e:
            print(f"[{name}] {time.strftime('%X')} done  {task}, but COMMIT REJECTED: {e.args[0].name()}"
                  " (I was kicked out of the group, so someone else will redo it)", flush=True)
except KeyboardInterrupt:
    pass
finally:
    consumer.close()

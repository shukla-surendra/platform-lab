# 04 · Kafka: a log, not a queue

**One idea:** Kafka **keeps** messages after they're read. Each consumer group just remembers how far it
has read (its **committed offset**, like a bookmark). Different groups read the same messages independently,
and can re-read them.

```
topic "events", partition 0
 offset:   0         1         2         3         4
         [event 1][event 2][event 3][event 4][event 5]  ◀── producer appends here
                                                  ▲
                              group A's bookmark ─┘ (read everything)
          ▲
          └─ a new group B starts here and reads all 5
```

## Run it

```bash
uv run producer.py 5      # append 5 messages: offsets 0-4
uv run consumer.py A      # group A reads 5
uv run consumer.py A      # group A reads 0: its bookmark is already at the end
uv run consumer.py B      # group B reads all 5 again: the messages were never deleted
uv run producer.py 2      # append 2 more: offsets 5-6
uv run consumer.py A      # group A reads only the 2 new ones
```

## What to look for

1. **Reading doesn't delete.** Compare with RabbitMQ lesson 01, where an acked job was gone for good.
2. **The bookmark belongs to the group**, not the message. Group A and group B are separate readers.
3. Kafka UI at http://localhost:8080 → **Topics** → `events` → *Messages* shows every message still there.
   **Consumers** shows each group and its lag (how far behind the end it is).

## Experiment: replay

Move group A's bookmark back to the start, then read again:

```bash
docker exec lab-kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group A --topic events --reset-offsets --to-earliest --execute
uv run consumer.py A      # reads all 7 again
```

This is the feature queues don't have: if a bug corrupted what a service built from these events, fix the
bug and replay the history.

Messages aren't kept forever: the topic's **retention** (7 days by default) decides when old ones are deleted.

Next: [05 · consumer groups and partitions](../05_kafka_consumer_groups/)

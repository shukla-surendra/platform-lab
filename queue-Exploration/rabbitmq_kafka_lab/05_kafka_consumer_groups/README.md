# 05 · Kafka partitions and consumer groups

**One idea:** a topic is split into **partitions**. Within one consumer group, each partition is read by
exactly **one** consumer. That's how Kafka spreads work, and also why it can't use more consumers than it
has partitions.

```
topic "orders" (3 partitions)          consumer group "shop"
  partition 0  ───────────────────────▶ c1
  partition 1  ───────────────────────▶ c2
  partition 2  ───────────────────────▶ c3
                                        c4  (idle: no partition left)
```

## Run it

```bash
uv run producer.py                 # 12 orders; note which partition each customer lands on

# then, one terminal each, starting them one at a time:
uv run consumer.py c1              # owns partitions [0, 1, 2], reads all 12
uv run consumer.py c2              # rebalance: c1 and c2 split the partitions
uv run consumer.py c3              # rebalance: one partition each
uv run consumer.py c4              # owns none: more consumers than partitions
uv run producer.py                 # 12 more: watch them spread across c1-c3
```

Then, in another terminal, a **different group**:

```bash
uv run consumer.py audit audit-group     # gets all 24 orders, independently of group "shop"
```

## What to look for

1. **Same key, same partition.** Every `alice` order lands on one partition, so one consumer sees all of
   alice's orders, in order. Kafka guarantees order *per partition*, not across the topic. Different keys
   can share a partition: `alice` and `bob` both land on partition 2, so that consumer gets twice as much.
2. **Rebalancing.** Each time a consumer joins or leaves (Ctrl+C), every consumer in the group prints its new
   partitions. While a rebalance happens, the group briefly pauses.
3. **Max parallelism = number of partitions.** `c4` sits idle. Compare with RabbitMQ lesson 01, where
   adding a worker always added capacity.
4. **Groups are independent.** `audit-group` reads everything. Same idea as lesson 04, now with partitions.
5. Kafka UI → **Consumers** → `shop` shows which member owns which partition.

## Queue vs. Kafka, so far

| | RabbitMQ (lessons 01-03) | Kafka (lessons 04-05) |
|---|---|---|
| After a message is handled | Deleted | Kept until retention expires |
| Who gets a message | One worker per queue | One consumer per partition, per group |
| Scaling readers | Add workers | Add partitions, then consumers |
| Ordering | Per queue (loosely) | Strict per partition (per key) |
| Many independent readers | One queue each (lesson 02) | One group each, reading the same log |

Next: [06 · a slow message in Kafka](../06_kafka_slow_message/)

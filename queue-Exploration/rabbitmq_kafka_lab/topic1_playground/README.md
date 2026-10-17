# topic1 playground

A free-play folder next to the lessons: a producer that sends a batch of JSON events, and a consumer to read
them. Both default to `topic1`, which was created by hand in Kafka UI with **1 partition**.

All the rules found here, in one list: [Kafka constraints](kafka_constraints.md).

```bash
uv run producer.py                        # 15 events to topic1
uv run producer.py 50                     # 50 events
uv run producer.py 15 topic1-3p           # 15 events to another topic
uv run consumer.py                        # read topic1 as group "topic1-readers"
uv run consumer.py groupB                 # a new group starts again from offset 0
uv run consumer.py groupC topic1-3p       # read another topic
uv run consumer.py workers topic1-3p w1   # third argument: a name to print, for several workers in one group
```

Each consumer prints the partitions it was given every time the group rebalances.

This folder is its own uv project (`pyproject.toml`, `uv.lock`, dependency `confluent-kafka`), so both ways
of running work from inside it:

- `uv run consumer.py` reads the `# /// script` block at the top of the file and uses a temporary environment.
- `uv run python consumer.py` uses this folder's `.venv`. Point VS Code at
  `topic1_playground/.venv/bin/python` so Pylance can find `confluent_kafka` too.

Before this folder had its own project, `uv run python consumer.py` picked up the repo's top-level project
(no `confluent-kafka`) and failed with `ModuleNotFoundError: No module named 'confluent_kafka'`.

## What a partition is

A **topic** is a name. The data is stored in one or more **partitions**: each partition is a separate
append-only log, a list of messages numbered 0, 1, 2, ... That number is the **offset**.

```
topic "topic1" (1 partition)
  partition 0:  [0] [1] [2] [3] ... [19]   ← new messages always go on the end

topic "topic1-3p" (3 partitions)
  partition 0:  [0] [1] [2] [3] [4]
  partition 1:  [0] [1] [2] [3]
  partition 2:  [0] [1] [2] [3] [4] [5]
```

Each partition counts its own offsets, starting from 0. So "offset 3" means nothing on its own: a message's
address is **(topic, partition, offset)**.

## Which partition a message goes to

The producer decides, from the message **key**:

- **With a key:** partition = hash(key) mod number of partitions. The same key always goes to the same
  partition (as long as the partition count doesn't change).
- **Without a key:** the producer spreads messages over the partitions itself.

In `topic1` there is only one partition, so every message landed on partition 0 whatever its key
(offsets 0–4 from the console producer, 5–19 from `producer.py`). The key had no visible effect.

The same 15-event batch sent to `topic1-3p` (3 partitions), sorted by partition:

```
key=user-3  partition 0 offset 0   {"id": 2,  "event": "purchase", ...}
key=user-4  partition 0 offset 1   {"id": 3,  "event": "login", ...}
key=user-4  partition 0 offset 2   {"id": 4,  "event": "add_to_cart", ...}
key=user-3  partition 0 offset 3   {"id": 6,  "event": "signup", ...}
key=user-4  partition 0 offset 4   {"id": 15, "event": "login", ...}
key=user-2  partition 1 offset 0   {"id": 1,  "event": "logout", ...}
key=user-2  partition 1 offset 1   {"id": 7,  "event": "login", ...}
...
key=user-1  partition 2 offset 0   {"id": 5,  "event": "purchase", ...}
key=user-1  partition 2 offset 1   {"id": 8,  "event": "purchase", ...}
...
```

What this shows:

1. **Same key, same partition.** All of `user-1` is on partition 2, all of `user-2` on partition 1.
2. **Two keys can share a partition.** `user-3` and `user-4` both hashed to partition 0. A partition is not
   "one per user"; it holds whichever keys hash to it.
3. **Partitions can be uneven.** 5, 4 and 6 messages here. A very busy key makes its partition "hot".

## Why partitions exist

| Reason | What it means |
|---|---|
| **Ordering** | Kafka keeps order **within one partition only**. Because a key always goes to one partition, all events for `user-1` are read in the order they were sent. Across partitions there is no order: id 1 (partition 1) and id 2 (partition 0) can be read in either order. |
| **Parallel reading** | In one consumer group, each partition is read by **one** consumer. 3 partitions → up to 3 consumers working at once; a 4th consumer sits idle. `topic1` (1 partition) can only ever be read by one consumer per group. |
| **Scale** | Different partitions can live on different brokers, so one topic can be bigger and busier than one machine. (This lab has one broker, so all partitions are on it.) |
| **Replication** | Each partition is copied to `replication factor` brokers. Here it is 1 (one broker), so there are no copies. See `tools/kafka/` for a 3-broker cluster with real copies. |

## Things to remember

- **Choose the key for ordering.** Use the thing whose events must stay in order (user id, order id, account id).
- **Partition count is the limit on parallel consumers** in a group. Pick it with room to grow.
- **You can add partitions later but not remove them**, and adding them changes `hash(key) mod N`: new
  messages for a key may go to a different partition than its old ones, breaking per-key order across the change.
- **Offsets are per partition**, and a consumer group stores one bookmark (committed offset) per partition.

## How many workers can read one topic?

Two different questions, two different answers:

| Question | Answer |
|---|---|
| How many consumers can **subscribe** to a topic? | **No real limit.** Any number of consumers, in any number of groups. |
| How many consumers in **one group** can do work at the same time? | **At most the number of partitions.** Extra consumers join the group but get no partition and sit idle. |

A **consumer group** is a team of workers sharing the work: each partition goes to exactly one member, so
each message is handled once by the team. A **different group** is a separate team that gets its own copy of
every message, with its own bookmark.

```
topic1-3p (3 partitions)        group "workers"              group "audit"
  partition 0  ───────────────▶  w3                ┌──────▶  audit  (all 3 partitions)
  partition 1  ───────────────▶  w1                │
  partition 2  ───────────────▶  w2                │
                                 w4  (idle)        │
  every partition ─────────────────────────────────┘
```

### Real run

4 workers in group `workers` and 1 consumer in group `audit`, all started together on `topic1-3p` (which
already held 15 messages), then 12 more messages sent:

```bash
uv run consumer.py workers topic1-3p w1    # one terminal each: GROUP TOPIC NAME
uv run consumer.py workers topic1-3p w2
uv run consumer.py workers topic1-3p w3
uv run consumer.py workers topic1-3p w4
uv run consumer.py audit   topic1-3p audit
uv run producer.py 12 topic1-3p
```

```
[w1]    assigned partitions [1]          read 6   (all user-2)
[w2]    assigned partitions [2]          read 9   (all user-1)
[w3]    assigned partitions [0]          read 12  (user-3 and user-4)
[w4]    assigned partitions none (idle)  read 0
[audit] assigned partitions [0, 1, 2]    read 27  (everything)
```

What this shows:

1. **The group split the work.** 6 + 9 + 12 = 27: every message was handled exactly once inside `workers`.
2. **The 4th worker got nothing.** 3 partitions, so at most 3 busy workers. `w4` is a spare: if a busy worker
   dies, a rebalance gives its partition to a spare.
3. **A rebalance moved a partition.** `w1` stopped first, and `w3` then printed `assigned partitions [0, 1]`:
   it took over `w1`'s partition. Kafka does this automatically whenever a member joins or leaves.
4. **The other group got its own copy.** `audit` read all 27 messages, independently of `workers`. One topic
   can feed many services this way (billing, analytics, audit…), each as its own group.
5. **`topic1` (1 partition) can only use 1 worker per group.** More workers there would all be idle.

### So how do you get more workers?

- Add partitions first (`kafka-topics.sh --alter --topic topic1-3p --partitions 6`), then add workers up to
  that number. Remember that adding partitions moves keys to new partitions (see above).
- Make each worker faster, or have one worker process messages from its partition in several threads.
  (Then you must handle ordering and commits yourself.)
- Compare RabbitMQ (lesson [01](../01_rabbitmq_work_queue/)): any number of workers can share one queue, and
  each new worker adds capacity. Kafka trades that for per-key ordering and replay.

## Why messages are not deleted after reading

**Reading never deletes a message in Kafka**, and acknowledging it doesn't either. This is the biggest
difference from RabbitMQ, where an ack deletes the message from the queue (lesson [01](../01_rabbitmq_work_queue/)).

### The "ack" in Kafka is a commit

`consumer.py` already acknowledges every message:

```python
consumer.commit(message=msg, asynchronous=False)   # move this group's bookmark past this message
```

A commit doesn't touch the message. It saves the group's **bookmark** (committed offset): "group
`topic1-readers` has handled partition 0 up to offset 20". Kafka stores it in an internal topic,
`__consumer_offsets`. Next time the group starts, it carries on from the bookmark instead of offset 0.

After running `uv run consumer.py` once:

```
$ docker exec lab-kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
    --describe --group topic1-readers
GROUP           TOPIC   PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
topic1-readers  topic1  0          20              20              0
```

| Column | Meaning |
|---|---|
| `CURRENT-OFFSET` 20 | The group's bookmark: the next offset it will read |
| `LOG-END-OFFSET` 20 | The offset the next new message will get |
| `LAG` 0 | Messages the group hasn't handled yet (log end − bookmark). 0 means it's fully caught up. |

All 20 messages (offsets 0–19) are still in the topic. Run `uv run consumer.py` again: it reads 0 messages,
because its bookmark is at the end. Run `uv run consumer.py groupX`: a new group with no bookmark, so it
reads all 20 again.

Without a commit (or with auto-commit off and no `commit()` call), the bookmark doesn't move: the group
reads the same messages again after a restart. That's how "at least once" delivery works in Kafka.

### So when are messages deleted?

Only by the topic's **retention** rules, never by consumers:

```
$ docker exec lab-kafka /opt/kafka/bin/kafka-configs.sh --bootstrap-server localhost:9092 \
    --entity-type topics --entity-name topic1 --describe --all | grep -E ' retention|cleanup.policy'
  cleanup.policy=delete
  retention.bytes=-1          # no size limit
  retention.ms=604800000      # 7 days
```

| Way | How it works |
|---|---|
| **Time** (`retention.ms`) | Messages older than this are deleted. Default 7 days. |
| **Size** (`retention.bytes`) | Oldest messages are deleted once a partition is bigger than this. Default -1 (no limit). |
| **Compaction** (`cleanup.policy=compact`) | Keeps only the latest message per key, like a table of current values. |
| **By hand** (`kafka-delete-records.sh`) | Deletes everything before an offset. For admins, not normal use. |

Deletion happens in whole **segments** (files of messages), not one message at a time, so messages can stay
a little past their retention time.

```bash
# see the oldest and newest offsets still stored (earliest, then latest)
docker exec lab-kafka /opt/kafka/bin/kafka-get-offsets.sh --bootstrap-server localhost:9092 --topic topic1 --time -2
docker exec lab-kafka /opt/kafka/bin/kafka-get-offsets.sh --bootstrap-server localhost:9092 --topic topic1

# try it: keep messages for only 1 minute, and start a new segment file every 10s
# (only closed segments are deleted, and the broker checks every 5 minutes, so wait up to ~6 minutes)
docker exec lab-kafka /opt/kafka/bin/kafka-configs.sh --bootstrap-server localhost:9092 \
  --entity-type topics --entity-name topic1 --alter --add-config retention.ms=60000,segment.ms=10000
# undo it afterwards
docker exec lab-kafka /opt/kafka/bin/kafka-configs.sh --bootstrap-server localhost:9092 \
  --entity-type topics --entity-name topic1 --alter --delete-config retention.ms,segment.ms

# replay: move a group's bookmark back to the start (the group must be stopped)
docker exec lab-kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group topic1-readers --topic topic1 --reset-offsets --to-earliest --execute
```

Why Kafka works this way: many groups read the same topic at their own pace, and any of them can replay
history. If one group's ack deleted the message, the other groups would never see it.

## Try it

```bash
# 1. One consumer reads all 3 partitions
uv run consumer.py shop topic1-3p

# 2. Two terminals, same group, started together: they split the partitions
#    (a consumer stops after 5s of silence, so run `uv run producer.py 30 topic1-3p` in a third terminal)
uv run consumer.py shop2 topic1-3p
uv run consumer.py shop2 topic1-3p
```

Then open Kafka UI (http://localhost:8080) → Topics → `topic1-3p` → **Messages** to filter by partition, and
→ **Consumers** to see which member owns which partition. Lesson
[05 · consumer groups](../05_kafka_consumer_groups/) goes deeper into rebalancing.

```bash
# see the partitions and their sizes from the command line
docker exec lab-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic topic1-3p
docker exec lab-kafka /opt/kafka/bin/kafka-get-offsets.sh --bootstrap-server localhost:9092 --topic topic1-3p
```

# Kafka constraints

The rules Kafka puts on you, in one place. Each one says what it means in practice, what to do about it,
and where it was seen in this lab. Numbers in **Default** come from the lab broker (`lab-kafka`, Kafka 4.0)
via `kafka-configs.sh --describe --all`.

## Reading and workers

| # | Constraint | What it means | What to do | Seen in |
|---|---|---|---|---|
| 1 | **Busy consumers per group ≤ number of partitions** | Each partition goes to one consumer in a group. Extra consumers get no partition and sit idle. | Create topics with enough partitions for the most workers you'll need. Add partitions before adding workers. | `w4` idle on `topic1-3p` ([README](README.md#how-many-workers-can-read-one-topic)), lesson [05](../05_kafka_consumer_groups/) |
| 2 | **A 1-partition topic has 1 busy worker per group** | `topic1` can never be read in parallel within one group. | Use more partitions if you need parallel workers. | `topic1` |
| 3 | **Rebalances pause the group** | When a consumer joins or leaves, partitions are reassigned and reading stops briefly. | Avoid constantly starting and stopping consumers. | `w3` took over `w1`'s partition, lesson [05](../05_kafka_consumer_groups/) |
| 4 | **A consumer must call `poll()` often** | If it doesn't call `poll()` within `max.poll.interval.ms`, Kafka assumes it's stuck and removes it from the group. Its uncommitted message is processed again by another consumer. | Keep each message's work short, raise the setting above your longest task, or hand slow work to another thread. | lesson [06](../06_kafka_slow_message/) Part 2. Default 300000 ms (5 min) |
| 5 | **One slow message blocks its partition** | Messages in a partition are handled one after another, so everything behind a slow message waits (head-of-line blocking). | Don't use Kafka for long-running jobs; use a job queue (RabbitMQ, SQS, Postgres). | lesson [06](../06_kafka_slow_message/) Part 1 |

## Ordering and keys

| # | Constraint | What it means | What to do | Seen in |
|---|---|---|---|---|
| 6 | **Order is kept only within one partition** | Across partitions there is no order. Message id 1 on partition 1 and id 2 on partition 0 can be read in either order. | Put events that must stay in order under the same key. | `topic1-3p` run ([README](README.md#why-partitions-exist)) |
| 7 | **Same key → same partition, by `hash(key) mod N`** | All of a key's events go to one partition. Several keys can share a partition. | Choose the key for ordering (user id, order id, account id). | `user-3` and `user-4` both on partition 0 |
| 8 | **A busy key makes a "hot" partition** | One partition gets much more traffic than others, and its one consumer becomes the bottleneck. | Pick a key with many evenly used values. | partitions held 5, 4 and 6 messages |
| 9 | **Partitions can be added, never removed** | To go down, you must create a new topic and move to it. | Plan the partition count up front. | — |
| 10 | **Adding partitions moves keys** | `N` changes, so new messages for a key may go to a different partition than its old ones. Per-key order breaks across the change. | Add partitions rarely, ideally before the topic has data. | — |

## Acknowledging and deleting

| # | Constraint | What it means | What to do | Seen in |
|---|---|---|---|---|
| 11 | **Reading never deletes a message** | A commit only moves the group's bookmark (committed offset). The message stays for every other group. | Expect messages to remain. Use `LAG` to see what a group still has to do. | `topic1-readers` at offset 20, all 20 messages still there ([README](README.md#why-messages-are-not-deleted-after-reading)) |
| 12 | **Messages are deleted only by retention** | Time (`retention.ms`), size (`retention.bytes`) or compaction. Never by consumers. | Set retention per topic to how long you need replay. | `topic1`: `retention.ms=604800000` (7 days), `retention.bytes=-1` (no limit) |
| 13 | **Deletion happens in whole segments, on a timer** | Only closed segment files are deleted, and the broker checks every 5 minutes. Messages can outlive their retention time. | Don't rely on exact deletion times. | `log.segment.bytes=1073741824` (1 GiB), `log.retention.check.interval.ms=300000` |
| 14 | **No commit means the message comes back** | A consumer that crashes before committing makes its group read the same message again: at-least-once delivery. | Make processing safe to repeat (idempotent), for example by checking an id before acting. | lesson [06](../06_kafka_slow_message/) Part 2 |
| 15 | **No built-in dead-letter queue** | A message that always fails blocks its partition, or gets skipped if you commit past it. | Catch errors, send the failing message to your own "dead letter" topic, then commit. | lesson [06](../06_kafka_slow_message/), compare RabbitMQ lesson [03](../03_rabbitmq_dead_letter/) |
| 16 | **A group's bookmark expires when the group is unused** | If a group has no consumers for longer than `offsets.retention.minutes`, its committed offsets are deleted, and it starts again from `auto.offset.reset`. | Keep that in mind for groups that run rarely. | `offsets.retention.minutes=10080` (7 days) |
| 17 | **Moving a bookmark needs the group stopped** | `--reset-offsets` fails while the group has active members. | Stop the consumers, reset, start them again. | lesson [06](../06_kafka_slow_message/) Part 2 |

## Size, replication and topics

| # | Constraint | What it means | What to do | Seen in |
|---|---|---|---|---|
| 18 | **Messages are about 1 MB at most** | Bigger messages are rejected. | Store large files elsewhere (S3, a database) and send a link. | `message.max.bytes=1048588` (~1 MiB) |
| 19 | **Replication factor ≤ number of brokers** | Each copy of a partition must be on a different broker. With one broker, there are no copies. | Use 3 brokers and replication factor 3 for real data. | this lab: 1 broker, `ReplicationFactor: 1`. `tools/kafka/` runs 3 |
| 20 | **`acks=all` is only as safe as `min.insync.replicas`** | With 1 replica, "all" means one copy, so a dead broker loses data. | Replication factor 3 with `min.insync.replicas=2`. | `tools/kafka/docker-compose.yml` |
| 21 | **Unknown topics are created automatically, with defaults** | Sending to a misspelled topic creates it with 1 partition and replication factor 1. | Create topics on purpose, and turn off `auto.create.topics.enable` in production. | `auto.create.topics.enable=true`, `num.partitions=1` |

## Check them yourself

```bash
K="docker exec lab-kafka /opt/kafka/bin"

# partitions and replicas of a topic
$K/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic topic1-3p

# a group's bookmark and lag per partition
$K/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group workers

# a topic's settings (retention, cleanup policy, ...)
$K/kafka-configs.sh --bootstrap-server localhost:9092 --entity-type topics --entity-name topic1 --describe --all

# the broker's defaults (message size, retention check interval, ...)
$K/kafka-configs.sh --bootstrap-server localhost:9092 --entity-type brokers --entity-name 1 --describe --all
```

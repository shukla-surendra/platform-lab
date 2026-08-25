# Kafka

**Category:** distributed event streaming platform (partitioned commit log)

## What it is

Apache Kafka is not a traditional message queue with a "message goes in, message gets
deleted when consumed" model — it's a **distributed, partitioned, append-only log**.
Messages are written to the end of a topic's partitions and stay there (subject to a
retention policy, not consumption) until they expire; consumers don't remove anything by
reading it, they just track their own position (**offset**) in the log. That one
structural difference is the reason Kafka can do things a classic queue (RabbitMQ, SQS)
can't: multiple, completely independent consumer groups can each read the exact same topic
from the beginning, at their own pace, with zero coordination and zero effect on each
other — because reading a log never mutates it. See
[`../kafka-vs-rabbitmq.md`](../kafka-vs-rabbitmq.md) for exactly what that structural
difference means in practice, grounded in both tools' real verified behavior side by side.

Everything below was built and verified against a real **3-broker Kafka 3.8 cluster**
(KRaft mode — no ZooKeeper) running in Docker on this machine — every command, every
script, every leader election and consumer-group rebalance actually ran. Three brokers,
not one, on purpose: replication, leader failover, and in-sync-replica behavior can't be
demonstrated for real on a single node — see
[`production-scenarios.md`](production-scenarios.md) for what that topology makes possible.

## Running it

```bash
cd mlops_aiops/docs/tools/kafka
docker compose up -d
```

This starts three containers — `kafka-lab-1`, `kafka-lab-2`, `kafka-lab-3` — each running
in **KRaft mode**: every node is both a broker and a controller-quorum voter, using
Kafka's own Raft-based consensus for cluster metadata instead of a separate ZooKeeper
cluster — the default since Kafka 3.3 (KIP-500). See
[`../zookeeper/README.md`](../zookeeper/README.md) for what ZooKeeper did in this role
pre-KRaft, and why it's no longer needed here.

Two listener families per node (see [`docker-compose.yml`](docker-compose.yml)), and which
one to use depends on where the command is running from:

- **From inside the Docker network** (`docker exec` against any `kafka-lab-*` container) —
  use the container's own hostname on the internal `PLAINTEXT` listener:
  `kafka-1:9092`, `kafka-2:9092`, `kafka-3:9092`.
- **From the host machine** (a Python script run directly, not through `docker exec`) —
  use the `PLAINTEXT_HOST` listener's mapped ports: `localhost:19092`, `localhost:19093`,
  `localhost:19094`.

```bash
docker exec kafka-lab-1 /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka-1:9092 --list
```

Mixing these up — e.g. a `docker exec` command using `localhost:19093` to reach broker 2
— is a real thing hit while building this: broker 2's `PLAINTEXT_HOST` listener is
advertised as `localhost:19093` specifically for the *host*, and that address means
something different (unreachable) from *inside* broker 1's own container network
namespace. The client hangs and eventually times out with no useful error — the fix is
always "which side of the Docker network boundary is this command actually running on."

## Topics and partitions, hands-on

```bash
$ docker exec kafka-lab-1 /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka-1:9092 \
    --create --topic orders --partitions 3 --replication-factor 3
Created topic orders.

$ docker exec kafka-lab-1 /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka-1:9092 \
    --describe --topic orders
Topic: orders   TopicId: 1K-WYuNTTEOe7_bRv7xrDA   PartitionCount: 3   ReplicationFactor: 3   Configs: min.insync.replicas=2
        Topic: orders   Partition: 0   Leader: 1   Replicas: 1,2,3   Isr: 1,2,3
        Topic: orders   Partition: 1   Leader: 2   Replicas: 2,3,1   Isr: 2,3,1
        Topic: orders   Partition: 2   Leader: 3   Replicas: 3,1,2   Isr: 3,1,2
```

A topic is a named log; a partition is one physically-ordered shard of that log — a topic
with 3 partitions is 3 independent append-only sequences, each with its own offset
numbering starting at 0. **`ReplicationFactor: 3`** means each partition has 3 copies
spread across the 3 brokers, with leadership itself spread round-robin (broker 1 leads
partition 0, broker 2 leads partition 1, broker 3 leads partition 2) — real load
distribution, not just redundancy. `Isr` (in-sync replicas) tracks which replicas are
actually caught up enough to be safely promoted to leader if the current leader dies — see
[`production-scenarios.md`](production-scenarios.md) for exactly what happens to this list
when a broker actually goes down.

## Producing and consuming, the raw CLI way

```bash
$ docker exec kafka-lab-1 /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka-1:9092 \
    --create --topic cli-demo --partitions 1 --replication-factor 3
Created topic cli-demo.

$ docker exec kafka-lab-1 bash -c \
    "echo 'hello kafka' | /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server kafka-1:9092 --topic cli-demo"

$ docker exec kafka-lab-1 /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server kafka-1:9092 \
    --topic cli-demo --from-beginning --max-messages 1 --timeout-ms 5000
hello kafka
Processed a total of 1 messages
```

Worth internalizing before writing any client code: `--from-beginning` reads from offset 0
because that's what was *asked for* — there's no other notion of "new" vs. "old" message at
the broker level. Whether a consumer sees history or only future messages is entirely a
property of what offset it starts reading from, which is exactly what the Python examples'
`auto.offset.reset` setting controls.

## Python usage — full walkthrough

```bash
pip install confluent-kafka
export KAFKA_BOOTSTRAP_SERVERS=localhost:19092,localhost:19093,localhost:19094
```

`confluent-kafka` (a binding over `librdkafka`, the same C client Confluent's own tools use)
is used throughout — `pip install confluent-kafka` pulls a prebuilt wheel on macOS/Linux, no
separate C library install needed. Listing all three brokers in `bootstrap.servers` isn't
just belt-and-suspenders — it's what makes a client resilient to any *one* of them being
down when it first connects (see [`production-scenarios.md`](production-scenarios.md)'s
broker-failure scenario for this exact behavior, live).

### The minimal round trip: produce, confirm delivery, consume, commit

```python
from confluent_kafka import Producer, Consumer

BOOTSTRAP = "localhost:19092,localhost:19093,localhost:19094"

producer = Producer({
    "bootstrap.servers": BOOTSTRAP,
    "acks": "all",                 # see "Delivery guarantees" below
    "enable.idempotence": True,    # see "Delivery guarantees" below
})

def on_delivery(err, msg):
    if err:
        print("delivery failed:", err)
    else:
        print(f"delivered to {msg.topic()} partition={msg.partition()} offset={msg.offset()}")

producer.produce("orders", key="order-1", value="hello", callback=on_delivery)
producer.flush(10)   # blocks until every queued message's callback has fired — see below

consumer = Consumer({
    "bootstrap.servers": BOOTSTRAP,
    "group.id": "my-group",
    "auto.offset.reset": "earliest",   # only matters the FIRST time this group.id reads this topic
    "enable.auto.commit": False,        # commit manually, after processing succeeds
})
consumer.subscribe(["orders"])
msg = consumer.poll(timeout=10)
if msg and not msg.error():
    print(msg.key(), msg.value())
    consumer.commit(msg)   # commit AFTER handling succeeds, not before
consumer.close()
```

Actually run, this produces `delivered to orders partition=1 offset=0` and the consumer
prints `b'order-1' b'hello'` — see
[`examples/basic_producer_consumer.py`](examples/basic_producer_consumer.py) for the full,
commented version, including why `producer.flush()` isn't optional (`produce()` is
async — it queues and returns immediately; skipping `flush()` is a real, silent way to
lose messages when a short-lived process exits before anything's actually sent).

### Delivery guarantees: what `acks` and `enable.idempotence` actually buy you

- **`acks="all"`**: the producer's delivery callback only fires once every in-sync replica
  (not just the partition leader) has the write. On this cluster,
  `min.insync.replicas=2` (verified via `kafka-configs.sh --describe`) — `acks="all"`
  genuinely means "at least one broker besides the leader has this durably" here, unlike a
  single-broker setup where `acks="all"` and `acks=1` would be indistinguishable. See
  [`production-scenarios.md`](production-scenarios.md) for what happens to a write's
  durability guarantee specifically when the ISR shrinks below that number.
- **`enable.idempotence=True`**: the producer tags each send with a sequence number; if a
  network blip causes it to retry a send the broker already received, the broker
  recognizes the duplicate sequence number and drops it instead of writing twice. Default
  Kafka producer behavior without this is *at-least-once* (retries can duplicate);
  idempotence makes the producer side *effectively-once* — real end-to-end exactly-once
  additionally needs the consumer/processing side to handle redelivery safely too (the
  commit-after-processing pattern every example here uses), which idempotence alone
  doesn't provide. For true atomic multi-message exactly-once, see the transactional
  producer scenario in [`production-scenarios.md`](production-scenarios.md).

A real first-run artifact worth knowing about, not treating as a bug: the very first time
`enable.idempotence=True` (or a transactional producer) is used against a fresh broker,
`librdkafka` logs `Failed to acquire idempotence/transactional PID from broker: Coordinator
load in progress: retrying` — the broker's internal coordinator is still initializing its
state topic. It resolves itself within the retry window; the send still succeeds.

### Ordering: only guaranteed *within* a partition

```
partition 0: [('order-B', 'created'), ('order-B', 'paid'), ('order-B', 'shipped')]
partition 1: [('order-A', 'created'), ('order-A', 'paid'), ('order-A', 'shipped')]
partition 2: [('order-C', 'created'), ('order-C', 'paid'), ('order-C', 'shipped')]
```

Real output from [`examples/keyed_ordering.py`](examples/keyed_ordering.py): the default
partitioner hashes the message **key** to pick a partition, deterministically — same key,
same partition, every time, which is the entire mechanism behind "every event for order
A arrives in the order it was sent." A `None` key scatters round-robin across partitions
instead — better throughput, no ordering guarantee at all across those messages. There is
**no such thing as topic-wide ordering** in Kafka; only ever partition-wide — and that
per-key guarantee is more fragile than it looks, see
[`production-scenarios.md`](production-scenarios.md) for exactly how a routine partition
count increase breaks it, silently, for every key already in use.

### Consumer groups: the same topic as both a queue and a pub/sub system

```
=== SAME group.id: partitions are DIVIDED between the two consumers ===
  consumer-A: assigned partitions [2], received 8 messages
  consumer-B: assigned partitions [0, 1], received 22 messages
  total messages processed by the GROUP: 30 (== 30 produced, each exactly once)

=== DIFFERENT group.id: each consumer gets its OWN full copy of every message ===
  consumer-X: assigned partitions [0, 1, 2], received 30 messages
  consumer-Y: assigned partitions [0, 1, 2], received 30 messages
```

Real output from
[`examples/consumer_group_rebalancing.py`](examples/consumer_group_rebalancing.py). Two
consumers sharing a `group.id` **divide** a topic's partitions — the group as a whole
processes every message exactly once, and adding consumers (up to the partition count)
adds real parallelism. Two consumers with *different* `group.id`s each get their own
complete, independent view — this is the actual mechanism that lets the same topic feed
multiple unrelated downstream systems (an analytics pipeline and a notification service
both reading "order events") without either affecting what the other sees. **Rebalancing**
is what happens every time group membership changes (a consumer joins, leaves, or is
considered dead) — partitions get reassigned, which is why the assignment above isn't
knowable in advance, only after `on_assign` actually fires. What that reassignment actually
*costs* the rest of the group depends heavily on which assignment protocol is in use — see
[`production-scenarios.md`](production-scenarios.md) for a real, timestamped comparison of
the two.

### Retention: time/size-based, not "delete on consume"

```
$ docker exec kafka-lab-1 /opt/kafka/bin/kafka-configs.sh --bootstrap-server kafka-1:9092 \
    --entity-type topics --entity-name orders --describe --all | grep -E "retention.ms|cleanup.policy"
cleanup.policy=delete
retention.ms=604800000   # 7 days, the cluster default
```

This is the concrete evidence for the "log, not queue" distinction at the top of this doc:
messages age out after `retention.ms` (or a size-based `retention.bytes` limit, whichever
is hit first) regardless of whether any consumer ever read them — not when a consumer
acknowledges them. `cleanup.policy=compact` is the other option (keeps only the latest
value per key, forever — used for things like a changelog of "current state per key"
rather than an event history) — not used here, but worth knowing this is a real, distinct
choice, not just a retention-duration knob.

### Consumer lag: how far behind a group actually is

```
$ docker exec kafka-lab-1 /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server kafka-1:9092 \
    --describe --group dlq-demo-group
GROUP           TOPIC   PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
dlq-demo-group  orders  0          1               1               0
dlq-demo-group  orders  1          2               2               0
dlq-demo-group  orders  2          2               2               0
```

`LAG = LOG-END-OFFSET - CURRENT-OFFSET` — how many messages exist on that partition past
where this group has committed. `LAG=0` across every partition here means fully caught up.
This is the actual, standard signal used to answer "is this consumer keeping up with
production," and what a real alerting rule (`kafka_consumergroup_lag` in Prometheus's
Kafka exporter, or an equivalent) watches.

## Runnable examples

Each script in [`examples/`](examples/) was run against this exact compose setup and its
printed output matches what's shown above and below.

| Script | Pattern | Mechanism demonstrated |
|---|---|---|
| [`basic_producer_consumer.py`](examples/basic_producer_consumer.py) | Minimal real round trip | `acks`, `enable.idempotence`, manual commit-after-processing |
| [`keyed_ordering.py`](examples/keyed_ordering.py) | Per-entity event ordering | Key → partition hashing; ordering is partition-scoped, not topic-scoped |
| [`consumer_group_rebalancing.py`](examples/consumer_group_rebalancing.py) | Scaling consumption vs. fan-out to independent systems | Same `group.id` (partition division) vs. different `group.id`s (full duplication) |
| [`dead_letter_queue.py`](examples/dead_letter_queue.py) | Poison-message handling without blocking a partition | Catch, republish to a DLQ topic, commit past it anyway |

```bash
pip install confluent-kafka
export KAFKA_BOOTSTRAP_SERVERS=localhost:19092,localhost:19093,localhost:19094
python3 examples/basic_producer_consumer.py
```

## When it breaks: production scenarios

The commands above are Kafka working as intended, on a healthy 3-broker cluster.
[`production-scenarios.md`](production-scenarios.md) covers the other half — a broker
actually dying and what leadership/ISR do in response (and the surprising thing that
*doesn't* happen automatically once it recovers), the unclean-leader-election
availability/durability trade, why increasing partition count silently breaks every
existing key's ordering guarantee, a real timestamped trace of eager vs. cooperative-sticky
rebalancing, what "aborted" actually means for a transactional message on disk, and why a
recreated topic can make a consumer group silently skip data instead of erroring — each one
run against the live cluster, not just named.

## Deploying on Kubernetes

The docker-compose lab above is for learning Kafka's mechanics locally;
[`k8s_observability/streaming-drift-detection/01-ingestion/`](../../../../k8s_observability/streaming-drift-detection/01-ingestion/)
is this repo's example of running it on a cluster instead — Bitnami's
`kafka` chart, KRaft mode (`kraft.enabled: true`, `broker.replicaCount: 0`
so combined controller+broker nodes run as one pod instead of two, cheaper
for a small cluster).

One gotcha worth knowing before reaching for that chart: `charts.bitnami.com/bitnami`,
the classic Helm repo URL used in most existing Kafka-on-k8s tutorials,
stopped receiving updates on **2025-08-28** — every previously-published tag
moved to `docker.io/bitnamilegacy` and the repo is effectively frozen.
Current Bitnami charts are **OCI-only**:
`oci://registry-1.docker.io/bitnamicharts/kafka`, added as a Helm chart
dependency the same way any `https://` repo would be
(`repository: "oci://registry-1.docker.io/bitnamicharts"`, no `helm repo add`
needed — OCI registries are referenced directly by URL).

## Operational gotchas

- **A stuck poison message blocks everything behind it on that partition, silently.**
  Kafka only allows committing offsets *in order* — there's no "skip just this one
  message" primitive. A consumer that retries a failing message forever doesn't just fail
  that message, it halts every later message on that partition too, with no error thrown
  anywhere obvious. [`dead_letter_queue.py`](examples/dead_letter_queue.py) is the standard
  fix, verified end to end: real output showed `order-3`, `order-1`, `order-5`, `order-2`
  all processed successfully while `order-4` (malformed `amount`) was routed to
  `orders-dlq` with the original error, offset, and partition preserved as message
  headers — and the partition never stalled.
- **`producer.flush()` is not optional, and skipping it fails silently.** `produce()`
  queues a message locally and returns immediately (async) — a short-lived script or
  Lambda that calls `produce()` and exits without `flush()` can lose messages with zero
  exception raised anywhere. Always `flush()` (with a timeout) before a producer's process
  exits.
- **Bigger, cluster-level operational scenarios — broker failure, rebalance storms,
  transaction/isolation edge cases, offset invalidation — get their own doc, in full**:
  [`production-scenarios.md`](production-scenarios.md).

## What it's used for, and where the theory lives

This README stays hands-on and operational on purpose — commands and scripts you can run,
output you can check against what's shown here.
[`production-scenarios.md`](production-scenarios.md) is the deeper hands-on layer above
this one — real cluster failure modes, not just steady-state usage. The delivery-guarantee
taxonomy (at-most-once/at-least-once/exactly-once, precisely), the ordering/partition-key
trade-off, consumer-group rebalancing protocols in depth, backpressure, and dead-letter-queue
design as a pattern (not just this one script) are covered at interview depth in:

- [`18_message_queues_and_event_driven_semantics.md`](../../../../fundamentals/system_design_foundation/00_prerequisite_concepts/18_message_queues_and_event_driven_semantics.md) —
  message queues and event-driven semantics in general, with Kafka as the running example
  throughout.
- [`system_design_practice/06_design_distributed_message_queue/tutorial.md`](../../../../fundamentals/system_design_practice/06_design_distributed_message_queue/tutorial.md) —
  designing a Kafka-like system from scratch, the way an interview loop would actually
  probe it.
- [`../zookeeper/README.md`](../zookeeper/README.md) — the coordination layer Kafka used
  before KRaft, and why modern Kafka doesn't need it anymore.
- [`../kafka-vs-rabbitmq.md`](../kafka-vs-rabbitmq.md) — direct mechanism contrast with
  [`../rabbitmq/`](../rabbitmq/README.md) and a "which to use where" decision framework.

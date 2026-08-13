# Kafka vs. RabbitMQ: A Mechanism-Level Contrast, and Which to Use Where

Both labs in this `tools/` directory — [`kafka/`](kafka/README.md) and
[`rabbitmq/`](rabbitmq/README.md) — were built and verified against real multi-node
clusters specifically so this comparison could be grounded in actually-observed behavior,
not the generic "Kafka is for streams, RabbitMQ is for queues" framing that's true as far
as it goes but doesn't explain *why*, or what breaks if you pick wrong. Every claim below
cites the specific verified example or scenario it's grounded in.

## The one structural difference everything else follows from

**Kafka is a distributed, partitioned, append-only log. RabbitMQ is a broker that routes
messages through exchanges into queues, where consumption is destructive.** This single
difference is the actual root of almost every other contrast below — not "Kafka is faster"
or "RabbitMQ has more features," a genuine architectural fork:

- In Kafka, reading a partition never mutates it — a consumer just advances its own offset
  bookmark. This is *why* [`kafka/examples/consumer_group_rebalancing.py`](kafka/examples/consumer_group_rebalancing.py)
  can show two independent consumer groups each reading **every** message, completely
  unaffected by each other, with zero coordination required — the data just sits there,
  replayable, until retention expires (`kafka/README.md`'s verified
  `retention.ms=604800000`, 7 days, regardless of whether anyone ever read it).
- In RabbitMQ, once a consumer acks a message, the broker's job is done — the message is
  gone. [`rabbitmq/examples/basic_pubsub.py`](rabbitmq/examples/basic_pubsub.py) achieves
  "multiple services get their own copy" not through Kafka's replay-from-any-offset
  mechanism, but through an *exchange topology decision made in advance* (bind multiple
  queues to one fanout exchange) — a new queue bound *after* a message was published simply
  never sees it. There is no "replay from an hour ago" primitive in RabbitMQ the way there
  is in Kafka; a queue is a live worklist, not a history.

## Routing: partition-key hashing vs. genuine content-based routing

Kafka has exactly one routing lever — the partition key, hashed to pick a shard
(`kafka/examples/keyed_ordering.py`, verified: `murmur2(key) % partition_count`). That's a
**sharding** decision (which copy of the consumer group handles this), not a **destination**
decision — every partition is read by the same logical consumer group, just split among its
members.

RabbitMQ has four real exchange types, and topic exchanges specifically do pattern-based
*destination* routing — `orders.us.*` and `orders.#` and `*.*.priority` can all be live,
independent bindings on the *same* published message, sending it to entirely different sets
of queues based on content (`rabbitmq/examples/topic_exchange_routing.py`, verified: one
publish to `orders.us.priority` landed in `all-orders`, `us-orders-only`, AND
`high-priority-only` simultaneously — three genuinely different downstream destinations
from one publish call). Kafka has no equivalent to this; achieving the same effect requires
either separate topics per concern or consumer-side filtering after the fact.

## Ordering guarantees

Kafka: ordering is guaranteed **only within a partition**, never topic-wide — verified
directly by increasing a topic's partition count and watching existing keys silently
scatter onto new partitions
([`kafka/production-scenarios.md`](kafka/production-scenarios.md)'s partition-increase
scenario).

RabbitMQ: a **single consumer** on a classic queue receives messages in the order they were
enqueued (real FIFO) — but the instant *multiple competing consumers* share one queue
(RabbitMQ's own standard scaling pattern —
[`rabbitmq/examples/work_queue_ack_prefetch.py`](rabbitmq/examples/work_queue_ack_prefetch.py)),
there is no ordering guarantee across them at all, by design; whichever consumer happens to
be dispatched a given message processes it whenever it gets to it. **Neither system gives
you "global order across many parallel workers" for free** — Kafka trades that for
partition-scoped order plus real parallelism; RabbitMQ trades it away entirely the moment
you scale consumers, for maximum work-distribution flexibility instead.

## Durability and failure behavior — the two flagship scenarios, side by side

| | Kafka | RabbitMQ |
|---|---|---|
| Replication unit | Partition (all partitions of a replicated topic) | Per-queue, opt-in (`x-queue-type: quorum`) |
| Default replication | None (`--replication-factor 1` unless set) | None (classic queue, single node) |
| What a node failure does to unreplicated data | That partition's leader moves if replicated; **data loss** if that was the only replica | Queue becomes a clean 404, **fully inaccessible** until the node returns (verified: `NOT_FOUND - queue 'orders' ... process is stopped by supervisor`) |
| What a node failure does to replicated data | New leader elected from the surviving ISR, verified sub-second; producers/consumers using the full `bootstrap.servers` list keep working transparently | Quorum queue elects a new Raft leader on a surviving node, verified: reads/writes kept working through the outage on a different node's connection |
| Does the recovered node reclaim its old role automatically? | **No** — verified: leadership stays on the failover broker until `kafka-leader-election.sh --election-type preferred` is run manually | **No** — verified: quorum queue leadership stays on the failover node after the original rejoins as a follower |

The "recovered node doesn't reclaim its role automatically" gotcha is real and identical in
*shape* across both systems, worth internalizing as a general distributed-systems fact, not
a quirk of either tool specifically: **automatic failover and automatic failback are two
different features, and most systems only give you the first one.**

One durability fact that's RabbitMQ-specific and easy to miss: a **durable queue does not
imply durable messages** — verified directly, a message published without
`delivery_mode=2` to an otherwise-durable queue was silently gone after a broker restart,
while a `delivery_mode=2` message on the same queue survived
([`rabbitmq/production-scenarios.md`](rabbitmq/production-scenarios.md)). Kafka has no
equivalent footgun here — every write to a replicated topic is durable by the same
mechanism, there's no separate per-message "actually mean it" flag to forget.

## Delivery guarantees, compared mechanism-to-mechanism

| Guarantee | Kafka | RabbitMQ |
|---|---|---|
| "Did my write actually land" | `acks="all"` + delivery callback (verified against `min.insync.replicas=2`) | Publisher confirms (`confirm_delivery()`) + `mandatory=True` (verified: unroutable publish raises `UnroutableError` immediately) |
| Avoiding duplicate writes on retry | `enable.idempotence=True`, broker-side sequence-number dedup | No built-in producer-side idempotence primitive — dedup, if needed, is application logic (e.g. an idempotency key checked before processing) |
| Atomic multi-message writes | Transactions (`begin_transaction`/`commit_transaction`), consumer-side `isolation.level=read_committed` filters aborted writes (verified: `read_uncommitted` sees an aborted message's bytes, `read_committed` doesn't) | No direct equivalent — RabbitMQ has AMQP transactions but they're a known performance anti-pattern; publisher confirms are the practical substitute for "did this land," not "did this group of messages land atomically" |
| Poison-message handling | Fully manual — catch, republish to a separate DLQ topic, commit past it (`kafka/examples/dead_letter_queue.py`) | Broker-native for two paths: TTL expiry and `basic_nack(requeue=False)` both auto-route to a configured dead-letter exchange with a real `x-death` header recording why (`rabbitmq/examples/dead_letter_exchange.py`) — less code, but the mechanism (partition/queue can't skip a stuck message) is the same underlying problem either way |

## Fair work distribution among competing consumers

Both systems need an explicit setting to get real, speed-proportional fairness, and both
default to something less than that:

- Kafka: partitions are divided among a consumer group's members at the *partition*
  granularity — a slow consumer holding one partition doesn't affect a fast consumer's
  different partition, but it does mean per-partition throughput is capped by whichever
  consumer happens to own it (no fine-grained rebalancing below one full partition).
- RabbitMQ: `prefetch_count` is required for real fairness at the *message* granularity —
  verified directly: unlimited prefetch let one consumer register first and hoard 100% of
  a 20-message backlog while a faster consumer sat completely idle, an arbitrary and
  non-speed-proportional outcome; `prefetch_count=1` fixed it (19/1 split, matching the
  actual speed difference). RabbitMQ's finer dispatch granularity (per-message, not
  per-partition) is a real advantage for uneven workloads, *conditional on* prefetch being
  tuned — the unlimited default actively works against you.

## Which to use where

**Reach for Kafka when:**
- Multiple independent systems need to read the *same* event stream, at their own pace,
  including systems that don't exist yet (a new analytics pipeline added next year should
  be able to read history from day one — this is a real, structural capability, not a
  configuration choice).
- Replay is a real requirement — reprocessing the last 7 days of events after fixing a bug
  in a consumer, rebuilding a materialized view from scratch, backfilling a new service.
- Throughput at genuinely large scale, with ordering that only needs to hold *within* a
  well-chosen key (per-user, per-order, per-device), matters more than complex routing.
- The data has lasting value as a system of record, not just as work to be done and
  discarded — event sourcing, CDC (change-data-capture) pipelines, audit logs, stream
  processing (joins/aggregations over a continuous stream).

**Reach for RabbitMQ when:**
- The core need is genuinely a **task queue** — work items that should be picked up,
  processed once, and discarded, with fair distribution across a worker pool
  (`prefetch_count`-tuned).
- Routing logic is inherently content-based and needs to be more expressive than "which
  shard" — a topic exchange's `*`/`#` patterns, or fanout to a dynamically changing set of
  downstream services, without needing separate Kafka topics per routing concern.
- Per-message features matter operationally: TTL, priority queues, delayed messages
  (via TTL+DLX), broker-native dead-lettering with less hand-rolled consumer logic.
- Request/reply (RPC-style) messaging is a real pattern in the system — RabbitMQ supports
  this naturally (a reply-to queue + correlation ID); Kafka's log model makes this an
  awkward fit (technically possible, rarely how it's actually used).
- Lower absolute message volume where RabbitMQ's per-message routing flexibility is worth
  more than Kafka's raw sustained-throughput ceiling.

**Both can superficially do "pub/sub"** — that surface similarity is exactly what makes
picking wrong easy. The actual decision variable is almost never throughput; it's whether
the workload's natural shape is **"a stream of history multiple things read
independently"** (Kafka) or **"a worklist of things that get done once and go away"**
(RabbitMQ) — and that's a property of the problem, not a preference.

## Where the deeper theory lives

- [`fundamentals/system_design_foundation/00_prerequisite_concepts/18_message_queues_and_event_driven_semantics.md`](../../../fundamentals/system_design_foundation/00_prerequisite_concepts/18_message_queues_and_event_driven_semantics.md) —
  message queues and event-driven semantics in general, delivery guarantee taxonomy, and
  backpressure, with Kafka as the running example.
- [`fundamentals/system_design_practice/06_design_distributed_message_queue/tutorial.md`](../../../fundamentals/system_design_practice/06_design_distributed_message_queue/tutorial.md) —
  designing a message-queue system from scratch, the way an interview loop would probe the
  trade-offs named above.

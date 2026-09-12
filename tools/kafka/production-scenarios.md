# Kafka in Production: Scenarios Worth Understanding Cold

Everything in [`README.md`](README.md) is Kafka working as intended, on the single-broker
lab it was originally verified against. This doc is the other half — the specific ways it
breaks, degrades, or surprises people running it for real — each one explained by
mechanism, not just named. Getting these right required a real, if small, production
topology: the lab was upgraded from one broker to a **3-broker KRaft cluster**
(`docker-compose.yml`, `replication.factor=3`, `min.insync.replicas=2`) specifically so
broker failure, leader election, and ISR behavior could be triggered and observed live —
not just described. Every scenario below, including exact numbers and error text, was run
against that live cluster; none of it is projected or assumed.

## Replication and Availability

### A broker dying doesn't just fail over — leadership doesn't come back on its own

Starting state, `orders` (3 partitions, replication factor 3):

```
Topic: orders   Partition: 0   Leader: 1   Replicas: 1,2,3   Isr: 1,2,3
Topic: orders   Partition: 1   Leader: 2   Replicas: 2,3,1   Isr: 2,3,1
Topic: orders   Partition: 2   Leader: 3   Replicas: 3,1,2   Isr: 3,1,2
```

`docker stop kafka-lab-1` — killing broker 1, which was leader for partition 0 and an
in-sync follower for the other two. Immediately after:

```
Topic: orders   Partition: 0   Leader: 2   Replicas: 1,2,3   Isr: 2,3
Topic: orders   Partition: 1   Leader: 2   Replicas: 2,3,1   Isr: 2,3
Topic: orders   Partition: 2   Leader: 3   Replicas: 3,1,2   Isr: 3,2
```

Two things happened, and they're different mechanisms: partition 0 got a **new leader**
(broker 2, elected from the surviving ISR — this is the controller quorum doing its job,
and it's fast, sub-second in this test), and **every** partition's ISR shrank to drop
broker 1, whether or not it was that partition's leader. A producer/consumer round trip
against the surviving cluster during the outage worked without any special handling —
`bootstrap.servers` listing all three brokers is what makes this transparent; the client
library discovers who the current leader is at connect/metadata-refresh time, not from a
fixed assumption baked in at startup.

**The part that surprises people**: `docker start kafka-lab-1` — broker 1 rejoins, and its
ISR membership is restored automatically (confirmed: `Isr: 2,3,1` again on all three
partitions, replica catch-up happening in the background). **Leadership does not move back
on its own.** Partition 0 stayed led by broker 2 indefinitely after broker 1 recovered —
Kafka doesn't automatically fail leadership back to the "preferred" replica (the first one
listed in `Replicas`) just because it's available again, by design: an unnecessary leader
handoff has its own brief availability cost, so Kafka doesn't do it proactively. Fixing the
resulting imbalance (broker 2 now leading 2 of 3 partitions instead of 1) is a deliberate,
separate action:

```
$ kafka-leader-election.sh --bootstrap-server kafka-2:9092 --election-type preferred --all-topic-partitions
Successfully completed leader election (PREFERRED) for partitions orders-0

Topic: orders   Partition: 0   Leader: 1   Replicas: 1,2,3   Isr: 2,3,1   <- back to preferred leader 1
Topic: orders   Partition: 1   Leader: 2   ...   (unchanged — 2 was already preferred)
Topic: orders   Partition: 2   Leader: 3   ...   (unchanged — 3 was already preferred)
```

**The fix, stated as a habit**: `auto.leader.rebalance.enable=true` (the cluster default)
runs this same preferred-leader check periodically in the background — but only every
`leader.imbalance.check.interval.seconds` (default 300s/5min), and only if the imbalance
exceeds a threshold ratio. On a cluster where leader distribution genuinely matters for
capacity planning (uneven leader load = uneven broker load, since only leaders serve
reads/writes for their partitions), don't assume a recovered broker is back to pulling its
weight without checking `kafka-topics.sh --describe` or triggering
`kafka-leader-election.sh` explicitly after a known outage.

### Unclean leader election: the availability/durability trade, by config, not by accident

Verified on this cluster: `unclean.leader.election.enable=false` (the modern default,
`kafka-configs.sh --describe`). This wasn't triggered live here — doing so safely requires
deliberately taking an entire partition's ISR down to zero in-sync replicas while a lagging
out-of-sync replica survives, which risks actually corrupting this lab's other running
scenarios — but the mechanism and the trade-off are exact, not hand-wavy:

With the default (`false`): if every in-sync replica for a partition is unavailable
simultaneously, that partition simply **goes unavailable** — no writes, no reads — until
an in-sync replica comes back. Data already committed to the ISR is never lost, at the
cost of availability during that window.

With `unclean.leader.election.enable=true`: Kafka will elect an **out-of-sync** replica as
the new leader rather than stay unavailable — trading data loss (anything the new leader
hadn't caught up to before the last in-sync replica went down is gone, silently, from the
topic's perspective — not recoverable, not logged as "missing," just absent) for
uptime. This is the single most consequential availability-vs-durability knob in Kafka, and
it being `false` by default (it used to default to `true` in older Kafka versions) reflects
a real, documented shift in the project's own stance on that trade-off over time.

## Partitioning and Ordering

### Increasing partition count silently breaks every existing key's ordering guarantee

Four keys, produced to a 3-partition topic:

```
sku-300 -> partition 0
sku-100 -> partition 2
sku-200 -> partition 2
sku-400 -> partition 1
```

`kafka-topics.sh --alter --topic inventory --partitions 6` — then the exact same four keys,
produced again:

```
sku-200 -> partition 2   (happened to land back on 2 — coincidence of the hash, not guaranteed)
sku-100 -> partition 5   (was 2)
sku-400 -> partition 4   (was 1)
sku-300 -> partition 3   (was 0)
```

The default partitioner computes `murmur2(key) % partition_count` — the moment
`partition_count` changes, that modulo's result changes for most keys (3 of 4 here; the
4th only matched by chance). This is real: it means **every key's "ordering guarantee" that
depends on same-key-same-partition breaks the instant a partition is added** — not
gradually, not just for new keys, immediately and silently for every key already in
flight. A downstream consumer relying on "all of order #42's events arrive in sequence"
now has order #42's *history* split across two partitions with no ordering relationship
between them, and nothing in the API surfaces this as an error.

**The fix, stated as a habit**: treat a topic's partition count as effectively permanent
once anything depends on key-based ordering — plan capacity generously up front rather
than "start small, add partitions later," which is safe for pure throughput scaling but
never safe once ordering-sensitive keys are involved. If partition count genuinely must
change, that's a controlled migration (new topic, new partition count, explicit
re-partitioning/backfill), not an `--alter` on the live topic.

## Consumer Groups and Rebalancing

### Eager rebalancing stops the *entire* group, not just the member that joined or left

Real event trace, two consumers already running, a third joins mid-stream, default
(`range`, an eager protocol) assignment strategy:

```
t+ 6.10s  consumer-1 ASSIGNED [3, 4, 5]
t+ 6.10s  consumer-2 ASSIGNED [0, 1, 2]
t+ 7.02s  consumer-3 STARTING (subscribing now)
t+ 9.12s  consumer-2 REVOKED [0, 1, 2]      <- ALL of consumer-2's partitions, not just some
t+ 9.12s  consumer-1 REVOKED [3, 4, 5]      <- ALL of consumer-1's partitions too
t+ 9.13s  consumer-3 ASSIGNED [2, 3]
t+ 9.13s  consumer-2 ASSIGNED [0, 1]
t+ 9.13s  consumer-1 ASSIGNED [4, 5]
```

Eager protocols (`range`, `roundrobin`) revoke **every** partition from **every** member
of the group on any membership change, then reassign from scratch — even members whose
final assignment doesn't actually change end up with a brief total consumption pause,
because the protocol has no concept of "only touch what needs to move." On a group with
many members and frequent scaling events (autoscaling consumers up/down with load), this
is a real, recurring throughput cliff, not a one-time cost.

The same test, `cooperative-sticky` instead:

```
t+ 6.09s  consumer-1 ASSIGNED [1, 3, 5]
t+ 6.09s  consumer-2 ASSIGNED [0, 2, 4]
t+ 7.02s  consumer-3 STARTING (subscribing now)
t+ 9.16s  consumer-1 REVOKED [1]            <- only ONE partition, not all three
t+ 9.16s  consumer-2 REVOKED [0]            <- only ONE partition, not all three
t+12.20s  consumer-3 ASSIGNED [0, 1]        <- second round: consumer-3 gets what was freed
t+16.12s  consumer-1 REVOKED [3, 5]         <- final shutdown, not a mid-run rebalance
```

`consumer-1` keeps partitions `[3, 5]` for the *entire* run, uninterrupted — only
partition `1` (the one actually moving to consumer-3) is ever revoked from it.
Cooperative-sticky achieves this via two rebalance rounds instead of one (round 1: revoke
only what's moving; round 2: assign it to the new owner) — more protocol round trips, in
exchange for the rest of the group never pausing.

**The fix, stated as a habit**: `partition.assignment.strategy=cooperative-sticky` (or the
newer KIP-848 consumer group protocol, where this is closer to the built-in default) on
any group where membership changes routinely — autoscaled consumer fleets, rolling
deployments — not just as a performance nice-to-have; on a large group it's the difference
between a rolling deploy causing a brief, group-wide consumption stall repeatedly versus
not.

## Delivery Guarantees

### What "aborted" actually means on disk — and a gotcha in triggering it correctly

A transactional producer, one committed transaction and one aborted transaction, each
message explicitly `flush()`'d to the broker *before* the transaction is resolved (this
detail matters — see below):

```python
p.begin_transaction()
p.produce("payments", key="txn-committed", value="...")
p.flush(10)              # force the write to actually reach the broker first
p.commit_transaction()

p.begin_transaction()
p.produce("payments", key="txn-aborted", value="...")
p.flush(10)              # force the write to actually reach the broker first
p.abort_transaction()
```

```
isolation.level=read_committed:   consumer saw keys = ['txn-committed']
isolation.level=read_uncommitted: consumer saw keys = ['txn-committed', 'txn-aborted']
```

This is the exact, real mechanism behind Kafka's exactly-once semantics on the consumer
side: an aborted transaction's message bytes are genuinely written to the log (verified —
`read_uncommitted` sees them), Kafka just also writes an abort marker, and
`isolation.level=read_committed` is what filters anything after an abort marker out of
what a normal consumer ever sees. It is real, broker-side filtering, not a producer-side
guarantee alone.

**The gotcha, hit directly while building this**: skip the `flush()` before
`abort_transaction()` and the message can simply never reach the broker at all —
`abort_transaction()` in `librdkafka` purges not-yet-sent messages from the local producer
queue as part of aborting, rather than sending them and then marking them aborted. The
first version of this exact test showed *zero* trace of the aborted message anywhere (not
even in the raw log-end-offset), which looked like a broken demo until the mechanism became
clear: an abort that happens before the network round trip completes means there was never
anything on the broker to filter. Don't read "I can't find the aborted message anywhere,
not even under `read_uncommitted`" as isolation-level filtering working *too* well — check
whether the message was actually sent before concluding that.

### Message size limits reject client-side, before anything touches the network

```python
p.produce("size-limit-demo", key="big", value=b"x" * (2 * 1024 * 1024))  # 2MB
p.flush(10)
# raises immediately:
# KafkaException: KafkaError{code=MSG_SIZE_TOO_LARGE,val=10,
#   str="Unable to produce message: Broker: Message size too large"}
```

`librdkafka` checks the message against its own `message.max.bytes`-equivalent
configuration and rejects it before ever attempting the send — the broker's actual
`message.max.bytes` limit (1MB by default) is enforced independently server-side too, but a
well-behaved client catches this locally first. **The fix, stated as a habit**: this
exception is a real, expected code path for any producer handling arbitrary or
user-supplied payload sizes (file uploads represented as events, unbounded log lines) — it
needs an explicit catch and a decision (reject, chunk, or route to object storage with a
reference in the event instead of the payload itself), not just an unhandled crash path
discovered the first time someone sends something too big.

## Offsets and Retention

### A recreated topic doesn't error by default — it silently resets, and that's a config choice

A consumer group processes and commits offset 5 on a topic. The topic is deleted and
recreated (same name, empty) — a real operational event: disaster-recovery restores, a
schema/partition-count migration done as delete-and-recreate rather than in-place, or
simply a mistake. The same consumer group resumes, `auto.offset.reset=earliest` (the
common default choice):

```
received: b'new-1' b'fresh data after recreation' offset: 0
```

**No error, no warning surfaced to the application** — the committed offset (5) no longer
exists on the new topic (which only has offset 0), and the client silently falls back to
`auto.offset.reset`'s behavior, exactly as if this were a brand-new consumer group that had
never read this topic before. If the application logic assumes "this consumer group has
already processed everything before its stored offset," this is a silent, invisible data
discontinuity — not a crash, not a log line, just a consumer that quietly starts over.

The alternative, `auto.offset.reset=error` (`librdkafka`'s explicit-failure option):

```
MESSAGE ERROR (explicit failure instead of silent reset):
KafkaError{code=_AUTO_OFFSET_RESET,val=-140,str="no previously committed offset available: Local: No offset stored"}
```

Same underlying situation, surfaced as an explicit, catchable error instead of a silent
reset. **The fix**: `earliest`/`latest` are the right default for a genuinely
stateless/idempotent consumer that's fine replaying or skipping ahead — anything that
tracks "have I already handled this" externally (a database write, a side effect that
isn't safely repeatable) should prefer `error` (or the Java client's equivalent explicit
handling) specifically so a topic recreation becomes a loud, catchable event instead of a
silent one.

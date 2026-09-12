# RabbitMQ in Production: Scenarios Worth Understanding Cold

Everything in [`README.md`](README.md) is RabbitMQ working as intended, on a healthy
3-node cluster. This doc is the other half — the specific ways it breaks, degrades, or
surprises people running it for real — each one explained by mechanism, not just named.
Every scenario below was run against the same live 3-node cluster this lab's README
verifies against; none of it is projected or assumed.

## Clustering and Availability

### Classic queues live on ONE node; quorum queues don't — and this is invisible until a node dies

A classic queue and a quorum queue, declared identically except for `x-queue-type`:

```
$ rabbitmqctl list_queues name type leader members
orders             classic   rabbit@rabbit1   [rabbit@rabbit1]
critical-orders    quorum    rabbit@rabbit1   [rabbit@rabbit1, rabbit@rabbit3, rabbit@rabbit2]
```

**Every classic queue in this cluster lives on exactly one node** — `rabbit1`, because
that's the node that happened to declare it — with no replication at all by default. The
quorum queue is automatically replicated to all three nodes, using RabbitMQ's own
Raft-based consensus (the same category of mechanism as Kafka's KRaft, applied here to an
individual queue's replicated log rather than cluster metadata).

`docker stop rabbitmq-lab-1` — killing the node every classic queue above lives on:

```
$ rabbitmqctl list_queues name type leader members    # run from rabbit2
orders             rabbit_classic_queue                    <- leader/members BLANK — gone
critical-orders    quorum    rabbit@rabbit3   [rabbit@rabbit1, rabbit@rabbit3, rabbit@rabbit2]
```

Trying to actually use the now-orphaned classic queue, from a different node in the
cluster:

```python
ch.basic_get(queue="orders", auto_ack=True)
# pika.exceptions.ChannelClosedByBroker: (404, "NOT_FOUND - queue 'orders' in vhost '/'
#   process is stopped by supervisor")
```

**A completely clean 404 — not "degraded," not "read-only," gone.** The quorum queue,
meanwhile, kept serving reads and writes from the surviving nodes without any special
client-side handling:

```python
ch.basic_get(queue="critical-orders", auto_ack=True)
# b'order-0'   <- works fine, mid-outage, against a different node's connection
```

**The fix, stated as a habit**: `x-queue-type: quorum` for anything where losing a single
node's worth of data or availability is a real incident, not an inconvenience — this is
not a performance-tuning knob, it's the actual durability/availability guarantee, and
classic queues (with no mirroring configured — RabbitMQ's older classic-mirrored-queue
feature is explicitly deprecated in favor of quorum queues) default to *none*. A cluster
"looking" highly available (3 nodes, no errors under normal operation) says nothing about
whether any individual queue actually benefits from that — that's a per-queue choice, not
a cluster-wide property.

### A recovered node doesn't reclaim leadership either — same shape as Kafka's failback gotcha

`docker start rabbitmq-lab-1` — the dead node rejoins:

```
[info] queue 'critical-orders' in vhost '/': follower did not have entry at 16 in 2.
       Requesting {'%2F_critical-orders',rabbit@rabbit3} from 15
[info] queue 'critical-orders' in vhost '/': detected a new leader
       {'%2F_critical-orders',rabbit@rabbit3} in term 2
```

Rabbit1's replica catches up (visible directly in the logs — it's replaying missed Raft
log entries from the new leader), and rejoins as a follower. **Leadership stays on
rabbit3.** This is the same shape of surprise as Kafka's broker-failure scenario (see
[`../kafka/production-scenarios.md`](../kafka/production-scenarios.md)) — recovery restores
redundancy, not the original topology, and nothing rebalances leadership back
automatically. If leader distribution across nodes matters for load reasons, that's a
separate, explicit check after any node recovery, not something to assume happened.

## Durability

### A durable queue does not make its messages durable — that's a second, separate setting

Two messages published to the *same durable queue*, one marked persistent, one not:

```python
ch.queue_declare(queue="durable-but-transient-msg", durable=True)
ch.basic_publish(..., body=b"not marked persistent")                                    # delivery_mode default = 1 (transient)
ch.basic_publish(..., body=b"marked persistent", properties=pika.BasicProperties(delivery_mode=2))
```

`docker restart rabbitmq-lab-1` — a full node restart, then read back:

```
durable-but-transient-msg: [b'marked persistent']
```

**Only the explicitly-`delivery_mode=2` message survived.** The queue being `durable=True`
only guarantees the *queue itself* (its existence, its bindings) survives a restart — each
individual message additionally needs `delivery_mode=2` to be written to disk rather than
kept in memory only. This is a genuinely easy mistake: a queue declared durable *looks*
like the durability box is checked, and most client libraries default `delivery_mode` to
1 (transient) unless told otherwise.

A non-durable queue is more dramatic — restart the same node again with a
`durable=False` queue in place:

```python
ch.queue_declare(queue="non-durable-queue", durable=False)
ch.basic_publish(..., body=b"in a non-durable queue")
# ... node restarts ...
ch.basic_get(queue="non-durable-queue", auto_ack=True)
# pika.exceptions.ChannelClosedByBroker: (404, "NOT_FOUND - no queue 'non-durable-queue' in vhost '/'")
```

**The entire queue is gone**, not just emptied — a non-durable queue doesn't survive a
broker restart even as an empty shell. **The fix, stated as a habit**: for anything where
message loss on a restart/crash is unacceptable, both `durable=True` on the queue *and*
`delivery_mode=2` on every message are required — neither one alone is sufficient, and
there's no warning or error when only one is set.

## Flow Control

### A memory (or disk) alarm blocks publishers silently — it doesn't reject the write, it just hangs

Verified default: `vm_memory_high_watermark` defaults to `0.4` (40% of available RAM)
across the cluster. Deliberately set far lower to trigger the alarm cheaply and observe the
actual mechanism, not just its existence:

```
$ rabbitmqctl set_vm_memory_high_watermark 0.00000001
$ rabbitmqctl status | grep -A3 Alarms
Alarms
Memory alarm on node rabbit@rabbit1
```

A publisher, with a `blocked_connection_timeout` configured, attempting to publish while
the alarm is active:

```
pika.exceptions.ConnectionBlockedTimeout: Blocked connection timeout expired.
```

**The publish call doesn't error immediately and it doesn't get rejected** — the broker
sends an AMQP `connection.blocked` signal and the client-side call simply **hangs**,
waiting for the alarm to clear, until (if configured) a client-side timeout gives up. A
publisher with no `blocked_connection_timeout` set (the pika default) hangs *indefinitely*
— every application-level retry/circuit-breaker logic built around "the publish call either
succeeds or raises quickly" silently stops working the moment a memory or disk alarm is
active cluster-wide, because the call just... doesn't return. **Consumers are unaffected**
— this is specifically a publisher-side block, since the whole point is stopping *new* data
from making the memory situation worse while existing data still drains.

**The fix, stated as a habit**: always set an explicit `blocked_connection_timeout` on
production publishers specifically so a memory/disk alarm becomes a loud, catchable
failure instead of an application that looks "stuck" with no exception, no log line, and
a healthy-looking TCP connection. Alerting on the alarm itself
(`rabbitmq_alarms_memory_used_watermark` or the equivalent Prometheus metric) is the actual
fix for the underlying condition — the client-side timeout only bounds how long the
application waits before failing loudly.

## Consumer Fairness

### Unlimited prefetch means dispatch fairness is arbitrary, not speed-proportional

Covered in full, with real numbers from both the unlimited-prefetch and
`prefetch_count=1` trials, in [`README.md`](README.md#manual-acknowledgment-and-prefetch--a-real-fairness-gotcha-not-just-a-knob) —
included here as a pointer since it's as much a production incident pattern as anything
else in this doc: a consumer fleet scaled up "for more throughput" that doesn't actually
get more throughput, because prefetch was left at the default and one consumer instance is
silently hoarding the backlog.

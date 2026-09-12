# RabbitMQ

**Category:** message broker (AMQP 0-9-1 — exchange/queue/binding routing model)

## What it is

RabbitMQ is a **broker**, not a log — the opposite structural choice from
[Kafka](../kafka/README.md). A message is published to an **exchange**, the exchange
routes it to zero or more **queues** based on **bindings** (routing rules), and once a
consumer acknowledges a message, the broker considers it handled and typically discards it
— there's no "rewind and replay from an hour ago" the way there is with a Kafka log, because
consumption is destructive by default. What RabbitMQ trades for that is a genuinely richer
**routing** layer: four exchange types (direct, fanout, topic, headers) that decide *where*
a message goes based on content, not just which partition-shard it lands in, plus
per-message TTL, priority, and broker-managed dead-lettering as first-class features rather
than patterns you build yourself on top.

Everything below was built and verified against a real **3-node RabbitMQ 4.0 cluster**
running in Docker on this machine — every command, every script, every queue failover
actually ran. See [`../kafka-vs-rabbitmq.md`](../kafka-vs-rabbitmq.md) for a direct,
mechanism-level contrast with the Kafka lab in this same `tools/` directory, and which
problem shape actually fits which tool.

## Running it

```bash
cd mlops_aiops/docs/tools/rabbitmq
docker compose up -d
```

Three containers — `rabbitmq-lab-1/2/3` — start independently and then need to be
explicitly clustered (RabbitMQ doesn't auto-form a cluster from `docker compose` alone the
way this lab's Kafka setup does with KRaft's quorum-voters config):

```bash
docker exec rabbitmq-lab-2 rabbitmqctl stop_app
docker exec rabbitmq-lab-2 rabbitmqctl join_cluster rabbit@rabbit1
docker exec rabbitmq-lab-2 rabbitmqctl start_app

docker exec rabbitmq-lab-3 rabbitmqctl stop_app
docker exec rabbitmq-lab-3 rabbitmqctl join_cluster rabbit@rabbit1
docker exec rabbitmq-lab-3 rabbitmqctl start_app

docker exec rabbitmq-lab-1 rabbitmqctl cluster_status
```

Real output, trimmed to the parts that matter:

```
Disk Nodes
rabbit@rabbit1
rabbit@rabbit2
rabbit@rabbit3

Running Nodes
rabbit@rabbit1
rabbit@rabbit2
rabbit@rabbit3

Network Partitions
(none)
```

Then create a real application user (the default `guest` user is restricted to
loopback-only connections — it won't work for a client connecting to the Docker-mapped
host ports, which arrive as non-loopback as far as the broker is concerned):

```bash
docker exec rabbitmq-lab-1 rabbitmqctl add_user labuser labpass
docker exec rabbitmq-lab-1 rabbitmqctl set_user_tags labuser administrator
docker exec rabbitmq-lab-1 rabbitmqctl set_permissions -p / labuser ".*" ".*" ".*"
```

Ports: AMQP on `5672`/`5673`/`5674` (nodes 1/2/3), management UI + HTTP API on
`15672`/`15673`/`15674` — `http://localhost:15672`, login `labuser`/`labpass`.

## Exchanges: where routing actually happens, hands-on

```bash
$ docker exec rabbitmq-lab-1 rabbitmqctl list_exchanges name type
name                   type
amq.fanout             fanout
amq.topic              topic
amq.direct             direct
amq.headers            headers
                       direct    <- the DEFAULT exchange: unnamed, always present
```

That last row — empty name, type `direct` — is the **default exchange** every queue is
implicitly bound to, with a routing key equal to the queue's own name. This is why
`basic_publish(exchange="", routing_key="my-queue")` (the simplest possible publish call)
works without ever declaring an exchange yourself: it's using this implicit binding, not
skipping the exchange layer entirely — there is no such thing as publishing to "no
exchange" in AMQP, only to this specific always-present one.

### Fanout: broadcast, no routing key needed

```python
ch.exchange_declare(exchange="notifications", exchange_type="fanout", durable=True)
ch.queue_declare(queue="email-service", durable=True)
ch.queue_declare(queue="sms-service", durable=True)
ch.queue_bind(exchange="notifications", queue="email-service")
ch.queue_bind(exchange="notifications", queue="sms-service")

ch.basic_publish(exchange="notifications", routing_key="", body=b"user signed up")
```

Real output — one publish, both queues get their own independent copy:

```
email-service received: b'user signed up'
sms-service received: b'user signed up'
```

Fanout ignores the routing key entirely — every bound queue gets a copy. This is the
direct analog of Kafka's "different `group.id` = independent full copy" behavior, except
here it's the exchange topology (not consumer group membership) that decides fan-out, and
it's decided by *whoever sets up the bindings*, not by how many independent consumer groups
happen to subscribe.

### Topic: routing-key pattern matching

```python
ch.exchange_declare(exchange="orders-topic", exchange_type="topic", durable=True)
ch.queue_bind(exchange="orders-topic", queue="all-orders", routing_key="orders.#")
ch.queue_bind(exchange="orders-topic", queue="us-orders-only", routing_key="orders.us.*")
ch.queue_bind(exchange="orders-topic", queue="high-priority-only", routing_key="*.*.priority")
```

Three messages published with routing keys `orders.us.standard`, `orders.eu.standard`,
`orders.us.priority` — real output:

```
all-orders:          ['US standard order', 'EU standard order', 'US priority order']  <- '#' matches everything after 'orders.'
us-orders-only:       ['US standard order', 'US priority order']                       <- '*' matches exactly one segment
high-priority-only:   ['US priority order']                                            <- pattern matched regardless of country
```

`*` matches exactly one dot-separated segment; `#` matches zero or more segments. This is
genuinely more expressive per-message routing than Kafka has any equivalent for — Kafka's
only routing lever is the partition key (Chapter: [`keyed_ordering.py`](../kafka/examples/keyed_ordering.py)),
which picks a *shard*, not a *destination*; there's no Kafka mechanism where a single
publish fans out to different downstream consumers based on the *content* of a routing key
pattern the way this is.

### Direct and headers, briefly

**Direct**: exact routing-key match only (no wildcards) — the simplest case, effectively
what the default exchange itself uses. **Headers**: routes based on message header
key/value matching instead of the routing key string at all (`x-match: all` or `any`) —
rare in practice, useful when routing criteria are naturally structured data rather than a
dot-separated string.

## Publisher confirms and mandatory publishing

```python
ch.confirm_delivery()   # switches the channel into publisher-confirms mode
ch.basic_publish(exchange="", routing_key="confirmed-queue", body=b"...",
                  properties=pika.BasicProperties(delivery_mode=2), mandatory=True)
# succeeds silently if the broker actually persisted/routed it

ch.basic_publish(exchange="", routing_key="no-such-queue-exists", body=b"...", mandatory=True)
# raises immediately:
# pika.exceptions.UnroutableError: 1 unroutable message(s) returned
```

Two independent knobs, easy to conflate: `delivery_mode=2` marks the message itself
persistent (survive a broker restart, *if* the queue is also durable) — it says nothing
about whether the message was ever successfully routed anywhere. `mandatory=True` +
`confirm_delivery()` is what actually tells you routing failed — without `mandatory=True`,
an unroutable message is **silently dropped** by default, no error, no dead-letter, just
gone. This pairing (confirms + mandatory) is the real equivalent of Kafka's `acks="all"` +
delivery-callback pattern — "don't just fire and hope," get a real signal either way.

## Manual acknowledgment and prefetch — a real fairness gotcha, not just a knob

Two competing consumers on the same queue, one artificially slow (0.5s/message), one fast
(no delay), 20 messages, prefetch **unlimited** (`prefetch_count=0`, easy to leave at the
default):

```
prefetch=0 (unlimited) results: {'fast': 0, 'slow': 12}
```

**One consumer got (almost) everything; the other got (almost) nothing** — and re-running
this exact test shows *either* one can be the "winner": with no prefetch limit, RabbitMQ
dispatches a burst of messages to whichever consumer's channel registers as ready first,
entirely a function of connection/registration timing, with **no regard for how fast that
consumer will actually process them**. Whichever one wins that race gets a huge backlog of
unacked messages queued into its local buffer — unavailable to the other consumer until the
winner gets around to acking them, even if the winner turns out to be the slow one. That's
the real failure mode: not "the slow consumer always wins" (it doesn't, reliably), but
"dispatch fairness is not speed-proportional at all without an explicit prefetch limit,
and which consumer gets starved is arbitrary."

Same test, `prefetch_count=1`:

```
prefetch=1 results: {'fast': 19, 'slow': 1}
```

With `prefetch_count=1`, RabbitMQ never sends a consumer a second message until it acks the
first — true work-stealing, proportional to actual processing speed, is what "fair
dispatch" in RabbitMQ actually requires opting into, not what happens by default. See
[`production-scenarios.md`](production-scenarios.md) for this same mechanism as a full
production incident writeup.

## Dead-lettering and TTL — broker-managed, not application code

```python
ch.exchange_declare(exchange="dlx", exchange_type="fanout", durable=True)
ch.queue_bind(exchange="dlx", queue="dead-letters")

ch.queue_declare(queue="ttl-demo", durable=True, arguments={
    "x-message-ttl": 2000,               # 2 seconds
    "x-dead-letter-exchange": "dlx",
})
ch.basic_publish(exchange="", routing_key="ttl-demo", body=b"this will expire")
```

Real output, 3 seconds later:

```
dead-letters queue: b'this will expire'
x-death header: [{'count': 1, 'reason': 'expired', 'queue': 'ttl-demo',
                   'time': ..., 'exchange': '', 'routing-keys': ['ttl-demo']}]
```

The broker itself expires the message and republishes it to the configured dead-letter
exchange — with a real `x-death` header recording *why* (`expired`, vs. `rejected` for a
nacked message, vs. `maxlen` for a queue-length-limit eviction) and *where it came from*.
This is the same DLQ pattern
[`kafka/examples/dead_letter_queue.py`](../kafka/examples/dead_letter_queue.py) builds by
hand in consumer code — here it's a queue *argument*, the broker does the routing and
annotation itself, no consumer-side try/except required for the TTL case specifically
(a consumer explicitly `basic_nack`-ing a message it can't process still needs its own
try/except, same as Kafka — see [`examples/dead_letter_exchange.py`](examples/dead_letter_exchange.py)
for both paths side by side).

## Runnable examples

| Script | Pattern | Mechanism demonstrated |
|---|---|---|
| [`basic_pubsub.py`](examples/basic_pubsub.py) | Broadcast to independent services | Fanout exchange, multiple queues, one publish |
| [`work_queue_ack_prefetch.py`](examples/work_queue_ack_prefetch.py) | Fair task distribution among competing workers | Manual ack, `prefetch_count`, the starvation gotcha above |
| [`topic_exchange_routing.py`](examples/topic_exchange_routing.py) | Content-based routing to different consumers | Topic exchange, `*`/`#` routing-key wildcards |
| [`dead_letter_exchange.py`](examples/dead_letter_exchange.py) | Expired and rejected messages, both paths | `x-message-ttl` + DLX, and manual `basic_nack` to a DLQ |

```bash
pip install pika
export RABBITMQ_HOST=localhost RABBITMQ_PORT=5672 RABBITMQ_USER=labuser RABBITMQ_PASSWORD=labpass
python3 examples/basic_pubsub.py
```

## When it breaks: production scenarios

[`production-scenarios.md`](production-scenarios.md) covers node failure and quorum-queue
leader failover (verified live on this 3-node cluster), the prefetch-starvation scenario
above as a full incident writeup, memory/disk alarm flow control silently blocking
publishers, message loss with publisher confirms turned off, and the classic-mirrored vs.
quorum queue distinction (and why one of them is deprecated for a real reason).

## What it's used for, and where the theory lives

This README stays hands-on and operational on purpose. The delivery-guarantee taxonomy,
exchange-routing theory, and RabbitMQ vs. Kafka architectural trade-offs at interview depth
are covered in:

- [`../kafka-vs-rabbitmq.md`](../kafka-vs-rabbitmq.md) — direct mechanism contrast and a
  "which to use where" decision framework, grounded in both labs' real verified behavior.
- [`18_message_queues_and_event_driven_semantics.md`](../../../../fundamentals/system_design_foundation/00_prerequisite_concepts/18_message_queues_and_event_driven_semantics.md) —
  message queues and event-driven semantics in general.
- [`system_design_practice/06_design_distributed_message_queue/tutorial.md`](../../../../fundamentals/system_design_practice/06_design_distributed_message_queue/tutorial.md) —
  designing a message-queue system from scratch, the way an interview loop would probe it.

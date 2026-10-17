# 02 · RabbitMQ pub/sub (fanout exchange)

**One idea:** producers never send to a queue directly. They send to an **exchange**, and the exchange
decides which queues get a copy. A **fanout** exchange copies every message to every queue bound to it.

```
                         ┌─▶ [ email's queue ]   ──▶ email subscriber
publisher ──▶ (orders) ──┤
               fanout    └─▶ [ billing's queue ] ──▶ billing subscriber
```

## Run it

```bash
# terminals 1 and 2
uv run subscriber.py email
uv run subscriber.py billing

# terminal 3
uv run publisher.py 5
```

## What to look for

1. **Both subscribers print all 5 orders.** Compare with lesson 01, where each job went to only one worker.
   The difference is one queue shared by workers vs. one queue *per subscriber*.
2. **Messages are not kept for absent subscribers.** Stop `billing`, publish 5 more, start `billing` again:
   it never sees those 5. Its private queue was deleted when it stopped, and no queue means no copy.
   (Lesson 04 shows Kafka keeping messages for later readers.)
3. Web UI → **Exchanges** → `orders` → *Bindings* lists one queue per running subscriber.

## Exchange types

| Type | Routes a message to |
|---|---|
| `direct` | Queues whose binding key equals the routing key exactly (lesson 01 used the default direct exchange) |
| `fanout` | Every bound queue (this lesson) |
| `topic` | Queues whose pattern matches, e.g. `orders.*.eu` or `orders.#` |
| `headers` | Queues matching message header values |

To keep messages for a subscriber that's offline, give it a **named, durable** queue instead of an exclusive one.

Next: [03 · retries and dead letters](../03_rabbitmq_dead_letter/)

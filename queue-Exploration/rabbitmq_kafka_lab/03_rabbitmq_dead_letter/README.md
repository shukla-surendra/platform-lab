# 03 · RabbitMQ retries and dead-letter queue

**One idea:** a message that keeps failing (a "poison message") must not retry forever. After a limit,
RabbitMQ moves it to a **dead-letter queue** (DLQ) where you can inspect it.

```
producer ──▶ [ payments ] ──▶ worker ── ack ──▶ (deleted)
                 ▲  │                └─ nack ─┐
                 └──┼── requeue (retry) ◀─────┘
                    │ after 3 redeliveries
                    ▼
            (payments.dlx) ──▶ [ payments.dead ]
```

## Run it

```bash
uv run producer.py           # creates the queues, sends 5 payments, one is BROKEN
uv run worker.py             # watch the BROKEN one fail repeatedly; Ctrl+C once it stops appearing
uv run read_dead_letters.py  # the BROKEN payment is here, with the reason
```

## What to look for

1. Good payments print `ok` once.
2. `pay-3 BROKEN` prints `FAIL` four times (first delivery + 3 redeliveries), with the redelivery count
   going up, then stops appearing.
3. `read_dead_letters.py` shows it with `reason=delivery_limit`.
4. Web UI → **Queues**: `payments` is empty, `payments.dead` has 1 message until you read it.

## Key terms

| Term | Here |
|---|---|
| nack + requeue | `basic_nack(requeue=True)`: "failed, put it back to retry" |
| Quorum queue | `x-queue-type: quorum`: replicated queue type, recommended for anything important |
| Delivery limit | `x-delivery-limit: 3`: max redeliveries before giving up |
| Dead-letter exchange | `x-dead-letter-exchange`: where given-up messages are sent |

In production, also add a delay between retries (for example a retry queue with a message TTL), so a
broken dependency isn't hammered in a tight loop.

Next: [04 · Kafka log and replay](../04_kafka_log_and_replay/)

# RabbitMQ and Kafka lab

Six small lessons, one idea each, to see how a **queue** (RabbitMQ) and a **log** (Kafka) behave
differently. Each lesson folder has a short README, a producer and a consumer.

Background reading: [Messaging tools compared](../messaging_tools_compared.html) (section 2: "Is Kafka a queue?").

## Setup

Needs Docker and [uv](https://docs.astral.sh/uv/). Scripts declare their own dependencies (`pika` for
RabbitMQ, `confluent-kafka` for Kafka), so `uv run script.py` installs them on first use.

```bash
cd rabbitmq_kafka_lab
docker compose up -d
docker compose ps            # wait until lab-rabbitmq and lab-kafka show "(healthy)"
```

| What | Where |
|---|---|
| RabbitMQ (AMQP) | `localhost:5672` |
| RabbitMQ web UI | http://localhost:15672 (user `guest`, password `guest`) |
| Kafka | `localhost:9092` |
| Kafka web UI | http://localhost:8080 |

When you're done:

```bash
docker compose down -v       # stop and delete all queues, topics and messages
```

## Lessons

Do them in order. Each one takes about 5 minutes and needs 2 to 4 terminals.

| # | Lesson | The one idea |
|---|---|---|
| 01 | [RabbitMQ work queue](01_rabbitmq_work_queue/) | Each message goes to one worker and is deleted once acked. A crashed worker's job is redelivered. |
| 02 | [RabbitMQ pub/sub](02_rabbitmq_pub_sub/) | Exchanges copy messages to queues. Fanout gives every subscriber a copy, but only while it's listening. |
| 03 | [RabbitMQ dead letters](03_rabbitmq_dead_letter/) | A message that keeps failing is moved to a dead-letter queue after a retry limit. |
| 04 | [Kafka log and replay](04_kafka_log_and_replay/) | Reading doesn't delete. Each consumer group keeps its own bookmark and can replay. |
| 05 | [Kafka consumer groups](05_kafka_consumer_groups/) | One consumer per partition per group. Same key, same partition, same order. |
| 06 | [Kafka slow message](06_kafka_slow_message/) | One slow message blocks its partition, and a too-slow consumer gets kicked out and the message reprocessed. |

Free play: [topic1 playground](topic1_playground/) has a batch producer and a consumer for any topic, plus
notes on what a partition is, from a real run.

## What you should come away with

| | RabbitMQ (queue) | Kafka (log) |
|---|---|---|
| After a message is handled | Deleted (01) | Kept, replayable (04) |
| Many services need the same message | One queue each, bound to an exchange (02) | One consumer group each (04, 05) |
| Scaling workers | Add workers; free ones take the next job (01) | Capped by partition count (05) |
| Ordering | Loose | Strict per partition / key (05) |
| Failed message | nack, retry limit, dead-letter queue (03) | No built-in DLQ; a stuck message blocks its partition (06) |
| Long-running jobs | Fine, with prefetch 1 and acks (01) | Poor: poll deadline and head-of-line blocking (06) |
| Use it for | "Do this job, once" | "This happened; anyone can read it, now or later" |

## How the compose file works

- **RabbitMQ** uses the `-management` image, which includes the web UI.
- **Kafka** runs as one node in **KRaft mode**: the same process is both broker and controller, so no
  ZooKeeper is needed. It has two listeners: `localhost:9092` for scripts on your Mac and `kafka:19092` for
  other containers (the Kafka UI). With one broker, every replication factor is set to 1.
- **Kafka UI** (kafbat) connects to `kafka:19092` and only starts once Kafka is healthy.

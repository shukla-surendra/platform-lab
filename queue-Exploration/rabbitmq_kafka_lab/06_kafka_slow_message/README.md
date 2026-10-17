# 06 · A slow message in Kafka

**One idea:** in Kafka, a partition is processed **in order by one consumer**. One slow message holds up
every message behind it, and if processing takes too long, Kafka assumes the consumer is dead.

This is why Kafka is a poor fit for long-running jobs, and RabbitMQ (or a database queue) is a better one.

## Part 1: the fast tasks wait

```bash
# two terminals
uv run consumer.py A
uv run consumer.py B

# third terminal
uv run producer.py         # task-1 takes 15s, tasks 2-5 take 1s each
```

If the consumers print `Unknown topic or partition` at first, that's because the producer hasn't created the
topic yet. It goes away once you run the producer.

What you'll see:
- Only **one** consumer owns the single partition. The other has nothing to do.
- task-2 to task-5 start only after task-1 finishes: each prints `waited ~15s in Kafka` or more.
- Run the same shape in RabbitMQ lesson 01 and the second worker would take the fast jobs immediately.

## Part 2: too slow, kicked out, processed twice

Stop both consumers. This topic now holds old tasks, so reset the group to start fresh:

```bash
docker exec lab-kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group task-workers --topic tasks --reset-offsets --to-latest --execute
```

Start both consumers with `--strict` (they must call `poll()` at least every 10s), then send tasks:

```bash
uv run consumer.py A --strict
uv run consumer.py B --strict
uv run producer.py
```

What you'll see:
1. A starts the 15-second task-1. It doesn't call `poll()` while working.
2. After 10s, Kafka decides A is stuck and **removes it from the group**. B is given the partition.
3. B's bookmark still points at task-1 (A never committed), so **B starts task-1 again**.
4. A finishes and tries to commit, and the commit is **rejected**: A no longer owns the partition.
5. B also takes 15s, so B gets kicked too, and the partition bounces between them. task-1 is started over and
   over and never committed, and **task-2 to task-5 never run at all**. Press Ctrl+C to stop.

You'll also see librdkafka's own warning: `Application maximum poll interval (10000ms) exceeded ... leaving group`.

This is what a "poison" slow message does to a Kafka consumer group: one message stalls the whole partition.

## How real systems handle this

- **Keep processing short**, or raise `max.poll.interval.ms` above the longest task (the default is 5 minutes).
- **Hand slow work to a separate thread** and keep calling `poll()` with the partition paused.
- **Use a job queue** (RabbitMQ, SQS, a Postgres queue) for long jobs, and Kafka for the event stream.
  See [`../../long_running_agent_jobs.html`](../../long_running_agent_jobs.html), section 8.

Back to the [lab overview](../README.md).

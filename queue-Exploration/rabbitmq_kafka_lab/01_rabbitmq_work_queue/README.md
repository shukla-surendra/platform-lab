# 01 · RabbitMQ work queue

**One idea:** a queue hands each message to **one** worker, and deletes it once that worker acks it.

```
producer ──▶ [ jobs queue ] ──▶ worker A   (gets job-1, job-3, ...)
                            └─▶ worker B   (gets job-2, job-4, ...)
```

## Run it

Open three terminals in this folder.

```bash
# terminal 1 and 2: start two workers
uv run worker.py A
uv run worker.py B

# terminal 3: send 10 jobs
uv run producer.py 10
```

## What to look for

1. **Each job is printed by exactly one worker.** No job runs twice.
2. **Work is shared by who's free, not strictly alternated.** `prefetch_count=1` means a worker gets
   its next job only after acking the current one, so a worker stuck on a 3-second job doesn't hoard more.
3. **Open the web UI** at http://localhost:15672 (guest / guest) → **Queues** → `jobs`. Send 30 jobs and
   watch *Ready* (waiting) and *Unacked* (being worked on) go down.

## Experiment: kill a worker mid-job

1. Send 10 jobs.
2. While worker A prints `got job-...`, press **Ctrl+C** in its terminal.
3. Worker B prints that same job with `<- REDELIVERED`.

A never acked it, so when its connection closed RabbitMQ put the job back for someone else. This is
**at-least-once delivery**: a job is never lost, but it can run twice (A may have half-done it), so real
jobs must be safe to repeat.

## Key terms

| Term | Here |
|---|---|
| Queue | `jobs`, declared `durable` so it survives a broker restart |
| Ack | `basic_ack`: "finished, delete it" |
| Prefetch | `basic_qos(prefetch_count=1)`: max unacked messages per worker |
| Persistent message | `delivery_mode=Persistent`: written to disk |

Next: [02 · pub/sub](../02_rabbitmq_pub_sub/)

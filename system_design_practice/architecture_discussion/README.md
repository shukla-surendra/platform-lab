# Architecture Discussion

Open-ended design write-ups: one problem, the options, and their trade-offs. Unlike the numbered
case studies in this section, these come from real backend questions rather than interview prompts.

| Topic | What it covers |
|---|---|
| [Long-running agent jobs in a multi-tenant system](long_running_agent_jobs.html) | Moving a FastAPI agent endpoint to submit-and-poll background runs: async request-reply, execution options (Postgres queue, Celery, Kafka, Temporal/Hatchet, K8s Jobs), the same design on Kafka vs RabbitMQ vs Redis vs SQS vs Azure Storage Queue, checkpointing and leases, polling vs SSE vs webhooks, tenant isolation and fairness, cloud-agnostic component mapping |
| [Messaging tools compared](messaging_tools_compared.html) | What Redis, RabbitMQ, Kafka, NATS, Pulsar, Postgres-as-queue, workflow engines and the cloud queues (SQS, SNS, Pub/Sub, Service Bus, Storage Queue, Event Hubs, Kinesis) are; queue vs pub/sub vs log vs workflow; why Kafka is a log, not a job queue; comparison table, when-to-use guide, common mistakes |
| [Postgres as a queue](postgres_as_a_queue.html) | How a queue is built from a table + `FOR UPDATE SKIP LOCKED`: claim query, leases and heartbeats, crash recovery, retries with backoff, why 50 pods never claim the same job (tested, with fencing tokens and idempotency), LISTEN/NOTIFY, measured cost of polling (with a benchmark script), a runnable Python worker, pgmq and libraries, limits and when to move on |

[`postgres_queue_lab/`](postgres_queue_lab/) holds the runnable scripts behind the Postgres page's concurrency tests.

[`rabbitmq_kafka_lab/`](rabbitmq_kafka_lab/) is a hands-on Docker Compose lab: six small lessons showing how RabbitMQ (a queue) and Kafka (a log) behave differently.

Open the `.html` files directly in a browser.

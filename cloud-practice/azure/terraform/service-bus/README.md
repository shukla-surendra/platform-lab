# Terraform: Azure Service Bus (minimal)

RG + a Basic-tier Service Bus Namespace + one Queue + a queue-scoped
authorization rule (Listen + Send, not Manage).

> ⚠️ **This creates billable resources.** Basic tier bills per-operation
> (a small number of cents per million), not per-hour like a VM -- cheap
> for a quick test, but not literally free. Run `terraform destroy` when done.

## "What's Azure's SQS?" -- two candidates, not one

There isn't a single 1:1 match; which AWS mental model you're porting
decides which Azure service is actually the right comparison:

| AWS | Azure equivalent | Why |
|---|---|---|
| **SQS Standard Queue** alone -- bare, cheap, point-to-point | **Azure Storage Queues** | A queue as a side-feature of a Storage Account (same account type as Blob Storage) -- minimal API, minimal cost, no enterprise features. Closest in *spirit* to plain SQS: the "just move a message from A to B, cheaply" primitive. |
| **SQS + SNS fan-out** -- queues *and* pub/sub, sessions, dead-lettering | **Azure Service Bus** (this module) | A real message broker: Queues (point-to-point, what this module builds) *and* Topics/Subscriptions (pub/sub fan-out, Standard tier+) in one service, plus FIFO-ordered sessions, dead-letter queues, transactions, and duplicate detection -- closer to a lightweight RabbitMQ/ActiveMQ replacement than to bare SQS. |

**The practical rule of thumb**: almost every real Azure architecture
doing serious queueing reaches for **Service Bus**, not Storage Queues --
the same way most production AWS systems reach for SQS *and* SNS together
rather than SQS alone, the moment fan-out to multiple consumers matters.
Storage Queues stay the right pick only when the workload is genuinely as
simple as "one producer, one consumer, no ordering/session/transaction
requirements" -- e.g. a lightweight work-item queue behind a single
background worker, not a system multiple services need to react to
independently.

## Usage

```bash
terraform init
terraform apply
```

The `az` CLI can manage the namespace/queue but has no send/receive
command -- get the connection string and use the Service Bus Explorer in
the Azure Portal, or any Service Bus SDK, to actually send/receive a
message:

```bash
terraform output -raw connection_string
```

## What's deliberately not here

Basic tier only, so no Topics/Subscriptions (pub/sub fan-out needs at
least Standard) -- this shows the simpler Queue (point-to-point,
processed once) primitive only. No dead-letter queue configuration
override, no session support, no VNet service endpoint, no
namespace-level (root) authorization rule -- this deliberately uses a
queue-scoped one instead, narrower than granting access to every
queue/topic in the namespace.

## Teardown

```bash
terraform destroy
```

# Terraform: Azure Service Bus (minimal)

RG + a Basic-tier Service Bus Namespace + one Queue + a queue-scoped
authorization rule (Listen + Send, not Manage).

> ⚠️ **This creates billable resources.** Basic tier bills per-operation
> (a small number of cents per million), not per-hour like a VM -- cheap
> for a quick test, but not literally free. Run `terraform destroy` when done.

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

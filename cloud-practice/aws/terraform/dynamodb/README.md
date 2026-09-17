# Terraform: DynamoDB — on-demand table with PITR, TTL, and an optional stream

Creates a single DynamoDB table: `PAY_PER_REQUEST` billing (no capacity
to plan or under-provision), point-in-time recovery on, encryption on,
and an optional TTL attribute + change stream.

> **Pay-per-request means pay-per-actual-use** — an idle table with
> `PAY_PER_REQUEST` billing costs $0. You only pay for reads/writes that
> actually happen, plus storage.

## What it creates

```
DynamoDB Table
  Partition key: hash_key (String)
  Sort key: range_key (String) — omit by setting range_key = "" for a simple key
  Point-in-time recovery (continuous backups, 35-day restore window)
  Server-side encryption (AWS-owned key, no separate KMS cost)
  TTL (optional — auto-delete expired items for free)
  Stream (optional — change feed for Lambda triggers)
```

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pin + default tags |
| `variables.tf` | Key schema, billing mode, PITR/TTL/stream toggles |
| `main.tf` | The table |
| `outputs.tf` | Table/stream ARNs + a `next_steps` runbook |

## Usage
```bash
cd aws/terraform/dynamodb
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
terraform output next_steps   # put-item / get-item / query commands
```

## Things to try (mini-labs)
1. `put-item` a few items sharing the same `pk` but different `sk` values, then `query` on just the `pk` — see every matching sort key come back in one call (this is the core DynamoDB access pattern: model your access pattern INTO the key schema, don't bolt it on after).
2. Enable PITR (on by default) and restore to a point 10 minutes ago via `aws dynamodb restore-table-to-point-in-time` into a NEW table name — confirm the original table is untouched (restores always create a new table).
3. `enable_ttl = true`, put an item with `expires_at` set to `$(date +%s)` (i.e. already expired), and check back in an hour or two — DynamoDB's TTL sweep isn't instant, but the item disappears without you doing anything.
4. Flip `enable_stream = true`, `apply`, then `put-item`/`update-item`/`delete-item` and inspect `aws dynamodbstreams get-records` — this is the exact feed a Lambda trigger (`aws_lambda_event_source_mapping`) would consume.

## Deliberately minimal
- No Global Secondary Indexes (add `global_secondary_index` blocks once
  you need to query by an attribute other than the primary key), no
  Global Tables (multi-region replication).

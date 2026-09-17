# Terraform: SNS + SQS — fan-out topic, durable queue, DLQ, optional Lambda trigger

Creates an SNS topic subscribed by an SQS queue (with `raw_message_delivery`
so subscribers see your original payload, not an SNS envelope), a
dead-letter queue for messages that fail repeatedly, and — if you pass in
`lambda/`'s outputs — an event source mapping that invokes that function
for every batch of messages.

> **Effectively free at lab scale** — SNS/SQS Free Tier is 1M
> requests/month each, forever (not just 12 months).

## What it creates

```
SNS Topic
SQS Queue (main) — redrive policy points at the DLQ
SQS Queue (dead-letter) — 14-day retention, the max
SQS Queue Policy (lets ONLY this SNS topic SendMessage)
SNS Topic Subscription (SNS -> SQS, raw delivery)
Lambda Event Source Mapping (optional — SQS -> Lambda, batch_size 10)
```

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pin + default tags |
| `variables.tf` | Timeouts, retention, DLQ threshold, optional Lambda wiring |
| `main.tf` | Topic, queues, policies, subscription, event source mapping |
| `outputs.tf` | ARNs/URLs, the IAM policy you must attach for Lambda, `next_steps` |

## Usage
```bash
cd aws/terraform/sns-sqs
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
aws sns publish --topic-arn "$(terraform output -raw topic_arn)" --message '{"hello":"world"}'
aws sqs receive-message --queue-url "$(terraform output -raw queue_url)"
```

## Things to try (mini-labs)
1. Publish, then `receive-message` — note the `Body` is your raw JSON, not wrapped in an `SNS Message/MessageId/...` envelope (that's `raw_message_delivery = true` at work; try it `false` to see the difference).
2. `receive-message` the SAME message `max_receive_count` times without ever calling `delete-message` — on the next attempt it's gone from the main queue and shows up in the DLQ instead.
3. Wire in `lambda/`'s outputs, attach the `lambda_execution_role_policy_needed` output's policy to that function's role by hand (`aws iam put-role-policy`), then `sns publish` again — watch `aws logs tail /aws/lambda/<function>` show the invocation with zero polling code of your own.
4. Subscribe a SECOND queue (or your own email, `protocol = "email"`) to the same topic and publish once — see both subscribers receive independent copies. This is the actual point of SNS fan-out vs. a single point-to-point queue.

## Deliberately minimal
- No FIFO queue (ordering/exactly-once) — add `fifo_queue = true` +
  `.fifo` name suffixes + a `MessageGroupId` on publish if strict
  ordering matters. No SNS message filtering (subscription filter
  policies) — every subscriber currently gets every message.

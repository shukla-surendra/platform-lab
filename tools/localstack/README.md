# LocalStack

**Category:** local cloud emulator (AWS, self-hosted/CI)

## What it is

A local cloud service emulator that runs in a single container and stands in for a large
slice of AWS itself — not just S3. Verified from LocalStack's own docs/GitHub: it emulates
**120+ AWS services** (S3, Lambda, DynamoDB, SQS, SNS, IAM, API Gateway, and most of the
rest of the commonly-used AWS surface). Your code talks to it using the exact same AWS
SDKs, AWS CLI, and IaC tools (Terraform, CDK, Pulumi) it would use against real AWS — only
the endpoint URL changes — so what's tested against LocalStack is meant to behave the same
way against real AWS.

## What it's used for

- **Mimicking a multi-service AWS architecture locally**, not a single service in
  isolation — e.g. an S3 upload triggering a Lambda that writes to DynamoDB and publishes
  to SQS, all runnable and testable on one machine with no AWS account.
- Local development and CI test suites for infrastructure-as-code (deploying real
  Terraform/CDK against LocalStack instead of a real AWS account for every CI run).
- Cost and speed: no AWS charges, no network latency to a real region, fully offline-capable.

## LocalStack vs. MinIO — the key distinction

If the actual need is narrower than "the whole of AWS" — just an S3-compatible bucket for
a service to read/write — [MinIO](../minio/README.md) is a real, standalone S3-API server:
simpler, faster to start, and it's genuinely S3 rather than an emulation layer for it.
LocalStack's value is specifically when **multiple AWS services need to interact** with
each other in the test, which is a scope MinIO alone doesn't cover.

## Alternatives

| Tool | Angle |
|---|---|
| **[MinIO](../minio/README.md)** | Real S3-compatible object storage only — narrower scope, simpler, faster when S3 is the only piece needed |
| **moto** | Python-only, in-process mock of AWS APIs via `boto3` patching — no real running server/container, fastest for pure-Python unit tests, but not usable from other languages or for testing against real network calls |
| **Real AWS (dev/sandbox account)** | Full fidelity, but real cost and no offline capability — LocalStack exists specifically to defer this until later in the dev cycle |

## Related

- [MinIO](../minio/README.md) — the narrower, S3-only alternative when a full AWS
  emulation isn't needed.
- [Mimir](../mimir/README.md), [Loki](../loki/README.md), [Tempo](../tempo/README.md) —
  self-hosted tools in this project's docs that need S3-compatible object storage,
  testable locally against either LocalStack's S3 emulation or MinIO directly.

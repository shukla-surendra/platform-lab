# MinIO

**Category:** object storage (self-hosted, S3-API-compatible)

## What it is

A real, standalone object storage server that implements the **S3 HTTP API itself** —
not an AWS emulator, a genuine S3-compatible store you run yourself (single Go binary or
Docker container). Any tool/SDK built for AWS S3 (boto3, the AWS CLI, Terraform's `aws_s3_*`
resources) works against it unmodified — you just point the client's endpoint at your MinIO
server instead of `s3.amazonaws.com`. Open-sourced under **AGPLv3**. Verified from MinIO's
own GitHub repo and docs.

## What it's used for

- **A local/self-hosted stand-in for S3** when testing a service that needs object storage,
  without an AWS account or network round-trips to real S3.
- **The object-storage backend for other self-hosted tools that need S3-shaped storage** —
  this is exactly what [Mimir](../mimir/README.md), [Loki](../loki/README.md), and
  [Tempo](../tempo/README.md) are designed around (all three store data in S3-compatible
  object storage as their durability layer), and MinIO is the common self-hosted choice
  when not using real AWS S3 for that.
- Runs as a single node for local dev, or as a distributed multi-node cluster for real
  self-hosted production object storage with erasure coding and (in multi-site setups)
  bucket replication.
- S3 API port defaults to `9000`; a web console for browsing buckets/objects ships on
  `9001`.

## MinIO vs. LocalStack — the key distinction

MinIO **is** an S3-compatible server — real object storage, real semantics, nothing
emulated. It does not know or care about any other AWS service (Lambda, DynamoDB, SQS).
If the goal is "test a service that needs an S3 bucket," MinIO alone is enough and is
simpler/faster than spinning up a full AWS emulator for it. If the goal is "mimic an
entire AWS-shaped architecture" (S3 + several other services interacting), see
[LocalStack](../localstack/README.md) instead.

## Alternatives

| Tool | Angle |
|---|---|
| **[LocalStack](../localstack/README.md)** | Emulates S3 *and* 120+ other AWS services in one container — broader scope, heavier |
| **moto** | Python-only, in-process mock of `boto3` calls — no real server, fastest for unit tests, but not usable for cross-language/cross-service integration testing |
| **Real AWS S3** | No local emulation at all — the thing MinIO/LocalStack exist to avoid needing during dev/test |

## Related

- [LocalStack](../localstack/README.md) — the broader local-AWS-emulator alternative when
  the need extends past S3 alone.
- [Mimir](../mimir/README.md), [Loki](../loki/README.md), [Tempo](../tempo/README.md) — the
  observability backends in this project's docs that need S3-compatible object storage,
  where MinIO is the typical self-hosted choice.

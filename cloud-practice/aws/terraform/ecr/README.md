# Terraform: ECR — container registry with scanning + lifecycle policy

Creates a single ECR repository with push-time vulnerability scanning,
immutable tags (prevents accidentally overwriting `v1` with different
content), and a lifecycle policy that expires untagged images after a
day and caps tagged image history. Feeds `ecs-fargate/`.

> **Effectively free at this scale** — ECR charges for storage past the
> Free Tier allowance (500MB/month for 12 months, then $0.10/GB/month)
> and for data transfer out. A handful of test images costs cents.

## What it creates

```
ECR Repository (scan_on_push, image_tag_mutability = IMMUTABLE)
Lifecycle Policy (expire untagged after 1 day; keep newest N tagged images)
```

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pin + default tags |
| `variables.tf` | Scan/mutability/retention settings |
| `main.tf` | The repository + lifecycle policy |
| `outputs.tf` | Repository URL + a `next_steps` runbook (docker login/push) |

## Usage
```bash
cd aws/terraform/ecr
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
terraform output next_steps   # docker login / build / push commands
```

## Things to try (mini-labs)
1. `docker login` + push a trivial image (`FROM alpine` is enough), then `describe-image-scan-findings` — see the CVE report land within a minute or two.
2. Try pushing the SAME tag twice with `image_tag_mutability = IMMUTABLE` — the second push is rejected; flip to `MUTABLE` and it silently overwrites instead. This is why prod repos use IMMUTABLE + a unique tag (git SHA, build number) per push.
3. Push 15 tagged images, wait for the daily lifecycle policy evaluation (or trigger it via `aws ecr start-lifecycle-policy-preview`), and confirm only `max_image_count` remain.

## Deliberately minimal
- Single repository, no cross-account repository policy, no replication
  configuration. For a multi-region setup, `aws_ecr_replication_configuration`
  (account-level, one per account) mirrors pushes to other regions
  automatically.

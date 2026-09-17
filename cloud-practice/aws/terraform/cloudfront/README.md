# Terraform: CloudFront — CDN in front of a private S3 bucket (OAC)

Creates a CloudFront distribution serving a **fully private** S3 bucket
(from the `s3/` module) using **Origin Access Control (OAC)** — the
modern replacement for the older Origin Access Identity. The bucket
itself never becomes public; CloudFront signs its requests to S3, and
the bucket policy this module attaches only trusts requests that came
from THIS specific distribution's ARN.

> **Pay-per-use, cheap at lab scale** — no hourly charge (unlike ALB);
> you pay per GB served + per 10,000 requests, and `PriceClass_100`
> keeps edge locations to North America + Europe only (cheaper than
> global).

## What it creates

```
Origin Access Control (SigV4, always-sign)
CloudFront Distribution (HTTPS only via viewer_protocol_policy, default cert)
S3 Bucket Policy (on the s3/ module's bucket — allows ONLY this distribution's ARN)
```

## Prerequisite
Apply `s3/` first and paste its three outputs
(`bucket_name`/`bucket_arn`/`bucket_regional_domain_name`) into this
module's `terraform.tfvars`.

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pin + default tags |
| `variables.tf` | Origin bucket references, TTL, price class |
| `main.tf` | OAC, distribution, bucket policy |
| `outputs.tf` | The `*.cloudfront.net` domain + a `next_steps` runbook |

## Usage
```bash
cd aws/terraform/cloudfront
cp terraform.tfvars.example terraform.tfvars   # paste in s3/'s outputs
terraform init
terraform apply     # first apply takes several minutes — CloudFront propagates globally
```

## Things to try (mini-labs)
1. Upload `index.html` to the S3 bucket, then `curl` the CloudFront domain — first request is a cache MISS (check `X-Cache: Miss from cloudfront`), second is a HIT.
2. `curl` the S3 bucket's own regional domain directly (from `s3/`'s output) — `403 Forbidden`, because only CloudFront's signed requests are allowed. This is the entire point of OAC.
3. Update the object in S3, `curl` again immediately — CloudFront still serves the OLD cached version until `default_ttl` (1 hour by default) expires. Force a refresh with `aws cloudfront create-invalidation --paths "/*"` and re-`curl`.
4. Change `price_class` to `PriceClass_All` and `apply` — no visible behavior change from your test location, but it now has edge locations available in South America/Australia/Asia too (relevant once real global users are involved).

## Deliberately minimal
- No custom domain/ACM certificate (uses CloudFront's own default
  `*.cloudfront.net` cert) — adding an alias needs an ACM cert issued in
  `us-east-1` specifically, regardless of which region your other
  resources live in (a CloudFront-specific quirk).
- No WAF attached, no signed URLs/cookies for private content, no
  Origin Shield.

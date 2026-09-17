# Terraform: S3 — versioned, encrypted, private-by-default bucket

Creates a general-purpose S3 bucket: versioning on, SSE-S3 encryption,
public access fully blocked (always — even in static-website mode), and
a lifecycle rule that transitions old object versions to cheaper storage
before expiring them. Meant as the origin for `cloudfront/`, the
artifact store pattern used by `codebuild/`/`codepipeline`/`codedeploy/`,
or just a general bucket.

> **Near-zero cost** at lab scale — S3 Standard storage is
> $0.023/GB/month; the real cost driver is data transfer OUT, which
> `cloudfront/` (caching) helps with directly.

## What it creates

```
S3 Bucket (name gets a random suffix — bucket names are globally unique)
Versioning (Enabled)
Server-Side Encryption (SSE-S3 / AES256, bucket keys enabled to cut KMS request costs — moot here since there's no KMS key, but the setting matters once you switch to SSE-KMS)
Public Access Block (ALL FOUR blocks on, unconditionally)
Website Configuration (optional — index/error docs; bucket stays private regardless, see README note)
Lifecycle Rule (noncurrent version -> STANDARD_IA -> expire; abort incomplete multipart uploads after 7 days)
```

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pins + default tags |
| `variables.tf` | Versioning, lifecycle timers, static-website toggle |
| `main.tf` | Bucket + versioning + encryption + public-access-block + lifecycle |
| `outputs.tf` | Bucket name/ARN/domain + a `next_steps` runbook |

## Usage
```bash
cd aws/terraform/s3
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
aws s3 cp ./somefile.txt s3://$(terraform output -raw bucket_name)/
terraform destroy   # note: a VERSIONED bucket with objects in it needs `-force` or manual emptying first — see mini-lab 4
```

## Things to try (mini-labs)
1. Upload a file, overwrite it, then `aws s3api list-object-versions` — see both versions still exist even though `aws s3 cp` looks like a plain overwrite from the CLI's perspective.
2. `aws s3api delete-object --bucket <name> --key <key>` (no `--version-id`) — the object "disappears" from a normal listing but is fully recoverable: S3 just added a delete marker, another version.
3. Confirm the bucket really is private: `curl -I https://<bucket_regional_domain_name>/anything` → `403 Forbidden`, even with `enable_static_website = true`. This is deliberate — see `cloudfront/` for the actual public-serving pattern.
4. Before `destroy`, if you uploaded real objects: `aws s3 rm s3://<bucket>/ --recursive` and, since versioning is on, also delete every version (or use `terraform destroy` and handle the "bucket not empty" error by scripting a version-cleanup loop — a good exercise in why versioned buckets need deliberate cleanup).

## Deliberately minimal
- No cross-region replication, no S3 Object Lock / retention (compliance
  mode), no bucket policy of its own — `cloudfront/` attaches ITS OWN
  bucket policy (Origin Access Control) onto this bucket by ARN, kept
  separate so this module stays a plain, reusable "give me a bucket."

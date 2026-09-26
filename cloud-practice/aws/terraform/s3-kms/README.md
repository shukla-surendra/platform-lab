# Terraform: S3 + KMS — bucket encrypted with a customer-managed key

Creates a private, versioned S3 bucket whose default encryption is **SSE-KMS
with a customer-managed key (CMK)** that this module also creates. Companion to
`s3/` (which uses SSE-S3 — no key to manage). Use this when you need to control
*who* can decrypt, audit every key use in CloudTrail, or be able to cut access
instantly by disabling the key.

> **Cost:** the CMK is $1/month (prorated) + $0.03 per 10,000 KMS requests;
> bucket keys keep request charges near zero. S3 storage is the usual
> $0.023/GB/month. A key scheduled for deletion stops billing after deletion.

## What it creates

```
KMS key (CMK)   — annual rotation on, key policy delegates to IAM, optional admins/users
KMS alias       — alias/<project>
S3 bucket       — random suffix, BucketOwnerEnforced (ACLs off)
 ├── Public Access Block   (all four on)
 ├── Versioning            (Enabled)
 ├── Default encryption    (aws:kms + the CMK, bucket key enabled)
 ├── Lifecycle             (noncurrent -> STANDARD_IA -> expire; abort stale multipart)
 └── Bucket policy         (deny non-TLS, deny explicit SSE-S3, deny a different KMS key)
Output: consumer_policy_json — IAM policy to attach to roles that need read/write + key use
```

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pins + default tags |
| `variables.tf` | Key deletion window, rotation, key admins/users, versioning/lifecycle |
| `main.tf` | Key + policy + alias, bucket + encryption/versioning/lifecycle/policy |
| `outputs.tf` | Bucket/key identifiers, consumer IAM policy, `next_steps` runbook |

## Usage
```bash
cd aws/terraform/s3-kms
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
terraform output next_steps
terraform destroy   # bucket must be empty (all versions) unless force_destroy = true
```

## How the access model works
Access to an SSE-KMS object needs **both** S3 permissions *and* KMS permissions.
The key policy's `EnableIamPolicies` statement (root principal) means IAM
policies in the account can grant KMS access; without it, only principals
named in the key policy could use the key. Attach `consumer_policy_json` to a
role and it can read/write the bucket. Cross-account access additionally
needs a key-policy statement for the other account.

## Things to try (mini-labs)
1. `aws s3 cp` a file, then `aws s3api head-object` — see `aws:kms`, the key ARN and `BucketKeyEnabled`.
2. Upload with `--sse AES256` → `AccessDenied` from the bucket policy. Upload with `--sse aws:kms --sse-kms-key-id <alias>` → also denied (the condition compares the ARN literally); with the ARN → allowed.
3. `aws kms disable-key` then `aws s3 cp s3://.../file -` → fails with `KMS.DisabledException`. Re-enable and it works again. This is the "crypto kill switch".
4. Create a role with S3 access *but not* the key permissions and try to read an object → `AccessDenied` on KMS. Then attach `consumer_policy_json`.
5. Look up the `GenerateDataKey`/`Decrypt` events in CloudTrail; toggle `bucket_key_enabled` and compare how many events a bulk upload produces.
6. Try a `terraform destroy`: the key goes into a pending-deletion window (`kms_deletion_window_days`), not gone immediately.

## Deliberately minimal
- Single-region key (no multi-region key or replication).
- No S3 access logging, Object Lock, or Macie.
- The bucket policy blocks explicit SSE-S3 / wrong-key writes but not SSE-C
  (customer-provided keys); block those with your org's SCPs if needed.
- Losing/deleting the key makes every object in the bucket permanently
  unreadable — that is the point, and also the risk.

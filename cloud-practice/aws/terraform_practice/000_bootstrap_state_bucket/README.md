# Bootstrap: remote-state bucket

Creates the S3 bucket that holds Terraform state for the other modules in
`terraform_practice/`. Deliberately uses **local** state — it can't store its own state
in a bucket that doesn't exist yet.

> **Status (2026-09-20): applied, used by `003` and `004`, then destroyed.** Re-applying
> creates a **new** bucket (random suffix). Put the new name in the `backend "s3"` block
> of each module's `versions.tf`; backend blocks can't use variables. Story:
> [`../JOURNEY.md`](../JOURNEY.md).

## Apply

```bash
terraform init && terraform apply
terraform output backend_snippet     # paste into a module's versions.tf, change `key`
```

Bucket: versioning, AES256 encryption, all public access blocked, TLS-only policy,
90-day expiry of old versions, `prevent_destroy`. Locking is S3-native
(`use_lockfile = true`, Terraform ≥ 1.10) — no DynamoDB table. The name uses a random
suffix rather than the AWS account ID because the repo is public.

Back up this module's local `terraform.tfstate` (gitignored) — it's the only record of the
bucket.

## Destroying it

`terraform destroy` alone will not work, by design. Once **no module's state in it still
tracks resources**:

1. Temporarily set `prevent_destroy = false` in `main.tf`.
2. Delete **every object version and delete marker** — `aws s3 rm --recursive` is not
   enough on a versioned bucket (lock files and old state versions pile up; ~57 accumulated
   here). List them with `aws s3api list-object-versions` and remove with
   `aws s3api delete-objects`.
3. `terraform destroy`.
4. Set `prevent_destroy = true` back so the code keeps its safeguard.

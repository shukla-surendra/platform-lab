# Terraform: importing existing (manually-created) resources

Teaches the workflow for bringing infrastructure that already exists in
AWS — created by hand, by another script, by a different team — under
Terraform management, **without destroying and recreating it**. Uses the
modern (Terraform >= 1.5) declarative `import` block + `terraform plan
-generate-config-out`, not the older `terraform import <addr> <id>` CLI
command.

> **Near-zero cost** — the worked example is a single empty S3 bucket.

## Why this is different from every other module here

Every other module in `aws/terraform/` assumes Terraform creates the
resource from nothing. Here the resource is created *first*, out-of-band
(`scripts/create-manual-bucket.sh`), and Terraform is pointed at it
afterward. That ordering — resource exists, then config catches up to it —
is the whole exercise.

## The two eras of "import" in Terraform

| | Classic `terraform import` | Import blocks (this module) |
|---|---|---|
| Terraform version | any | >= 1.5 |
| Where it's declared | CLI argument, nowhere in `.tf` files | `import { to = ..., id = ... }` block, checked into version control |
| Resource config | you hand-write it *first*, then import state into it — if your HCL doesn't match reality, `plan` shows a diff after import | Terraform can **generate** the resource block for you from the live resource via `-generate-config-out` |
| Repeatable / plannable | no — a one-shot imperative command | yes — `terraform plan` shows you what an import *would* do before it happens |
| Team workflow | error-prone (attributes typed by hand from memory/console) | attributes come straight from the provider's read of the real resource |

This module only covers the import-block workflow. `imports.tf` has the
block; `main.tf` has the (already cleaned-up) resulting resource.

## Step-by-step: doing this for real

### 1. Create something "by hand" to practice on
```bash
cd scripts
./create-manual-bucket.sh my-unique-practice-bucket-12345
cd ..
```
This is standing in for infrastructure someone already created before
Terraform was involved. In real life, skip this step — you already have
the resource.

### 2. Point variables at it
```bash
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars: bucket_name = "my-unique-practice-bucket-12345"
terraform init
```

### 3. Generate config from the live resource
`imports.tf` already has:
```hcl
import {
  to = aws_s3_bucket.imported
  id = var.bucket_name
}
```
Run:
```bash
terraform plan -generate-config-out=generated.tf
```
Terraform reads the real bucket through the AWS provider and writes a
`resource "aws_s3_bucket" "imported" { ... }` block into `generated.tf`.
**This does not touch state or `main.tf`.** It's a draft for you to review.

### 4. Cleaning up generated config
Raw generator output is deliberately conservative and ugly — it dumps
every readable attribute, including computed/output-only ones that aren't
valid to *set*, and hardcodes literal values instead of using your
variables. Typical raw output looks like:

```hcl
# __generated__ by Terraform
resource "aws_s3_bucket" "imported" {
  bucket              = "my-unique-practice-bucket-12345"
  bucket_prefix       = null
  force_destroy       = null
  object_lock_enabled = false
  tags                = {}
  tags_all            = {}
  # ... plus arn, bucket_domain_name, hosted_zone_id,
  #     bucket_regional_domain_name, region, id — all computed, all invalid
  #     to leave in a resource block you intend to apply
}
```

`main.tf` in this repo is what that becomes after cleanup:
- literal bucket name → `var.bucket_name`
- every computed-only attribute (`arn`, `*_domain_name`, `hosted_zone_id`,
  `region`, `id`) deleted — the generator includes them for visibility,
  Terraform will reject/ignore them as arguments (or error, depending on
  the attribute)
- `null`-valued optional arguments you don't care about, deleted
- empty `tags = {}` replaced with this module's real `local.tags`
- the `# __generated__` comment removed once you've taken ownership of the
  block

Move the cleaned block into `main.tf` (already done here), delete
`generated.tf`, and re-run `terraform plan` — it should now show little to
no diff between your HCL and the real resource.

### 5. Actually import
`plan` never writes to state — only `apply` does:
```bash
terraform plan    # sanity check: no changes, or only cosmetic ones
terraform apply   # this is the step that writes aws_s3_bucket.imported into state
terraform state list
```
`outputs.tf`'s `next_steps` output repeats this as a runbook after
`apply`.

### 6. Confirm it's really managed
```bash
terraform plan   # "No changes" — Terraform's view now matches reality
```
From here the bucket behaves like any other Terraform-managed resource:
edit `main.tf`, `terraform plan`/`apply` as normal.

## Files
| File | Purpose |
|---|---|
| `imports.tf` | The `import` block(s) — the actual mechanism this module demonstrates |
| `main.tf` | Cleaned-up resource block matching the real bucket (post `generate-config-out`) |
| `variables.tf` | `bucket_name` of the pre-existing resource, tags |
| `outputs.tf` | Bucket name/ARN + a `next_steps` runbook |
| `versions.tf` | Terraform >= 1.5 pin (required for `import` blocks) |
| `scripts/create-manual-bucket.sh` | Creates a practice bucket out-of-band (run yourself) |
| `scripts/cleanup.sh` | Removes from state AND deletes the bucket (run yourself) |

## Gotchas / things that bite people doing this for real
1. **One resource type per import block.** A real bucket usually has
   versioning, encryption, a bucket policy, and a public-access-block as
   *separate* resources in the AWS provider (v4+). Each needs its own
   `import` block and its own generate-config-out pass — see the comment
   in `main.tf`. Nothing auto-discovers "everything attached to this
   bucket."
2. **Sensitive attributes don't come back.** Anything the provider marks
   sensitive (e.g. a secret string on some resource types) reads as null
   or a placeholder after import/generate — you must fill it in by hand,
   because Terraform state legitimately doesn't have it either until you
   set it and apply.
3. **`generate-config-out` refuses to overwrite an existing file** — if
   you re-run it, delete or rename the previous `generated.tf` first, or
   it errors out rather than silently clobbering your review.
4. **`plan` producing a non-empty diff right after import is normal** —
   it means your cleaned-up HCL doesn't perfectly match reality yet (e.g.
   you dropped an argument the resource actually has a non-default value
   for). Iterate: adjust `main.tf`, `plan` again, until it's empty.
5. **Deleting the `import` block afterward is optional, not required.**
   Once the resource is in state, the block is inert on every future
   `plan`/`apply`. Some teams keep it permanently as a changelog of "how
   did this enter Terraform."

## Deliberately minimal
- Worked example is a single bare bucket, not versioning/encryption/policy
  sub-resources — see gotcha #1 for how to extend it.
- No `moved` blocks (renaming an already-Terraform-managed resource is a
  different problem from importing an unmanaged one).
- Not wired into CI/CD anywhere — this is a manual, one-time-per-resource
  operation by design, not something you'd automate blindly.

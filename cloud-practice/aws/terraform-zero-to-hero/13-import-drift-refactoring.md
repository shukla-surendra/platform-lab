# 13 · Import, drift, and refactoring

## 🎯 Goal

Handle the messy real world: adopt resources created by hand, deal with
drift, rename or move code without destroying anything, force a
replacement on purpose, and hand resources back.

> Hands-on companion (Azure, but the concepts are identical):
> [`../../azure/terraform/import-basics/`](../../azure/terraform/import-basics/)
> walks through import step by step with real output.

---

## 🧠 Mental model: five "code-only" state operations

All of these change **Terraform's memory** (state), not AWS, and all of
them can now be written **as code** so they show up in the plan:

| Situation | Block (preferred) | Old CLI command |
|---|---|---|
| Something exists in AWS; Terraform should manage it | `import { }` | `terraform import` |
| You renamed or moved code | `moved { }` | `terraform state mv` |
| Terraform should stop managing something (and leave it in AWS) | `removed { }` | `terraform state rm` |
| AWS drifted and you want to *accept* the drift into state | `plan/apply -refresh-only` | `terraform refresh` (deprecated) |
| An object is broken and needs recreating | `apply -replace=ADDR` | `terraform taint` (deprecated) |

Why blocks beat commands: **they appear in the plan, they're reviewed in
pull requests, and they run in every environment automatically**. A CLI
command is something one person ran once on one state.

---

## 🛠 Walkthrough

### Step 1: import: adopting existing resources

The situation: someone created a bucket by hand, and now Terraform should
own it.

```hcl
import {
  to = aws_s3_bucket.legacy_uploads
  id = "notes-legacy-uploads"          # the import ID: see the resource's docs
}

resource "aws_s3_bucket" "legacy_uploads" {
  bucket = "notes-legacy-uploads"
}
```

```bash
terraform plan
#   # aws_s3_bucket.legacy_uploads will be imported
#   Plan: 1 to import, 0 to add, 0 to change, 0 to destroy.
terraform apply
```

**The golden rule:** keep editing the resource block until the plan says
**`0 to change`**. Any `~` means your code differs from reality and the
import would *modify* the live resource. Fix the code, not AWS.

**What's the ID?** It's different for every resource type. The bottom of
each resource's page in the Terraform Registry has an **"Import"** section.
Examples:

| Resource | Import ID |
|---|---|
| `aws_s3_bucket` | bucket name |
| `aws_instance` | `i-0abc…` |
| `aws_vpc` / `aws_subnet` | `vpc-…` / `subnet-…` |
| `aws_iam_role` | role **name** |
| `aws_iam_role_policy_attachment` | `role-name/arn:aws:iam::aws:policy/…` |
| `aws_security_group` | `sg-…` |
| `aws_db_instance` | DB identifier |
| `aws_route53_record` | `ZONEID_name_TYPE` e.g. `Z123_api.example.com_A` |

### Step 2: let Terraform write the code

For a resource with 40 attributes, don't guess. Write only the `import`
block, then:

```bash
terraform plan -generate-config-out=generated.tf
```

Terraform reads the real object and writes a `resource` block for it.
Then:

1. Apply, to import.
2. **Tidy** `generated.tf`: delete empty and default values, replace
   hard-coded IDs with references, and move it into the right file.
3. Plan again. It should still say **No changes**.

### Step 3: import many at once

Import blocks accept `for_each` (Terraform 1.7+):

```hcl
locals {
  legacy_buckets = {
    uploads = "notes-legacy-uploads"
    exports = "notes-legacy-exports"
  }
}

import {
  for_each = local.legacy_buckets
  to       = aws_s3_bucket.legacy[each.key]
  id       = each.value
}

resource "aws_s3_bucket" "legacy" {
  for_each = local.legacy_buckets
  bucket   = each.value
}
```

After a successful apply, **delete the import blocks**. They've done their job.

> On AWS, watch for **split resources**. Since AWS provider v4, an S3
> bucket's settings (versioning, encryption, lifecycle, policy) are
> *separate* resources. Importing `aws_s3_bucket` alone doesn't bring in
> its versioning configuration. Import `aws_s3_bucket_versioning` etc. too,
> or Terraform won't manage those settings.

### Step 4: drift, and the three ways to respond

**Drift** is when AWS no longer matches the state, because someone changed
it outside Terraform. `terraform plan` detects it during the refresh.

You have three choices:

**A. Terraform is right, so revert the drift.** Just `terraform apply`.
Your code wins.

**B. The drift is right, so adopt it into the code.** Update your `.tf`
to match, then plan: *No changes*.

**C. Just update the state, touch nothing** (e.g. to see drift clearly,
or when outputs are stale):

```bash
terraform plan -refresh-only      # shows what changed in AWS vs state
terraform apply -refresh-only     # accept: write the real values into state
```

After (C), the normal plan may still show changes, because the *code*
still disagrees. Then go to (A) or (B).

> **Detecting drift continuously:** run `terraform plan -detailed-exitcode`
> on a schedule (lesson 21). Exit code `0` = no changes, `2` = changes
> (drift), `1` = error.

### Step 5: `moved`: refactor without destroying

Renaming, switching `count` to `for_each`, or moving code into a module
all change **addresses**. Without help, Terraform plans destroy + create.

```hcl
# 1. simple rename
moved {
  from = aws_instance.web
  to   = aws_instance.frontend
}

# 2. count → for_each
moved {
  from = aws_subnet.private[0]
  to   = aws_subnet.private["ap-south-1a"]
}
moved {
  from = aws_subnet.private[1]
  to   = aws_subnet.private["ap-south-1b"]
}

# 3. into a module (lesson 14)
moved {
  from = aws_vpc.main
  to   = module.network.aws_vpc.this
}
```

The plan shows:

```
  # aws_instance.web has moved to aws_instance.frontend
    resource "aws_instance" "frontend" { id = "i-0a1b2c3d" ... }
Plan: 0 to add, 0 to change, 0 to destroy.
```

**Keep `moved` blocks for a while** (or forever in shared modules), so
every environment and every consumer that hasn't applied yet also gets the
move. They're harmless once applied.

### Step 6: `removed`: stop managing without deleting

```hcl
removed {
  from = aws_s3_bucket.legacy["exports"]

  lifecycle {
    destroy = false          # forget it, don't delete it
  }
}
```

```
  # aws_s3_bucket.legacy["exports"] will no longer be managed by Terraform, but will not be destroyed
```

Deleting the resource block **without** a `removed` block means
**destroy**. That's the trap this block exists to prevent.
(`destroy = true` also exists, for when you *do* want it deleted and want
to be explicit about it.) Terraform 1.7+.

### Step 7: `-replace`: recreate on purpose

Sometimes a resource is "fine" according to Terraform but actually
broken, like a wedged instance or a corrupted node:

```bash
terraform plan  -replace='aws_instance.web'
terraform apply -replace='aws_instance.web'
#   # aws_instance.web will be replaced, as requested
```

This replaces the old `terraform taint` (which marked a resource in state
for replacement on the *next* apply, without any preview). With
`-replace`, you see the replacement in the plan you're approving.

Terraform also **taints automatically** when a create fails partway (e.g.
a provisioner failed). The plan then shows `is tainted, so must be replaced`.

### Step 8: moving resources between states

Splitting a big state into two (lesson 16) means moving resources from
state A to state B. The modern approach, which avoids editing state files
by hand:

1. In config **A**: a `removed { from = …, lifecycle { destroy = false } }` block. Apply. A forgets it.
2. In config **B**: the `resource` block plus an `import { }` block. Apply. B adopts it.

Nothing in AWS changes at any point.

---

## ⚠️ Common mistakes

- **Applying an import plan with `~` changes** "to fix it later". The import *changes the live resource*.
- **Deleting a resource block to "stop managing" it.** That destroys it. Use `removed`.
- **Renaming without `moved`.** Destroy and recreate, with data loss.
- **Deleting `moved` blocks too early** in a shared module. Consumers who upgrade later get destroy/create.
- **Forgetting split S3 resources** when importing buckets.
- **`apply -refresh-only` thinking it fixes drift.** It updates *state* to match AWS. The code may still disagree.

---

## 🎤 Interview corner

**Q: How do you bring existing infrastructure under Terraform?**

> Write `import` blocks with the resource address and the provider's
> import ID. Optionally generate the resource code with
> `plan -generate-config-out`. Iterate on the code until the plan shows
> "N to import, 0 to change", then apply and delete the import blocks.
> Watch for provider-default differences and split sub-resources like S3
> bucket settings. The older `terraform import` command does the same thing
> without a preview.

**Q: How do you rename a resource or refactor into a module without recreating anything?**

> Use `moved` blocks mapping old addresses to new ones. The plan shows
> moves and zero changes. They're declarative, reviewable, and apply to
> every workspace, and in shared modules they protect consumers who
> upgrade later. `terraform state mv` is the imperative alternative.

**Q: What's drift and how do you handle it?**

> Drift is divergence between real infrastructure and state or code,
> usually from manual changes. `plan` detects it via refresh. You either
> re-apply to enforce the code, update the code to accept the change, or
> use `-refresh-only` to reconcile state only. In production we run
> scheduled `plan -detailed-exitcode` jobs to alert on drift, and restrict
> console write access so drift doesn't happen.

**Q: `taint` vs `-replace`?**

> Both force recreation. `taint` modified state immediately and affected
> the next apply without a preview. It's deprecated. `-replace=ADDR` is
> part of plan/apply, so the replacement is visible in the plan you approve.

**Q: How do you move a resource from one state to another?**

> Remove it from the source with a `removed` block using
> `destroy = false`, then import it in the destination with an `import`
> block. Nothing in the cloud changes. Previously: `terraform state mv`
> with `-state-out`, or pull/rm/import.

---

## ✅ Check yourself

1. An import plan shows `1 to import, 1 to change`. What should you do?
2. You change `resource "aws_s3_bucket" "logs"` to `"access_logs"`. What does the plan show without and with a `moved` block?
3. What's the difference between `removed { lifecycle { destroy = false } }` and deleting the resource block?
4. Your plan shows drift in a security group rule that the security team added on purpose. What's the right fix?

<details><summary>Answers</summary>

1. Don't apply. Read the `~` lines and change your code to match the current values (left of the arrow) until it's `0 to change`.
2. Without: destroy `logs` + create `access_logs` (the bucket is deleted). With: "has moved", 0 changes.
3. The `removed` block makes Terraform forget the resource and leaves it in AWS. Deleting the block makes Terraform **destroy** it.
4. Add the rule to your code (option B), so Terraform stops trying to revert it. Then plan shows No changes.

</details>

➡️ **Next:** [14 · Modules](14-modules.md)

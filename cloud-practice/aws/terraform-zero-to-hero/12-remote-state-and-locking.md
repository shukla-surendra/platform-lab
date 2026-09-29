# 12 · Remote state and locking on AWS

## 🎯 Goal

Move state off your laptop into S3, protect it with locking, encryption,
and versioning, solve the "who creates the state bucket?" chicken-and-egg
problem, and share values safely between configurations.

---

## 🧠 Mental model: a shared notebook with a pen

Imagine the state is a notebook. With **local state**, everyone has their
own copy of the notebook. Alice writes "created server A", Bob's copy
doesn't have it, and Bob creates server A again.

**Remote state** means one notebook in a shared place (S3). **Locking**
means there's only **one pen**: whoever is running `apply` holds it, and
everyone else waits.

```
 Alice: terraform apply ──▶ takes the lock ──▶ reads state ──▶ changes AWS ──▶ writes state ──▶ releases
 Bob:   terraform apply ──▶ lock is taken ──▶ "Error acquiring the state lock" (or waits with -lock-timeout)
```

---

## 🛠 Walkthrough

### Step 1: the problems with local state

| Problem | What goes wrong |
|---|---|
| Not shared | two people have two different "truths" and create duplicates |
| No locking | two simultaneous applies corrupt state or fight over resources |
| On one laptop | laptop lost means state lost, which means Terraform has amnesia |
| Unencrypted, easy to commit | secrets leak |

Local state is fine for learning alone. For anything else, use a **backend**.

### Step 2: the S3 backend

```hcl
terraform {
  backend "s3" {
    bucket       = "acme-terraform-state-111122223333"
    key          = "notes-app/dev/terraform.tfstate"   # the "path" of this state inside the bucket
    region       = "ap-south-1"
    encrypt      = true            # server-side encryption
    use_lockfile = true            # native S3 locking (Terraform 1.10+)
  }
}
```

- **`bucket`**: one bucket can hold the state of **many** projects.
- **`key`**: must be **unique per state**. Use a clear convention, like
  `<project>/<env>/<component>/terraform.tfstate`.
- **`encrypt = true`**: encrypted at rest. Add `kms_key_id` to use your own KMS key.
- **`use_lockfile = true`**: Terraform creates a small `<key>.tflock`
  object next to the state while it holds the lock, using S3's
  conditional writes so only one writer can create it.

After adding or changing a backend block, run `terraform init`. If you
already had local state, `init` offers to **copy it into the new
backend**. Say yes.

### Step 3: locking: old way vs new way

| | DynamoDB table (the classic way) | `use_lockfile = true` (modern) |
|---|---|---|
| Needs | an extra DynamoDB table with key `LockID` | nothing extra |
| Terraform version | any | 1.10+ (experimental), GA in 1.11 |
| Status | **deprecated** in recent Terraform | the recommended choice |

You'll still meet the DynamoDB setup in existing code and interviews:

```hcl
backend "s3" {
  # ...
  dynamodb_table = "terraform-locks"   # legacy locking
}
```

For a migration you can enable **both** for a while, then drop DynamoDB.

**Locks get stuck** if a run is killed (CI timeout, laptop closed):

```
Error: Error acquiring the state lock
Lock Info:
  ID:        6d2f1c4e-...
  Operation: OperationTypeApply
  Who:       runner@ci-1234
  Created:   2026-09-29 10:14:03
```

First make **sure** that run is really dead, then:

```bash
terraform force-unlock 6d2f1c4e-...
```

Unlocking while another apply is really running is how states get corrupted.

### Step 4: the chicken-and-egg: who creates the state bucket?

The backend bucket must exist **before** `terraform init`, so Terraform
can't create it using that same backend. The usual solutions:

1. **A small bootstrap configuration** with **local state** that creates
   only the bucket (and optionally the lock table), applied once. Its tiny
   state can then be migrated into the bucket it created.
2. Create the bucket with the AWS CLI or CloudFormation, once per account.
3. A platform team's account vending process creates it.

A bootstrap config looks like this:

```hcl
resource "aws_s3_bucket" "state" {
  bucket = "acme-terraform-state-111122223333"
  lifecycle { prevent_destroy = true }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }      # every state version kept → undo
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "aws:kms" }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

**Versioning is your undo button.** If a state is corrupted or badly
edited, you restore the previous object version in S3.

(This repo has a real bootstrap example in
[`../terraform_practice/000_bootstrap_state_bucket/`](../terraform_practice/000_bootstrap_state_bucket/).)

### Step 5: who can touch the state? (IAM)

A minimal policy for a role that runs Terraform for **one** state:

```json
{
  "Statement": [
    { "Effect": "Allow", "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::acme-terraform-state-111122223333" },
    { "Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::acme-terraform-state-111122223333/notes-app/dev/*" },
    { "Effect": "Allow", "Action": "s3:DeleteObject",
      "Resource": "arn:aws:s3:::acme-terraform-state-111122223333/notes-app/dev/*.tflock" }
  ]
}
```

Scoping by **key prefix** means the dev pipeline physically can't read or
overwrite prod's state. Add KMS permissions if you use a customer-managed key.

### Step 6: backend blocks can't use variables

```hcl
backend "s3" {
  bucket = var.state_bucket     # ❌ Error: Variables may not be used here.
}
```

The backend is needed **before** anything else is evaluated. Terraform
has to know where the state is before it can even read variables (lesson
18 explains the evaluation order). The solution is **partial configuration**:
leave values out of the block and pass them to `init`:

```hcl
terraform {
  backend "s3" {}      # empty, or only the common settings
}
```

```bash
terraform init -backend-config=backend/dev.hcl
```

```hcl
# backend/dev.hcl
bucket       = "acme-terraform-state-111122223333"
key          = "notes-app/dev/terraform.tfstate"
region       = "ap-south-1"
use_lockfile = true
encrypt      = true
```

That's how one codebase uses a different state per environment.
Switching environments in the same folder needs `terraform init -reconfigure`.

### Step 7: reading another configuration's outputs

Big systems are split into several states (lesson 16): a **network** state
creates the VPC, and the **app** state needs the VPC ID. There are two ways.

**Option A: `terraform_remote_state`.** Read the other state's outputs:

```hcl
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = "acme-terraform-state-111122223333"
    key    = "notes-app/dev/network/terraform.tfstate"
    region = "ap-south-1"
  }
}

resource "aws_instance" "web" {
  subnet_id = data.terraform_remote_state.network.outputs.public_subnet_ids[0]
}
```

Downside: the reader needs **read access to the entire other state**,
secrets included, and the two configs are tightly coupled.

**Option B: data sources or a parameter store** (usually preferred):

```hcl
# network config publishes:
resource "aws_ssm_parameter" "vpc_id" {
  name  = "/notes-app/dev/network/vpc_id"
  type  = "String"
  value = aws_vpc.main.id
}

# app config reads:
data "aws_ssm_parameter" "vpc_id" { name = "/notes-app/dev/network/vpc_id" }
# or simply look it up by tag:
data "aws_vpc" "main" { tags = { Name = "notes-app-dev" } }
```

The only coupling is a name or tag, and nobody needs access to anyone
else's state.

### Step 8: other backends (for reference)

| Backend | Where state lives | Locking |
|---|---|---|
| `local` | a file on disk (the default) | local file lock only |
| **`s3`** | S3 object | S3 lockfile (or legacy DynamoDB) |
| `azurerm` | Azure Blob Storage | blob lease |
| `gcs` | Google Cloud Storage | built in |
| **HCP Terraform / Terraform Enterprise** (`cloud` block) | HashiCorp's service | built in, plus a UI, runs, and policies |
| `kubernetes`, `pg`, `consul`, `http` | various | varies |

---

## ⚠️ Common mistakes

- **The same `key` for two environments.** Dev and prod then overwrite each other's state. Make the key include the environment.
- **No versioning on the state bucket.** There's no undo when state gets corrupted.
- **`force-unlock` while another apply is running.** Check first.
- **Trying `bucket = var.x` in a backend.** Use partial config (`-backend-config`).
- **`terraform_remote_state` everywhere.** It couples states and exposes secrets. Prefer SSM parameters or tag lookups.
- **Forgetting `init -reconfigure`** when switching backend configs in the same folder, so you apply against the wrong state.

---

## 🎤 Interview corner

**Q: How do you set up remote state on AWS?**

> An S3 bucket with versioning, encryption (ideally SSE-KMS), a public
> access block, and restrictive IAM, created by a separate bootstrap
> configuration. Each configuration has a `backend "s3"` block with a
> unique `key` per state and locking. On Terraform 1.10+ that's
> `use_lockfile = true` (S3 native locking using conditional writes).
> Older setups use a DynamoDB table, which is now deprecated.
> Environment-specific values are passed with `-backend-config`.

**Q: Why can't you use variables in the backend block?**

> The backend is initialised before the configuration is evaluated,
> because Terraform needs to know where state lives before it can
> process variables, and variables could themselves depend on state.
> Backend values must be static, or supplied through partial
> configuration at `init` time.

**Q: What happens if two engineers apply at the same time?**

> With locking, the second run fails to acquire the lock (or waits with
> `-lock-timeout`) until the first finishes. Without locking, both read
> the same state, both write, and the last write wins: changes and
> resources get lost from state, and you can end up with orphans or corruption.

**Q: `terraform_remote_state` vs data sources for cross-stack values?**

> `terraform_remote_state` reads another state's outputs. It's simple, but
> it requires read access to the whole state (including secrets) and
> tightly couples the stacks. Publishing values to SSM Parameter Store, or
> discovering resources via data sources by tag, keeps stacks decoupled
> and permissions minimal.

---

## ✅ Check yourself

1. What must be unique for every state that shares a bucket?
2. Why enable versioning on the state bucket?
3. Name two ways to pass the bucket name to a backend without hard-coding it.
4. Your CI job was killed mid-apply and now every run says the state is locked. What do you do, step by step?

<details><summary>Answers</summary>

1. The `key`.
2. Every state write becomes a version you can restore after corruption or a bad manual change.
3. `terraform init -backend-config=file.hcl`, or `-backend-config="bucket=..."` key/value pairs. (The `TF_CLI_ARGS_init` environment variable is a third way.)
4. Confirm no Terraform process is still running for that state (check CI), read the lock ID from the error, run `terraform force-unlock <ID>`, then `terraform plan` to see what the half-finished apply left behind, and fix forward.

</details>

➡️ **Next:** [13 · Import, drift, and refactoring](13-import-drift-refactoring.md)

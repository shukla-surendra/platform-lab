# 19 · Security and secrets

## 🎯 Goal

Keep credentials out of code, keep secrets out of state where possible
(and protect the state where not), give Terraform least-privilege access,
and catch insecure configuration before it's deployed.

---

## 🧠 Mental model: four doors to lock

```
 1. HOW Terraform gets into AWS          → credentials (no static keys)
 2. WHAT Terraform is allowed to do      → IAM for the Terraform role
 3. WHERE secrets end up                 → state, plan files, logs
 4. WHAT Terraform builds                → insecure resources (public buckets, open SGs)
```

Most Terraform security incidents come through door 3 (secrets in state
or Git) or door 4 (a public S3 bucket shipped by code).

---

## 🛠 Walkthrough

### Step 1: door 1: credentials without long-lived keys

| Where Terraform runs | Use | Never |
|---|---|---|
| your laptop | `aws sso login` + `AWS_PROFILE`, or `aws-vault` | access keys in `~/.aws/credentials` that never expire |
| CI (GitHub Actions, GitLab) | **OIDC federation** → assume a role (lesson 21) | access keys stored as CI secrets |
| inside AWS (CodeBuild, EC2, ECS) | the compute's IAM role | keys in environment variables |
| any | `assume_role` in the provider for cross-account work | keys in `.tf` files |

**OIDC** in one sentence: CI proves its identity to AWS with a short-lived,
signed token ("I'm repo `acme/infra`, branch `main`"), and AWS exchanges it
for temporary credentials. There's nothing to leak and nothing to rotate.

### Step 2: door 2: least privilege for Terraform itself

Terraform often runs with `AdministratorAccess`. That's convenient, and
dangerous. Better:

- **Separate roles for plan and apply.** PR pipelines get a **read-only**
  role (plus read on state). Only `main` gets the apply role.
- **Scope per layer**: the app pipeline can manage ECS, ALB, and app IAM
  roles, but not VPCs or the organisation's IAM.
- **Permission boundaries**: if Terraform creates IAM roles, require a
  permission boundary on them, so Terraform can't mint a role more
  powerful than itself (a classic privilege-escalation path).
- **Deny guard rails** with SCPs at the organisation level (e.g. nobody may
  disable CloudTrail or delete the state bucket).

### Step 3: door 3: why secrets end up in state

State stores **every attribute** of every resource (lesson 11). So if you
write:

```hcl
variable "db_password" { sensitive = true }

resource "aws_db_instance" "main" {
  password = var.db_password           # ← stored in state in PLAIN TEXT
}
```

the password is in `terraform.tfstate` and in any saved plan file.
`sensitive = true` hides it **on screen only**.

Here are your options, **best first**.

**Option 1: let AWS own the secret (no secret in Terraform at all).**

```hcl
resource "aws_db_instance" "main" {
  identifier                  = "notes-prod"
  engine                      = "postgres"
  instance_class              = "db.t4g.medium"
  allocated_storage           = 20
  username                    = "notes_admin"
  manage_master_user_password = true      # RDS creates + rotates it in Secrets Manager
}

# the app reads the secret at runtime, via the ARN:
output "db_secret_arn" {
  value = aws_db_instance.main.master_user_secret[0].secret_arn
}
```

Terraform only ever knows the secret's **ARN**, not its value. Many AWS
services support this pattern (RDS, Aurora, Redshift, DocumentDB).

**Option 2: ephemeral values and write-only arguments (Terraform 1.10 / 1.11+).**

Terraform added two features for exactly this problem:

- **Ephemeral resources** (`ephemeral` blocks, 1.10+) produce values that
  are **never written to state or plan files**.
- **Write-only arguments** (1.11+, named like `password_wo`) accept a
  value, send it to the API, and **don't store it**. A companion
  `…_wo_version` number tells Terraform when to send a new value, since
  it can't compare against a stored one.

```hcl
ephemeral "random_password" "db" {          # generated, never stored
  length  = 24
  special = true
}

resource "aws_secretsmanager_secret" "db" {
  name = "notes/prod/db-password"
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id                = aws_secretsmanager_secret.db.id
  secret_string_wo         = ephemeral.random_password.db.result
  secret_string_wo_version = 1              # bump to rotate
}
```

> Which resources support `_wo` arguments depends on your provider
> version. Check the resource's docs. It's the direction Terraform is
> moving, and knowing it scores points in interviews.

**Option 3: fetch at runtime, not deploy time.** Store secrets in Secrets
Manager or SSM Parameter Store (created by a separate secure process), give
the *application's* IAM role permission to read them, and pass only the
**name or ARN** through Terraform.

**Option 4, when a secret must be in state:** accept it, and lock down the
state: an encrypted bucket (SSE-KMS with a restricted key), versioning,
tight IAM, and no human read access except break-glass.

### Step 4: secrets in other places

| Leak path | Prevention |
|---|---|
| `terraform.tfvars` committed | never put secrets in tfvars; use `TF_VAR_x` from a CI secret, or Option 1–3 |
| saved plan files (`tfplan`) | treat as secrets; short-lived CI artifacts only |
| `TF_LOG=DEBUG` logs | contain request bodies; never upload them publicly |
| outputs | Terraform forces `sensitive = true`; still visible via `output -json` |
| `user_data` scripts | stored in EC2 metadata, visible to anyone with `DescribeInstanceAttribute`; fetch secrets inside the script from Secrets Manager instead |
| Git history | add `gitleaks` / `trufflehog` as a pre-commit hook and in CI |

### Step 5: door 4: don't build insecure things

Make the **secure option the default** in your modules:

```hcl
resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "aws:kms" }
  }
}
```

And **scan** every change automatically:

| Tool | What it does |
|---|---|
| **Checkov** | hundreds of built-in policies (public S3, open SGs, unencrypted RDS…) on code or plan JSON |
| **Trivy** (`trivy config .`) | config misconfiguration scanning; absorbed the former **tfsec** |
| **KICS**, **Terrascan** | similar scanners |
| **tflint** + AWS ruleset | not security as such, but catches invalid values (instance types, etc.) |

```bash
checkov -d .                       # scan the code
terraform show -json tfplan > plan.json && checkov -f plan.json   # scan the PLAN (sees computed values)
trivy config .
```

When a rule doesn't apply, suppress it **in code with a reason**, so the
exception is reviewed:

```hcl
resource "aws_s3_bucket" "public_site" {
  # checkov:skip=CKV_AWS_20: This bucket intentionally hosts a public static website
  bucket = "notes-public-site"
}
```

### Step 6: supply-chain safety

- **Pin providers** (`~>` + the committed lock file with hashes).
- **Pin modules** to a tag, or better, a **commit SHA** for third-party Git modules (tags can be moved).
- Review what a public module does before using it: it runs with *your* credentials.
- Large companies mirror providers and modules internally (`provider_installation` in the CLI config, or a private registry).

---

## ⚠️ Common mistakes

- **Believing `sensitive = true` is encryption.**
- **Admin credentials in CI** shared by every pipeline and every branch.
- **Letting PR branches run `apply`**, or assume the apply role.
- **Generating passwords with `random_password` (non-ephemeral)** and thinking they're secret. The result is in state.
- **Suppressing scanner findings globally** instead of per resource with a reason.

---

## 🎤 Interview corner

**Q: How do you handle secrets in Terraform?**

> First, avoid having Terraform know them: use AWS-managed secrets like
> RDS `manage_master_user_password`, or have applications read Secrets
> Manager at runtime with Terraform only passing ARNs. On Terraform 1.10+,
> use ephemeral resources and write-only arguments, so values never reach
> state or plan files. When a secret must be in state, protect the state:
> an encrypted S3 backend with KMS, versioning, least-privilege access.
> `sensitive = true` only redacts CLI output. And never commit tfvars or
> state with secrets. Scan Git with gitleaks.

**Q: How should CI authenticate to AWS for Terraform?**

> With OIDC federation: the CI provider issues a signed identity token,
> and an IAM role trusts the OIDC provider with conditions on repo, branch,
> or environment. The job assumes it for short-lived credentials. PR jobs
> get a read-only plan role, and only protected branches or environments
> can assume the apply role. No long-lived access keys.

**Q: How do you prevent Terraform from deploying insecure resources?**

> Secure defaults in shared modules, static analysis (Checkov, Trivy,
> tflint) on code and plan JSON in CI, policy-as-code gates (OPA/Conftest
> or Sentinel) that block non-compliant plans, and organisational
> guard rails (SCPs, permission boundaries) as the last line of defence.

---

## ✅ Check yourself

1. Where does a `password` argument's value end up, besides AWS?
2. What does `manage_master_user_password = true` change about secret handling?
3. What's the difference between an ephemeral resource and a write-only argument?
4. Why give PR pipelines a different AWS role than main-branch pipelines?

<details><summary>Answers</summary>

1. In the state file and in saved plan files, in plain text.
2. RDS generates, stores, and rotates the password in Secrets Manager. Terraform only knows the secret's ARN, never the value.
3. An ephemeral resource *produces* a value that's never persisted. A write-only argument *accepts* a value and sends it to the API without persisting it. They're used together.
4. PR code isn't reviewed yet. A read-only plan role means a malicious or buggy PR can't change infrastructure. Only merged, reviewed code can use the apply role.

</details>

➡️ **Next:** [20 · Testing and policy](20-testing-and-policy.md)

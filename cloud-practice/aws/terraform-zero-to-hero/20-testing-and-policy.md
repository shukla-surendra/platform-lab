# 20 · Testing and policy

## 🎯 Goal

Build confidence in Terraform code the way you would in application code:
fast static checks, unit-style tests with `terraform test`, runtime
assertions with `check` blocks, integration tests, and **policy as code**
that blocks non-compliant plans.

---

## 🧠 Mental model: the testing pyramid for infrastructure

```
                         ▲  slow, costly, most realistic
            ┌────────────┴────────────┐
            │  integration / e2e       │  real apply in a sandbox account, then destroy
            │  (terraform test apply,  │  (Terratest, terraform test with command=apply)
            │   Terratest)             │
          ┌─┴──────────────────────────┴─┐
          │  plan-level tests & policy    │  terraform test (plan, mocks), OPA/Sentinel on plan JSON
        ┌─┴───────────────────────────────┴─┐
        │  static checks                     │  fmt · validate · tflint · checkov/trivy
        └────────────────────────────────────┘
                         ▼  fast, free, run on every commit
```

Run the bottom layers on every commit. Run the top layer on module
changes or nightly.

---

## 🛠 Walkthrough

### Step 1: static checks (seconds, free)

```bash
terraform fmt -check -recursive      # formatting
terraform init -backend=false        # init without touching real state (fine for CI checks)
terraform validate                   # types, references, required arguments
tflint --init && tflint              # linting + provider-aware rules
checkov -d . / trivy config .        # security (lesson 19)
```

**tflint** catches things `validate` can't, because it knows AWS:

```hcl
resource "aws_instance" "web" {
  instance_type = "t3.mircro"      # validate: fine (it's a string). tflint: ❌ invalid instance type
}
```

It also flags unused variables, deprecated syntax, and missing `required_version`.
Configure it with `.tflint.hcl` and enable the AWS ruleset plugin.

**pre-commit** makes all of this automatic before each commit
(`antonbabenko/pre-commit-terraform` bundles fmt, validate, tflint,
checkov, and terraform-docs).

### Step 2: input validation and conditions (built into the code)

You already met these:
- `validation` blocks on variables (lesson 07): reject bad input.
- `precondition` / `postcondition` (lesson 09): assert assumptions and results.

They're tests that run **every time**, in every environment, for free.

### Step 3: `terraform test`, the native test framework (1.6+)

Tests live in `*.tftest.hcl` files (usually in `tests/`). Each file has
one or more **`run` blocks**, and each run executes a `plan` or `apply`
and checks **assertions**.

Testing our `modules/network` module:

```hcl
# modules/network/tests/network.tftest.hcl

variables {                       # defaults for every run in this file
  name     = "test"
  cidr     = "10.0.0.0/16"
  az_count = 2
}

run "creates_one_private_subnet_per_az" {
  command = plan                  # plan only: fast, nothing created

  assert {
    condition     = length(aws_subnet.private) == 2
    error_message = "Expected 2 private subnets."
  }

  assert {
    condition     = alltrue([for s in aws_subnet.private : !s.map_public_ip_on_launch])
    error_message = "Private subnets must not assign public IPs."
  }
}

run "rejects_invalid_cidr" {
  command = plan

  variables {
    cidr = "not-a-cidr"
  }

  expect_failures = [var.cidr]    # the TEST PASSES if this variable's validation fails
}
```

```bash
cd modules/network
terraform init
terraform test
# tests/network.tftest.hcl... in progress
#   run "creates_one_private_subnet_per_az"... pass
#   run "rejects_invalid_cidr"... pass
# Success! 2 passed, 0 failed.
```

Key features:

| Feature | What it gives you |
|---|---|
| `command = plan` | fast checks of the planned values, no AWS resources |
| `command = apply` (the default) | **real** resources in the test account, **destroyed automatically** after the file finishes |
| `expect_failures` | test that validations and conditions fire when they should |
| run blocks share state in order | a later run can check the result of an earlier one; `run.<name>.<output>` reads earlier outputs |
| `module { source = "./tests/setup" }` in a run | create prerequisites (e.g. a VPC) with a helper module |
| **`mock_provider "aws" {}`** (1.7+) | fake the provider entirely: **no credentials, no AWS**; computed values get generated fakes |
| `override_resource` / `override_data` | pin specific fake values (e.g. an AMI data source's ID) |

With a mock provider, even `command = apply` runs without touching AWS,
which is great for fast CI on every PR:

```hcl
mock_provider "aws" {
  override_data {
    target = data.aws_availability_zones.available
    values = { names = ["ap-south-1a", "ap-south-1b", "ap-south-1c"] }
  }
}
```

### Step 4: `check` blocks: continuous assertions (1.5+)

A `check` block asserts something about **running infrastructure**, and
it's evaluated on every `plan` and `apply`. A failure is a **warning**, not
an error, so it reports problems without blocking changes:

```hcl
check "app_is_healthy" {
  data "http" "health" {                        # a "scoped" data source, only for this check
    url = "http://${aws_lb.app.dns_name}/health"
  }

  assert {
    condition     = data.http.health.status_code == 200
    error_message = "notes-app health endpoint is not returning 200."
  }
}
```

Combine it with scheduled drift-detection plans (lesson 21) and you get
lightweight monitoring of "is what we deployed actually working?"

| | `validation` | `precondition`/`postcondition` | `check` |
|---|---|---|---|
| About | an input variable | one resource / data / output | anything, including external endpoints |
| On failure | error | error (blocks the resource) | **warning** |
| Typical use | bad input | wrong assumptions | health and compliance signals |

### Step 5: integration tests with Terratest

**Terratest** (Go) applies real infrastructure and then tests it *from
outside*: HTTP calls, SSH, AWS API queries.

```go
func TestNotesApp(t *testing.T) {
    opts := &terraform.Options{TerraformDir: "../examples/complete"}
    defer terraform.Destroy(t, opts)            // always clean up
    terraform.InitAndApply(t, opts)

    url := terraform.Output(t, opts, "app_url")
    http_helper.HttpGetWithRetry(t, url+"/health", nil, 200, "ok", 30, 10*time.Second)
}
```

Use it for modules where "it planned fine" isn't enough, like "the ALB
actually serves traffic". Run it in a **dedicated sandbox account**, with
unique names per test run, and a nightly cleanup job (e.g. `aws-nuke`)
for anything a crashed test left behind.

### Step 6: policy as code: guard rails on the plan

Tests check that *your module* works. **Policies** check that *any*
change follows the organisation's rules, whoever wrote it. They run on the
**plan JSON**, so they see real computed values:

```bash
terraform plan -out=tfplan
terraform show -json tfplan > plan.json
```

**OPA / Conftest** (open source, the Rego language):

```rego
# policy/s3.rego
package main

deny contains msg if {
  rc := input.resource_changes[_]
  rc.type == "aws_s3_bucket_public_access_block"
  rc.change.after.block_public_acls == false
  msg := sprintf("%s must block public ACLs", [rc.address])
}

deny contains msg if {
  rc := input.resource_changes[_]
  rc.mode == "managed"
  rc.change.actions[_] == "create"
  not rc.change.after.tags_all.Owner
  msg := sprintf("%s is missing the Owner tag", [rc.address])
}
```

```bash
conftest test plan.json --policy policy/
# FAIL - plan.json - main - aws_s3_bucket.logs is missing the Owner tag
```

**Sentinel** is HashiCorp's policy language, built into HCP Terraform
and Terraform Enterprise, with advisory, soft-mandatory, and
hard-mandatory enforcement levels. **Checkov custom policies** (YAML or
Python) are a third option.

Typical policies: required tags, allowed regions, allowed instance
families, no public S3 or `0.0.0.0/0` on SSH, encryption on, and "no
deletes of `aws_db_instance` without approval".

### Step 7: cost as a check

**Infracost** reads the plan and comments on the PR:
"this change adds $412/month (3 × m6i.xlarge)". It's cheap to add, and it
catches the "oops, wrong instance size" class of mistakes before finance does.

### Step 8: a sensible testing setup for `notes-app`

| When | What runs |
|---|---|
| pre-commit (laptop) | fmt, validate, tflint, gitleaks |
| every PR | the above + checkov/trivy + `terraform test` (mocks) + plan + conftest + infracost |
| module change | + `terraform test` with real apply in a sandbox account |
| nightly | drift detection plans + `check` blocks + sandbox cleanup |

---

## ⚠️ Common mistakes

- **Only testing with `validate`**, which can't know if a value is valid for AWS.
- **Real-apply tests in a shared or prod account.** Always use a dedicated sandbox.
- **Tests without cleanup.** `terraform test` destroys automatically. Terratest needs `defer Destroy`, plus a nightly sweep.
- **Policies on HCL source instead of plan JSON.** They miss module-generated and computed values.
- **Using `check` blocks as hard gates.** They only warn. Use conditions or policies to block.

---

## 🎤 Interview corner

**Q: How do you test Terraform code?**

> In layers. Static checks on every commit (fmt, validate, tflint,
> Checkov/Trivy). Unit-style tests with `terraform test`: plan-level
> assertions, `expect_failures` for validations, and mock providers so
> they run without credentials. Integration tests that apply real
> infrastructure in a sandbox account, via `terraform test` with apply or
> Terratest, and verify behaviour externally. Plus policy-as-code on the
> plan JSON in CI, and `check` blocks for ongoing health assertions.

**Q: What's the difference between `check` blocks and preconditions?**

> Preconditions and postconditions are tied to a specific resource, data
> source, or output, and **fail** the run when violated. `check` blocks
> are standalone, can use their own scoped data sources, and only
> produce **warnings**, so they report health or compliance without
> blocking operations.

**Q: How do you enforce organisational standards across many teams' Terraform?**

> Policy as code evaluated on the plan JSON in the pipeline, using
> OPA/Conftest or Sentinel in HCP Terraform, with rules like required
> tags, allowed regions and instance types, encryption, and no public
> access. Combined with shared modules that embed the standards, scanners,
> and organisation-level guard rails like SCPs.

---

## ✅ Check yourself

1. Name one error tflint catches that `terraform validate` doesn't.
2. In a `.tftest.hcl` file, how do you test that a bad `cidr` input is rejected?
3. What does `mock_provider "aws" {}` let you do?
4. Why run policies against `terraform show -json` output rather than `.tf` files?

<details><summary>Answers</summary>

1. An invalid instance type like `t3.mircro` (also unused variables, deprecated syntax…).
2. A `run` block with `variables { cidr = "bad" }` and `expect_failures = [var.cidr]`.
3. Run tests (even `apply`) without AWS credentials or real resources, with fake computed values that you can override.
4. The plan contains the fully evaluated result, including module internals, variable values, and computed attributes. Source files don't.

</details>

➡️ **Next:** [21 · CI/CD and team workflow](21-cicd-and-team-workflow.md)

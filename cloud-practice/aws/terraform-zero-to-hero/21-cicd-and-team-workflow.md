# 21 · CI/CD and team workflow

## 🎯 Goal

Run Terraform the way teams do: every change through a pull request,
plans visible to reviewers, applies only from CI with exactly the
reviewed plan, safe credentials via OIDC, and drift detected automatically.

---

## 🧠 Mental model: the GitOps loop

```
  developer          pull request                    merge to main
  ─────────▶  ┌──────────────────────────┐  approve ┌─────────────────────────┐
  push branch │ CI: fmt/validate/lint/scan│ ───────▶ │ CI: plan (again) → apply│
              │ CI: terraform plan        │          │ (protected environment, │
              │ bot comments the plan     │          │  manual approval for    │
              │ humans review CODE + PLAN │          │  prod)                  │
              └──────────────────────────┘          └─────────────────────────┘
                                                               │
                         nightly: plan -detailed-exitcode ◀────┘  (drift detection)
```

**Rule:** humans never run `apply` against shared environments from
laptops. The pipeline is the only thing with apply credentials.

---

## 🛠 Walkthrough

### Step 1: why reviewers need the *plan*, not just the code

A 1-line code change can produce a 50-resource plan (a changed module
default, a provider upgrade, a `count` shifting). **The plan is the real
diff of your infrastructure.** Reviewers must see it, especially lines
with `destroy` or `replace`.

### Step 2: OIDC from GitHub Actions to AWS (no stored keys)

One-time setup in AWS:

1. Create an **IAM OIDC identity provider** for `token.actions.githubusercontent.com`.
2. Create roles that trust it, with **conditions** on who may assume them:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::111122223333:oidc-provider/token.actions.githubusercontent.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
      "StringLike":   { "token.actions.githubusercontent.com:sub": "repo:acme/notes-infra:environment:prod" }
    }
  }]
}
```

The `sub` condition is the security. This role can only be assumed by
jobs in repo `acme/notes-infra` running in the GitHub **environment**
`prod`, which you protect with required reviewers. Create a separate,
read-only **plan role** whose `sub` allows `repo:acme/notes-infra:pull_request`.

(These roles are themselves managed by Terraform, in the `bootstrap` layer.)

### Step 3: the pipeline

```yaml
# .github/workflows/terraform.yml
name: terraform
on:
  pull_request:
    paths: ["live/prod/app/**", "modules/**"]
  push:
    branches: [main]
    paths: ["live/prod/app/**", "modules/**"]

permissions:
  id-token: write          # needed for OIDC
  contents: read
  pull-requests: write     # to comment the plan

concurrency:
  group: terraform-prod-app          # never two runs on the same state at once
  cancel-in-progress: false

defaults:
  run:
    working-directory: live/prod/app

jobs:
  plan:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
        with: { terraform_version: "1.11.4" }       # pinned, same as required_version
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::333333333333:role/terraform-plan   # read-only
          aws-region: ap-south-1
      - run: terraform fmt -check -recursive
      - run: terraform init -input=false
      - run: terraform validate
      - run: terraform plan -input=false -lock-timeout=5m -out=tfplan
      - run: terraform show -no-color tfplan > plan.txt
      # post plan.txt as a PR comment (e.g. with actions/github-script or a marketplace action)

  apply:
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    environment: prod                  # ← required reviewers + OIDC sub "environment:prod"
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
        with: { terraform_version: "1.11.4" }
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::333333333333:role/terraform-apply
          aws-region: ap-south-1
      - run: terraform init -input=false
      - run: terraform plan -input=false -lock-timeout=5m -out=tfplan
      - run: terraform apply -input=false tfplan          # exactly the plan just made
```

The important details:

| Detail | Why |
|---|---|
| `concurrency` group per state | two merges can't apply to the same state simultaneously |
| pinned Terraform version | same version as developers and `required_version` |
| `-input=false` | fail instead of waiting forever for a prompt |
| `-lock-timeout` | wait briefly for a lock instead of failing immediately |
| plan role vs apply role | PR code can never change infrastructure |
| `environment: prod` | manual approval gate + scopes the OIDC trust |
| `paths` filters | only run for the state that changed (monorepo) |

### Step 4: merge-then-apply vs apply-then-merge

| | Merge, then apply (above) | Apply from the PR, then merge (Atlantis style) |
|---|---|---|
| `main` means | "desired state" (maybe not applied yet) | "what's actually deployed" |
| If apply fails | `main` has unapplied code; fix with another PR | the PR stays open; fix and re-apply before merging |
| Stale plans | the plan is re-made after merge, so the reviewer saw a *similar* plan | the plan applied is exactly the one reviewed |
| Locking | concurrency groups | the tool locks the state per PR |

Both are fine and widely used. Be ready to discuss the trade-off in interviews.

### Step 5: promotion across environments

```
 PR merged ─▶ apply dev ─▶ (automatic)
            ─▶ apply staging ─▶ (automatic, after dev succeeds + smoke tests)
            ─▶ apply prod ─▶ (manual approval on the environment)
```

With **versioned modules**, promotion becomes "bump the module version in
`live/dev`, then `live/staging`, then `live/prod`", with three small PRs,
each reviewed with its own plan.

### Step 6: drift detection

A scheduled job plans every state and alerts when reality differs from the code:

```yaml
on:
  schedule: [{ cron: "0 3 * * *" }]     # 03:00 daily
jobs:
  drift:
    # ... checkout, setup, OIDC with the READ-ONLY role, init ...
    steps:
      - run: |
          set +e
          terraform plan -input=false -detailed-exitcode -lock=false > plan.txt
          code=$?
          if [ $code -eq 2 ]; then echo "DRIFT DETECTED"; cat plan.txt; exit 1; fi   # alert
          exit $code
```

`-detailed-exitcode`: **0** = no changes, **1** = error, **2** = changes
present. (`-lock=false` is acceptable here because the job only reads.)

### Step 7: platforms that do this for you

| Tool | Model |
|---|---|
| **Atlantis** | self-hosted bot: comment `atlantis plan` / `atlantis apply` on the PR; locks per PR |
| **HCP Terraform** (formerly Terraform Cloud) / **Terraform Enterprise** | runs in HashiCorp's (or your) runners, remote state, VCS-triggered plans, Sentinel/OPA policies, private registry, cost estimation, RBAC |
| **Spacelift**, **env0**, **Scalr**, **Terrateam** | commercial alternatives with stacks, policies, drift detection, and dependency ordering |
| plain CI (GitHub Actions, GitLab CI, CodePipeline+CodeBuild) | full control, more to build yourself |

### Step 8: team conventions that prevent incidents

- Pin the Terraform version (`required_version` + `.terraform-version` for `tfenv`, or `mise`).
- One state = one pipeline = one concurrency lock.
- CODEOWNERS per directory, and 2 approvals for prod.
- Never `-target` in pipelines. Never `force-unlock` without checking.
- Read-only console access in prod, so drift is rare.
- A runbook for "apply failed halfway": plan again, understand, fix forward.

---

## ⚠️ Common mistakes

- **Applying from laptops** "just this once".
- **Long-lived AWS keys in CI secrets.** Use OIDC.
- **The same role for PR plans and main applies.**
- **No concurrency control**, which means lock errors, or worse, interleaved applies with local backends.
- **Applying a plan made hours ago** after other merges. Re-plan (or rely on the saved plan's staleness check).
- **Reviewing code without the plan.**

---

## 🎤 Interview corner

**Q: Describe a Terraform CI/CD pipeline you'd build.**

> On pull request: fmt, validate, tflint, security scans, `terraform test`,
> then `plan -out` with a read-only role assumed via OIDC, posting the plan
> and cost estimate to the PR, and policy checks on the plan JSON. After
> review and merge: a job in a protected environment with required
> approvers assumes the apply role, re-plans, and applies that saved plan.
> Concurrency is one run per state. Promotion goes dev → staging → prod.
> Scheduled `plan -detailed-exitcode` jobs catch drift. There are no
> long-lived keys, and no applies from laptops.

**Q: How do you guarantee that what's applied is what was reviewed?**

> Save the plan (`plan -out`) and apply that file. Terraform refuses a
> saved plan if the state changed since it was created. In apply-from-PR
> workflows (Atlantis), the reviewed plan is the one applied. In
> merge-then-apply, the post-merge plan should be reviewed or gated,
> especially for destroys, which policies can block.

**Q: What does `-detailed-exitcode` return?**

> 0 for no changes, 1 for errors, 2 for a successful plan with changes.
> It's used for drift detection and for conditional pipeline steps.

---

## ✅ Check yourself

1. Why does the apply job use a GitHub *environment*?
2. What stops two merges from applying to the same state at the same time?
3. A nightly job returns exit code 2. What happened?
4. Name one advantage of apply-before-merge.

<details><summary>Answers</summary>

1. It adds manual approval (required reviewers), and the OIDC trust policy's `sub` is scoped to that environment, so only approved runs get apply credentials.
2. The workflow `concurrency` group, and the state lock as a backstop.
3. The plan succeeded and found changes: drift (or unapplied code on main).
4. `main` always reflects what's actually deployed, and the reviewed plan is exactly the one applied (also: failed applies don't leave unapplied code on `main`).

</details>

➡️ **Next:** [22 · Troubleshooting](22-troubleshooting.md)

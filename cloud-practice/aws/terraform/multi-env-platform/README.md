# Multi-environment Terraform on AWS (dev / qa / stage / prod)

A reference layout for how teams manage one codebase across environments with a
real pipeline. Deliberately small (VPC + S3) so the *structure* is the lesson.

```
bootstrap/        run once per account: state bucket + GitHub OIDC deploy roles
modules/          reusable building blocks (network, storage) – no env knowledge
envs/<env>/       thin root module per env: backend + tfvars + module calls
pipeline/         GitHub Actions workflows (copy to repo-root .github/workflows/)
```

## Key ideas

| Concern | How it's handled |
|---|---|
| Same code, different envs | Shared `modules/`; each env differs only in `terraform.tfvars` (CIDR, NAT on/off, retention, force_destroy) |
| Isolation / blast radius | Directory per env => separate state key (`dev/terraform.tfstate` …) and separate pipeline job |
| State | S3, versioned, KMS-encrypted, native lockfile (`use_lockfile`, TF ≥ 1.10) |
| Credentials | No static keys. GitHub OIDC -> role per env, trust pinned to the GitHub *Environment* |
| Change control | PR: fmt, tflint, trivy, `plan` for all envs. Merge: apply dev → qa → stage → prod |
| Approvals | GitHub Environment required reviewers on `stage` and `prod` |
| Cost control | NAT gateway only in stage/prod; dev/qa buckets are `force_destroy` |

Why directories, not workspaces? Workspaces share one backend/config and make it easy
to run `apply` in the wrong env. Directories make the target explicit and let
prod diverge (separate account, different provider settings) when needed.

## Try it

```bash
# 0. offline sanity check – no AWS needed
make validate-all

# 1. bootstrap (local state, once)
cd bootstrap
terraform init
terraform apply -var state_bucket_name=<unique-name> -var github_repo=<owner/repo>

# 2. put the bucket name into envs/*/versions.tf (REPLACE_WITH_STATE_BUCKET)

# 3. deploy an env by hand (what the pipeline does)
make plan  ENV=dev
make apply ENV=dev
```

## Wiring the pipeline (GitHub)

1. Copy `pipeline/*.yml` to `.github/workflows/` at the repo root.
2. Create GitHub Environments: `dev qa stage prod` and `dev-plan qa-plan stage-plan prod-plan`.
3. In each, set variable `DEPLOY_ROLE_ARN` to that env's role from `bootstrap` output
   (plan envs may reuse the same role; the trust policy in bootstrap needs the
   `-plan` subject added, or use a separate read-only role — recommended).
4. Add required reviewers to `stage` and `prod`; protect `main` (PR + passing checks).

## What real production adds (next steps)

- **Separate AWS accounts per env** (prod isolated); one bootstrap per account.
- Least-privilege deploy policies instead of `PowerUserAccess`; read-only role for PR plans.
- Saved plan from PR reused at apply (so what was reviewed is what's applied).
- Module versioning (git tags / registry) so prod pins an older module version than dev.
- Drift detection (scheduled `plan`), Infracost, OPA/Conftest policy checks.

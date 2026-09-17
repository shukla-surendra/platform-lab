# Terraform: CodeCommit — the "source" stage of a CI/CD pipeline

Creates a single CodeCommit Git repository. This is the source stage that
`codebuild/` and `codepipeline/` reference. Kept as its own module so you
can study the source stage in isolation before wiring the full pipeline.

> ⚠️ **CodeCommit is closed to new AWS customers.** Accounts created after
> 2024-07-25 cannot create new CodeCommit repositories at all (existing
> repos in older accounts keep working). If `terraform apply` fails with
> an access-denied/not-available error here, that's why — use GitHub (or
> any Git host) as the source instead, and connect it to CodeBuild/
> CodePipeline via a **CodeStar Connection**
> (`aws_codestarconnections_connection`), which every module's README
> notes as the drop-in alternative source stage.

> Otherwise, **effectively free** — CodeCommit itself has no charge at
> this scale.

## What it creates

```
CodeCommit repository (empty by default)
  └── optional: one seeded commit (README.md), pushed via local git (seed_readme = true)
```

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pin + default tags |
| `variables.tf` | Repo name, default branch, seed toggle |
| `main.tf` | The repository, plus an optional `local-exec` seed commit |
| `outputs.tf` | Clone URLs + a `next_steps` runbook (credential helper setup) |

## Usage
```bash
cd aws/terraform/codecommit
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
terraform output next_steps
```

## Things to try (mini-labs)
1. Set up the credential helper (see `next_steps`), then `git clone` and push a real commit — watch it show up in the console under Commits.
2. Flip `seed_readme = true` and `apply` — Terraform itself pushes an initial commit via a `local-exec` provisioner (a deliberate, narrow exception to "Terraform shouldn't shell out"; CodeCommit has no API to create a file directly).
3. After a commit exists, run the `update-default-branch` command from `next_steps` and confirm in the console that "main" is now marked default.

## Deliberately minimal
- No branch protection / approval rules configured (see `aws_codecommit_approval_rule_template` if you want that next).
- The `local-exec` seed step assumes `git` and a working credential helper are on your PATH — it's off by default so a fresh `apply` never hangs waiting on a credential prompt.

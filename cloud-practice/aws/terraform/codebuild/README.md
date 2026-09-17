# Terraform: CodeBuild — the "build" stage of a CI/CD pipeline

Creates a standalone CodeBuild project with its own IAM role, CloudWatch
Logs group, and S3 artifact bucket. Defaults to `source_type = NO_SOURCE`
so it runs and produces a real build with **zero other modules** —
useful to see a green build before wiring in CodeCommit/GitHub/
CodePipeline.

> ⚠️ **Small ongoing charge only while builds run** — CodeBuild bills
> per build-minute, not per hour idle. An S3 bucket sits at near-zero
> cost. Run `terraform destroy` when done.

## What it creates

```
S3 bucket (build artifacts, versioned + encrypted) — unless artifact_bucket_name is passed in
CloudWatch Log Group (/aws/codebuild/<project>)
IAM Role (logs + artifact bucket + optional CodeCommit git-pull)
CodeBuild Project (source_type: NO_SOURCE | CODECOMMIT | GITHUB)
```

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pins + default tags |
| `variables.tf` | Source type, image/compute size, inline `buildspec` |
| `main.tf` | Artifact bucket, log group, IAM role/policy, the project |
| `outputs.tf` | Project ARN + a `next_steps` runbook |

## Usage
```bash
cd aws/terraform/codebuild
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
aws codebuild start-build --project-name "$(terraform output -raw project_name)"
aws logs tail "/aws/codebuild/$(terraform output -raw project_name)" --follow
terraform destroy
```

## Things to try (mini-labs)
1. Leave `source_type = NO_SOURCE`, `apply`, then `start-build` — read the log stream and note the artifact lands in the S3 bucket even with no repo involved.
2. Point `source_type = "CODECOMMIT"` at the `codecommit/` module's `clone_url_http` output and re-`apply` — same project, now pulling real source instead of running the inline buildspec against nothing.
3. Edit the `buildspec` variable to add a `test` phase between `pre_build` and `build` that runs `exit 1` — watch the build go red, and see CodeBuild stop before `post_build`.
4. Set `privileged_mode = true` and change the buildspec to run `docker build .` — this is what a container-image build stage needs (pairs with `ecr/`).

## Prerequisites for GITHUB source
A CodeBuild project reading from GitHub needs a **CodeStar Connection**
authorized once in the console (Developer Tools → Settings →
Connections → Create connection → GitHub → authorize the app) — this
step can't be done via Terraform since it requires an interactive OAuth
grant. Once authorized, its ARN is what `codepipeline/`'s GitHub source
action needs.

## Deliberately minimal
- One project, one environment. For a real pipeline (source → build →
  deploy, triggered automatically on push), see `codepipeline/`.

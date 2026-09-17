# Terraform: CodePipeline — wiring Source → Build → Deploy together

The flagship CI/CD module. Doesn't create a repo, build project, or
deploy target itself — it **wires together** resources already created
by `codecommit/` (or GitHub), `codebuild/`, and `codedeploy/`, plus its
own artifact bucket, IAM role, and (for CodeCommit) an EventBridge rule
so a push triggers the pipeline immediately instead of CodePipeline
polling for changes every minute.

> **Effectively free at rest** — CodePipeline bills per active pipeline
> per month (small, flat) plus whatever CodeBuild/EC2/S3 usage the
> stages themselves generate. Run `terraform destroy` when done
> experimenting.

## What it creates

```
S3 bucket (inter-stage artifacts, versioned, public access blocked)
IAM Role (S3 + StartBuild/BatchGetBuilds + CreateDeployment/Get* + source-specific)
CodePipeline
  Source stage  → CodeCommit  (or CodeStarSourceConnection for GitHub)
  Build stage   → CodeBuild
  Deploy stage  → CodeDeploy
EventBridge Rule + Role (CodeCommit only: push -> StartPipelineExecution, no polling)
```

## Prerequisites — apply these three modules FIRST
1. `codecommit/` (or set up a GitHub CodeStar Connection — see `codebuild/`'s README) → gives you `repository_name` / connection ARN.
2. `codebuild/` with `source_type` matching your source → gives you `project_name`.
3. `codedeploy/` (which itself needs `autoscaling/` applied first) → gives you `application_name` + `deployment_group_name`.

Then copy each output into this module's `terraform.tfvars`.

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pins + default tags |
| `variables.tf` | Which upstream resources to wire together |
| `main.tf` | Artifact bucket, IAM role, the pipeline, the push trigger |
| `outputs.tf` | Pipeline name/ARN + a `next_steps` runbook |

## Usage
```bash
cd aws/terraform/codepipeline
cp terraform.tfvars.example terraform.tfvars   # fill in the three upstream outputs
terraform init
terraform apply
aws codepipeline get-pipeline-state --name "$(terraform output -raw pipeline_name)"
```

## Things to try (mini-labs)
1. `apply`, then push a commit to your source repo's `main` branch — watch `get-pipeline-state` (or the console) move through Source → Build → Deploy without you triggering anything.
2. `aws codepipeline start-pipeline-execution --name <name>` to trigger a run on demand, e.g. to re-deploy the same commit.
3. Break the CodeBuild `buildspec` (from the `codebuild/` module) so it fails — watch the pipeline stop at the Build stage and never reach Deploy.
4. Compare `PollForSourceChanges = false` (EventBridge-driven, this module's default) against setting it `true` and removing the EventBridge rule — the difference is push-driven (seconds) vs. polling (up to a 1-minute delay).

## Deliberately minimal
- Three linear stages, one environment. A production pipeline usually
  adds a manual-approval action between Build and Deploy
  (`category = "Approval"`, `provider = "Manual"`) and a second
  Deploy stage for a second environment — both are a few extra
  `action` blocks inside this same `aws_codepipeline` resource once the
  three-stage version is working.

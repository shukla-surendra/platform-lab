# Terraform: CodeDeploy — the "deploy" stage of a CI/CD pipeline

Creates a CodeDeploy Application + Deployment Group targeting an
existing Auto Scaling Group (`autoscaling/`'s output), with an in-place
deployment strategy, optional ALB traffic control, and automatic
rollback on failure. Ships a runnable `sample-app/` (appspec.yml +
lifecycle-hook scripts) so you can deploy something real without waiting
on CodeBuild/CodePipeline.

> **Effectively free** — CodeDeploy itself isn't billed for EC2/On-Premises
> deployments; you're only paying for the ASG instances and S3 storage
> already created by other modules.

## What it creates

```
S3 bucket (deployment revisions) — unless artifact_bucket_name is passed in
IAM Role (AWSCodeDeployRole managed policy)
CodeDeploy Application (compute_platform = Server)
CodeDeploy Deployment Group (targets an ASG by name, in-place, auto-rollback)
sample-app/  (appspec.yml + BeforeInstall/AfterInstall/ApplicationStart/ValidateService scripts)
```

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pins + default tags |
| `variables.tf` | ASG target, ALB target group, deployment config, rollback |
| `main.tf` | Revision bucket, IAM role, application, deployment group |
| `outputs.tf` | Deployment group name + a `next_steps` runbook |
| `sample-app/` | A real, deployable appspec + lifecycle scripts |

## Usage
```bash
cd aws/terraform/codedeploy
cp terraform.tfvars.example terraform.tfvars   # paste in autoscaling/'s asg_name output
terraform init
terraform apply
terraform output next_steps   # package sample-app, upload, and create-deployment commands
```

## Things to try (mini-labs)
1. Follow `next_steps` to deploy `sample-app/` — `curl` an instance's private IP (via SSM port-forwarding, or the ALB DNS name if attached) afterward and see the new `index.html`.
2. Edit `sample-app/index.html`, re-zip, re-upload under a new key, and `create-deployment` again — watch CodeDeploy walk through each lifecycle hook in the console's deployment timeline.
3. Break `scripts/validate_service.sh` (e.g. `curl` a path that 404s) and redeploy — with `auto_rollback_on_failure = true`, watch CodeDeploy detect the failed hook and roll the instance back to the previous revision automatically.
4. Change `deployment_config_name` to `CodeDeployDefault.AllAtOnce` and redeploy — compare the deployment timeline: every instance updates simultaneously instead of one at a time.

## Deliberately minimal
- `compute_platform = "Server"` (EC2/ASG). For containers, a CodeDeploy
  app targeting ECS needs `compute_platform = "ECS"` plus two ALB target
  groups for blue/green — see `ecs-fargate/`'s README for why that
  module uses ECS's own native rolling deployment instead.

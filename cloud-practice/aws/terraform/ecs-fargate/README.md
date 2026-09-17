# Terraform: ECS on Fargate — cluster, task definition, service

Creates an ECS cluster, a Fargate task definition (execution role vs.
task role kept separate — see comments in `main.tf`), and a service with
ECS's own native rolling deployment. Runs a public demo image
(`httpd`) by default so it applies with **zero other modules**; point
`container_image` at `ecr/`'s `repository_url` for your own image, and
`target_group_arn` at `alb/`'s output to be load-balanced instead of
task-level public IPs.

> ⚠️ **Creates billable resources** (Fargate vCPU/memory-hours ×
> `desired_count`). Defaults to 2 × 0.25 vCPU / 512 MiB — a few cents/hour.
> Run `terraform destroy` when done.

## What it creates

```
ECS Cluster (Container Insights enabled)
CloudWatch Log Group (/ecs/<project>)
IAM Role: execution (pull image + ship logs — AmazonECSTaskExecutionRolePolicy)
IAM Role: task (your app's own AWS permissions — empty by default)
Security Group (container_port in, all out)
Task Definition (FARGATE, awsvpc network mode)
ECS Service (rolling deployment, optional ALB target group attachment)
```

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pin + default tags |
| `variables.tf` | Image, sizing, desired count, optional ALB attachment |
| `main.tf` | Cluster, log group, IAM roles, task def, service |
| `outputs.tf` | Cluster/service names + a `next_steps` runbook |

## Usage
```bash
cd aws/terraform/ecs-fargate
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
aws ecs describe-services --cluster "$(terraform output -raw cluster_name)" --services "$(terraform output -raw service_name)"
terraform destroy
```

## Things to try (mini-labs)
1. `apply`, then `describe-services` — watch `runningCount` climb to `desiredCount` as Fargate provisions the tasks (no EC2 instances to manage — that's the entire point of Fargate vs. EC2 launch type).
2. Change `container_image` to a different tag and `apply` — a NEW task definition revision is created and the service rolls to it, old tasks draining while new ones start (`deployment_minimum_healthy_percent = 50` caps how many can be down at once).
3. Attach `alb/`'s `target_group_arn`, `apply`, then `curl` the ALB — traffic now spreads across every task, and unhealthy tasks get replaced based on the ALB's health check.
4. `aws ecs update-service --desired-count 4` — watch it scale without touching the task definition at all.

## Deliberately minimal
- No auto-scaling policy (add `aws_appautoscaling_target` +
  `aws_appautoscaling_policy` targeting `ecs:service:DesiredCount` for
  that — same target-tracking idea as `autoscaling/`'s CPU policy).
- Task role has no permissions — attach `aws_iam_role_policy` to it as
  your container actually needs to call other AWS services.

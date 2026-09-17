# Terraform: Auto Scaling Group — self-healing fleet + CodeDeploy target

Creates a Launch Template (AL2023, httpd + the CodeDeploy agent baked
into `user_data`) and an Auto Scaling Group with an optional
target-tracking CPU scaling policy. This is the compute layer
`codedeploy/` deploys onto, and can optionally attach to `alb/`'s target
group for load-balanced traffic.

> ⚠️ **Creates billable resources** (up to `max_size` EC2 instances).
> Defaults to `desired_capacity = 2` on `t3.micro`. Run `terraform
> destroy` when done.

## What it creates

```
Security Group (80 in, all out)
IAM Role + Instance Profile (SSM + S3 read-only, for the CodeDeploy agent)
Launch Template (AL2023, user_data installs httpd + codedeploy-agent)
Auto Scaling Group (min/max/desired, instance_refresh enabled)
  └── optional: attach to an existing ALB target group
Target-tracking scaling policy (CPU, optional)
```

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pin + default tags |
| `variables.tf` | Sizing, target group attachment, scaling policy toggle |
| `main.tf` | SG, IAM, launch template, ASG, scaling policy |
| `outputs.tf` | ASG name + a `next_steps` runbook |

## Usage
```bash
cd aws/terraform/autoscaling
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "$(terraform output -raw asg_name)"
terraform destroy
```

## Things to try (mini-labs)
1. `apply`, then terminate one instance by hand (`aws ec2 terminate-instances`) — watch the ASG replace it automatically within a minute or two.
2. `aws autoscaling set-desired-capacity ... --desired-capacity 3` and watch a third instance launch from the same launch template.
3. Generate CPU load on an instance (`yes > /dev/null &` over SSM) and watch the target-tracking policy scale out on its own.
4. Set `target_group_arn` from `alb/`'s output, `apply`, then hit the ALB's DNS name — traffic now spreads across every instance, and `health_check_type` flips to `ELB` (unhealthy instances get replaced based on the ALB's health check, not just EC2 status checks).

## Deliberately minimal
- Scaling policy is CPU-only; a real service usually also scales on
  request count or queue depth. Security group allows 80 from anywhere —
  restrict to the ALB's own security group when composing with `alb/`.

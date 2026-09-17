# Terraform: Application Load Balancer — target group + HTTP listener

Creates an internet-facing ALB, one target group, and an HTTP listener
forwarding to it. Meant to be composed with `autoscaling/` (pass this
module's `target_group_arn` output into that one's `target_group_arn`
variable) or `ec2/`.

> ⚠️ **Small hourly charge** even with zero traffic (ALBs bill per hour
> + per LCU). Run `terraform destroy` when done.

## What it creates

```
Security Group (80 in from anywhere, all out)
Application Load Balancer (internet-facing, spans every subnet in the default VPC)
Target Group (HTTP:80, health check configurable)
Listener (HTTP:80 -> forward to the target group)
```

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pin + default tags |
| `variables.tf` | Health check path |
| `main.tf` | SG, ALB, target group, listener |
| `outputs.tf` | DNS name, target group ARN, a `next_steps` runbook |

## Usage
```bash
cd aws/terraform/alb
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
curl http://$(terraform output -raw dns_name)   # 502 until targets are attached
terraform destroy
```

## Things to try (mini-labs)
1. `apply` alone first — `curl` the DNS name and see a `502 Bad Gateway` (no healthy targets registered yet — this is the expected, useful failure).
2. Feed `target_group_arn` into `autoscaling/` and `apply` that module — re-`curl` the ALB and watch it start returning `200`.
3. `aws elbv2 describe-target-health --target-group-arn <arn>` — watch instances move from `initial` → `healthy` as the health check interval ticks.
4. Terminate one instance behind the ALB — traffic keeps flowing from the survivors while the ASG replaces it (this is the actual point of load balancing + auto scaling together).

## Deliberately minimal
- HTTP only, no ACM certificate/HTTPS listener, no WAF. For a real
  internet-facing service add an `aws_lb_listener` on 443 with an ACM
  cert and redirect 80→443.

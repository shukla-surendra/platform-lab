# Terraform: EC2 — SSM-only access, encrypted root volume, optional web server

Launches a single EC2 instance with no SSH key required (access is via
**SSM Session Manager**, using an instance profile), an encrypted gp3 root
volume, and an optional `user_data` script that installs `httpd` and
serves a landing page. This is the foundational compute module other
modules in this directory build on top of (`autoscaling/`, `codedeploy/`).

> ⚠️ **Creates billable resources** (EC2 instance, optional EIP). Free
> Tier covers a `t3.micro` for the first 12 months on a new account. Run
> `terraform destroy` when done.

## What it creates

```
Security Group (22 restricted to allowed_ssh_cidr, 80 open if web server enabled)
IAM Role + Instance Profile (AmazonSSMManagedInstanceCore)
EC2 instance (AL2023, encrypted gp3 root, user_data installs httpd)
Elastic IP (optional, static public IP)
```

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pin + default tags |
| `variables.tf` | Instance type, AZ, SSH CIDR, web server toggle, EIP toggle |
| `main.tf` | Security group, IAM role/profile, instance, optional EIP |
| `outputs.tf` | Instance ID, public IP, a `next_steps` runbook |

## Usage
```bash
cd aws/terraform/ec2
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
terraform output next_steps
terraform destroy
```

## Things to try (mini-labs)
1. Connect with `aws ssm start-session --target <instance_id>` — no key pair, no open SSH port needed.
2. Set `install_web_server = true`, `apply`, then `curl` the public IP — watch `user_data` run exactly once, at first boot.
3. Flip `associate_eip` from `false` to `true` and `apply` — the public IP becomes static across `stop`/`start` cycles instead of changing.
4. `aws ec2 stop-instances --instance-ids <id>` to stop paying for compute while keeping the (small, cheap) EBS root volume; `start-instances` to resume.

## Deliberately minimal
- Single instance, default VPC. For a fleet with health-check-based
  replacement, see `autoscaling/`. For traffic distribution across
  multiple instances, see `alb/`.

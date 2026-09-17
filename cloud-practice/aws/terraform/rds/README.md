# Terraform: RDS PostgreSQL — encrypted, backed up, credentials in Secrets Manager

Creates a single-AZ (by default) PostgreSQL instance, storage-encrypted,
with a randomly generated master password stored in **Secrets Manager**
(never in `terraform.tfvars`, never typed by hand), a security group
that only allows 5432 from within the VPC, and automated backups.

> ⚠️ **Creates billable resources** (RDS instance-hours + storage; `db.t3.micro`
> is Free-Tier eligible in most accounts for the first 12 months).
> `skip_final_snapshot = true` by default so `terraform destroy` fully
> cleans up for lab use — flip to `false` before this ever holds real data.

## What it creates

```
random_password (master password — never appears in .tf files or CLI args)
Secrets Manager Secret (username/password/host/port/dbname as one JSON blob)
DB Subnet Group (spans the default VPC's subnets)
Security Group (5432 from the VPC CIDR only — NOT the internet)
RDS Instance (postgres, gp3, encrypted, automated backups, storage autoscaling ceiling)
```

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pins + default tags |
| `variables.tf` | Engine/instance sizing, Multi-AZ, backup/snapshot behavior |
| `main.tf` | Password + secret, networking, the instance |
| `outputs.tf` | Endpoint, secret ARN, a `next_steps` runbook |

## Usage
```bash
cd aws/terraform/rds
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply       # RDS instances take 5-10 minutes to create
terraform output next_steps
terraform destroy
```

## Things to try (mini-labs)
1. `aws secretsmanager get-secret-value ... | jq .` — see the full connection JSON, then connect with `psql` from something inside the VPC (e.g. via SSM port-forwarding from `ec2/`'s instance — the security group deliberately has no path in from the public internet).
2. Confirm automated backups exist: `aws rds describe-db-snapshots` after the first backup window passes.
3. Flip `multi_az = true` and `apply` — watch a standby appear in a second AZ; then `reboot-db-instance --force-failover` and watch the endpoint keep working through the failover (same DNS name, different underlying instance).
4. Try `terraform destroy` with `skip_final_snapshot = false` — it now REQUIRES `final_snapshot_identifier`, which this module sets automatically; compare the destroy time/behavior against the `true` case.

## Deliberately minimal
- Single database engine (Postgres), no read replicas, no Performance
  Insights, no parameter group customization (uses the engine default).
  No public accessibility — this is intentionally reachable only from
  inside the VPC.

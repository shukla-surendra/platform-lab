# RDS PostgreSQL + RDS Proxy: lifecycle for a DevOps engineer

Applies to `main.tf` in this folder. Settings that matter are called out; verify details against current AWS docs before relying on them in production.

## 0. Where does the data live?

| Thing | Lives in | Notes |
|---|---|---|
| Table data, WAL | **EBS volume managed by RDS** (20 GB gp3) | You never see the volume; it exists only while the instance exists |
| Automated backups + transaction logs | RDS-managed S3 (not visible in your S3) | **Disabled here** (`backup_retention_period = 0`) |
| Manual / final snapshots | RDS-managed S3 | Survive instance deletion; billed until you delete them |
| Master password | **Secrets Manager** (created by `manage_master_user_password = true`) | Not in Terraform state |
| Terraform's record of the infra | `terraform.tfstate` | Holds IDs, endpoints, secret ARN; not the password or data |
| Proxy | Stateless | Holds no data, only a connection pool |

Key point: **the data is only in the DB instance (and its snapshots/backups). Terraform state, the proxy and the secret hold none of it.**

## 1. Create (`terraform apply`)

Order Terraform follows (from dependencies): subnet group + security groups → RDS instance (~5-10 min) → IAM role/policy (needs the secret ARN, created by RDS) → proxy → proxy target group → proxy target.

- Proxy target registers only once the DB is available; first health check can take a few minutes.
- Outputs: `db_endpoint`, `proxy_endpoint`, `secret_arn`.
- Billing starts as soon as the instance is `available` (and for the proxy once created).

## 2. Use

- DB is private (`publicly_accessible = false`); reach it from inside the VPC (e.g. the 008 SSM instance, or port-forward with SSM).
- Apps connect to **`proxy_endpoint`**, not the DB endpoint. TLS is required.
- Password: read from the secret (`aws secretsmanager get-secret-value --secret-id <secret_arn>`). JSON with `username` and `password`.
- Proxy pools connections and survives DB failover/restart better (apps reconnect to the same endpoint).

## 3. Change (`terraform apply` after editing)

| Change | Effect |
|---|---|
| `instance_class` | Downtime (reboot, minutes); data kept. Use `apply_immediately = true` or it waits for the maintenance window |
| `allocated_storage` up | Online (with limits: only once per ~6 hours; may be "optimizing"). **Cannot shrink**: must dump/restore to a new instance |
| `engine_version` major | In-place upgrade, downtime, **irreversible**; take a snapshot first. Parameter groups / extensions may need updating |
| `engine_version` minor | Short downtime; auto minor upgrades can also happen by themselves |
| `multi_az` false → true | Standby is created from a snapshot; brief impact |
| `identifier`, `engine`, `db_name`, `username` | **Force replacement = data loss** (destroy + create). Read the plan! |
| Security groups / proxy settings | Generally in place, no data impact |

Always read `terraform plan` for `-/+` (replace) or `must be replaced` on `aws_db_instance`.

## 4. Stop / start (cost saving without destroying)

- `aws rds stop-db-instance` keeps data and storage; you pay storage only.
- **AWS auto-starts a stopped instance after 7 days.**
- The **proxy keeps billing** while the DB is stopped; it does not stop. If you only pause, you still pay ~$22/month for the proxy.
- Terraform doesn't model stopped state; an out-of-band stop shows no drift on most attributes.

## 5. Destroy (`terraform destroy`): what happens to the data

With **this lab's settings**:

- `skip_final_snapshot = true` → **no final snapshot. Data is gone permanently.**
- `backup_retention_period = 0` → there are no automated backups to restore from.
- `deletion_protection = false` → nothing blocks the delete.
- The RDS-managed secret is **deleted along with the instance**.
- Proxy, IAM role/policy, SGs, subnet group are deleted. Proxy holds no data, so nothing is lost there.
- EBS storage is released and billing stops.

For anything you care about, use instead:

```hcl
skip_final_snapshot       = false
final_snapshot_identifier = "proxy-lab-db-final"   # must be unique; a re-run fails if it already exists
backup_retention_period   = 7
deletion_protection       = true                   # destroy fails until set to false and applied
delete_automated_backups  = false                  # keep automated backups after deletion (default true deletes them)
lifecycle { prevent_destroy = true }               # Terraform itself refuses to destroy
```

What survives deletion, and its cost:

| Artifact | After `destroy` |
|---|---|
| Final snapshot | **Kept** until you delete it; billed per GB-month |
| Manual snapshots | Kept; billed |
| Automated backups | Deleted by default (kept if `delete_automated_backups = false`, until retention expires) |
| Secret | Deleted with the instance |
| Terraform state | Resource entries removed; state file remains (don't forget it holds history) |

## 6. Restore options

1. **Restore from a snapshot** → always creates a **new** instance (new endpoint). In Terraform: `snapshot_identifier = "<snapshot>"` on the `aws_db_instance`. Then point the proxy target at the new instance.
2. **Point-in-time restore** (needs backups enabled; to any second within retention) → also a **new** instance.
3. **Logical backup** (`pg_dump` / `pg_restore`), the only way to shrink storage or move across major versions/regions/accounts easily.
4. **Cross-region/cross-account**: copy and share snapshots.

Restoring never overwrites the existing instance; plan the cutover (endpoint/DNS or proxy target swap).

## 7. Backups & high availability (not enabled in this lab)

- **Backups**: `backup_retention_period` 1-35 days, daily snapshot + transaction logs; enables PITR.
- **Multi-AZ**: synchronous standby in another AZ; automatic failover (~60-120 s); doubles instance cost. Proxy shortens client-visible failover.
- **Read replicas**: for read scaling; can be promoted (DR).

## 8. Credentials & secrets

- `manage_master_user_password = true`: RDS creates the secret and **rotates it automatically (every 7 days by default)**; the proxy reads the current value, so apps using the proxy don't see rotation breaks.
- Apps should fetch credentials at runtime from Secrets Manager (or use IAM auth with the proxy) rather than hard-coding them.
- Never commit passwords; with this setup there is none in the repo or state.

## 9. Operations a DevOps engineer should know

- **Monitoring**: CloudWatch (CPU, connections, FreeStorageSpace, burst credits on t4g), Performance Insights, Enhanced Monitoring. Alarm on storage and connections.
- **Burstable class (t4g)**: CPU credits; sustained load throttles. Fine for labs, not for steady production load.
- **Maintenance window**: AWS applies patches/minor upgrades; set a window you can tolerate.
- **Parameter groups**: custom settings (`max_connections`, logging); some need a reboot.
- **Logs**: enable `log_min_duration_statement` and export to CloudWatch if needed.
- **Tags & cost**: tag resources; watch Cost Explorer for RDS + proxy.
- **Security**: private subnet/SG-only access, TLS, least-privilege IAM, encryption at rest (default on for new instances in many setups; set `storage_encrypted = true` explicitly for production).

## 10. Terraform-specific notes

- **State**: contains instance attributes and the secret ARN. Use a remote encrypted backend (see `000_bootstrap_state_bucket`).
- **Drift**: console changes (instance class, storage, SG) show up in the next `plan`; decide to revert via `apply` or update code.
- **Import**: `terraform import aws_db_instance.this proxy-lab-db` to adopt an existing instance.
- **Delete ordering problems**: proxy ENIs can delay SG/subnet deletion for a few minutes; re-run `destroy` if it times out.
- **Final snapshot name clash**: a second destroy with the same `final_snapshot_identifier` fails; use a timestamp or clean up the old snapshot.
- **Partial failures**: if `apply` dies midway, re-run it; check the console for half-created RDS/proxy resources before assuming nothing exists.

## 11. Cost recap (us-east-1, approx.; verify)

| Item | ~Monthly |
|---|---|
| `db.t4g.micro` Postgres | ~$12 |
| 20 GB gp3 | ~$2 |
| RDS Proxy (2 vCPU minimum) | ~$22 |
| Snapshots (manual/final) | per GB-month, after destroy too |

Lab habit: `terraform apply` → test → `terraform destroy` the same day, then check the console for leftover snapshots.

## 12. Quick checklist before `destroy` in a real environment

1. Is there a recent snapshot (or will `final_snapshot_identifier` produce one)?
2. Has someone confirmed nothing still connects to the proxy/DB?
3. Is `deletion_protection` the only thing in the way? Don't just flip it; confirm intent.
4. After destroy: delete leftover snapshots you no longer need, and verify the secret and proxy are gone.

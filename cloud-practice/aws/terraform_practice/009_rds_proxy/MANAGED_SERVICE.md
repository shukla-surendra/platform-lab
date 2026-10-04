# RDS is a managed service: what that means and what tools it gives you

Verify feature availability per engine/version in the AWS docs; not every feature exists for every engine.

## Is only Aurora managed?

No. **All of RDS is managed**, including standard PostgreSQL, MySQL, MariaDB, Oracle and SQL Server. Aurora is one engine family within RDS (AWS's cloud-built, MySQL/PostgreSQL-compatible engine).

| | Standard RDS (this lab) | Aurora |
|---|---|---|
| Managed by AWS | Yes | Yes |
| Storage | One EBS volume per instance | Distributed storage across 3 AZs, grows automatically |
| Failover | Multi-AZ standby (~60-120 s) | Faster (typically tens of seconds) |
| Read replicas | Up to 5 (engine dependent) | Up to 15, share storage |
| Cost | Lower | Usually higher; serverless option |
| Alternative (not managed) | DB installed yourself on EC2 | n/a |

## Who does what

AWS handles:
- Hardware, OS, DB software install
- Patching (including minor version upgrades)
- Automated backups and point-in-time restore (if enabled)
- Failover (if Multi-AZ)
- Storage provisioning, monitoring hooks

You handle:
- Schema, queries, indexes, tuning
- DB users and permissions
- Instance size, backup retention, Multi-AZ choice
- Network access and security groups
- Major version upgrades, parameter settings

Trade-off: **no SSH / OS access** to the host.

## Tools RDS provides

### Availability & durability
- **Automated backups + PITR**: daily snapshot + transaction logs, restore to any second in retention (1-35 days). Off in this lab (`backup_retention_period = 0`).
- **Manual snapshots**: kept until you delete them; can be copied across regions and shared with other accounts.
- **Multi-AZ**: synchronous standby in another AZ with automatic failover.
- **Read replicas**: scale reads; can be cross-region; can be promoted for DR.
- **Blue/Green deployments**: create a staging copy, test changes (upgrades, parameter changes), then switch over with short downtime.

### Connections
- **RDS Proxy** (this lab): connection pooling, faster failover, secrets/IAM-based auth.
- **IAM database authentication**: short-lived tokens instead of passwords.
- **Secrets Manager integration**: `manage_master_user_password` creates and auto-rotates the master secret.

### Security
- **Encryption at rest** (KMS) and **in transit** (TLS).
- **VPC + security groups**, private subnets, `publicly_accessible = false`.
- **CloudTrail** records RDS API calls (who changed what).
- Compliance support (varies by engine/region).

### Monitoring & troubleshooting
- **CloudWatch metrics**: CPU, connections, FreeStorageSpace, IOPS, replica lag, burst credits.
- **Enhanced Monitoring**: OS-level metrics at up to 1-second granularity.
- **Performance Insights**: shows top SQL, waits, load; first thing to open for slow DB.
- **Database logs**: view/download or export to CloudWatch Logs (slow query, error logs).
- **Event notifications** via SNS (failover, backup, maintenance, low storage).
- **RDS recommendations**: console hints (pending maintenance, config issues).

### Configuration & maintenance
- **Parameter groups**: engine settings (`max_connections`, logging); some need a reboot.
- **Option groups**: extra features for some engines (Oracle/SQL Server/MySQL).
- **Maintenance window**: when patches may apply; **auto minor version upgrade** toggle.
- **Storage autoscaling**: set `max_allocated_storage` so storage grows automatically (never shrinks).
- **Modify with `apply_immediately`** vs wait for the window.

### Data movement
- **Snapshot export to S3** (Parquet) for analytics.
- **AWS DMS** for migrations/replication into or out of RDS.
- **Cross-region snapshot copy / replicas** for DR.

### Escape hatches
- **RDS Custom** (Oracle/SQL Server): more OS/DB access while still partly managed.
- **Self-managed on EC2**: full control, full responsibility.

## What this lab uses vs. skips

| Tool | In `009`? |
|---|---|
| Managed master password in Secrets Manager | Yes |
| RDS Proxy | Yes |
| Security-group isolation, private access | Yes |
| Automated backups / PITR | No (retention 0) |
| Multi-AZ, replicas | No |
| Performance Insights, Enhanced Monitoring | No (can be added) |
| Storage autoscaling, deletion protection | No |

Good next small lessons: enable backups + a manual snapshot and restore it; add Performance Insights; try a read replica.

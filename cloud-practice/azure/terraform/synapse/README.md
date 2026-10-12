# Terraform: Azure Synapse Analytics learning lab (2-3 hours)

A cost-controlled Synapse workspace on an ADLS Gen2 lake, with generated sample data (~2.5 MB, 62k orders), SQL labs, and a Spark lab.

> ⚠️ **Billing:** the workspace and serverless SQL are effectively free at this scale. The **Spark pool** and the **dedicated SQL pool** are what cost money. Details below. Run `terraform destroy` when done.

Checked *(verified)*: `terraform validate` passes and `terraform plan` (read-only) succeeds with azurerm 5.x. **Not applied yet**: the SQL/Spark labs and `upload_data.sh` are written against documented behaviour but not run, so expect to fix small things (Spark runtime version, role-propagation delays).

## Tools you need

| Tool | Why | Check |
|---|---|---|
| Azure subscription (Contributor + User Access Administrator, or Owner) | Terraform creates role assignments | `az account show` |
| Terraform >= 1.5 | infra | `terraform version` |
| Azure CLI | login, upload data, pause pools | `az login` |
| Python 3 (stdlib only) | generates the sample data | `python3 --version` |
| A browser | **Synapse Studio** is where you do the learning (SQL scripts, notebooks, pipelines) | URL is a Terraform output |
| Optional: Azure Data Studio / SSMS | connect to the serverless endpoint from a desktop client | endpoint is a Terraform output |

Register the resource provider once if needed: `az provider register -n Microsoft.Synapse`.

## Pricing (approximate, USD; verify in the [Azure pricing calculator](https://azure.microsoft.com/pricing/calculator/) for your region, rates vary)

| Component | How it bills | This lab |
|---|---|---|
| Synapse workspace | **Free** | $0 |
| Serverless SQL (built-in) | ~$5 per TB of data processed (minimum 10 MB per query) | Data is ~2.5 MB CSV, so **cents at most** |
| Storage (ADLS Gen2, LRS) | ~$0.02/GB-month plus tiny transaction fees | cents/month |
| **Spark pool** | per vCore-hour **only while a session/job is running** (roughly $0.1-0.2 per vCore-hour). The pool here is 3 x Small (4 vCores) = **12 vCores**, so roughly **$1.5-2.5/hour while active**. Auto-pauses 5 min after idle | 1 hr of active use ≈ **$2**, plus the idle 5 min. Budget ~$3-5 for the session |
| **Dedicated SQL pool** (off by default) | per hour **while Online**, even when idle. DW100c ≈ **$1.2-1.5/hour**; paused = compute free (storage still billed ~$0.12/GB-mo) | $0 unless you enable it. If you do, 1 hour ≈ $1.5; **pause it after use** |
| Pipelines / Data Explorer / etc. | not created | $0 |

**Realistic total for a 2-3 hour session:** ~**$0.50 if you skip Spark and dedicated**, ~**$3-6 with Spark**, ~**$5-8 with Spark + 1-2 hours of dedicated pool**. Forgetting a dedicated pool running costs ~$30-36/day. Spark idle is safe (auto-pause); dedicated is not.

Safety nets: set a budget alert (Cost Management > Budgets, e.g. $10); `./scripts/cost_guard.sh` lists and pauses running pools; `terraform destroy` removes everything.

## Setup

```bash
az login
cd cloud-practice/azure/terraform/synapse
export TF_VAR_sql_admin_password='<a strong password, 12+ chars>'   # not stored on disk
terraform init
terraform plan
terraform apply          # ~5-10 min (workspace creation is slow)
./scripts/upload_data.sh # generates data, uploads to the "raw" filesystem
```

Toggle options: `-var enable_spark_pool=false` (skip Spark), `-var enable_dedicated_pool=true` (add the paid pool later with another apply). Your public IP is auto-detected and added to the Synapse firewall; if your IP changes, re-run `terraform apply`.

Open `terraform output studio_url`.

## Suggested 3-hour path

| Time | Topic | Where | Cost |
|---|---|---|---|
| 0:00-0:20 | **Tour Studio**: Data, Develop, Integrate, Monitor, Manage hubs. Look at Linked services (the workspace lake is pre-linked), Manage > Apache Spark pools, SQL pools (Built-in is always there) | Studio | $0 |
| 0:20-1:00 | **Serverless SQL basics**: `sql/01_serverless_basics.sql`. OPENROWSET, wildcards, `filepath()`, explicit types, JSON. Open Monitor > SQL requests and note *data processed* per query: that is your bill | Studio | ~$0 |
| 1:00-1:30 | **Logical data warehouse**: `sql/02_external_tables_and_cetas.sql`. External tables, CETAS to Parquet, views. Re-run the same aggregation on Parquet vs CSV and compare data processed | Studio | ~$0 |
| 1:30-2:15 | **Spark**: `spark/01_spark_lab.py`. Pool cold start, DataFrames, partitioned Parquet, **Delta** update + time travel, lake database visible from serverless | Studio notebook | ~$2-3 |
| 2:15-2:35 | **Pipelines (Integrate hub)**: build a Copy activity from `raw/reference/customers.csv` to `curated/customers_copy/` as Parquet, debug-run it. Look at Data flows and triggers (don't leave anything running) | Studio | cents (DIU minutes) |
| 2:35-2:50 | **Security & governance**: Manage > Access control (Synapse RBAC vs Azure RBAC), managed identity, firewall, Linked services | Studio | $0 |
| optional | **Dedicated pool**: `enable_dedicated_pool=true`, then `sql/03_dedicated_pool.sql`: distributions, COPY, columnstore, `EXPLAIN`. **Pause it right after** (Manage > SQL pools > Pause) | Studio | ~$1.5/hr |
| end | `./scripts/cost_guard.sh`, then `terraform destroy` | shell | |

## What each Synapse feature is for (and when NOT to use it)

- **Serverless SQL**: ad hoc queries and a thin SQL layer directly over lake files. Great for exploration and cheap ETL via CETAS. Not for low-latency, high-concurrency BI.
- **Dedicated SQL pool**: classic MPP warehouse (60 distributions) for large, repeatedly queried data. Costs while online; the main reason people overspend on Synapse.
- **Spark pool**: big transforms, ML, Delta. Slow cold start (minutes).
- **Pipelines**: ADF-style orchestration and copy, built in.
- **Lake databases / shared metadata**: tables made in Spark show up in serverless SQL.
- Good to know: Microsoft now steers new analytics projects toward **Microsoft Fabric**; Synapse is still widely used and a fine thing to learn, but compare when choosing for production.

## Troubleshooting

- `403` on upload or on serverless queries: role assignments take 1-5 minutes to propagate; retry.
- Studio shows "no access": the workspace creator is auto-admin, so check your IP in Manage > Firewalls.
- Spark pool creation fails on version: pick a supported one from Studio and pass `-var spark_version=...`.
- Serverless `CREATE MASTER KEY` error "already exists": skip it.
- Can't create resources in region: change `-var location=...`.

## Cleanup

```bash
./scripts/cost_guard.sh
terraform destroy
```

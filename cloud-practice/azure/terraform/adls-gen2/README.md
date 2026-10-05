# Terraform: ADLS Gen2 (Azure Data Lake Storage Gen2), medallion layout

A storage account with the **hierarchical namespace** (that is all "Gen2" means), three filesystems (**bronze / silver / gold**), a folder skeleton, RBAC, an optional ACL, and a lifecycle policy. Related but different from `../delta-lake/`: that project is a minimal lake used to explore the Delta table format; this one focuses on the **lake itself** (layout, access control, lifecycle).

> ⚠️ Creates billable resources, but only storage (no compute). A few KB of data costs effectively nothing. Run `terraform destroy` when done.

Checked *(verified)*: `terraform validate` passes with azurerm 5.x, and `terraform plan` (read-only) shows **13 resources to add** by default and **14** when `reader_object_id` is set. The `az` commands used in `scripts/demo.sh` exist in the installed CLI. **Not applied yet**: the expected behaviour of the demo script is the intended outcome to confirm when you run it.

## "ADLS Gen2" is a setting, not a service

```
Storage Account (StorageV2)
   is_hns_enabled = false  ->  plain Blob Storage (flat; "folders" are just "/" in names)
   is_hns_enabled = true   ->  ADLS Gen2: real directories, atomic rename/move, POSIX ACLs
```

| | Blob (flat namespace) | ADLS Gen2 (hierarchical namespace) |
|---|---|---|
| Directories | Fake (prefix in the blob name) | Real |
| Rename/move a "folder" | Copy + delete every blob | One atomic metadata operation |
| Permissions | RBAC / SAS / keys | RBAC **plus POSIX ACLs per directory/file** |
| Endpoints | `blob.core.windows.net` | `dfs.core.windows.net` **and** blob (same data) |
| Analytics engines | Work, but slow on rename-heavy jobs | The designed target (Spark, Synapse, Databricks, Delta) |
| Choice is made | any time | **at creation**; flipping later means a migration |

Terminology: Blob **container** = ADLS Gen2 **filesystem**.

## What gets created

```
rg-adls-gen2-demo
└─ stadls<random>   (StorageV2, HNS on, LRS, TLS 1.2, soft delete 7 days)
     ├─ bronze/   raw/sales, raw/customers      raw landing data, as received
     ├─ silver/   sales, customers               cleaned, validated, typed
     └─ gold/     reports                        curated, business-ready
   RBAC:  you = Storage Blob Data Owner (account)
          optional reader = Storage Blob Data Reader (gold only) + ACL r-x on gold/reports
   Lifecycle: bronze/raw -> Cool after 30 days, deleted after 365
```

Medallion layers: **bronze** (raw, immutable history) -> **silver** (cleaned) -> **gold** (aggregates for BI/ML). Separate filesystems make it easy to give different people different access and to apply different lifecycle rules.

## Files

| File | Purpose |
|---|---|
| `main.tf` | everything above, commented step by step |
| `scripts/demo.sh` | guided walk-through with PASS/FAIL checks (upload, read back, atomic rename, blob API, ACL) |
| `.gitignore` | state, tfvars, `.terraform/` |

## Run

```
az login                       # and: az account set --subscription <id> if needed
terraform init
terraform plan
terraform apply                # ~1-2 min

./scripts/demo.sh              # Entra ID login (uses your Data Owner role)
AUTH=key ./scripts/demo.sh     # or the account key, if the role has not propagated yet
```

Expected demo output (confirm when you run it): `isHnsEnabled = true`; three filesystems; the `bronze/raw/sales` directory; upload + identical download of the CSV; `raw/customers` moved and moved back; the Blob API lists the file written through DFS; ACL entries printed; the `abfss://` URIs.

Optional reader:
```
terraform apply -var "reader_object_id=$(az ad signed-in-user show --query id -o tsv)"
```
(Use any user/group/service principal object id; here it is yourself, just to see the plan and ACL.)

## Access control: the part that surprises people

Two independent layers:

| | **RBAC** (Azure roles) | **ACLs** (POSIX-style) |
|---|---|---|
| Granularity | account / filesystem | directory / file |
| Managed via | `azurerm_role_assignment` | `ace` blocks on `azurerm_storage_data_lake_gen2_path` |
| Roles | Storage Blob Data Owner / Contributor / Reader | `r`, `w`, `x` for user / group / other + masks |
| Evaluated | **First** | **Only if RBAC did not already allow it** |

- **Owner or Contributor on the subscription is not enough to read file contents with Entra ID.** Those are control-plane roles. You need a *data* role (**Storage Blob Data ***).
- To read `gold/reports/x.csv` through ACLs alone, a user needs `x` on every directory on the path (including the filesystem root) and `r` on the file.
- **Default ACLs** (scope `default`) are inherited by *new* children only; they do not rewrite existing files.
- Role assignments take a few minutes to propagate; `AuthorizationPermissionMismatch` right after apply usually means "wait".

## Provider choice made here (and what production changes)

`shared_access_key_enabled = true` because Terraform creates filesystems and directories through the data plane with the account key. Production hardening:

- `shared_access_key_enabled = false` and use Entra ID only (`storage_use_azuread = true` in the provider block; your identity needs Storage Blob Data Owner).
- **Private endpoints** (`dfs` and `blob` sub-resources) and `public_network_access_enabled = false`, or at least a network rule with allowed VNets/IPs.
- ZRS/GRS instead of LRS; **versioning** and **change feed** where needed; **resource locks** on the account.
- **Customer-managed keys** if policy requires; diagnostic logs to Log Analytics.
- Terraform state in a **remote backend** (an `azurerm` backend on a separate, locked-down storage account), not a local file.

## Reaching the data

| From | How |
|---|---|
| Spark / Databricks / Synapse | `abfss://<filesystem>@<account>.dfs.core.windows.net/<path>` (see output `abfss_uris`) |
| `az` CLI | `az storage fs ...` (used in the demo), `az storage blob ...` |
| AzCopy / Storage Explorer | HTTPS + Entra login |
| Python | `azure-storage-file-datalake`, or `deltalake` / `pandas` + `adlfs` (see `../delta-lake/examples/`) |
| Same file via Blob API | `https://<account>.blob.core.windows.net/<filesystem>/<path>` (multi-protocol access) |

## Cost *(approximate; verify current Azure pricing)*

Pay per GB-month stored (hot, LRS, a few cents per GB), per transaction (ADLS Gen2 operations cost somewhat more than plain Blob), and for data egress. The demo data is a few bytes. The lifecycle policy moves old raw data to cooler (cheaper) tiers. Soft-deleted data still counts toward storage during its retention period.

## Destroy

```
terraform destroy
```
Deleting the storage account removes its data. A recently deleted account may be recoverable for a limited time (check Azure's storage account recovery rules), but do not rely on that.

## Exercises

1. Run `terraform apply -var "reader_object_id=<object id of a second test user>"`, then use `az storage fs access show -f gold -p reports` to read the ACL, and test access as that user.
2. Add a 4th filesystem (`variables.tf`-style: add to `var.filesystems`) and a directory under it.
3. Turn on `shared_access_key_enabled = false` and `storage_use_azuread = true`; see which operations then fail until your role has propagated.
4. Add a **private endpoint** for the `dfs` sub-resource in a small VNet and close public access.
5. Compare `az storage fs directory move` of a directory with 1,000 files on this account vs a non-HNS account (time it): the point of HNS.

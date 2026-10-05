# What is ADLS Gen2? A beginner's guide (written for people coming from AWS)

This is explanatory, from general knowledge of Azure. Details and limits change, so check Microsoft's current docs before relying on a specific number or feature table. What was actually run in this repo: `terraform validate` and `terraform plan` for the project in `main.tf` (nothing applied yet).

## 1. The one-minute version

- **ADLS Gen2 is not a separate Azure service.** It is a normal **Azure Storage Account** with **one switch turned on** when you create it: the **hierarchical namespace** (HNS).
- Without the switch, the account is plain **Blob Storage**: a giant bucket of objects where "folders" are an illusion.
- With the switch, the same account has **real folders**, can **rename/move a folder instantly**, and can put **per-folder permissions** on things.
- It was built for **big-data/analytics** (Spark, Databricks, Synapse, Delta Lake), where jobs create, rename and delete huge numbers of files inside folders.
- It is the **same account, same data, same pricing family**. You are not choosing a different product, you are choosing a different *mode* of the same product.

## 2. A layman's mental model

**Plain Blob Storage = a huge warehouse of labelled boxes.**

Every box has one long label, like `2026/10/sales/orders.csv`. The slashes are just characters in the label. There are no real aisles. The "folder" `2026/10/sales/` doesn't exist as a thing: it's only the common start of many labels.

- To **rename a folder**, you must go box by box, re-label each one, and throw the old label away. A folder with a million boxes means a million operations.
- You can't say "this *aisle* is only for the finance team", because there are no aisles, only boxes.

**ADLS Gen2 = the same warehouse, but with real aisles and shelves.**

There is a real "sales" aisle containing real "2026" and "10" shelves.

- **Moving or renaming an aisle** is one change of a sign. Instant, no matter how many boxes are inside.
- You can hand out **keys per aisle** ("finance can enter /reports, nobody else").
- Deleting an aisle is one operation, not a million.

That's the whole idea. Everything else is detail.

## 3. The AWS translation

If you know S3, you already know most of Blob Storage. The mapping:

| Azure | AWS (closest) | Notes |
|---|---|---|
| **Storage Account** | *(no direct equivalent)* | A top-level container for **several** storage services (Blob, Files, Queue, Table) with shared settings (redundancy, networking, keys). Think "an S3-like service + EFS-like + SQS-like + DynamoDB-like, bundled under one account." |
| **Blob container** | S3 **bucket** | Where objects live |
| **Blob** | S3 **object** | |
| "Folder" in Blob (flat) | S3 **prefix** | Same illusion: just part of the name |
| **ADLS Gen2 filesystem** | S3 bucket **+** real-directory behaviour | Same thing as a container, but with real directories inside |
| **Hierarchical namespace** | *(S3 has no standard equivalent)* | S3 "directory buckets" (S3 Express One Zone) have a directory notion, but regular S3 buckets are flat |
| **ACLs per directory** | S3 has bucket policies / IAM (prefix conditions), no POSIX ACLs | Different model |
| **RBAC (Storage Blob Data *)** | IAM policies | Similar purpose |
| **SAS token** | S3 pre-signed URL (roughly) | Time-limited delegated access |
| **Account key** | *(no good equivalent: a root-like secret)* | Treat like a password; prefer Entra ID |
| **Lifecycle management policy** | S3 Lifecycle rules | |
| **Access tiers: Hot/Cool/Cold/Archive** | S3 Standard / Standard-IA / Glacier tiers | |
| **abfss:// (ABFS driver)** | `s3a://` (S3A) / `s3://` (EMRFS) | How Spark/Hadoop address the lake |
| **Synapse / Databricks / HDInsight** | Athena, EMR, Glue, Redshift Spectrum, Databricks on AWS | The compute engines |
| **Purview** | Glue Data Catalog + Lake Formation (loosely) | Governance/catalog side |

Why this matters: **S3 is flat too**, and in the AWS world the "no real folders" problem exists but is mostly hidden by table formats (Iceberg/Delta/Hudi), Glue/Athena and committers that avoid renames. ADLS Gen2 tackled the problem at the *storage* layer instead, because Azure's analytics stack came from the Hadoop world, which assumes real directories and atomic rename.

## 4. What Blob Storage (flat) could NOT do well, and what ADLS Gen2 adds

| Problem on flat Blob | With ADLS Gen2 (HNS on) |
|---|---|
| **Renaming/moving a "folder"** = copy + delete every object (slow, not atomic, can leave a mess if it fails midway) | **One atomic metadata operation**, instant |
| **Deleting a "folder"** = delete each object one by one | **One operation** |
| **Permissions per folder**: impossible. Only account/container level (RBAC), keys, SAS | **POSIX-style ACLs** on any directory or file (read / write / execute per user, group, other) |
| **Empty folders**: can't exist (no objects = no folder) | **Real, empty directories** |
| **Listing a "folder"**: scans a prefix, slow for deep trees | Directory-aware listing, faster for analytics patterns |
| **Hadoop/Spark compatibility**: needs workarounds; job "commits" use rename, which is slow and unsafe | **ABFS driver** designed for HNS; atomic rename makes job commits safe and fast |
| **Delta/Iceberg/Hudi commit protocols** that need atomic operations | Work reliably (these rely on atomic rename/commit semantics) |
| **File-system style access** (SFTP, NFS, mount as a drive) | SFTP and NFS 3.0 support require HNS; also mountable via blobfuse2 |

Honest caveat: **some Blob features have restrictions on HNS-enabled accounts**. The exact support table changes over time; check "Blob Storage feature support in Azure Storage accounts" in Microsoft's docs before depending on a specific feature (e.g. versioning, certain replication/tiering behaviours).

## 5. Is it the same as a normal storage account?

**Yes. Same account, extra mode.** Nothing about it is a separate product.

| | Same as a normal Storage Account | Different with HNS |
|---|---|---|
| Account type | `StorageV2` | (same) |
| Redundancy (LRS/ZRS/GRS...) | same options | (same) |
| Networking (firewall, private endpoints) | same | (same) |
| Authentication (Entra ID, keys, SAS) | same | + **ACLs** layer |
| Access tiers, lifecycle management | same idea | (some tier/feature limits) |
| Blob API / `blob.core.windows.net` | still works | **Same data is also available at** `dfs.core.windows.net` |
| Pricing meters | same family (storage, transactions, egress) | ADLS operations are priced a bit differently from plain Blob; check the pricing page |
| Created with | `azurerm_storage_account` | the same resource + `is_hns_enabled = true` |

**Important:** the choice is made **at creation**. In Terraform, changing `is_hns_enabled` on an existing account forces a new account (destroying data). Microsoft does offer an *upgrade* path for existing Blob accounts to HNS, which is a one-way migration with validation steps, not a casual toggle. Decide up front.

You can read and write the **same files** through either endpoint ("multi-protocol access"):

```
https://<account>.blob.core.windows.net/<filesystem>/<path>   (Blob API)
https://<account>.dfs.core.windows.net/<filesystem>/<path>    (Data Lake API: directories, ACLs, rename)
abfss://<filesystem>@<account>.dfs.core.windows.net/<path>    (how Spark/Hadoop writes it)
```

## 6. When do you need it?

**Use ADLS Gen2 (HNS on) when:**

- You are building a **data lake / lakehouse** (bronze/silver/gold layers).
- You run **Spark, Databricks, Synapse, Fabric, HDInsight, Data Factory** pipelines against the data.
- You use **Delta Lake / Iceberg / Hudi** tables.
- Jobs **rename or delete large folders** (typical of ETL "write to temp, rename to final").
- You need **folder-level permissions** ("team A reads /sales, team B reads /hr").
- You have **millions of files** in deep folder trees and listing/moving them must be fast.
- You need **SFTP** into storage (requires HNS).
- You are migrating from **HDFS/Hadoop**.

**Plain Blob (HNS off) is fine when:**

- Storing **app files**: images, videos, user uploads, documents.
- **Backups, logs, archives** that are written once and read rarely.
- **Static website** assets and simple object storage needs.
- You rely on a Blob feature that HNS doesn't support (check the table).
- Folder renames and per-folder security don't matter to you.

**Simple rule:** if the data will be processed by analytics engines in **folders**, turn HNS on. If it's "just objects," don't bother.

## 7. How you reach and manage it (the tools)

| Tool | What it's for |
|---|---|
| **Azure Portal** | Create/configure accounts; browse filesystems (basic) |
| **Azure Storage Explorer** (desktop app) | The "file browser": drag and drop, manage ACLs, SAS tokens. Closest thing to an S3 browser |
| **AzCopy** (CLI) | Fast bulk copy/sync (like `aws s3 sync`), also between accounts and from S3 |
| **Azure CLI** (`az storage fs ...`, `az storage blob ...`) | Scripting; `scripts/demo.sh` uses it |
| **Azure PowerShell** | Scripting on Windows-heavy shops |
| **Terraform** (`azurerm`) | Infra: account, filesystems, directories, RBAC, ACLs (this project) |
| **SDKs** (Python `azure-storage-file-datalake`, Java, .NET, JS) | Application code |
| **REST API** | Underlying API (DFS and Blob) |
| **Spark / Databricks / Synapse / Fabric / HDInsight** | Analytics on the lake via `abfss://` |
| **Azure Data Factory / Synapse pipelines** | Move and orchestrate data in/out |
| **blobfuse2 / NFS 3.0 / SFTP** | Mount or access it like a file system |
| **Python libs** (`pandas` + `adlfs`, `deltalake`, `pyarrow`) | Data work from a laptop (see `../delta-lake/examples/`) |
| **Microsoft Purview** | Catalog and governance across lakes |

Auth options, from best to worst: **Entra ID (RBAC)** > **SAS (time-limited)** > **account key (full access: avoid)**. Remember: being Subscription Owner does **not** let you read file contents. You need a **data role** (*Storage Blob Data Reader/Contributor/Owner*).

## 8. What this project gives you (and how it maps)

`main.tf` creates a storage account with `is_hns_enabled = true`, three **filesystems** (bronze/silver/gold), folders, RBAC, an optional ACL and a lifecycle rule. `scripts/demo.sh` shows the HNS advantage in action: it **renames a directory** and then **reads the same file through both the DFS and Blob APIs**.

AWS translation of the layout:

```
rg-adls-gen2-demo                  ~  an AWS "stack"/resource group of resources
└─ stadls<random>   (account)      ~  (no single AWS equivalent; holds S3-like storage)
     ├─ bronze/  raw/sales ...     ~  s3://lake-bronze/raw/sales/...
     ├─ silver/  sales ...         ~  s3://lake-silver/sales/...
     └─ gold/    reports           ~  s3://lake-gold/reports/...
```

In AWS you'd likely make three buckets or one bucket with prefixes and use **IAM + Lake Formation** for fine-grained access. In Azure the fine-grained part can live **in the storage itself** (ACLs).

## 9. Quick glossary

| Term | Plain meaning |
|---|---|
| **Storage account** | The Azure "account" that holds storage services and shared settings |
| **Blob** | An object (file) |
| **Container** | A top-level folder/bucket for blobs |
| **Filesystem** | Another name for a container when HNS is on |
| **Hierarchical namespace (HNS)** | The switch that makes folders real |
| **DFS endpoint** | The address for the Data Lake API (`dfs.core.windows.net`) |
| **ABFS / `abfss://`** | The Hadoop/Spark driver and URL scheme for HNS accounts (`s` = TLS) |
| **ACL** | Per-folder/file permissions in POSIX style (read/write/execute) |
| **RBAC** | Azure role-based access control (who may use the data at all) |
| **SAS** | A signed URL/token granting limited, time-boxed access |
| **Medallion (bronze/silver/gold)** | A layout: raw -> cleaned -> curated |
| **Delta Lake** | An open table format on top of files (ACID, time travel); see `../delta-lake/` |
| **Multi-protocol access** | Same data reachable through both Blob and DFS APIs |

## 10. Common beginner questions

**"So is ADLS Gen2 just S3?"** It's the closest thing, with extras: real directories, atomic folder rename and per-folder ACLs. S3 would need a table format or special committer to be safe for rename-heavy jobs.

**"Why is it called Gen2? What was Gen1?"** Gen1 was a separate, standalone data lake service (now retired). Gen2 merged those ideas into Blob Storage, so you get lake features on cheap, widely supported storage.

**"Do I need a separate service to run it?"** No. It's just a storage account. You only need compute (Spark, etc.) if you want to *process* the data.

**"Can I turn it on later?"** Only through an explicit, one-way upgrade/migration. In Terraform, flipping `is_hns_enabled` recreates the account. Decide at creation.

**"Will my normal Blob tools still work?"** Mostly yes: the Blob API still works. A few Blob features are restricted on HNS accounts, so check the feature-support table for what you rely on.

**"Is it more expensive?"** Storage is priced like Blob. Operations can cost a bit differently, but Gen2 can save money in practice by making renames/deletes cheap and enabling tiering. Verify current numbers on the pricing page.

**"Why did my user get 'Forbidden' even though they are Contributor?"** Contributor/Owner are control-plane roles. File access needs a data role (Storage Blob Data *) or an ACL that grants it.

## 11. Where to go next in this folder

1. Read `README.md` (what the Terraform builds, access control details).
2. `terraform apply`, then `./scripts/demo.sh` to *see* the rename and the two endpoints.
3. Try the exercises at the end of `README.md`.
4. Then look at `../delta-lake/` to see a table format running on top of this storage.

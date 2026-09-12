# Terraform: Delta Lake on Azure (ADLS Gen2, open-source, no compute cluster)

RG + an ADLS Gen2 storage account (hierarchical namespace on — that's what
makes it "Data Lake" and not just Blob Storage) + a filesystem, as a real
place to put Delta tables. No Databricks, no Synapse — the four scripts in
`examples/` talk directly to storage with the open-source `deltalake`
(delta-rs) Python library, which is enough to explore every core Delta Lake
concept: ACID commits, time travel, and schema enforcement/evolution.

> ⚠️ **This creates billable resources**, though only storage (no compute
> cluster runs anywhere in this setup) — a few files' worth of Parquet +
> JSON, effectively pennies. Run `terraform destroy` when done.

## "Azure Delta Lake" isn't one product

Delta Lake is an open-source *table format* (Linux Foundation project,
originally Databricks) — a specification for how to lay out Parquet files
plus a JSON transaction log so a set of files behaves like a real table
with ACID writes, time travel, and schema enforcement. Azure doesn't ship
a service called "Delta Lake" — what you actually pick is:

1. **ADLS Gen2** — the storage underneath (what this module provisions).
2. **A compute engine that understands the Delta format** — Azure
   Databricks (Spark, the fully-managed/production-typical pairing),
   Synapse Analytics Spark pools (on-demand Spark, no always-on cluster),
   or — what this module uses — nothing at all beyond a Python script and
   the open-source `deltalake` library, which implements the Delta
   protocol natively in Rust with no JVM/Spark involved.

The Python-only route is the cheapest and fastest way to actually see the
Delta format's mechanics (this is what every script below proves against
real storage), at the cost of not being the pattern a production data
platform typically runs at scale — see "If you want the full production
pattern" below for that trade-off spelled out.

## What ADLS Gen2 Actually Is

**It's not a separate storage service.** It's the exact same
`azurerm_storage_account` resource every other module in this repo uses,
`kind = "StorageV2"`, with one property flipped. Checked live against the
account this module created:

```json
{
  "kind": "StorageV2",
  "sku": "Standard_LRS",
  "isHnsEnabled": true,
  "primaryEndpoints": {
    "blob": "https://stdeltalakenlgx37.blob.core.windows.net/",
    "dfs":  "https://stdeltalakenlgx37.dfs.core.windows.net/",
    "file": "https://stdeltalakenlgx37.file.core.windows.net/",
    "queue": "https://stdeltalakenlgx37.queue.core.windows.net/",
    "table": "https://stdeltalakenlgx37.table.core.windows.net/",
    "web":  "https://stdeltalakenlgx37.z29.web.core.windows.net/"
  }
}
```

Same SKU, same replication, same billing as any other storage account.
`isHnsEnabled: true` is the entire difference this module's
`is_hns_enabled = true` line controls — and it's what makes a second
endpoint, `dfs.core.windows.net`, show up at all. That `dfs` endpoint is
the Data Lake filesystem API — `abfss://` URIs (what `abfss_uri_base`
outputs, and what every example script connects to) talk to it, not to
the plain `blob` endpoint.

**What flipping that one flag changes, concretely:**

- **Without it** (plain Blob Storage): a "folder" is fake. A blob named
  `orders/_delta_log/00000000000000000000.json` is really *one blob*
  whose name happens to contain slashes — there is no directory object
  anywhere. "Renaming a folder" means copying every blob under that
  prefix to new names and deleting the old ones, one blob at a time —
  not atomic, and O(number of files).
- **With it on** (ADLS Gen2): directories are real, first-class objects
  with their own metadata. Renaming or moving one is a single atomic
  metadata operation regardless of how many files live inside it. HNS
  also brings POSIX-style permissions — listing this module's actual
  filesystem shows exactly that model in the output:

  ```
  Group       IsDirectory  Owner       Permissions   Name
  $superuser  True         $superuser  rwxr-x---     orders
  $superuser  True         $superuser  rwxr-x---     orders/_delta_log
  $superuser  False        $superuser  rw-r-----     orders/_delta_log/00000000000000000000.json
  ```

  Plain Blob Storage has no equivalent concept — blobs don't have POSIX
  owners/groups/permission bits at all.

**Why this specifically matters for Delta Lake**: every write appends one
file to `_delta_log/` and Delta's reader has to reliably, cheaply list
"everything under this table's `_delta_log/` prefix, in order" on every
read. Real directories with real metadata make that listing efficient and
give dependable atomic-rename semantics for the write path — part of why
ADLS Gen2 (not plain Blob Storage) is the default substrate for lake
workloads on Azure generally, Delta Lake included.

## Usage

```bash
cd cloud-practice/azure/terraform/delta-lake
terraform init
terraform apply
```

## Run the demos

Each script in `examples/` is self-contained (own `uv` inline dependencies
— `uv run` fetches them on the fly, no venv to manage) and creates its own
table, so they can run in any order:

```bash
export STORAGE_ACCOUNT_NAME=$(terraform output -raw storage_account_name)
export STORAGE_ACCOUNT_KEY=$(terraform output -raw primary_access_key)
export FILESYSTEM_NAME=$(terraform output -raw filesystem_name)

uv run examples/01_create_and_append.py       # versions, append vs. overwrite
uv run examples/02_time_travel.py             # query an earlier version
uv run examples/03_schema_enforcement.py      # rejected write, then opt-in schema evolution
uv run examples/04_inspect_transaction_log.py # the ACID mechanism itself, read as plain JSON blobs
```

| Script | What it proves |
|---|---|
| `01_create_and_append.py` | A write is a new *version*, not an in-place mutation — appending never touches earlier files. |
| `02_time_travel.py` | Reading "as of version N" is just telling Delta which commit's file list to honor — every version's data is still sitting in storage. |
| `03_schema_enforcement.py` | An append with an unexpected column is rejected by default; schema changes require explicitly opting in (`schema_mode="merge"`). |
| `04_inspect_transaction_log.py` | Reads `_delta_log/*.json` directly with the plain Blob SDK (no Delta library) — proves the "transaction log" is just small, ordered JSON files, and explains how atomic file-creation on storage is the entire ACID mechanism. |

## How Delta Lake gets ACID out of plain files

The mechanism, confirmed live by `04_inspect_transaction_log.py`: every
write to a Delta table adds exactly one new, sequentially-numbered JSON
file under `<table>/_delta_log/` (`00000000000000000000.json`,
`00000000000000000001.json`, ...). Each file lists which Parquet file(s)
just got added (and, for deletes/updates, which got logically removed)
relative to the version before it. A reader's job is trivial: read every
commit file in order, replay "add"/"remove" entries, and it knows exactly
which Parquet files are live as of any version — including the latest.

The ACID part comes from one narrow guarantee the underlying storage
provides: **only one writer can successfully create a given filename when
it doesn't already exist** (an atomic "create-if-absent", not a
read-then-write race). If two processes both try to commit version 7 at
the same time, exactly one of their `00000000000000000007.json` creations
succeeds; the other sees the conflict and either retries as version 8 or
fails. There's no lock manager, no coordinator, no database underneath —
one storage-level atomicity primitive, applied per-commit, is the whole
mechanism.

This is also *why* ADLS Gen2's hierarchical namespace matters here (this
module's `is_hns_enabled = true`): the storage layer needs efficient,
metadata-only listing of `_delta_log/` and dependable path semantics —
plain Blob Storage historically lacked equivalent atomic rename guarantees
across renamed "directories," which is part of why Gen2 became the default
substrate for lake workloads on Azure, Delta or otherwise.

## If you want the full production pattern

Real deployments almost never run bare `deltalake`-against-storage at
scale the way this module's demos do — they run Spark (Databricks or
Synapse) so many executors can write/read Delta tables in parallel, use
Unity Catalog / a metastore for table discovery and access control, and
get `OPTIMIZE`/`VACUUM`/`Z-ORDER` maintenance operations that keep a table
performant as it accumulates many small files over months of writes. This
module deliberately skips all of that — it's the fastest path to
understanding the *format itself*, not a production reference architecture.
Point `azure_storage_account_name`/`abfss_uri_base` at a Databricks or
Synapse workspace's mounted storage to layer that on top; the underlying
storage account and Delta tables this module creates don't change.

## What's deliberately not here

No Databricks workspace, no Synapse workspace, no compute of any kind — by
design, per the "None — open-source Python" choice above. No `OPTIMIZE`/
`VACUUM`/compaction demo (relevant once a table has accumulated many small
files from many small writes; this demo's tables are too small to show
anything real). No concurrent-writer conflict demo (would need two
processes racing on purpose — the mechanism is explained in "How Delta
Lake gets ACID out of plain files" above instead of staged live).

## Teardown

```bash
terraform destroy
```

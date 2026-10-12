# 2. Delta Lake

## What it is

An open **table format**: Parquet data files plus a transaction log (`_delta_log/`) that defines
which files make up each version of the table. It adds database guarantees to object storage.

```
my_table/
├── _delta_log/
│   ├── 00000000000000000000.json     commit 0
│   ├── 00000000000000000001.json     commit 1
│   ├── ...
│   └── 00000000000000000010.checkpoint.parquet   snapshot of state at v10
├── part-0000-....snappy.parquet
└── part-0001-....snappy.parquet
```

Each commit lists **actions**: `add` (file), `remove` (file), `metaData` (schema, partitioning),
`protocol` (reader/writer versions), `commitInfo` (who/what/when), `txn` (streaming app progress).
The current table = replay the log (starting from the latest checkpoint) to get the live set of files.

## Anatomy of a table folder: every file you will see

A real listing from lesson 1 (`ls -a`, Delta 4.0.0 on a local disk):

```
orders/
├── _delta_log/
│   ├── 00000000000000000000.json            Delta   commit 0: the actions (add/metaData/protocol/commitInfo)
│   ├── 00000000000000000000.crc             Delta   version checksum for version 0
│   ├── 00000000000000000001.json            Delta   commit 1
│   ├── 00000000000000000001.crc             Delta   version checksum for version 1
│   ├── .00000000000000000000.json.crc       Hadoop  checksum OF the .json file
│   ├── .00000000000000000000.crc.crc        Hadoop  checksum OF the Delta .crc file
│   ├── .00000000000000000001.json.crc       Hadoop
│   ├── .00000000000000000001.crc.crc        Hadoop
│   └── _staged_commits/                     Delta   (empty here; see note below)
├── part-00000-<uuid>-c000.snappy.parquet    Spark   data file
├── .part-00000-<uuid>-c000.snappy.parquet.crc   Hadoop  checksum OF the data file
└── ...
```

| File | Written by | What it is | Needed? |
|---|---|---|---|
| `_delta_log/NNNN.json` | Delta | One commit: the list of actions. **This defines the table.** | **Yes** |
| `_delta_log/NNNN.checkpoint.parquet` | Delta | Snapshot of the full table state at version N, so readers skip replaying every commit (default: every 10 commits) | Optimisation, but readers expect it once written |
| `_delta_log/_last_checkpoint` | Delta | Pointer to the latest checkpoint | Optimisation |
| `_delta_log/NNNN.crc` | Delta | **Version checksum file**: JSON with table size, file count, and a copy of the metadata and protocol at that version. Used to validate state and load snapshots faster | Optional in the protocol; don't rely on it existing |
| `part-*.parquet` | Spark | A data file, referenced by an `add` action | **Yes** |
| `.<name>.crc` (leading dot) | **Hadoop** local filesystem | Checksum of the file named `<name>`, to detect corruption on read | No (not part of Delta) |
| `_staged_commits/` | Delta | Directory used by newer commit mechanisms; empty in this lab (purpose not verified here) | n/a |
| `col=value/` folders | Spark | Partition folders, when the table is partitioned | Yes, if partitioned |
| deletion vector files | Delta | Bitmaps of deleted rows, when deletion vectors are on | Yes, if referenced |

### The two kinds of `.crc`, and the `.crc.crc` confusion

- **`00000000000000000001.crc`** (no leading dot) is **Delta's** version checksum file. It is JSON; a
  version's file looked like `{"tableSizeBytes":3170,"numFiles":3,"numMetadata":1,"numProtocol":1,...,"metadata":{...}}`.
- **`.<anything>.crc`** (leading dot) is **Hadoop's**. When Spark writes through Hadoop's local
  filesystem, that layer adds a hidden checksum file beside **every** file it writes, including Delta's own `.crc`.
- So **`.00000000000000000001.crc.crc`** is Hadoop's checksum of Delta's checksum file:
  `.` + `00000000000000000001.crc` + `.crc`. And `.00000000000000000001.json.crc` is Hadoop's checksum of the commit file.
- On S3, ADLS and GCS these hidden files normally **do not appear**, because those filesystems don't add
  them. You mostly see them in local runs.

### Handling the hidden `.crc` files

- Safe to ignore. They are not part of the table.
- Don't delete them by hand from a table you still read through Hadoop's local filesystem: a missing
  checksum file is tolerated, but a file changed without updating its checksum gives a checksum error on read.
- Don't edit commit JSON or data files by hand for the same reason (and because it corrupts the table).
- When copying a table, copy the **whole folder including `_delta_log`**. Data files without the log are
  just Parquet files, and the log without its data files is a broken table.
- Tools that list "the files of a table" should ask Delta (`DESCRIBE DETAIL`, `DeltaTable.detail()`,
  or read the log), not list the directory: the folder also holds files that are no longer part of the
  current version until `VACUUM` removes them.

## ACID on object storage

- **Atomicity:** a commit is one log file written atomically. Either it exists or it doesn't.
- **Consistency:** schema enforcement and constraints reject bad writes.
- **Isolation:** **optimistic concurrency control**. Writers work against a snapshot, then try to
  commit version N+1. If someone else committed first, Delta checks for logical conflicts: if the
  files you read or changed were also changed, you fail (`ConcurrentModificationException`);
  otherwise it retries on top of the new version. Readers never block and see a consistent snapshot
  (snapshot isolation; the default write isolation level is *WriteSerializable*).
- **Durability:** data files are written before the commit, so committed data is on durable storage.

Updates and deletes never modify files in place. They **write new files and mark old ones removed**
(copy-on-write). Old files stay until `VACUUM`.

## Core features

### Time travel
```sql
SELECT * FROM t VERSION AS OF 5;
SELECT * FROM t TIMESTAMP AS OF '2026-01-01';
RESTORE TABLE t TO VERSION AS OF 5;
DESCRIBE HISTORY t;
```
Limited by `delta.logRetentionDuration` (30 days) and by `VACUUM` removing old files
(`delta.deletedFileRetentionDuration`, 7 days). **Time travel is not a backup**.

### Schema enforcement and evolution
- Default: a write whose schema doesn't match **fails**. That is enforcement.
- Evolution: `.option("mergeSchema", "true")` (append/overwrite) or `spark.databricks.delta.schema.autoMerge.enabled`
  for `MERGE`. Adds new columns; safe type widening only.
- `overwriteSchema` replaces the schema (use with care).
- **Column mapping** (`delta.columnMapping.mode = name`) allows renaming and dropping columns without rewriting data.

### MERGE (upsert)
```sql
MERGE INTO target t USING updates s ON t.id = s.id
WHEN MATCHED AND s.op = 'D' THEN DELETE
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
WHEN NOT MATCHED BY SOURCE THEN DELETE;      -- optional
```
- Needs a **unique key in the source**. Multiple source rows matching one target row = error.
- Cost: joins source to target, rewrites every file that has a match. Put the join key (or a
  partition/clustering column) in the `ON` condition so the scan prunes files.

### Constraints and generated columns
`NOT NULL`, `CHECK` constraints, **generated columns** (`GENERATED ALWAYS AS (...)`), identity columns.

### Change Data Feed (CDF)
`delta.enableChangeDataFeed = true`. Row-level changes with `_change_type`
(`insert`, `update_preimage`, `update_postimage`, `delete`), `_commit_version`, `_commit_timestamp`.
Used for incremental downstream propagation. Read with `readChangeFeed`.

### Deletion vectors
Instead of rewriting a file for a small delete/update, mark rows as deleted in a side file.
Much faster `DELETE`/`UPDATE`/`MERGE` on large files. Rows are physically removed at the next `OPTIMIZE`/`REORG`.

### Shallow and deep clone
`CREATE TABLE b SHALLOW CLONE a` copies only metadata (fast, shares files); `DEEP CLONE` copies data too.

### Identity and uniqueness
Delta does **not enforce primary keys** (they are informational in Unity Catalog). Uniqueness is
your pipeline's responsibility.

## Table layout and performance

### File sizing and the small-file problem
Many tiny files = slow reads (listing, per-file open cost). Fixes:
- `OPTIMIZE t` compacts small files into ~1 GB (bin-packing).
- **Auto optimize** (`optimizeWrite`, `autoCompact`) or **predictive optimization** (managed tables).

### Partitioning vs the alternatives

| Technique | How it works | Good for | Pitfall |
|---|---|---|---|
| **Partitioning** | One folder per value | Low-cardinality column used in filters (date, region); tables > ~1 TB | High cardinality → millions of tiny files |
| **Z-ORDER** (`OPTIMIZE t ZORDER BY (a,b)`) | Co-locates related values in the same files, using file-level min/max stats | 1–4 high-cardinality filter columns | Rewrites data; each `OPTIMIZE` re-sorts; not incremental |
| **Liquid clustering** (`CLUSTER BY (a,b)`) | Incremental, changeable clustering | Replaces partitioning + Z-ORDER for most new tables | Newer feature; check support for your runtime |
| **Bloom filter index** | Probabilistic point-lookup index | Needle-in-haystack equality on a high-cardinality column | Niche |

**Data skipping:** Delta stores min/max/null-count stats for the first 32 columns per file (by
default). Queries skip files whose range can't match. Stats only help if the data is *clustered*
on the filter column, which is why Z-ORDER/clustering matters. Reorder columns or set
`delta.dataSkippingNumIndexedCols` if your filter column is beyond the first 32.

### Maintenance commands
| Command | Does | Notes |
|---|---|---|
| `OPTIMIZE t [ZORDER BY]` | Compact files | Run on a schedule or use auto compaction |
| `VACUUM t [RETAIN n HOURS]` | Delete files no longer referenced and older than retention | Default 7 days. Shorter than the longest-running reader/stream breaks them |
| `ANALYZE TABLE t COMPUTE STATISTICS` | Optimizer stats for query planning | |
| `DESCRIBE HISTORY / DETAIL` | Inspect | |
| `REORG TABLE ... APPLY (PURGE)` | Physically remove deleted rows (with deletion vectors) | |

`VACUUM` deletes files; it never changes the table's current contents. Only run `VACUUM` with a
retention under 7 days if you are certain no reader or stream needs older versions.

## Delta protocol and compatibility
Tables record **minReaderVersion / minWriterVersion** plus named **table features**. Enabling a
feature (deletion vectors, column mapping) can make the table unreadable by older clients. Upgrades
are one-way in practice.

## Delta vs Parquet vs Iceberg vs Hudi

| | Parquet (plain) | Delta | Iceberg | Hudi |
|---|---|---|---|---|
| ACID | No | Yes | Yes | Yes |
| Metadata | Folder listing | JSON log + checkpoints | Manifest tree (snapshots) | Timeline |
| Upserts | Rewrite whole partitions | `MERGE` | `MERGE` | Strong, record-level index |
| Engines | Everything | Spark-first; many others via connectors/UniForm | Broadest multi-engine support | Spark/Flink |
| Hidden partitioning | No | Via clustering/generated columns | Yes | No |

**UniForm** lets a Delta table expose Iceberg (and Hudi) metadata so other engines can read it.

## Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `ConcurrentAppendException`, `ConcurrentDeleteReadException` | Two writers touching overlapping files | Partition/narrow `ON` conditions, serialise the writers, retry |
| `DeltaAnalysisException: schema mismatch` | Schema enforcement | `mergeSchema` or fix the source |
| `FileNotFoundException` on old reads | `VACUUM` removed files a long reader needed | Longer retention |
| Slow reads, millions of files | Small files, over-partitioning | `OPTIMIZE`, change partition strategy |
| `MERGE` is slow | No pruning in `ON`, large target | Add partition/cluster predicates; deletion vectors |
| Multiple source rows matched | Duplicate keys in source | Deduplicate source first |

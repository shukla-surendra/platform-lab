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

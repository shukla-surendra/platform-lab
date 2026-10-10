# Hard Databricks and data-engineering interview questions

Answers are written the way you'd say them: the core claim first, then the reasoning. "Follow-up"
lines are what a good interviewer asks next. Difficulty: ★ standard, ★★ senior, ★★★ staff-level.

Sections: [Delta Lake](#delta-lake) · [Spark internals and performance](#spark-internals-and-performance) ·
[Streaming](#streaming) · [Platform and governance](#platform-and-governance) ·
[Pipeline design](#pipeline-design) · [Debugging scenarios](#debugging-scenarios) · [System design](#system-design)

---

## Delta Lake

### 1. How does Delta Lake provide ACID on object storage, which has no transactions? ★★
Object stores give atomic put-per-object and (now) strong consistency, but no multi-file transactions.
Delta writes new Parquet files first (invisible, because nothing references them), then **commits by
atomically creating the next numbered log file** (`N.json`) using *put-if-absent* semantics. A table
version is only the set of files listed by replaying the log, so readers see all of a commit or none of it.
Concurrency uses **optimistic concurrency control**: writers read a snapshot, do the work, and try to
commit version N+1. If the file already exists, someone won; Delta checks whether the winning commits
conflict logically with what this transaction read or wrote, and retries or fails.
Follow-up: *on S3 without strong put-if-absent?* Older S3 needed a DynamoDB log store for multi-cluster
writes; S3 now supports conditional writes, and Databricks handles this for you.

### 2. Two jobs write to the same Delta table at once. What happens? ★★
It depends on what they touch. Two **appends** both succeed (they don't read anything the other writes).
Two `MERGE`/`UPDATE`/`DELETE` that **touch the same files** → the second to commit fails with
`ConcurrentAppendException`/`ConcurrentDeleteReadException`/`ConcurrentDeleteDeleteException`.
Reduce conflicts by making operations **disjoint**: partition the table and put the partition column in
the `ON`/`WHERE` clause so each job only reads/writes its own files (this is how isolation level
`WriteSerializable` lets disjoint writers coexist). Otherwise serialise the writers or retry.
Row-level concurrency (newer runtimes with deletion vectors) narrows conflicts further.

### 3. `MERGE` fails with "multiple source rows matched". Why, and how do you fix it properly? ★
`MERGE` must be deterministic: one target row can be changed by at most one source row. Duplicate keys
in the source violate that. Deduplicate the source *before* merging, keeping the latest per key with a
deterministic ordering and tie-breaker (`row_number()` over `partition by key order by seq desc, ingested_at desc`).
Don't use `dropDuplicates(["key"])`: it keeps an arbitrary row.

### 4. Why is `MERGE` slow on a 5 TB table, and how do you speed it up? ★★★
`MERGE` joins source to target to find matches, then **rewrites every file containing at least one
match** (copy-on-write). So cost scales with files touched, not rows changed. Speed-ups:
1. Make the `ON` condition prune: include the partition/clustering column (`t.dt = s.dt AND t.id = s.id`),
   or add a predicate to scan only the relevant slice.
2. Cluster/Z-ORDER the target on the merge key so matches concentrate in few files.
3. Enable **deletion vectors** so small updates don't rewrite whole files.
4. Make the source small and unique; consider broadcasting it.
5. Enable optimized writes / avoid tiny files; run `OPTIMIZE` regularly.
6. For append-mostly data, consider an insert-only merge, or splitting "new" from "changed" rows.
Follow-up: *how do you detect which files are rewritten?* `DESCRIBE HISTORY` operation metrics
(`numTargetFilesAdded/Removed`, `numTargetRowsUpdated`).

### 5. Z-ORDER vs partitioning vs liquid clustering. When do you use each? ★★
- **Partitioning:** physical folders. Good for **low-cardinality** columns filtered nearly every query (date),
  and tables large enough that each partition is ≥ ~1 GB. Over-partitioning → small-file hell. Can't change cheaply.
- **Z-ORDER:** multi-dimensional sorting inside files so min/max stats become selective for 1–4 columns.
  Not incremental (each `OPTIMIZE ZORDER` re-sorts), and effectiveness decays as data arrives.
- **Liquid clustering:** the modern replacement for both for most new tables: incremental, can change
  keys without rewriting everything, handles skew and high cardinality. Use `CLUSTER BY`.
Choose partitioning only when you also need partition-level operations (delete/replace a day, retention by partition).

### 6. What does `VACUUM` do, and why can it break a running stream or a long query? ★★
It physically deletes data files that are no longer referenced by the current table version **and** are older than the
retention period (default 7 days). Time travel and any reader still using an older snapshot depend on
those files. A long-running job or a stream that is far behind and reads an older version fails with
`FileNotFoundException` if `VACUUM` removed them. Don't set retention below your longest reader/stream
lag or the checkpoint horizon. Delta also refuses retention < 7 days unless you disable the safety check.
It also doesn't clean `_delta_log`; that expires by `logRetentionDuration`.

### 7. Time travel: how does it work and what are its limits? ★
Version N is just the log replayed up to N, so reading an old version means listing the files that were
live then. It works while the data files exist (not vacuumed) and the log entries are retained
(`logRetentionDuration`, 30 days). It is **not backup**: it lives in the same storage, same table, and
can be vacuumed. Use clones or replicated storage for recovery. `RESTORE` rewrites the table state back
to an old version as a **new commit** (history is preserved).

### 8. What are deletion vectors and why do they matter? ★★
Instead of rewriting a Parquet file to remove or change a few rows, Delta writes a small bitmap listing
deleted row positions; readers filter them out. `DELETE`/`UPDATE`/`MERGE` become much cheaper
(merge-on-read for the delete half). The cost moves to reads (apply the vectors) until `OPTIMIZE`/
`REORG ... PURGE` rewrites the files. Also relevant for GDPR deletes: rows are *logically* deleted
immediately but physically removed only after a rewrite **and** a `VACUUM` of the old files.

### 9. How do you handle GDPR "right to be forgotten" in a Delta lake? ★★★
Time travel and old files keep the data. Process: `DELETE` the rows (use a key-lookup optimised table or
clustering on the user id to avoid scanning everything), then if deletion vectors are on, run
`REORG TABLE ... APPLY (PURGE)` to rewrite files, then `VACUUM` after the retention period so old
versions disappear. Also cover: bronze copies, downstream gold tables, ML features, backups,
CDF history, streaming checkpoints, logs. Best design: **keep PII in a small separate table keyed
by a surrogate id** so deletion is cheap and the rest of the lake never holds raw PII; or use
crypto-shredding (delete the user's encryption key).

### 10. Schema evolution: what is safe, and what breaks? ★★
Adding nullable columns is safe (`mergeSchema`). Type **widening** (int→long) is supported on newer
tables with the feature enabled. Renaming/dropping needs **column mapping** (otherwise physical Parquet
column names would have to change). Narrowing types, or changing nullability from nullable to
non-null, requires a rewrite. For streams, a schema change in the source can fail the query until it
restarts (Auto Loader `addNewColumns` fails once by design, then picks up the new schema).
Downstream consumers need a contract; evolution at bronze, controlled promotion into silver.

### 11. Delta vs Iceberg: what actually differs? ★★
Both are ACID table formats on Parquet. Delta: linear JSON log + checkpoints, tight Spark/Databricks
integration, deletion vectors, liquid clustering. Iceberg: tree of metadata (snapshot → manifest list →
manifests), hidden partitioning and partition evolution, broad multi-engine support (Trino, Flink,
Snowflake, etc.). Practically the gap is narrowing: **UniForm** lets one table be read as Delta and
Iceberg, and Unity Catalog can expose Iceberg REST. Decide on engine/ecosystem, not on features.

### 12. What is the Change Data Feed and when would you not use it? ★★
CDF records row-level changes (insert, update pre/post-image, delete) per commit so downstream jobs can
process **only what changed** without diffing. Not for: tables with a huge change volume where storage
overhead matters, or when append-only streaming reads are enough. Remember retention is tied to `VACUUM`,
and enabling it only records changes **from that version onward**.

---

## Spark internals and performance

### 13. Walk me through what happens when you run `df.groupBy("k").count().write...`. ★★
Driver parses the DataFrame ops into a logical plan → Catalyst optimises (pushdown, pruning) → physical
plan (HashAggregate partial → Exchange hashpartitioning(k) → HashAggregate final). The action `write`
triggers a job split into **two stages** at the shuffle. Stage 1: each task reads a partition, does a
partial aggregation, writes shuffle files. Stage 2: each task fetches its hash-range of shuffle blocks
from all stage-1 outputs, merges, and writes output files. AQE may coalesce the shuffle partitions at
runtime. The partial aggregation is why `count` per key is cheap even on large data.

### 14. A job has one task that runs 30 minutes while others finish in 20 seconds. Diagnose and fix. ★★★
That's **skew**. Confirm in the Spark UI stage page: task duration/shuffle-read max ≫ median, maybe spill
on one task. Find the hot key (`groupBy(key).count()`), often `NULL` or a default/"unknown" value.
Fixes in order: (1) is AQE skew-join enabled and kicking in (look for `skew` in the plan)? (2) broadcast
the smaller side if it fits; (3) filter/handle the hot key separately (`NULL` rows never match anyway
in an inner join); (4) **salting**: add `salt = rand()*N` to the big side, explode the small side
across `0..N-1`, join on `(key, salt)`, aggregate afterward; (5) for aggregations, two-phase
aggregation with a salt. Don't just add nodes; one partition is one core.

### 15. Explain broadcast join vs sort-merge join, and what AQE changes. ★★
Broadcast: ship the small table to every executor; no shuffle of the large side. Sort-merge: shuffle
and sort both sides by the key, then merge. Normally decided from **estimated** size vs
`autoBroadcastJoinThreshold`; estimates are often wrong after filters/joins. AQE re-plans at runtime
with **actual** shuffle sizes and can switch to broadcast, coalesce partitions, and split skewed
partitions. Limits: AQE needs a shuffle boundary to re-plan, and it can't fix skew in aggregations
or in cases where both sides have the same hot key without further handling.

### 16. Why are Python UDFs slow and what are the alternatives? ★★
Each row is serialised from the JVM to a Python worker process and back, with no vectorisation,
and Catalyst can't optimise or push down through them. Alternatives, best first: built-in functions /
SQL expressions; **pandas UDFs** (Arrow batches, vectorised); `mapInPandas` / `applyInPandas` for
group-wise logic; Scala/Java UDFs; or push the logic into SQL. If a UDF is unavoidable, make it
deterministic, avoid per-row network calls (batch them), and keep heavy initialisation outside the row
function.

### 17. What is a shuffle and why is it expensive? How do you reduce them? ★
Redistributing data across partitions by key: map tasks write partitioned shuffle files to local disk,
reduce tasks fetch over the network, which costs disk I/O, serialisation, network, and often spill.
Reduce by: filtering and projecting before wide operations; broadcast joins; pre-aggregating; using
bucketed/co-partitioned tables (rarely), avoiding unneeded `distinct`/`orderBy`/`repartition`;
combining several wide operations on the same key so they reuse one partitioning.

### 18. `repartition` vs `coalesce`. When does `coalesce` hurt? ★
`repartition(n)` does a full shuffle and gives balanced partitions (can grow or shrink). `coalesce(n)`
only merges existing partitions without a shuffle (shrinks only). It's cheaper, but can produce
**uneven partitions** and, because it narrows the *whole upstream stage*, can reduce the parallelism of
the expensive computation before it (the entire stage runs with n tasks). Use `repartition` when
upstream work is heavy; `coalesce` for final cheap file-count reduction.

### 19. How does Spark decide the number of tasks and files written? ★★
Read: file splits (~128 MB each, `maxPartitionBytes`; small files are packed together up to
`openCostInBytes` logic). After a shuffle: `spark.sql.shuffle.partitions` (AQE coalesces). Write: **one
file per task per partition value**, so 200 tasks × 365 partition values can mean 73,000 files. Control with
`repartition(partitionCols)` before write, optimized writes, `maxRecordsPerFile`, and `OPTIMIZE`.

### 20. Your Spark job OOMs on the driver. Likely causes? ★★
`collect()`/`toPandas()`/`take(big)`; broadcasting a table that's bigger than expected; listing a table
with millions of files (driver holds the file index); huge numbers of partitions/tasks (task metadata);
accumulating large state in Python; very wide plans (loops with `withColumn`/`union`). Fix by
aggregating before collecting, raising driver memory only as a last resort, reducing file counts,
and restructuring plans.

### 21. What does `cache()` really do, and when is it harmful? ★
It marks a DataFrame to be stored (default memory-and-disk) **the first time an action computes it**.
Helpful when the same expensive DataFrame feeds several actions in one job. Harmful when used once
(extra cost), when it evicts execution memory (causing spill), when the data changes underneath (stale),
or when never `unpersist`ed. On Databricks, the **disk cache** already speeds repeated Parquet/Delta
reads, so `cache()` is rarely needed for plain reads.

### 22. Narrow vs wide dependencies, and why does it matter for fault tolerance? ★★
Narrow: each child partition depends on one parent partition (pipelined, a lost partition is recomputed
alone). Wide: child depends on many parents (shuffle). Fault recovery after losing an executor's shuffle
output re-runs the parent stage tasks that produced the missing blocks. That's why shuffle-heavy jobs
suffer on spot instance loss, and why the external shuffle service / shuffle persistence helps.

### 23. What are the limits of data skipping, and how do you make it effective? ★★
Skipping uses per-file min/max/null counts for (by default) the first 32 columns. It works only if values
for the filter column are **clustered**: random distribution makes every file's range overlap the filter.
Make it effective via Z-ORDER/liquid clustering, sorting before write, putting filter columns early
or raising `dataSkippingNumIndexedCols`, avoiding functions on the filter column (`WHERE date(ts)=...`
may block pushdown), and keeping files reasonably sized (huge files → coarse stats).

---

## Streaming

### 24. How does Structured Streaming achieve exactly-once? ★★
Three parts: a **replayable source** (offsets can be re-read), a **checkpoint** that durably records
offsets and state per micro-batch (write-ahead log: offsets are recorded *before* processing, commits
after), and an **idempotent sink**. Delta is idempotent because each batch commits with a `(queryId, batchId)`
transaction marker; a replayed batch whose id is already committed is skipped. Custom `foreachBatch`
sinks must be made idempotent by you (MERGE by key, or check `batch_id`). The guarantee is end-to-end
only if all three hold.

### 25. Explain watermarks. What happens to late data and to state? ★★
A watermark is `max(event_time seen) − allowed lateness`. It tells Spark when a window is **complete**, so
it can emit final results (append mode) and **drop state** for older windows. Events older than the
watermark are discarded from stateful aggregations (silently). Without a watermark, state for
aggregations, dedup and stream-stream joins grows forever, and append mode isn't allowed for
aggregations. Trade-off: bigger lateness → more correct, more state, higher latency.
Follow-up: *multiple streams?* The global watermark is the **minimum** across inputs (default policy).

### 26. A stream's batch time keeps growing. How do you find out why? ★★★
Check `lastProgress`: input rate vs processing rate, per-operator durations, **state rows / memory**. Causes: unbounded
state (missing watermark, high-cardinality keys), skew, small files in the source or sink, slow
`foreachBatch` logic (unpruned `MERGE` getting slower as the target grows), undersized cluster, source
throttling (`maxFilesPerTrigger`/`maxOffsetsPerTrigger`), many tiny micro-batches creating files.
Fix according to the cause: bound state, prune merges, enable optimized writes + compaction, scale compute.

### 27. You changed a streaming query and it won't restart from the checkpoint. Why? ★★★
Checkpoints store operator state keyed by operator ids and schema. Changing stateful logic (aggregation keys,
adding/removing a stateful operator, changing the join, changing `shuffle.partitions` of a stateful query,
or the schema of state) makes the saved state incompatible. Stateless changes (filters, projections,
sink options) are usually fine. Options: keep the change compatible; or start a **new checkpoint** and
choose the start point deliberately (`startingVersion`/`startingOffsets`) and backfill/replay to rebuild
state. This is why lower environments should exercise checkpoint upgrade paths.

### 28. Auto Loader vs `COPY INTO` vs plain `readStream.format("json")`. ★★
Plain file source lists the whole directory every batch; cost grows with directory size.
`COPY INTO` is a SQL command, idempotent, tracks loaded files, great for modest file counts, no streaming.
Auto Loader scales to billions of files (incremental listing or cloud notifications), tracks state in
RocksDB in the checkpoint, handles schema inference/evolution and rescued data, and works as streaming
or scheduled `availableNow`. Caveat: Auto Loader doesn't notice a file **overwritten in place** (it tracks
paths); design sources as immutable, uniquely-named files.

### 29. Streaming vs scheduled batch: how do you choose? ★
Pick on the latency requirement and cost. Minutes-to-hours: scheduled `availableNow` incremental job
(same code, no 24/7 cluster, simpler operations, easier backfills). Seconds: continuous micro-batch on a
dedicated cluster. Sub-second: specialised engines. "Real-time" is usually a business word for "within
15 minutes", so ask for the actual SLA.

---

## Platform and governance

### 30. Explain the Unity Catalog permission model. Why does a user with `SELECT` still get denied? ★★
Hierarchy: metastore → catalog → schema → table. To read a table you need `SELECT` on it, **plus** `USE SCHEMA`
on its schema, **plus** `USE CATALOG` on the catalog. Privileges inherit down, so granting `SELECT` on a
schema covers its tables including future ones. Common denial causes: missing a `USE` privilege; the
principal is a service principal that lacks what *you* personally have; compute in a legacy no-isolation mode;
the table is behind a view owned by someone without access (views run with the owner's rights for the underlying
tables); path-based access without an external location grant.

### 31. Managed vs external tables: tradeoffs and what `DROP` does. ★
Managed: UC owns the storage location and lifecycle; `DROP` removes data too (recoverable for a window
with `UNDROP`); benefits from automated maintenance. External: data at a path you control and may
share with other tools; `DROP` removes only metadata. Default to managed; use external when other
systems must read/write the same files, or when location is mandated.

### 32. How would you implement row- and column-level security? ★★
UC **row filters** (a SQL UDF returning boolean, attached to the table) and **column masks** (a UDF
returning the masked value, attached to the column), keyed on group membership
(`is_account_group_member`). Versus dynamic views: filters/masks attach to the table, so they apply on every access path;
dynamic views are bypassed if users can query the base table. Combine with tags to find PII, keep
grants group-based, and test as a non-privileged user.

### 33. Dev/staging/prod on Databricks: how would you structure it? ★★
Separate **catalogs** per environment (and optionally separate workspaces, attached to the same or
different metastores). Code in Git; **Asset Bundles** deploy identical definitions with per-target
overrides (catalog name, cluster size, schedule). Production jobs run as **service principals** with
narrowly scoped grants; humans have read access. CI runs unit tests on local Spark, deploys to staging,
runs integration tests on sample data, then promotes. Workspace bindings restrict prod catalogs to the prod workspace.
Infrastructure (workspaces, metastore, policies) via Terraform.

### 34. How do you keep Databricks costs under control for a large team? ★★
Cluster **policies** (limits, mandatory tags, auto-termination), job clusters for production, serverless
for spiky workloads, spot workers, autoscaling bounds, tagging for chargeback, budgets and alerts built on
`system.billing.usage`, scheduled incremental jobs instead of 24/7 streams, and fixing inefficient queries
before adding capacity. Review top-N costly jobs monthly.

### 35. What does Photon change, and when does it not help? ★★
Photon is a native vectorised execution engine running Spark SQL/DataFrame operators (scans, filters, joins,
aggregations, Delta writes) faster with the same API. It helps CPU-bound SQL-heavy work. It doesn't speed up
Python UDFs, RDD code, tiny jobs dominated by startup, or I/O-bound/shuffle-skew-bound jobs. DBU rate is higher, so
check that wall-clock savings outweigh it.

---

## Pipeline design

### 36. Design an idempotent daily load so a rerun or backfill is safe. ★★
Parameterise by the processing date. Read the source slice for exactly that date (no `now()`). Write using
**`replaceWhere`** on the date partition (atomic overwrite of just that slice) or `MERGE` on the business key.
Keep ingestion metadata so retries reproduce the same output. Store no state outside the table,
or write state transactionally. Test by running the same date twice and diffing the table.

### 37. Implement SCD Type 2 in Delta. What are the pitfalls? ★★★
`MERGE` with a staged source: for each changed key emit two rows: one with the real key (matches and closes the
current row: `is_current=false, valid_to=effective_ts`) and one with a `NULL` merge key (doesn't match, inserts
a new current row). Pitfalls: multiple changes for one key in one batch (order by sequence and process each, or
collapse deliberately), late-arriving changes (must re-sequence history; naive merge appends in the
wrong order), detecting change (compare a hash of tracked columns, mind `NULL` semantics with `<=>`),
non-overlapping validity intervals, concurrency with other merges, and the cost of merging a big dimension.
Lakeflow's `APPLY CHANGES … STORED AS SCD TYPE 2` handles ordering for you.

### 38. How do you ingest a CDC feed (inserts/updates/deletes) into a Delta table correctly? ★★★
Order by the **source sequence** (LSN/commit timestamp), not by arrival. Within each micro-batch collapse to the
last change per key. `MERGE`: delete when `op='D'`, update when matched **and** `s.seq > t.seq` (ignore stale/late
events), insert otherwise. Prefer soft deletes if you need audit or late-event safety. Handle schema drift from the
source, initial snapshot + incremental changes handoff (don't lose or duplicate the overlap), and keep
raw CDC in bronze so you can replay.

### 39. Data arrives late, up to 3 days. How do you keep daily aggregates correct? ★★
Don't assume yesterday's partition is final. Options: (a) **reprocess a sliding window** (the last 3-4 days)
every run using `replaceWhere` — simple and idempotent; (b) stream with a 3-day watermark (large state,
latency); (c) incremental `MERGE` of corrections into the aggregate table; (d) lambda-style "provisional + final"
tables. Communicate freshness semantics to consumers ("final after T+3").

### 40. Bronze/silver/gold: what belongs where, and what goes wrong? ★
Bronze: raw, immutable, replayable. Silver: validated, deduplicated, typed. Gold: business models.
Failures: cleaning data in bronze (can't replay), business logic duplicated across gold tables,
silver tables with no contract, sources that bypass silver, and analysts querying bronze.
Add data-quality gates between layers and a clear owner per layer.

### 41. How do you make a Spark pipeline testable? ★
Separate pure transformations (`def transform(df) -> df`) from I/O. Unit test with small in-memory DataFrames
on a local Spark session, covering nulls, duplicates, empty inputs, late rows, schema changes. Integration
tests on a staging catalog with sample data. Assert row counts, uniqueness and null rates after runs.
Keep notebooks thin; business logic in a versioned library.

---

## Debugging scenarios

### 42. Yesterday the job took 20 minutes; today it takes 3 hours. Nothing was deployed. ★★★
Check, in order: **data volume or skew change** (a new hot key, a partition much bigger than usual); **small
files accumulated** (no `OPTIMIZE`, a streaming writer making many files); **a broadcast that no longer fits**,
so the plan fell back to sort-merge (compare plans); **cluster change** (spot loss, fewer nodes, a different
runtime/Photon setting); **upstream late/backfilled data** inflating the input; **concurrency** (another job on the
shared cluster, `MERGE` conflicts retrying). Use the Spark UI of both runs side by side: the stage that changed
tells you which category.

### 43. A `MERGE` that worked for months now fails with `ConcurrentAppendException`. ★★
A new concurrent writer or a changed overlap. Find out which operations committed in between (`DESCRIBE HISTORY`).
Fix by partitioning/clustering and adding the partition predicate to `ON`, separating writers to disjoint partitions,
serialising with a lock or a single writer queue, or retrying with backoff. If a new `OPTIMIZE` job runs concurrently,
note compaction can conflict with long merges: schedule them apart (or rely on managed maintenance).

### 44. Row counts differ between source and a Delta table after an Auto Loader ingest. ★★★
Possibilities: files **overwritten in place** after being ingested (not re-read); schema mismatch rows went to
`_rescued_data` or were nulled; malformed records dropped under `DROPMALFORMED`; file filters/glob patterns excluded
files; a deleted/recreated checkpoint reprocessed files and duplicated rows; the downstream transformation deduplicated or
filtered; the source count includes records still in flight. Reconcile per file (`_metadata.file_path`) to find which
files differ, and inspect `_rescued_data`.

### 45. Your streaming job is correct locally but has duplicate rows in production after a restart. ★★★
The sink isn't idempotent or the checkpoint was lost/changed: a `foreachBatch` doing plain `INSERT`/append
(a replayed batch inserts twice), a new checkpoint path on redeploy (re-reads from the beginning), at-least-once
upstream (Kafka producer retries without idempotence), or Auto Loader with files re-delivered under new names.
Fix: `MERGE` by business key (or Delta `txnAppId/txnVersion` per batch), keep checkpoints stable across
deployments, dedup within the watermark window.

### 46. A table has 4 million tiny files. What do you do, and how do you prevent it? ★★
Immediate: `OPTIMIZE` (in chunks by partition with a `WHERE` if it's huge), then `VACUUM` after retention. Find
the cause: over-partitioned (high-cardinality partition column), many small streaming micro-batches, or a
wide `repartition` before a partitioned write. Prevent: optimized writes + auto compaction, fewer partitions or
liquid clustering, `availableNow` triggers with bigger batches, predictive optimization on managed tables.

---

## System design

### 47. Design a lakehouse for 500 sources, mixed batch and streaming, with PII and multiple teams. ★★★
Layers and responsibilities:
- **Ingestion:** Auto Loader for files, Kafka/Kinesis streaming for events, CDC tools for databases, Lakeflow
  Connect for SaaS. All land raw in bronze with lineage metadata. Metadata-driven ingestion (config table
  defines source → target) so adding a source isn't new code.
- **Processing:** Lakeflow Declarative Pipelines or jobs for silver/gold; shared libraries; expectations for quality gates;
  quarantine tables.
- **Storage/format:** Delta in UC managed locations; liquid clustering; predictive optimization.
- **Governance:** Unity Catalog with catalogs per domain/environment, groups-based grants, PII tags with
  column masks / row filters, lineage, audit via system tables, Delta Sharing for external consumers.
- **Platform:** Terraform for infrastructure; Asset Bundles + CI/CD for workloads; service principals;
  cluster policies and cost tags; separate dev/stage/prod.
- **Operations:** monitoring on freshness/volume/failure, SLAs per data product, on-call runbooks, DR plan.
Call out trade-offs: central platform team vs domain ownership (data mesh), schema contracts between producers
and the lake, cost allocation, and a deprecation process for unused tables.

### 48. Migrate a 200-table Hive/warehouse workload to Databricks with minimal downtime. ★★★
Inventory and classify tables (size, change rate, consumers, SLAs). Land historical data into Delta via bulk load
or `CONVERT TO DELTA`/`DEEP CLONE` where already Parquet. Run **dual pipelines** (old and new) with automated
reconciliation (row counts, checksums, business totals) per table until parity is proven. Migrate by
consumer group, not by table, behind views so cutover is a view repoint. Convert SQL dialect issues and UDFs,
re-implement scheduling as Jobs/Lakeflow, set UC governance up front, then decommission. Risk register: type
and null semantics differences, timestamp/timezone handling, sort-order dependence, hidden consumers.

### 49. Real-time dashboard with 5-second freshness on clickstream: how and what are the limits? ★★★
Kafka → Structured Streaming (micro-batch, 1–5 s trigger) → Delta silver → incremental aggregates into a gold table
→ SQL warehouse/serving layer. Limits: small-file creation from frequent commits (use optimized writes, compaction),
checkpoint and commit overhead floor of ~seconds, warehouse cache/refresh behaviour, and the cost of an always-on
cluster. If the real SLA is sub-second or requires high-concurrency point lookups, use a serving store (e.g. an
OLAP DB or key-value store) fed from the stream, and keep Delta as the system of record.

### 50. How would you prove a refactored pipeline produces identical results? ★★
Run old and new on the same frozen input snapshot (Delta version pin / clone). Compare with a full outer join on the
business key and a row hash: counts missing on each side, rows with differing hashes, then column-level diffs of a
sample. Check aggregates and distributions, tolerance for floating point, nondeterministic ordering, and
timestamp semantics. Automate it as a regression test and keep it for future changes.

---

## Rapid-fire (one-line answers)

| Question | Answer |
|---|---|
| Default `shuffle.partitions`? | 200 (AQE coalesces) |
| Default broadcast threshold? | 10 MB |
| Default `VACUUM` retention? | 7 days (168 hours) |
| Default log retention? | 30 days |
| Stats collected on how many columns? | First 32 |
| Does Delta enforce primary keys? | No (informational constraints only) |
| `DROP` of an external table? | Removes metadata, keeps data |
| What triggers a Spark job? | An action |
| Can `OPTIMIZE` break readers? | No, it's a normal commit; old files stay until vacuum |
| `cache()` vs `persist()`? | `cache()` = `persist(MEMORY_AND_DISK)` for DataFrames |
| Streaming checkpoint shared between queries? | Never |
| `foreachBatch` delivery guarantee? | At-least-once unless you make it idempotent |
| Where does the DAG of stages split? | At shuffle (wide) dependencies |
| Job vs all-purpose cluster cost? | Job compute has the lower DBU rate |
| Which join for two big tables? | Sort-merge (AQE may adapt) |
| Why is `count(distinct)` costly? | Needs a shuffle to deduplicate per group |
| `union` vs `unionByName`? | Position vs column-name matching |
| Cheap emptiness check? | `df.isEmpty()` / `limit(1)`, not `count()` |

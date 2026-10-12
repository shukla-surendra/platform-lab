# 7. Data engineering patterns

Concepts that apply on Databricks and anywhere else. Lessons 7 and 8 implement several of them.

## Load strategies

| Strategy | How | Good for | Risk |
|---|---|---|---|
| **Full refresh** | Rebuild the whole table each run | Small tables, simple logic | Cost grows with data |
| **Incremental append** | Add only new records (by watermark column or file arrival) | Immutable events/logs | Missed late rows; no handling of updates |
| **Incremental upsert (`MERGE`)** | Apply inserts, updates, deletes by key | Mutable entities (customers, orders) | Duplicate source keys; merge cost |
| **Partition overwrite (`replaceWhere`)** | Rewrite one day/partition atomically | Idempotent daily batches, reprocessing | Needs a clear partition column |
| **CDC apply** | Replay a change stream (insert/update/delete) | Mirroring an operational DB | Ordering, deletes, schema changes |

### Watermarks for incremental batch
Store the high-water mark (max `updated_at` or max ingested id) after a successful run; next run reads
`WHERE updated_at > :last`. Pitfalls: late-arriving rows with an older timestamp, clock skew,
non-monotonic ids. Mitigate with an **overlap window** (re-read the last N hours) combined with an idempotent `MERGE`.

## Deduplication

Keep the **latest row per key**:

```python
from pyspark.sql import Window
from pyspark.sql.functions import row_number, col
w = Window.partitionBy("customer_id").orderBy(col("updated_at").desc(), col("_ingested_at").desc())
latest = df.withColumn("rn", row_number().over(w)).filter("rn = 1").drop("rn")
```
Always include a **deterministic tie-breaker** in the ordering, or reruns can pick different rows.
`dropDuplicates(["key"])` keeps an *arbitrary* row, so never use it when you need the latest.

## Slowly changing dimensions (SCD)

| Type | Behavior | History? |
|---|---|---|
| 0 | Never changes | n/a |
| **1** | Overwrite | No |
| **2** | New row per change, with `valid_from`, `valid_to`, `is_current` | Yes |
| 3 | Previous value in an extra column | Only one step |

SCD2 `MERGE` pattern:
1. Find incoming rows whose tracked attributes differ from the current row.
2. Close the current row (`valid_to = now`, `is_current = false`).
3. Insert a new current row.

A one-statement trick: union the changed rows twice, once with a `NULL` merge key (so they hit
`WHEN NOT MATCHED` and insert as the new version) and once with the real key (so they hit
`WHEN MATCHED` and close the old one). Lesson 7 does this.

Point-in-time join: `fact.event_time >= dim.valid_from AND fact.event_time < dim.valid_to`.

## CDC (change data capture)

Records changes with an operation (`I`/`U`/`D`), a **sequence** (LSN, timestamp, version) and the key.

Rules for applying:
- Order by the **source sequence**, not arrival time.
- Within a batch, keep only the **last change per key** before merging.
- Deletes: hard delete (`WHEN MATCHED AND op='D' THEN DELETE`) or soft delete (`is_deleted` flag; better for audits and late events).
- A late event with an older sequence than the target row's must be ignored (`WHEN MATCHED AND s.seq > t.seq`).

## Late and out-of-order data

| Where | Handling |
|---|---|
| Streaming aggregations | Watermark; late rows beyond it are dropped |
| Batch incremental | Overlap window + idempotent merge |
| Facts joining dimensions | Dimension may arrive after the fact: keep an "unknown" dimension row, then repair, or re-run the join later |
| Event time vs ingest time | Partition by **ingest date** for operational loads; by **event date** for analytics, with reprocessing for late data |

## Idempotency checklist

A job can be re-run (retry, backfill, repair) and produce the same result.
- Deterministic transformations (no `current_timestamp()` in business keys, no unseeded `rand()`).
- Overwrite by partition or `MERGE` by key, never blind append.
- Exactly-once into Delta from batch jobs with `txnAppId` + `txnVersion`.
- Writes are atomic (Delta). Don't write outside Delta mid-job.

## Data modeling

- **Normalised (3NF):** operational systems; silver layer often stays close to source entities.
- **Dimensional (star schema):** fact tables (events/measures) + dimensions (descriptive); gold layer for BI.
  - Fact grain must be stated precisely ("one row per order line").
  - Surrogate keys for dimensions; handle unknown members.
- **One Big Table / wide tables:** denormalised for speed and simplicity; larger storage, harder updates.
- **Data vault:** hubs/links/satellites for auditability across many sources; more joins.
- **Nested types:** Spark handles `STRUCT`, `ARRAY`, `MAP` natively; `explode` arrays; avoid exploding then re-aggregating on huge data without need. `VARIANT` stores semi-structured JSON flexibly.

## Data quality

| Level | Examples | Tooling |
|---|---|---|
| Schema | Types, required columns | Delta enforcement, `NOT NULL`, schema contracts |
| Row | Ranges, formats, referential integrity | `CHECK` constraints, DLT expectations |
| Dataset | Row counts vs source, freshness, uniqueness, null rate | SQL checks, Lakehouse Monitoring, Great Expectations / Soda |
| Cross-system | Reconcile with source totals | Reconciliation jobs |

**Spark 4 ANSI mode (found while building lesson 5):** Spark 4 enables ANSI SQL mode by default, so
`CAST('abc' AS DOUBLE)` and invalid dates **raise an error and fail the job** instead of returning `NULL`.
For validation, use `try_cast` (or `expr("try_cast(x AS DOUBLE)")`) so bad values become `NULL` and
can be routed to a rejects table. Older Spark versions (3.x) silently returned `NULL`, so old code can
behave differently after an upgrade.

Failure policy per rule: **warn**, **drop/quarantine**, or **fail the job**. Choose deliberately, since
silently dropping rows hides outages.

Quarantine pattern: route bad rows to `<table>_rejects` with a reason column instead of losing them.

## Testing data pipelines

1. **Unit:** pure functions on small DataFrames (local Spark). Test edge cases: nulls, duplicates, late rows, empty input.
2. **Integration:** run the pipeline end to end on a sample in a staging catalog.
3. **Data tests:** assertions after each run (uniqueness, not-null, row-count deltas).
4. **Regression:** compare outputs of the new and old logic on the same input.

## File formats

| Format | Row/columnar | Schema | Notes |
|---|---|---|---|
| CSV / JSON | row | none/inferred | Human-readable, slow, ambiguous types |
| Avro | row | embedded | Good for streams/Kafka, schema evolution |
| **Parquet** | **columnar** | embedded | Default analytic format; compression, predicate pushdown |
| ORC | columnar | embedded | Hive world |
| **Delta** | Parquet + log | in log | ACID, time travel, updates |

Compression: **snappy** (fast, default), **zstd** (smaller, a bit slower).

## Anti-patterns

- Transforming in bronze or editing raw data. Keep it replayable.
- A single giant "do everything" notebook.
- Schema inferred from a sample on every run (use explicit schemas for production).
- Business logic in dashboards instead of the gold layer.
- Treating time travel as a backup.
- Unbounded retries on non-idempotent jobs.
- One shared all-purpose cluster for production jobs.

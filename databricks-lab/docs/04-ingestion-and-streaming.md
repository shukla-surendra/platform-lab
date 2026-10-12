# 4. Ingestion and Structured Streaming

## Ingestion patterns

| Pattern | Source | Tool |
|---|---|---|
| Files landing in cloud storage | CSV/JSON/Parquet/Avro in S3/ADLS/GCS | **Auto Loader** |
| Database tables | Operational DB (Postgres, MySQL, SQL Server, Oracle) | Lakeflow Connect / CDC tools (Debezium, DMS, Fivetran), JDBC for small loads |
| Event streams | Kafka, Kinesis, Event Hubs | Structured Streaming connectors |
| SaaS apps | Salesforce, etc. | Lakeflow Connect, partner ETL |
| SQL batch loads | Files already in storage | `COPY INTO`, `INSERT INTO ... SELECT` |

## Auto Loader (`cloudFiles`)

Databricks-only. Incrementally and idempotently ingests *new files* as they arrive.

```python
(spark.readStream.format("cloudFiles")
   .option("cloudFiles.format", "json")
   .option("cloudFiles.schemaLocation", "/Volumes/main/raw/_schemas/events")
   .load("/Volumes/main/raw/events")
 .writeStream
   .option("checkpointLocation", "/Volumes/main/raw/_checkpoints/events")
   .trigger(availableNow=True)
   .toTable("main.bronze.events"))
```

How it knows what's new, via two **file discovery modes**:

| Mode | How | When |
|---|---|---|
| **Directory listing** (default) | Lists the folder, remembers what it has seen in the checkpoint (RocksDB) | Small/moderate folders; incremental listing is optimised |
| **File notification** | Cloud events (S3 → SNS/SQS, Azure Event Grid → Queue) | Huge directories, lower latency, lower listing cost |

Key features:
- **Schema inference and evolution:** infers a schema, stores it at `schemaLocation`, and handles new columns by `cloudFiles.schemaEvolutionMode` (`addNewColumns` default → fails once then restarts with the new schema, `rescue`, `failOnNewColumns`, `none`).
- **Rescued data column** (`_rescued_data`): values that don't match the schema (extra columns, type mismatches) are kept instead of dropped.
- **Exactly-once for files:** state in the checkpoint prevents re-processing.
- Scales to billions of files, and works with `trigger(availableNow=True)` for scheduled incremental batches.

**Auto Loader vs `COPY INTO`:** `COPY INTO` is simple, idempotent, SQL, fine up to thousands of files
per run. Auto Loader scales better, handles schema evolution, and supports streaming.

## Structured Streaming

Spark's streaming engine: treat a stream as an **unbounded table** and write the same DataFrame
queries as for batch. Processing is **micro-batch** by default.

```python
(spark.readStream.table("bronze.events")
   .withWatermark("event_time", "10 minutes")
   .groupBy(window("event_time", "5 minutes"), "user_id").count()
 .writeStream
   .outputMode("append")
   .option("checkpointLocation", "...")
   .toTable("silver.user_counts"))
```

### Triggers

| Trigger | Behavior |
|---|---|
| default | Next micro-batch as soon as the previous finishes |
| `processingTime="1 minute"` | Fixed interval |
| `availableNow=True` | Process everything available, in multiple batches, then stop. **Best for scheduled "incremental batch".** |
| `once=True` | Deprecated one-batch version of the above |
| `realTime` (newer) | Very low latency mode; check docs for availability |

**Pattern:** run streaming code with `availableNow` as a scheduled job. You get checkpointed
incrementality without a 24/7 cluster.

### Output modes
- **append:** only new final rows. Aggregations need a watermark.
- **update:** rows changed since the last batch.
- **complete:** the entire result table every batch (small aggregates only).

### Checkpoints
A checkpoint stores: source offsets, state store data, and committed batch ids. It's what makes
restarts safe and gives **exactly-once** semantics when combined with an idempotent sink.

- Never share a checkpoint between queries.
- Never delete it casually: deleting it makes the stream start over (re-reading from `startingOffsets`).
- Changing the query can make an old checkpoint incompatible (adding a stateful operator, changing
  aggregation keys, changing the number of shuffle partitions of a stateful query).

### Delivery guarantees

| Component | Guarantee |
|---|---|
| Replayable source (Kafka, files, Delta) | Needed for recovery |
| Checkpoint | Records what was processed |
| Sink: Delta | Idempotent via transaction ids (`txn` action) → effectively **exactly-once** |
| Sink: `foreachBatch` custom | You must make it idempotent (use `batchId`, or `MERGE`) |

### Stateful processing: watermarks and windows

- **Event time:** when something happened (in the data). **Processing time:** when Spark saw it.
- **Watermark:** `withWatermark("event_time", "10 minutes")` = "I accept data up to 10 minutes late". State older than the watermark is dropped, which keeps state bounded.
- **Windows:** tumbling `window(ts, "5 minutes")`, sliding `window(ts, "10 minutes", "5 minutes")`, session windows.
- **Late data** past the watermark is silently dropped from aggregations. If correctness matters, widen the watermark or write the late data to a side output.
- **Stream-stream joins:** need watermarks on both sides and a time-bounded join condition, or state grows forever.
- **Deduplication:** `dropDuplicatesWithinWatermark` / `dropDuplicates(["id", "event_time"])` with a watermark.
- **State store:** RocksDB state store (recommended on Databricks) for large state.

### `foreachBatch`

Run arbitrary batch logic on each micro-batch. Standard way to do **MERGE (upsert) from a stream**:

```python
def upsert(batch_df, batch_id):
    batch_df.createOrReplaceTempView("updates")
    batch_df.sparkSession.sql("""
        MERGE INTO silver.customers t USING updates s ON t.id = s.id
        WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *""")

stream.writeStream.foreachBatch(upsert).option("checkpointLocation", cp).start()
```

Deduplicate inside the batch first (keep the latest row per key), because `MERGE` fails on duplicate
source keys.

### Delta as a streaming source
`spark.readStream.table("t")` reads appended data incrementally. If rows are updated or deleted
upstream, the stream **fails** unless you set `skipChangeCommits=true` (ignore them) or read the
**Change Data Feed** (`readChangeFeed`) to get the changes explicitly.

### Monitoring and failure modes

| Symptom | Likely cause |
|---|---|
| Batch duration keeps growing | State growing (no watermark), skew, small files |
| `inputRowsPerSecond` > `processedRowsPerSecond` | Falling behind; scale compute or reduce work |
| Stream fails on restart after code change | Incompatible checkpoint (stateful change) |
| Source reports offsets no longer available (Kafka) | Retention expired while the stream was down |
| Many small files in the sink | Short triggers; enable optimized writes / auto-compaction, or use `availableNow` |
| Duplicates in the sink | Non-idempotent `foreachBatch` or at-least-once source |
| Missing late data | Watermark too tight |

Use the **Streaming query progress** / `lastProgress`, the Spark UI's Structured Streaming tab, and
`StreamingQueryListener` for metrics.

## Batch vs streaming: choosing

- Latency requirement in **minutes or more** → scheduled `availableNow` incremental job. Cheapest.
- **Seconds** → continuous micro-batch streaming on an always-on cluster.
- **Sub-second** → a purpose-built engine (Flink, Kafka Streams) or real-time mode.

# Apache Spark

**Category:** distributed data processing (batch + streaming)

## What it is

Spark is a distributed compute engine for processing data that's too
large (or needs to be processed too fast) for one machine — it splits
data and work across a cluster of machines, coordinates them, and handles
failure/recovery automatically. The Python interface (**PySpark**) is a
wrapper around a JVM engine: Python code builds a query plan, which is
then optimized and executed by the JVM, with data movement between the
JVM and Python happening only where Python-specific code (UDFs) actually
requires it. On Databricks specifically, Spark comes pre-configured with
a managed cluster, Delta Lake as the default table format, and Unity
Catalog for governance — the context this repo's own Spark usage
(`docs/tools/evidently/examples/databricks_xgboost_batch_monitoring.py`)
runs in.

## The problem it solves

[pandas](../pandas/README.md) is fast and simple but fundamentally
single-machine and in-memory: a pandas DataFrame must fit in the RAM of
one process, and every operation runs on one machine's CPU cores (with no
built-in cross-machine parallelism). Once data volume crosses from
"fits in memory on a big single machine" to "needs many machines," two
different problems appear that Spark is built to solve together:

- **Distributed storage/compute**: the data itself is spread across
  many machines (in S3/HDFS/Delta Lake), and the *computation* needs to
  happen where the data lives (or be shipped efficiently), not by pulling
  everything onto one machine first.
- **Fault tolerance at scale**: with enough machines running long enough,
  individual node failures become a certainty, not an edge case — Spark
  tracks enough lineage (via RDDs' recomputation model) to recover lost
  partitions by recomputing them rather than failing the whole job.

## Alternatives

| Tool | How it differs |
|---|---|
| **[pandas](../pandas/README.md)** | Single-machine, in-memory, eager execution — the right tool once Spark's own output (or a pre-filtered subset) is small enough to fit in one process, as in this repo's `.toPandas()` step after a Spark aggregation. |
| **Dask** | Python-native distributed computing with a pandas-like API and lazy task graphs — lighter-weight to operate than Spark, popular when a team is Python-only and doesn't want JVM/cluster-manager complexity, but with a smaller ecosystem for SQL-heavy or streaming workloads. |
| **Flink** | Built stream-first (Spark's Structured Streaming is micro-batch by default; Flink's core model is true event-at-a-time streaming), generally lower latency for streaming use cases, less dominant for pure batch/ETL. |
| **Presto/Trino** | A distributed SQL query engine, not a general compute framework — no native DataFrame API, no ML libraries, built purely for federated/interactive SQL queries across many data sources, often faster than Spark SQL for ad hoc interactive queries but not a general-purpose processing engine. |
| **DuckDB** | Single-machine, embedded, extremely fast for analytical SQL on data that fits on one machine (including reading remote Parquet/S3 directly) — increasingly used as a "do I even need a cluster for this" check before reaching for Spark. |

## Architecture

```
Driver  ──────────────┐
 (runs your main       │  builds logical plan, sends tasks
  program, holds        │
  the SparkSession)      ▼
                    Cluster Manager (YARN / Kubernetes / Standalone / Databricks)
                          │  allocates resources
              ┌───────────┼───────────┐
              ▼           ▼           ▼
          Executor     Executor     Executor
         (JVM process, (JVM process, (JVM process,
          runs tasks,   runs tasks,   runs tasks,
          holds cached  holds cached  holds cached
          partitions)   partitions)   partitions)
```

- **Driver**: runs the user's `main()`, holds the `SparkSession`, builds
  the logical query plan, and coordinates execution — it does not process
  data itself at scale; it schedules work onto executors. A driver that
  accidentally pulls too much data back to itself (e.g. an unnecessary
  `.collect()` on a huge DataFrame) is the single most common cause of a
  driver OOM.
- **Executors**: JVM processes on worker nodes that actually run tasks and
  hold cached partitions in memory/disk. Each executor runs multiple
  tasks concurrently across its allocated CPU cores.
- **Cluster manager**: allocates physical resources (nodes, cores, memory)
  to the Spark application — YARN, Kubernetes, Spark Standalone, or a
  managed layer like Databricks' own cluster manager.
- **Job → Stages → Tasks**: an **action** (e.g. `.count()`, `.write()`)
  triggers a **job**; the job is broken into **stages** at each shuffle
  boundary (see below); each stage is broken into **tasks**, one task per
  partition, run in parallel across executor cores.

## Lazy evaluation: transformations vs. actions

Spark code doesn't execute when it's written — it builds up a plan, and
only runs when an **action** forces a result to materialize.

- **Transformations** (lazy): `select`, `filter`/`where`, `groupBy`,
  `join`, `withColumn`, `orderBy` — each returns a new DataFrame
  describing "the data after this step," without computing anything yet.
- **Actions** (eager, trigger execution): `.count()`, `.collect()`,
  `.show()`, `.write.save(...)`, `.toPandas()`.

```python
df2 = df.filter(df.amount > 100).select("id", "amount")   # nothing runs yet
df2.show()                                                  # NOW the whole plan executes
```

Laziness exists specifically so the **Catalyst optimizer** can see the
*entire* chain of transformations before generating any physical
execution plan — it can reorder, merge, or eliminate steps (e.g. push a
`filter` down before a `join` so less data is shuffled) that would be
impossible to apply if each line executed independently and eagerly like
pandas does.

## Catalyst optimizer and Tungsten

Every DataFrame/SQL query goes through four stages before it runs:

1. **Unresolved logical plan** — parsed from the DataFrame API calls or
   SQL text, column/table names not yet validated against the actual
   schema.
2. **Resolved (analyzed) logical plan** — column and table references
   checked against the catalog/schema; errors here are the "column not
   found" exceptions raised before any data is touched.
3. **Optimized logical plan** — rule-based rewrites: **predicate
   pushdown** (move filters as close to the data source as possible, so a
   Parquet reader can skip whole row groups without decompressing them),
   **column pruning** (only read columns actually referenced downstream),
   constant folding, join reordering.
4. **Physical plan** — concrete execution strategy chosen (e.g. which join
   algorithm — see below), then compiled via **Tungsten** into optimized
   JVM bytecode (whole-stage code generation), avoiding the overhead of
   Spark's own generic row-by-row interpretation.

The practical upshot: writing `df.filter(...).select(...)` vs.
`df.select(...).filter(...)` produces the **same physical plan** in most
cases — Catalyst reorders it either way — so readability of the
DataFrame code, not manual operation ordering, should drive how it's
written.

## Partitioning

A Spark DataFrame is split into **partitions** — chunks of rows,
physically distributed across executors, that are Spark's unit of
parallelism (one task per partition per stage).

- **Default parallelism**: on read, roughly determined by input file
  splits (e.g. one partition per ~128MB HDFS/Parquet block, tunable via
  `spark.sql.files.maxPartitionBytes`); after a shuffle, controlled by
  `spark.sql.shuffle.partitions` (default 200 — often wrong for both very
  small and very large jobs, one of the most commonly retuned settings).
- **`repartition(n)`**: triggers a **full shuffle** to redistribute data
  into exactly `n` partitions, roughly evenly — expensive, but needed when
  going to more partitions (increasing parallelism) or fixing a skewed
  distribution.
- **`coalesce(n)`**: merges existing partitions down to `n` **without a
  full shuffle** (only combines adjacent partitions) — cheap, but only
  works to *reduce* partition count, and can't fix skew since it doesn't
  redistribute rows, only groups existing partitions together.
- **Partition skew**: when one or a few partitions hold disproportionately
  more rows than others (e.g. a `groupBy("country")` where one country
  dominates the dataset) — the whole stage waits on the slowest task, so
  one skewed partition can dominate total job time even though every
  other partition finished quickly. Two standard fixes:
  - **Salting**: append a random suffix to the skewed key
    (`concat(key, '_', rand_int)`) before the shuffle to artificially
    spread the hot key across more partitions, then aggregate in two
    stages (partial aggregate per salted key, then a final aggregate that
    strips the salt).
  - **Adaptive Query Execution (AQE)**, on by default since Spark 3.0,
    detects skewed partitions at runtime (using actual shuffle statistics,
    not just the static plan) and automatically splits them into smaller
    sub-partitions — often removes the need to hand-salt manually.

## Shuffles

A **shuffle** is a full redistribution of data across the cluster — every
executor writes partitioned output to disk, and every executor then reads
the partitions relevant to it from every other executor over the network.
It's the most expensive operation type in Spark (disk I/O + network I/O +
serialization, versus a purely in-memory, same-partition operation).

Operations that **require** a shuffle: `groupBy`/`agg` (rows with the same
key must land on the same partition to be aggregated together),
non-broadcast `join` (same reasoning — matching keys must co-locate),
`distinct`, `repartition`, `orderBy` (global sort needs all data
comparable against all other data).

Operations that **don't**: `filter`, `select`, `withColumn`, `map`-like
per-row transformations — these are **narrow transformations**, where
each output partition depends on exactly one input partition, so they can
run entirely within an executor with no network movement. The
narrow-vs-wide (shuffle-requiring) distinction is exactly what defines
**stage boundaries**: a new stage starts at every wide transformation.

## Joins

| Strategy | When Spark picks it | Mechanism |
|---|---|---|
| **Broadcast hash join** | One side is small enough to fit in memory (below `spark.sql.autoBroadcastJoinThreshold`, default 10MB, or forced via `broadcast(df)` hint) | The small DataFrame is sent in full to *every* executor; the large side is joined locally with no shuffle needed on the large side at all — the fastest join strategy when applicable, since it avoids shuffling the large table entirely. |
| **Sort-merge join** | Default for two large DataFrames | Both sides are shuffled so matching keys co-locate on the same partition, each partition is sorted by join key, then merged — Spark's general-purpose join, correct at any size but pays the full shuffle cost on both sides. |
| **Shuffle hash join** | Occasionally chosen when one side is small-ish but over the broadcast threshold | Shuffles both sides by key, then builds an in-memory hash table on the smaller post-shuffle side per partition — less common than sort-merge in modern Spark's default planner. |

Practical guidance: explicitly hint a broadcast join
(`df_large.join(broadcast(df_small), "key")`) when joining a large fact
table against a small dimension table and Spark's size-based auto-decision
might be borderline (e.g. the small table is just over the default
threshold but still comfortably fits in executor memory) — don't rely
purely on the default threshold for anything performance-critical.
**Join skew** (one join key value dramatically more frequent than others)
causes the same single-slow-task problem as groupBy skew, with the same
salting/AQE-skew-handling fixes.

## Caching and persistence

```python
df.cache()                              # shorthand for persist(MEMORY_AND_DISK)
df.persist(StorageLevel.MEMORY_ONLY)    # explicit storage level
...
df.unpersist()                          # release when done
```

Caching stores a DataFrame's computed partitions (in memory, on disk, or
both, per the chosen `StorageLevel`) so a **subsequent action** doesn't
recompute the whole lineage from scratch. It only pays off when the same
DataFrame is used by **multiple downstream actions** — caching something
used exactly once adds overhead (the cache write itself) with no reuse to
recoup it. Because Spark is lazy, `df.cache()` alone does nothing until an
action runs; the first action after `.cache()` both computes *and*
populates the cache, and only actions after that one benefit from the
speedup.

## File formats

- **Parquet** (Spark's default): columnar, compressed, self-describing
  schema, supports predicate pushdown (skip whole row groups based on
  min/max statistics without decompressing them) and column pruning (read
  only referenced columns off disk) — both of which Catalyst exploits
  automatically. The standard choice for anything Spark writes that will
  be read again by Spark (or pandas, or most other analytical engines).
- **Delta Lake** (the format underlying Databricks tables, including
  `ml_monitoring.reference_scored` in this repo's monitoring example): an
  open storage layer on top of Parquet that adds ACID transactions, schema
  enforcement/evolution, and time travel (`VERSION AS OF`) — plain Parquet
  has none of these; a directory of Parquet files alone gives no
  transactional guarantees across concurrent readers/writers.
- **CSV/JSON**: row-based, no compression or pushdown benefits, schema
  must be inferred (an extra full pass over the data, or explicitly
  declared) — fine for interchange with non-Spark tools, a poor choice for
  anything performance-sensitive or repeatedly read.
- **`partitionBy`**: `df.write.partitionBy("date").parquet(path)` writes
  separate subdirectories per partition value (`date=2026-08-13/`, etc.)
  — a query that filters on `date` can then skip reading entire
  subdirectories rather than scanning the whole dataset (**partition
  pruning**, distinct from the in-memory partitioning discussed above,
  though the same underlying concept of "avoid touching data you don't
  need").

## UDFs and why built-ins beat Python UDFs

```python
from pyspark.sql.functions import udf
from pyspark.sql.types import DoubleType

@udf(returnType=DoubleType())
def to_fahrenheit(celsius):
    return celsius * 9 / 5 + 32

df.withColumn("temp_f", to_fahrenheit(df.temp_c))
```

A plain Python UDF forces Spark to **serialize each row out of the JVM,
deserialize it into a Python process, run the Python function, then
serialize the result back into the JVM** — that round trip, per row, is
the single biggest performance trap for Python Spark users, and it also
blocks Catalyst from optimizing across the UDF boundary (the UDF is a
black box to the optimizer; predicate pushdown and code generation stop
at its edges). Two better options, in order of preference:

1. **Built-in `pyspark.sql.functions`** (e.g. `F.when`, `F.expr`,
   arithmetic on columns directly) whenever the logic can be expressed
   without a UDF at all — stays entirely in JVM-native, Catalyst-optimized
   execution.
2. **Pandas UDFs** (`@pandas_udf`, formerly "vectorized UDFs"): operate on
   a whole **column of data as a pandas Series per batch**, not row by
   row, using Apache Arrow to transfer data between the JVM and Python in
   a columnar, batched, zero-copy-friendly format instead of row-by-row
   pickling — typically an order of magnitude faster than a plain UDF for
   the same logic, while still allowing arbitrary Python/pandas/NumPy code.

## Window functions

```python
from pyspark.sql import Window
from pyspark.sql import functions as F

w = Window.partitionBy("user_id").orderBy("event_time")
df.withColumn("row_num", F.row_number().over(w)) \
  .withColumn("running_total", F.sum("amount").over(w))
```

Window functions compute a value **per row**, relative to a window of
other rows (partitioned and ordered, like `groupBy` plus an ordering),
*without* collapsing rows the way a `groupBy`/`agg` does — the output has
the same row count as the input. Common uses: running totals,
row-number/rank within a group, lag/lead (comparing a row to the previous
one within its partition) — a `groupBy` alone can't express any of these
because it discards individual-row identity once aggregated.

## Structured Streaming

Spark's streaming model processes an unbounded input as a sequence of
small **micro-batches**, each handled through the *same* DataFrame
API/Catalyst pipeline as batch queries — a streaming query and a batch
query over the same schema can share nearly identical code.

- **Trigger interval**: how often a new micro-batch is processed (e.g.
  every 4 hours, matching this repo's own batch-scoring cadence described
  in the Evidently monitoring example — architecturally a scheduled batch
  job rather than continuous streaming, but the same underlying
  micro-batch model applies when true streaming is used instead).
- **Watermarking**: tells Spark how late an event is allowed to arrive
  (relative to its event-time timestamp) before being dropped from
  windowed aggregations — necessary because unbounded streaming state
  (e.g. "sum per 5-minute window") can't be kept forever; watermarking
  bounds how long a window stays open waiting for stragglers.
- **Checkpointing**: streaming queries persist their processing offsets
  and intermediate state to a checkpoint location, so a restarted query
  resumes exactly where it left off (exactly-once semantics when paired
  with an idempotent/transactional sink like Delta Lake) rather than
  reprocessing or dropping data.

## Memory management

Each executor's memory is split (since Spark's "Unified Memory Manager")
into a single pool shared dynamically between:

- **Execution memory**: working memory for shuffles, joins, sorts,
  aggregations — data actively being computed on.
- **Storage memory**: cached/persisted DataFrames.

The two can borrow from each other under pressure (with execution able to
evict cached storage blocks if it genuinely needs the space), rather than
being fixed hard partitions as in older Spark versions — this is why
excessive caching can still cause execution-side slowdowns/spills even
though it "should" be a separate pool. When memory pressure exceeds what's
available, Spark **spills** intermediate data to executor local disk
rather than failing outright — correct, but far slower than staying in
memory; frequent spilling in the Spark UI's stage metrics is a sign
partitions are too large or too skewed for current executor memory.
Executor **OOM** (as opposed to a graceful spill) typically comes from:
partition size too large relative to executor memory (fix: more/smaller
partitions via `repartition`), a broadcast join against a table that
turned out bigger than expected, or a UDF/collect operation materializing
more data at once than the JVM heap allows.

## Adaptive Query Execution (AQE)

On by default since Spark 3.0 — re-optimizes the physical plan **during**
execution using actual runtime statistics (row counts, partition sizes)
rather than only the static, pre-execution estimates Catalyst's cost-based
optimizer relies on. Three concrete things AQE does:

- **Dynamically coalesces shuffle partitions**: if the static plan created
  too many small post-shuffle partitions (a common outcome of the default
  `spark.sql.shuffle.partitions=200` on a job with much less data), AQE
  merges them down at runtime.
- **Dynamically switches join strategy**: if a join input turns out
  smaller than initially estimated (e.g. after an upstream filter
  removed most rows), AQE can switch a planned sort-merge join to a
  broadcast join on the fly.
- **Dynamically handles skewed joins**: splits an oversized shuffle
  partition detected at runtime into smaller sub-partitions, the
  runtime counterpart to manual salting.

## Worked example: this repo's Databricks batch-scoring monitor

`docs/tools/evidently/examples/databricks_xgboost_batch_monitoring.py`
shows real Spark usage in this repo's context — reading Delta tables,
filtering, converting to pandas for a library (Evidently) that needs an
in-memory DataFrame, then writing results back:

```python
# Read a Delta table via Spark SQL, filter using Spark (not pandas) so the
# filter runs distributed/pushed-down rather than after pulling everything
# onto the driver
current_data = (
    spark.table("ml_monitoring.batch_predictions")
    .filter("scoring_ts >= current_timestamp() - interval 4 hours")
    .toPandas()   # deliberate: only AFTER Spark has already reduced this
                  # down to one batch window's worth of rows -- not used as
                  # a general escape hatch for large data
)
```

```python
# Writing a small result back as an appended Delta row -- createDataFrame
# from a plain Python list/tuple is fine here because the data is tiny
# (one row); this is not the pattern for writing large data
spark.createDataFrame(
    [(drift_detected,)], ["dataset_drift_detected"]
).withColumn("run_ts", F.current_timestamp()).write.mode("append").saveAsTable(
    "ml_monitoring.drift_history"
)
```

Full file: [`databricks_xgboost_batch_monitoring.py`](../evidently/examples/databricks_xgboost_batch_monitoring.py).
The `.filter()` call happening in Spark *before* `.toPandas()` is the
important detail — filtering after conversion would mean pulling the
entire table onto the driver first and defeating the point of using Spark
at all for that read.

## Relationship to other tools in this repo

- **[pandas](../pandas/README.md)**: `.toPandas()` is the standard bridge
  from a Spark result back to pandas, correct once Spark has already
  reduced the data to something that fits on one machine — never a
  substitute for doing the reduction in Spark first.
- **[MLflow](../mlflow/README.md)**: on Databricks, MLflow's tracking and
  model registry work directly against Unity Catalog with no separate
  server, and `mlflow.xgboost.log_model`/batch-scoring jobs commonly run
  as Spark jobs that load a registered model and apply it across a Spark
  DataFrame via a pandas UDF, rather than pulling data to a single machine
  to score it.
- **[Evidently](../evidently/README.md)**: the monitoring example above
  is exactly this pattern — Spark does the distributed read/filter,
  Evidently does the (single-machine, pandas-based) drift analysis on the
  resulting batch.

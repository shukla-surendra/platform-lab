# 3. Spark internals and performance

## Execution model

```
your code (DataFrame / SQL)
   └─> logical plan ──(Catalyst optimizer)──> optimized logical plan ──> physical plan
        └─> jobs ──> stages (split at shuffles) ──> tasks (one per partition, run on executors)
```

- **Driver:** plans the query, schedules tasks, collects results. One per application.
- **Executors:** run tasks, hold cached data and shuffle files.
- **Job:** triggered by an *action* (`count`, `write`, `collect`, `show`).
- **Stage:** a set of tasks that can run without moving data between machines.
- **Task:** one partition processed by one core.
- **Lazy evaluation:** transformations only build a plan; nothing runs until an action. This lets Catalyst optimise the whole thing.

### Narrow vs wide transformations

| | Examples | Data movement |
|---|---|---|
| Narrow | `filter`, `select`, `withColumn`, `map` | None; each output partition depends on one input partition |
| Wide | `groupBy`, `join`, `distinct`, `orderBy`, `repartition` | **Shuffle**: data is redistributed across the network, written to disk, read back |

**Shuffles are the dominant cost** in most Spark jobs. Performance work is mostly about avoiding,
shrinking, or balancing them.

## Reading plans

```python
df.explain("formatted")      # physical plan, readable
```
Look for: `Exchange` (shuffle), `BroadcastHashJoin` vs `SortMergeJoin`, `PushedFilters`
(predicate pushdown into the scan), `PartitionFilters`, `ReadSchema` (column pruning),
`AdaptiveSparkPlan`. The Spark UI (SQL tab, Stages tab) shows time, rows and skew per stage.

## Catalyst and Tungsten
- **Catalyst:** rule-based and cost-based optimiser: predicate pushdown, column pruning, constant
  folding, join reordering, join strategy choice.
- **Tungsten:** binary in-memory format, off-heap memory, whole-stage code generation.
- **Photon** (Databricks) replaces parts of the physical execution with a vectorised native engine.

## Join strategies

| Strategy | When | Cost |
|---|---|---|
| **Broadcast hash join** | One side small (default threshold 10 MB, set higher with `spark.sql.autoBroadcastJoinThreshold`; AQE can convert at runtime) | No shuffle of the big side. Fastest. |
| **Shuffle hash join** | Medium size, one side fits per-partition memory | Shuffle both sides, no sort |
| **Sort-merge join** | Default for two large tables | Shuffle and sort both sides |
| **Broadcast nested loop / cartesian** | Non-equi joins, no keys | Very expensive |

Hint a broadcast: `big.join(broadcast(small), "key")`. If the "small" table isn't small enough, the
driver and executors run out of memory.

## Adaptive Query Execution (AQE)

On by default. Re-optimises using runtime statistics after each shuffle:
1. **Coalesce shuffle partitions:** merges many tiny post-shuffle partitions (so the `200` default matters less).
2. **Switch join strategy:** sort-merge → broadcast when a side turns out small after filtering.
3. **Skew join handling:** splits oversized partitions of a skewed join key.

AQE does not fix every problem. It can't help skew in `groupBy` aggregations, or in a join where
both sides are skewed on the same key in certain shapes.

## Data skew

**Symptom:** one task runs for 40 minutes while 199 finish in seconds; one executor has far more
shuffle read; spill to disk on a single task.

**Diagnose:** Spark UI → Stages → task duration/shuffle-read distribution (max vs median). Check
the key distribution: `df.groupBy("key").count().orderBy(desc("count"))`.

**Fixes:**
- Let AQE skew-join handle it (check it kicked in).
- **Salting:** add a random suffix to the hot key on the big side, replicate the small side across all suffixes, join on `(key, salt)`, then aggregate away the salt.
- Broadcast the small side (no shuffle, so no skew).
- Filter or separately handle hot keys (e.g. `NULL` or a default value that dominates).
- For aggregations: two-phase aggregation (partial aggregate with salt, then final).

## Partitions

| Concept | Notes |
|---|---|
| Input partitions | From file splits (~128 MB each, `spark.sql.files.maxPartitionBytes`) |
| Shuffle partitions | `spark.sql.shuffle.partitions` (default 200); AQE coalesces them |
| `repartition(n)` | Full shuffle, can increase or decrease; `repartition(n, col)` hashes by column |
| `coalesce(n)` | Decrease only, no shuffle, can cause uneven partitions |
| Rule of thumb | 2–4 tasks per core; partitions of roughly 100–200 MB |

**Too few partitions:** low parallelism, huge partitions, spill, out of memory.
**Too many:** scheduling overhead, tiny output files.

## Memory

Executor memory is split into execution (shuffles, joins, sorts, aggregations) and storage
(cache) regions, with overhead outside the JVM heap (`spark.executor.memoryOverhead`, important for
PySpark and pandas UDFs).

- **Spill:** data that doesn't fit in memory is written to disk. Slow but survivable. Visible in the Spark UI.
- **OOM on the driver:** `collect()`, `toPandas()`, big broadcast, too many small files being listed.
- **OOM on an executor:** skewed partition, too-wide rows, too few partitions, exploding arrays.
- **Container killed by YARN/K8s (exit 137):** off-heap/overhead exceeded; raise `memoryOverhead`.

## Caching

`df.cache()` / `persist()` keeps data across actions. Use when a DataFrame is reused several times
in one job *and* is expensive to compute. It isn't free: memory, and it's invalidated by file
changes. On Databricks, the **disk cache** (local SSD caching of remote Parquet/Delta) is
automatic on suitable instances and is usually better than `cache()` for reads.
Always `unpersist()` when done.

## Python and UDFs

| Option | Speed | Notes |
|---|---|---|
| Built-in functions (`pyspark.sql.functions`) | Fastest | Run inside the JVM/Photon. Prefer always. |
| Pandas UDF (vectorised, Arrow) | Medium | Batches of rows via Arrow |
| Python UDF (row at a time) | Slow | Serialises every row to Python and back |
| SQL expressions / `expr()` | Fast | |
| Scala/Java UDF | Fast | No Python round trip |

Optimiser can't see inside UDFs: no predicate pushdown through them, no code generation.

## Storage-level performance (see doc 2)
- File size: avoid small files; target 128 MB–1 GB.
- Partition by low-cardinality filter columns only, or use liquid clustering.
- Data skipping depends on clustering of the filter column.
- Select only needed columns (Parquet is columnar).
- Filter early so predicate pushdown applies.

## Common performance anti-patterns

| Anti-pattern | Why bad | Do instead |
|---|---|---|
| `collect()` / `toPandas()` on big data | Driver OOM, single-threaded | Aggregate first, write to storage |
| `for` loop over rows in Python | No parallelism | Column expressions |
| Row-level Python UDF for built-in work | Slow | Built-in functions |
| `count()` just to check emptiness | Full scan | `df.isEmpty()` / `limit(1)` |
| Many `withColumn` calls in a loop | Plan bloat | One `select` with all expressions |
| Reading a huge table then filtering in Python | No pushdown | Filter in Spark |
| `repartition(1)` before writing | Single-task bottleneck | Write many files, then `OPTIMIZE` |
| Partitioning by a high-cardinality column | Millions of tiny files | Cluster or Z-ORDER |
| Joins on mismatched types (`int` vs `string`) | Casts defeat pushdown, can skew | Align types |
| Ignoring `NULL` join keys | All nulls land in one partition | Filter or handle nulls separately |

## Tuning checklist

1. Look at the Spark UI: which stage dominates? Is it a shuffle? Is it skewed? Is it spilling?
2. Are scans reading too much (check `PushedFilters`, partition filters, files read)?
3. Are there small files, or is a table over-partitioned?
4. Are joins using the right strategy? Is a broadcast possible?
5. Is a Python UDF on the critical path?
6. Is AQE on and doing its job?
7. Only then consider cluster size. Bigger clusters rarely fix skew or bad plans.

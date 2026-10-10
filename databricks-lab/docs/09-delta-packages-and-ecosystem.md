# 9. Where Delta lives: packages, implementations and the ecosystem

Questions this answers: *Is Delta part of Databricks? What do I actually install? Which language is
it written in? Who builds it? How does it relate to Unity Catalog?*

> **Verification status.** Written from knowledge of the project, not checked line by line against
> the current repositories. Items marked **(unverified)** are the ones to check against the official
> docs before relying on them. The package layout in the first two sections is what this lab's
> `common.py` and `pyproject.toml` use.

## 1. Delta Lake is open source and separate from Databricks

- **Delta Lake** = an open **table format** (Parquet files + a transaction log) with an open
  specification and open-source implementations. It runs on plain Apache Spark.
- **Databricks** = a commercial platform that uses Delta by default and adds proprietary features on top
  (Photon, Unity Catalog's full feature set, predictive optimization, Lakeflow, serverless).
- Some new Delta features appear on Databricks first and reach open source later, or never. Check the
  release notes of the version you run.

## 2. What you actually install

Delta is split into a **JVM library** (the real implementation) and a **Python wrapper**.

```
databricks-lab/.venv
 ├─ pyspark          Spark engine (includes Spark's own JARs)
 └─ delta-spark      Python wrapper: delta.tables.DeltaTable, configure_spark_with_delta_pip

~/.ivy2*/jars        (downloaded on first Spark start, by Maven coordinates)
 ├─ io.delta:delta-spark_2.13   the Delta implementation (Scala/Java)  ← the real code
 └─ io.delta:delta-storage      storage and log-store abstractions
```

| Piece | Where it comes from | Role |
|---|---|---|
| **JARs** `io.delta:delta-spark_<scala>` and `delta-storage` | Maven Central | Transaction log, `MERGE`, `OPTIMIZE`, `VACUUM`, Spark SQL integration |
| **PyPI** `delta-spark` | pip | Python API (`DeltaTable`) that calls into the JVM library, plus a helper that adds the JAR coordinates to Spark |
| **PyPI** `pyspark` | pip | The engine. Delta is a plugin to it |

`configure_spark_with_delta_pip(builder)` does **not** contain the JARs. It adds the right Maven
coordinates to `spark.jars.packages`, so Spark downloads them on the **first run**. That is why the
first start needs internet and pauses with no output.

### Turning Delta on (what `common.py` does)

```python
SparkSession.builder
  .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
  .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
```

- The **extension** adds Delta's SQL syntax and optimizer rules (`MERGE`, `OPTIMIZE`, `RESTORE`, `DESCRIBE HISTORY`, ...).
- The **catalog** replaces Spark's default catalog so Delta tables are created and resolved correctly.
- On Databricks both are already configured.

### Version matching

Delta and Spark must match. Mismatches fail at start-up with class or method errors.

| Delta | Spark | Scala artifact |
|---|---|---|
| 4.0.x | 4.0.x | `_2.13` |
| 3.x | 3.5.x | `_2.12` (also `_2.13`) |

(unverified: confirm the exact compatibility table in the Delta release notes for your versions.)
This lab pins `pyspark==4.0.0` and `delta-spark==4.0.0`. Confirmed by running the lessons: Spark resolved
`io.delta#delta-spark_2.13;4.0.0` and `io.delta#delta-storage;4.0.0` from Maven Central into `~/.ivy2.5.2/jars`,
next to older jars that other projects had downloaded.

## 3. Languages: Scala/Java on the JVM, not Python

- The main implementation (`delta-io/delta`, the `delta-spark` module) is predominantly **Scala**,
  with some **Java** (for example in Delta Kernel and storage). (unverified: exact language split)
- Python is only a thin wrapper that sends calls to the JVM through Spark's Py4J bridge.
- You rarely touch the Scala code. You *use* it through SQL, Python or Scala APIs.

## 4. How you configure Delta (three layers)

| Layer | Where | Examples |
|---|---|---|
| **Session** | Spark config, set at session start or with `spark.conf.set` | `spark.databricks.delta.schema.autoMerge.enabled`, `spark.databricks.delta.retentionDurationCheck.enabled` |
| **Table** | `TBLPROPERTIES`, stored **in the table's log** so it travels with the table | `delta.enableChangeDataFeed`, `delta.logRetentionDuration`, `delta.deletedFileRetentionDuration`, `delta.columnMapping.mode`, `delta.enableDeletionVectors` |
| **Operation** | Writer or command options | `.option("mergeSchema", "true")`, `replaceWhere`, `OPTIMIZE ... ZORDER BY`, `VACUUM ... RETAIN n HOURS` |

```sql
ALTER TABLE t SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');
SHOW TBLPROPERTIES t;
```

Table properties win over session defaults for that table. Some properties also bump the table's
**protocol version** (required reader/writer features), so older clients may no longer read it.
Many config names start with `spark.databricks.delta.*` even in open source. That is a historical
naming quirk, not a sign that they are Databricks-only. (unverified per setting)

## 5. Who builds it

- **Created by Databricks** (in use internally from about 2017), **open-sourced in 2019**, then moved
  under the **Linux Foundation** as a vendor-neutral project (`delta.io`, repo `delta-io/delta`).
- Databricks engineers write much of the code. Other companies and individuals contribute and
  maintain connectors. (unverified: current contributor and maintainer list)
- Governance is under the Linux Foundation, but in practice roadmap and release timing are strongly influenced by Databricks.

## 6. The protocol: one format, several implementations

The log format and the rules for readers and writers are written down as a **specification**
(`PROTOCOL.md` in the Delta repo). Anything that follows it can read and write the same tables.

| Implementation | Language | Typical use |
|---|---|---|
| **delta-spark** (the main one) | Scala/Java | Apache Spark and Databricks |
| **Delta Kernel** | Java and Rust | A library for engines to add Delta read/write support without re-implementing the protocol |
| **delta-rs** (`deltalake` on PyPI) | Rust | Python and Rust programs, pandas/Polars/DataFusion, **no Spark or JVM** |
| Connectors (Flink, Trino, Hive, others) | various | Query Delta from other engines |

Practical consequences:
- A table written by Spark can be read by `deltalake` and the other way around.
- **Feature support varies by implementation and version.** A table with deletion vectors or column
  mapping enabled may be unreadable by an older or less complete reader. Check the table's reader/writer
  **table features** against the client before enabling them.
- For small scripts or CI checks where Spark is too heavy, `pip install deltalake` is a handy alternative:

```python
from deltalake import DeltaTable
dt = DeltaTable("path/to/table")
print(dt.version(), dt.files()[:3])
df = dt.to_pandas()
```

## 7. Delta vs Unity Catalog vs Databricks

Delta is the **format**; Unity Catalog is the **catalog and governance layer**; Databricks is the
**platform** that runs both.

```
Platform:        Databricks (compute, notebooks, jobs, Photon)
                       │
Catalog:         Unity Catalog:  catalog → schema → table / volume / function / model
                 (names, permissions, lineage, audit)
                       │ points at
Table format:    Delta Lake (also: Iceberg, Parquet, CSV, ...)
                       │
Files:           Parquet + _delta_log in S3 / ADLS / GCS / local disk
```

- Unity Catalog is **not built on top of Delta** in the sense of depending on it. It catalogs
  things, and a UC table is usually Delta but can be another format. Iceberg is exposed through an
  Iceberg REST interface and UniForm (a Delta table can publish Iceberg metadata). (unverified: current format support)
- **Unity Catalog has an open-source version** (a Linux Foundation project, with a server you can run
  locally and a Spark connector). It is a **smaller feature set** than Databricks' Unity Catalog:
  row filters, column masks, automatic lineage, system tables and ABAC are Databricks-side features
  as far as I know. (unverified: current OSS feature list)
- Without any catalog you can still use Delta by **path** (`load("/path")`), which is what the lessons do.

## 8. What can you practice without Databricks

| Topic | Local, open source | Needs Databricks |
|---|---|---|
| Delta log, ACID, time travel, `MERGE`, schema, constraints | yes | |
| `OPTIMIZE`, Z-ORDER, `VACUUM` | yes | |
| Change Data Feed, `RESTORE`, clones | yes (check version) | |
| Deletion vectors, column mapping | yes, version permitting | |
| Liquid clustering | check your Delta version | yes (for sure) |
| Structured Streaming with Delta | yes | |
| Spark performance (joins, skew, AQE) | yes | Photon needs Databricks |
| Unity Catalog basics | OSS server possible, limited | full governance |
| Auto Loader, Lakeflow pipelines, Jobs, bundles, system tables | | yes |

## 9. Troubleshooting setup issues

| Symptom | Cause |
|---|---|
| First Spark start hangs or is slow with no output | Downloading JARs from Maven (needs internet once) |
| `ClassNotFoundException: io.delta...` | Extensions/JAR not configured, or `spark.jars.packages` not applied (session already created) |
| `NoSuchMethodError` / incompatible-class errors | Delta and Spark versions don't match |
| `uv sync` seems stuck | `pyspark` is a ~430 MB source package; there's no progress bar by default (use `uv sync -v`) |
| Works on Databricks, fails locally | Feature is Databricks-only or needs a newer open-source Delta |
| Old Delta jar loaded | Another project's jar in `~/.ivy2*`; clear the cache or use a separate `spark.jars.ivy` directory |

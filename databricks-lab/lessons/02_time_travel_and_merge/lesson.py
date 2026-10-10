"""Lesson 2: every write is a version; MERGE upserts; time travel reads the past.

Run:  uv run python lessons/02_time_travel_and_merge/lesson.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import fresh, get_spark, show_files

from delta.tables import DeltaTable
from pyspark.sql import Window
from pyspark.sql.functions import col, row_number

spark = get_spark()
path = fresh("l02/customers")

schema = "id INT, name STRING, city STRING, updated_at INT"
spark.createDataFrame([(1, "alice", "Pune", 1), (2, "bob", "Delhi", 1)], schema).write.format("delta").save(path)

print("\n== incoming changes: id 2 changed city, id 3 is new, id 1 appears TWICE (a duplicate key)")
updates = spark.createDataFrame(
    [(2, "bob", "Mumbai", 2), (3, "carol", "Goa", 2), (1, "alice", "Pune", 2), (1, "alice", "Nashik", 3)],
    schema,
)

print("== MERGE with duplicate source keys fails:")
try:
    (DeltaTable.forPath(spark, path).alias("t")
        .merge(updates.alias("s"), "t.id = s.id")
        .whenMatchedUpdateAll().whenNotMatchedInsertAll().execute())
except Exception as e:
    print("  FAILED as expected:", str(e).splitlines()[0][:110])

print("\n== fix: keep the latest row per key (deterministic order), then merge")
w = Window.partitionBy("id").orderBy(col("updated_at").desc())
latest = updates.withColumn("rn", row_number().over(w)).filter("rn = 1").drop("rn")
(DeltaTable.forPath(spark, path).alias("t")
    .merge(latest.alias("s"), "t.id = s.id")
    .whenMatchedUpdateAll().whenNotMatchedInsertAll().execute())
spark.read.format("delta").load(path).orderBy("id").show()

print("== history: each commit is a version, with operation metrics")
spark.sql(f"DESCRIBE HISTORY delta.`{path}`").select("version", "operation", "operationMetrics").show(truncate=60)

print("== time travel: the table as of version 0")
spark.read.format("delta").option("versionAsOf", 0).load(path).orderBy("id").show()

print("== RESTORE back to version 0 (itself a new commit, history is kept)")
spark.sql(f"RESTORE TABLE delta.`{path}` TO VERSION AS OF 0")
spark.read.format("delta").load(path).orderBy("id").show()
spark.sql(f"DESCRIBE HISTORY delta.`{path}`").select("version", "operation").show()

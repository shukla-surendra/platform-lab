"""Lesson 4: the small-file problem, OPTIMIZE, and VACUUM.

Run:  uv run python lessons/04_small_files_optimize_vacuum/lesson.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import fresh, get_spark, show_files

spark = get_spark()
path = fresh("l04/readings")

def stats(label):
    d = spark.sql(f"DESCRIBE DETAIL delta.`{path}`").first()
    print(f"  [{label}] numFiles={d['numFiles']}  sizeInBytes={d['sizeInBytes']}")

print("\n== 20 tiny appends = 20 commits and at least 20 files")
for i in range(20):
    spark.range(i * 50, (i + 1) * 50).selectExpr("id", "id % 7 AS sensor") \
        .coalesce(1).write.format("delta").mode("append").save(path)
stats("after tiny appends")

print("\n== OPTIMIZE compacts them into fewer, bigger files (old files are NOT deleted yet)")
spark.sql(f"OPTIMIZE delta.`{path}`")
stats("after OPTIMIZE")
parquet_on_disk = len(list(Path(path).glob("*.parquet")))
print(f"  parquet files physically on disk: {parquet_on_disk}  (old + new)")

print("\n== VACUUM removes files no longer referenced, but only older than the retention period")
spark.sql(f"VACUUM delta.`{path}` DRY RUN").show(truncate=False)   # nothing is 7 days old yet
print("  (dry run lists nothing: all old files are younger than 7 days)")

print("== forcing retention to 0 hours (ONLY for this demo; never do this on real tables)")
spark.conf.set("spark.databricks.delta.retentionDurationCheck.enabled", "false")
spark.sql(f"VACUUM delta.`{path}` RETAIN 0 HOURS")
print(f"  parquet files physically on disk now: {len(list(Path(path).glob('*.parquet')))}")

print("\n== consequence: time travel to an old version now fails because its files are gone")
# NB: count() alone can be answered from the statistics in the log without reading any file,
# so it would "succeed". Force a real read of the data instead.
try:
    spark.read.format("delta").option("versionAsOf", 1).load(path).agg({"id": "sum"}).collect()
    print("  did NOT fail (unexpected): the files for that version still exist")
except Exception as e:
    msg = next((l for l in str(e).splitlines() if "FileNotFound" in l or "does not exist" in l), str(e).splitlines()[0])
    print("  FAILED as expected:", msg.strip()[:140])

print("\n== Z-ORDER co-locates values so data skipping works")
spark.sql(f"OPTIMIZE delta.`{path}` ZORDER BY (sensor)")
stats("after ZORDER")

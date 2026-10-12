"""Lesson 1: what a Delta table physically is.

Run:  uv run python lessons/01_delta_basics/lesson.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import fresh, get_spark, show_files

spark = get_spark()
path = fresh("l01/orders")

df = spark.createDataFrame(
    [(1, "alice", 120.0), (2, "bob", 80.5), (3, "carol", 42.0)],
    ["order_id", "customer", "amount"],
)

print("\n== write version 0")
df.write.format("delta").save(path)
show_files(path)

print("\n== append version 1")
spark.createDataFrame([(4, "dave", 15.0)], df.schema).write.format("delta").mode("append").save(path)
show_files(path)

print("\n== the transaction log is JSON: one file per commit")
for f in sorted(Path(path, "_delta_log").glob("*.json")):
    print(f"\n-- {f.name}")
    for line in f.read_text().splitlines():
        action = next(iter(__import__("json").loads(line)))
        print("  action:", action)

print("\n== read it back")
spark.read.format("delta").load(path).orderBy("order_id").show()

print("== DESCRIBE DETAIL (size, file count, format)")
spark.sql(f"DESCRIBE DETAIL delta.`{path}`").select("format", "numFiles", "sizeInBytes").show()

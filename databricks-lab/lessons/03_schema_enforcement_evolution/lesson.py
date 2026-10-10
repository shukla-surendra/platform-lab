"""Lesson 3: schema enforcement, schema evolution, and CHECK constraints.

Run:  uv run python lessons/03_schema_enforcement_evolution/lesson.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import fresh, get_spark, show_files

spark = get_spark()
path = fresh("l03/events")

spark.createDataFrame([(1, "click")], "id INT, kind STRING").write.format("delta").save(path)

print("\n== 1. enforcement: appending an extra column is rejected by default")
extra = spark.createDataFrame([(2, "view", "mobile")], "id INT, kind STRING, device STRING")
try:
    extra.write.format("delta").mode("append").save(path)
except Exception as e:
    print("  FAILED as expected:", str(e).splitlines()[0][:110])

print("\n== 2. evolution: mergeSchema adds the column; old rows get NULL")
extra.write.format("delta").mode("append").option("mergeSchema", "true").save(path)
spark.read.format("delta").load(path).orderBy("id").show()

print("== 3. a type mismatch is still rejected (string into INT)")
bad = spark.createDataFrame([("abc", "tap", "web")], "id STRING, kind STRING, device STRING")
try:
    bad.write.format("delta").mode("append").save(path)
except Exception as e:
    print("  FAILED as expected:", str(e).splitlines()[0][:110])

print("\n== 4. CHECK constraint: bad rows are rejected, the whole write fails atomically")
spark.sql(f"ALTER TABLE delta.`{path}` ADD CONSTRAINT id_positive CHECK (id > 0)")
try:
    spark.createDataFrame([(5, "ok", "x"), (-1, "bad", "x")], "id INT, kind STRING, device STRING") \
        .write.format("delta").mode("append").save(path)
except Exception as e:
    # the first line is just a Py4J wrapper; the real reason is further down
    reason = next((l for l in str(e).splitlines() if "constraint" in l.lower()), str(e).splitlines()[0])
    print("  FAILED as expected:", reason.strip()[:140])
print("  rows after the failed write (the good row 5 was NOT written either):")
spark.read.format("delta").load(path).orderBy("id").show()

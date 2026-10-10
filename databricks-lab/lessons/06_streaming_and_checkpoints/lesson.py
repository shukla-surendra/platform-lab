"""Lesson 6: Structured Streaming from Delta to Delta, checkpoints, and availableNow.

Run:  uv run python lessons/06_streaming_and_checkpoints/lesson.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import fresh, get_spark, show_files

from pyspark.sql.functions import col, window

spark = get_spark()
root = fresh("l06")
SRC, SINK, AGG, CP, CP2 = (f"{root}/{n}" for n in ("source", "sink", "agg", "cp_sink", "cp_agg"))
SCHEMA = "event_id INT, user STRING, event_time TIMESTAMP"


def add_events(rows):
    spark.createDataFrame(rows, SCHEMA).write.format("delta").mode("append").save(SRC)


def run_copy_stream():
    """Incremental copy. availableNow = process what's new, then stop (a scheduled 'incremental batch')."""
    q = (spark.readStream.format("delta").load(SRC)
         .writeStream.format("delta").option("checkpointLocation", CP)
         .trigger(availableNow=True).start(SINK))
    q.awaitTermination()


from datetime import datetime as D
add_events([(1, "a", D(2026, 1, 1, 10, 0)), (2, "b", D(2026, 1, 1, 10, 1))])
run_copy_stream()
print("\n== run 1: sink rows =", spark.read.format("delta").load(SINK).count())

run_copy_stream()
print("== run 2 with NO new data: sink rows =", spark.read.format("delta").load(SINK).count(), "(checkpoint remembers what was done)")

add_events([(3, "a", D(2026, 1, 1, 10, 2))])
run_copy_stream()
print("== run 3 after 1 new row: sink rows =", spark.read.format("delta").load(SINK).count(), "(only the new row was processed)")

print("\n== checkpoint contents: offsets (what was read), commits (what finished), sources, metadata")
for p in sorted(Path(CP).iterdir()):
    print("  ", p.name, "/" if p.is_dir() else "")

print("\n== delete the checkpoint and run again: the stream starts from scratch, duplicating rows")
import shutil
shutil.rmtree(CP)
run_copy_stream()
print("   sink rows =", spark.read.format("delta").load(SINK).count(), "(3 originals + 3 re-read = 6; this is why you never delete checkpoints casually)")

print("\n== windowed aggregation with a watermark (state is bounded by the watermark)")
q = (spark.readStream.format("delta").load(SRC)
     .withWatermark("event_time", "5 minutes")
     .groupBy(window("event_time", "2 minutes"), "user").count()
     .writeStream.format("delta").outputMode("append")
     .option("checkpointLocation", CP2).trigger(availableNow=True).start(AGG))
q.awaitTermination()
spark.read.format("delta").load(AGG).orderBy("window", "user").show(truncate=False)
print("(append mode only emits windows the watermark has closed; the newest window may still be open)")

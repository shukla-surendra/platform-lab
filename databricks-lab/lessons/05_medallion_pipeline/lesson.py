"""Lesson 5: bronze -> silver -> gold, with data-quality quarantine and an idempotent daily load.

Run:  uv run python lessons/05_medallion_pipeline/lesson.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import fresh, get_spark, show_files

from delta.tables import DeltaTable
from pyspark.sql import Window
from pyspark.sql.functions import col, current_timestamp, expr, lit, row_number, sum as sum_, to_date

spark = get_spark()
root = fresh("l05")
BRONZE, SILVER, REJECTS, GOLD = (f"{root}/{n}" for n in ("bronze", "silver", "rejects", "gold"))

RAW = "order_id STRING, customer STRING, amount STRING, order_ts STRING"
day1 = [("o1", "alice", "100.5", "2026-01-01 10:00:00"),
        ("o2", "bob", "abc", "2026-01-01 11:00:00"),          # bad amount
        ("o3", None, "20", "2026-01-01 12:00:00"),            # missing customer
        ("o1", "alice", "100.5", "2026-01-01 10:00:00")]      # duplicate delivery
day2 = [("o4", "carol", "40", "2026-01-02 09:00:00")]


def ingest_bronze(rows, batch_id):
    """BRONZE: exactly what arrived (all strings), plus ingestion metadata. Append only."""
    (spark.createDataFrame(rows, RAW)
        .withColumn("_ingested_at", current_timestamp()).withColumn("_batch_id", lit(batch_id))
        .write.format("delta").mode("append").save(BRONZE))


def build_silver(batch_id):
    """SILVER: typed, validated, deduplicated. Bad rows go to a rejects table with a reason."""
    b = spark.read.format("delta").load(BRONZE).filter(col("_batch_id") == batch_id)
    # Spark 4 has ANSI mode ON: cast("abc" AS DOUBLE) raises an error and kills the job.
    # try_cast returns NULL instead, so the bad row can be routed to the rejects table.
    typed = (b.withColumn("amount_d", expr("try_cast(amount AS DOUBLE)"))
               .withColumn("order_ts_t", expr("try_cast(order_ts AS TIMESTAMP)")))
    reason = (col("customer").isNull() | col("amount_d").isNull())
    rejects = typed.filter(reason).withColumn(
        "reason", lit("missing customer or non-numeric amount")).select("order_id", "customer", "amount", "reason", "_batch_id")
    good = typed.filter(~reason)
    w = Window.partitionBy("order_id").orderBy(col("_ingested_at").desc())
    clean = (good.withColumn("rn", row_number().over(w)).filter("rn = 1")
             .select("order_id", "customer", col("amount_d").alias("amount"), col("order_ts_t").alias("order_ts")))
    rejects.write.format("delta").mode("append").save(REJECTS)
    if DeltaTable.isDeltaTable(spark, SILVER):                       # idempotent upsert by key
        (DeltaTable.forPath(spark, SILVER).alias("t").merge(clean.alias("s"), "t.order_id = s.order_id")
            .whenMatchedUpdateAll().whenNotMatchedInsertAll().execute())
    else:
        clean.write.format("delta").save(SILVER)


def build_gold(day):
    """GOLD: daily revenue per customer. Rebuilds ONE day with replaceWhere, so reruns are safe."""
    s = spark.read.format("delta").load(SILVER).withColumn("dt", to_date("order_ts")).filter(col("dt") == day)
    agg = s.groupBy("dt", "customer").agg(sum_("amount").alias("revenue"))
    (agg.write.format("delta").mode("overwrite").option("replaceWhere", f"dt = '{day}'").save(GOLD)
     if DeltaTable.isDeltaTable(spark, GOLD) else agg.write.format("delta").partitionBy("dt").save(GOLD))


def run_day(rows, batch_id, day):
    ingest_bronze(rows, batch_id)
    build_silver(batch_id)
    build_gold(day)


print("\n== run day 1")
run_day(day1, "b1", "2026-01-01")
print("silver:");  spark.read.format("delta").load(SILVER).orderBy("order_id").show()
print("rejects (quarantine, with a reason):");  spark.read.format("delta").load(REJECTS).show(truncate=False)
print("gold:");  spark.read.format("delta").load(GOLD).orderBy("customer").show()

print("== run day 2")
run_day(day2, "b2", "2026-01-02")

print("== RERUN day 1 gold only: idempotent, the totals do not change")
build_gold("2026-01-01")
spark.read.format("delta").load(GOLD).orderBy("dt", "customer").show()

print("bronze keeps everything, including the duplicate and the bad rows (replayable):")
print("  bronze rows:", spark.read.format("delta").load(BRONZE).count())

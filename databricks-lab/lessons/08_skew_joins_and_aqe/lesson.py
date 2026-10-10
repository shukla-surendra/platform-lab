"""Lesson 8: join strategies, data skew, salting and Adaptive Query Execution.

Run:  uv run python lessons/08_skew_joins_and_aqe/lesson.py
Look at the printed plans, not just the timings (a laptop is too small to show real cluster behaviour).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import fresh, get_spark, show_files

import time
from pyspark.sql.functions import broadcast, col, concat_ws, explode, floor, lit, rand, sequence, sum as sum_, when

spark = get_spark()
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "-1")      # start with broadcast OFF so we see sort-merge
spark.conf.set("spark.sql.adaptive.enabled", "false")             # and AQE OFF to see the raw behaviour

# 1,000,000 fact rows where 70% of rows share one hot key (key 0), the rest spread over 1000 keys
facts = (spark.range(1_000_000)
         .withColumn("key", when(rand(7) < 0.7, lit(0)).otherwise((rand(11) * 1000).cast("int") + 1))
         .withColumn("v", lit(1)))
dim = spark.range(0, 1001).withColumnRenamed("id", "key").withColumn("label", concat_ws("-", lit("k"), col("key")))


def timed(name, df):
    t = time.time()
    n = df.count()
    print(f"  {name:<28} rows={n:<8} {time.time() - t:5.1f}s")


def partition_sizes(df, key="key"):
    sizes = df.repartition(4, key).rdd.glom().map(len).collect()
    print("  rows per post-shuffle partition (4 partitions):", sizes)


print("\n== the skew: one key owns most rows, so one shuffle partition gets most of the work")
partition_sizes(facts)

print("\n== 1. sort-merge join (default for two big sides): look for Exchange + SortMergeJoin")
j = facts.join(dim, "key")
j.explain()
timed("sort-merge join", j)

print("\n== 2. broadcast join: the small side is shipped to every task, no shuffle of the big side")
jb = facts.join(broadcast(dim), "key")
jb.explain()
timed("broadcast join", jb)

print("\n== 3. skewed AGGREGATION fixed with salting (two-phase aggregation)")
direct = facts.groupBy("key").agg(sum_("v").alias("n"))
timed("groupBy key (skewed)", direct)
SALTS = 8
salted = (facts.withColumn("salt", floor(rand(3) * SALTS))
          .groupBy("key", "salt").agg(sum_("v").alias("partial"))        # phase 1: spread the hot key across 8 groups
          .groupBy("key").agg(sum_("partial").alias("n")))               # phase 2: combine the 8 partials
timed("two-phase with salt", salted)
same = direct.orderBy("key").collect() == salted.orderBy("key").collect()
print("  results identical:", same)

print("\n== 4. AQE: re-plans at runtime using real sizes")
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "10m")
ja = facts.join(dim.filter("key < 500"), "key")
ja.explain()
timed("join with AQE on", ja)
print("  (see AdaptiveSparkPlan in the plan; with a 10 MB threshold AQE/the planner can choose a broadcast)")

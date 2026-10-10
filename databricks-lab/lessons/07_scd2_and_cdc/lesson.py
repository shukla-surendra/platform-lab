"""Lesson 7: SCD Type 2 with one MERGE, and applying a CDC feed in the right order.

Run:  uv run python lessons/07_scd2_and_cdc/lesson.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import fresh, get_spark, show_files

from delta.tables import DeltaTable
from pyspark.sql import Window
from pyspark.sql.functions import col, lit, row_number, when

spark = get_spark()
root = fresh("l07")
DIM, CUST = f"{root}/dim_customer", f"{root}/customer_current"

print("\n================ PART A: SCD Type 2 ================")
dim_schema = "customer_id INT, city STRING, valid_from INT, valid_to INT, is_current BOOLEAN"
spark.createDataFrame([(1, "Pune", 1, None, True), (2, "Delhi", 1, None, True)], dim_schema) \
    .write.format("delta").save(DIM)

# day 5: customer 1 moved to Mumbai, customer 3 is new, customer 2 unchanged
changes = spark.createDataFrame([(1, "Mumbai"), (2, "Delhi"), (3, "Goa")], "customer_id INT, city STRING")
EFFECTIVE = 5

dim = DeltaTable.forPath(spark, DIM)
current = spark.read.format("delta").load(DIM).filter("is_current")

# rows that really changed or are new; is_new = there is no current row for this key yet
changed = (changes.alias("s").join(current.alias("t"), "customer_id", "left")
           .filter(col("t.city").isNull() | (col("s.city") != col("t.city")))
           .select("customer_id", col("s.city").alias("city"), col("t.city").isNull().alias("is_new")))

# the trick: a CHANGED existing row appears twice
#   copy 1: real key         -> MATCHES the current row    -> closes it
#   copy 2: merge_key = NULL -> matches nothing            -> INSERTS the new version
# a brand-new key only needs copy 2 (nothing to close). Emitting copy 1 as well would insert it twice.
close_old = changed.filter("NOT is_new").withColumn("merge_key", col("customer_id"))
insert_new = changed.withColumn("merge_key", lit(None).cast("int"))
staged = close_old.unionByName(insert_new)

(dim.alias("t").merge(staged.alias("s"), "t.customer_id = s.merge_key AND t.is_current = true")
    .whenMatchedUpdate(set={"is_current": lit(False), "valid_to": lit(EFFECTIVE)})
    .whenNotMatchedInsert(values={"customer_id": col("s.customer_id"), "city": col("s.city"),
                                  "valid_from": lit(EFFECTIVE), "valid_to": lit(None).cast("int"),
                                  "is_current": lit(True)})
    .execute())
spark.read.format("delta").load(DIM).orderBy("customer_id", "valid_from").show()
print("customer 1 has two rows (history); customer 2 was untouched; customer 3 is new.")

print("\n================ PART B: applying a CDC feed ================")
spark.createDataFrame([(1, "alice", 1), (2, "bob", 1), (3, "carol", 1)], "id INT, name STRING, seq INT") \
    .write.format("delta").save(CUST)

# out-of-order feed: note the seq values. id=2 has an update (seq 3) arriving BEFORE an older one (seq 2).
cdc = spark.createDataFrame(
    [(2, "bobby", 3, "U"), (2, "bob_old", 2, "U"), (1, None, 4, "D"), (4, "dave", 2, "I"), (1, "alice2", 3, "U")],
    "id INT, name STRING, seq INT, op STRING",
)
w = Window.partitionBy("id").orderBy(col("seq").desc())
last_change = cdc.withColumn("rn", row_number().over(w)).filter("rn = 1").drop("rn")   # latest per key BY SEQUENCE
print("last change per key (chosen by seq, not arrival order):"); last_change.orderBy("id").show()

(DeltaTable.forPath(spark, CUST).alias("t").merge(last_change.alias("s"), "t.id = s.id")
    .whenMatchedDelete(condition="s.op = 'D'")
    .whenMatchedUpdate(condition="s.op != 'D' AND s.seq > t.seq", set={"name": "s.name", "seq": "s.seq"})
    .whenNotMatchedInsert(condition="s.op != 'D'", values={"id": "s.id", "name": "s.name", "seq": "s.seq"})
    .execute())
spark.read.format("delta").load(CUST).orderBy("id").show()
print("id 1 deleted, id 2 has the newest value (bobby), id 4 inserted, id 3 untouched.")

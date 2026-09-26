"""Glue PySpark job: raw orders CSV -> validated, partitioned Parquet.

Arguments (set as job default_arguments by Terraform):
  --raw_path       s3://.../raw/orders/
  --curated_path   s3://.../curated/orders/
  --rejected_path  s3://.../rejected/orders/

Good rows go to curated_path as Parquet partitioned by order_date.
Bad rows (null keys, non-positive quantity/price, unparseable timestamp,
duplicate order_id) go to rejected_path as JSON with a `reject_reason`.
"""
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import Window
from pyspark.sql import functions as F

args = getResolvedOptions(sys.argv, ["JOB_NAME", "raw_path", "curated_path", "rejected_path"])

sc = SparkContext()
glue_context = GlueContext(sc)
spark = glue_context.spark_session
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

# transformation_ctx is what lets job bookmarks track which raw files were
# already processed — on a re-run only NEW files are read.
raw_dyf = glue_context.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [args["raw_path"]], "recurse": True},
    format="csv",
    format_options={"withHeader": True},
    transformation_ctx="raw_orders",
)

if raw_dyf.count() == 0:
    print("No new raw data (bookmark up to date) - nothing to do.")
    job.commit()
    sys.exit(0)

df = raw_dyf.toDF()

# --- Typing -----------------------------------------------------------------
typed = (
    df.select(
        F.trim(F.col("order_id")).alias("order_id"),
        F.trim(F.col("customer_id")).alias("customer_id"),
        F.lower(F.trim(F.col("product"))).alias("product"),
        F.lower(F.trim(F.col("category"))).alias("category"),
        F.col("quantity").cast("int").alias("quantity"),
        F.col("unit_price").cast("double").alias("unit_price"),
        F.to_timestamp(F.col("order_ts")).alias("order_ts"),
        F.upper(F.trim(F.col("status"))).alias("status"),
    )
)

# --- Validation: tag each row with the first rule it breaks -----------------
reason = (
    F.when(F.col("order_id").isNull() | (F.col("order_id") == ""), "missing_order_id")
    .when(F.col("customer_id").isNull() | (F.col("customer_id") == ""), "missing_customer_id")
    .when(F.col("quantity").isNull() | (F.col("quantity") <= 0), "invalid_quantity")
    .when(F.col("unit_price").isNull() | (F.col("unit_price") <= 0), "invalid_unit_price")
    .when(F.col("order_ts").isNull(), "invalid_timestamp")
)
tagged = typed.withColumn("reject_reason", reason)

rejected_invalid = tagged.filter(F.col("reject_reason").isNotNull())
valid = tagged.filter(F.col("reject_reason").isNull()).drop("reject_reason")

# --- Dedupe: keep the latest record per order_id ----------------------------
w = Window.partitionBy("order_id").orderBy(F.col("order_ts").desc())
ranked = valid.withColumn("_rn", F.row_number().over(w))
deduped = ranked.filter(F.col("_rn") == 1).drop("_rn")
rejected_dupes = (
    ranked.filter(F.col("_rn") > 1).drop("_rn").withColumn("reject_reason", F.lit("duplicate_order_id"))
)

# --- Features / derived columns ---------------------------------------------
curated = (
    deduped.withColumn("total_amount", F.round(F.col("quantity") * F.col("unit_price"), 2))
    .withColumn("order_date", F.to_date(F.col("order_ts")))
    .withColumn("order_hour", F.hour(F.col("order_ts")))
    .withColumn("is_high_value", (F.col("total_amount") >= 100).cast("int"))
)

# --- Write ------------------------------------------------------------------
# append (not overwrite) so bookmarked incremental runs accumulate; the crawler
# then picks up new order_date=... partitions.
curated.write.mode("append").partitionBy("order_date").parquet(args["curated_path"])

rejected = rejected_invalid.unionByName(rejected_dupes)
if rejected.head(1):
    rejected.write.mode("append").json(args["rejected_path"])

print(f"curated rows: {curated.count()}, rejected rows: {rejected.count()}")

job.commit()

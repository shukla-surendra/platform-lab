"""Lakeflow Declarative Pipelines (formerly Delta Live Tables): bronze -> silver (with CDC + SCD2).

Attach this file to a pipeline (not a normal notebook run). The framework derives the dependency
graph, manages checkpoints and retries, and records expectation metrics in the event log.
"""
import dlt
from pyspark.sql.functions import col, expr

LANDING = "/Volumes/<catalog>/<schema>/landing/customers_cdc/"


@dlt.table(comment="Raw CDC events, exactly as received.")
def customers_cdc_bronze():
    return (spark.readStream.format("cloudFiles")
            .option("cloudFiles.format", "json")
            .load(LANDING))


@dlt.view
@dlt.expect_or_drop("has_key", "customer_id IS NOT NULL")        # drop rows that break the rule
@dlt.expect("valid_op", "op IN ('I','U','D')")                   # keep the row but record the violation
def customers_cdc_clean():
    return dlt.read_stream("customers_cdc_bronze").select(
        "customer_id", "name", "city", "op", col("event_ts").cast("timestamp").alias("event_ts"))


dlt.create_streaming_table("customers_silver")

dlt.apply_changes(                       # a.k.a. AUTO CDC: ordering, deletes and SCD2 handled for you
    target="customers_silver",
    source="customers_cdc_clean",
    keys=["customer_id"],
    sequence_by="event_ts",              # out-of-order events are placed correctly
    apply_as_deletes=expr("op = 'D'"),
    except_column_list=["op"],
    stored_as_scd_type=2,                # keep history (use 1 to overwrite)
)


@dlt.table(comment="Customers per city: a gold aggregate over current rows.")
def customers_by_city_gold():
    return (dlt.read("customers_silver").filter("__END_AT IS NULL")   # current rows only (SCD2 columns)
            .groupBy("city").count())

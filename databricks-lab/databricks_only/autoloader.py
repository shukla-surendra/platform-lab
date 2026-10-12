"""Auto Loader: ingest new files incrementally into a bronze table.

Run as a Databricks job or notebook. `spark` is provided by Databricks.
"""
from pyspark.sql.functions import col, current_timestamp

SOURCE = "/Volumes/<catalog>/<schema>/landing/orders/"          # a Unity Catalog volume
SCHEMA_DIR = "/Volumes/<catalog>/<schema>/_meta/orders_schema"  # inferred schema is stored here
CHECKPOINT = "/Volumes/<catalog>/<schema>/_meta/orders_checkpoint"

(spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", SCHEMA_DIR)
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")   # new columns: fail once, restart with new schema
    .option("cloudFiles.inferColumnTypes", "true")
    .option("rescuedDataColumn", "_rescued_data")                # values that don't fit the schema are kept, not lost
    .load(SOURCE)
    .withColumn("_ingested_at", current_timestamp())
    .withColumn("_source_file", col("_metadata.file_path"))      # which file did each row come from?
 .writeStream
    .option("checkpointLocation", CHECKPOINT)
    .option("mergeSchema", "true")
    .trigger(availableNow=True)                                  # incremental batch: process new files, then stop
    .toTable("<catalog>.<schema>.bronze_orders"))

# Synapse Studio > Develop > New notebook > attach to "sparksmall", language PySpark.
# Paste cell by cell. First cell takes 2-4 minutes (pool cold start); billing runs while the session is live.
# Replace <SA> with your storage account name.

SA = "<SA>"
raw = f"abfss://raw@{SA}.dfs.core.windows.net"
cur = f"abfss://curated@{SA}.dfs.core.windows.net"

# --- Cell 2: read CSVs ---------------------------------------------------------------------
sales = spark.read.csv(f"{raw}/sales/", header=True, inferSchema=True)
products = spark.read.csv(f"{raw}/reference/products.csv", header=True, inferSchema=True)
customers = spark.read.csv(f"{raw}/reference/customers.csv", header=True, inferSchema=True)
sales.printSchema(); print(sales.count())

# --- Cell 3: transform + write partitioned Parquet (Silver) ---------------------------------
from pyspark.sql import functions as F
silver = (sales.join(products, "product_id").join(customers, "customer_id")
          .withColumn("revenue", F.col("quantity") * F.col("unit_price") * (1 - F.col("discount_pct") / 100))
          .withColumn("month", F.date_format("order_date", "yyyy-MM")))
silver.write.mode("overwrite").partitionBy("month").parquet(f"{cur}/silver/sales_enriched")

# --- Cell 4: Delta Lake (ACID, time travel) ---------------------------------------------------
silver.write.format("delta").mode("overwrite").save(f"{cur}/delta/sales_enriched")
from delta.tables import DeltaTable
dt = DeltaTable.forPath(spark, f"{cur}/delta/sales_enriched")
dt.update("country = 'UK'", {"discount_pct": "0"})                    # an UPDATE on a data lake
display(dt.history())                                                  # every version
display(spark.read.format("delta").option("versionAsOf", 0).load(f"{cur}/delta/sales_enriched").limit(5))

# --- Cell 5: Lake database table usable from Spark SQL (and from serverless SQL automatically) -----
spark.sql("CREATE DATABASE IF NOT EXISTS lab")
silver.write.mode("overwrite").format("parquet").saveAsTable("lab.sales_enriched")
display(spark.sql("SELECT country, ROUND(SUM(revenue),0) revenue FROM lab.sales_enriched GROUP BY country ORDER BY 2 DESC"))
# Now go to serverless SQL and run:  SELECT TOP 10 * FROM lab.dbo.sales_enriched   (shared metadata sync)

-- ONLY if you set enable_dedicated_pool = true.  THIS BILLS PER HOUR WHILE ONLINE.
-- Run against the "dw100" dedicated pool. Pause it when you are not actively typing queries.
-- Replace <SA> with your storage account name.

-- Hash-distributed fact table in a clustered columnstore index (the MPP default for big facts)
CREATE TABLE dbo.fact_sales
WITH (DISTRIBUTION = HASH(customer_id), CLUSTERED COLUMNSTORE INDEX)
AS SELECT * FROM (SELECT CAST(NULL AS INT) AS order_id, CAST(NULL AS DATE) AS order_date, CAST(NULL AS INT) AS customer_id,
                         CAST(NULL AS INT) AS product_id, CAST(NULL AS INT) AS quantity, CAST(NULL AS INT) AS discount_pct) t WHERE 1 = 0;

-- Bulk load straight from the lake with COPY (fastest path; uses the workspace identity)
COPY INTO dbo.fact_sales
FROM 'https://<SA>.dfs.core.windows.net/raw/sales/'
WITH (FILE_TYPE = 'CSV', FIRSTROW = 2, CREDENTIAL = (IDENTITY = 'Managed Identity'));

-- Small dimension: REPLICATE a copy to every compute node to avoid data movement on joins
CREATE TABLE dbo.dim_product (product_id INT, product_name VARCHAR(100), category VARCHAR(50), unit_price DECIMAL(10,2))
WITH (DISTRIBUTION = REPLICATE, CLUSTERED INDEX (product_id));

COPY INTO dbo.dim_product
FROM 'https://<SA>.dfs.core.windows.net/raw/reference/products.csv'
WITH (FILE_TYPE = 'CSV', FIRSTROW = 2, CREDENTIAL = (IDENTITY = 'Managed Identity'));

-- Inspect how rows landed across the 60 distributions (skew = slow queries)
DBCC PDW_SHOWSPACEUSED('dbo.fact_sales');

-- See the plan and data movement steps
EXPLAIN SELECT category, SUM(quantity) FROM dbo.fact_sales f JOIN dbo.dim_product p ON p.product_id = f.product_id GROUP BY category;

-- Serverless: build a logical data warehouse over the lake, then write Parquet back with CETAS.
-- Run once in master:   CREATE DATABASE lakehouse;   then switch the database dropdown to "lakehouse".
-- Replace <SA> with your storage account name.

-- One-time setup -----------------------------------------------------------------------------
CREATE MASTER KEY ENCRYPTION BY PASSWORD = 'Ch@ngeMe-Str0ng-Passw0rd!';

-- Authenticate to storage as the WORKSPACE MANAGED IDENTITY (Terraform granted it Blob Data Contributor)
CREATE DATABASE SCOPED CREDENTIAL wi_cred WITH IDENTITY = 'Managed Identity';

CREATE EXTERNAL DATA SOURCE raw_lake     WITH (LOCATION = 'https://<SA>.dfs.core.windows.net/raw',     CREDENTIAL = wi_cred);
CREATE EXTERNAL DATA SOURCE curated_lake WITH (LOCATION = 'https://<SA>.dfs.core.windows.net/curated', CREDENTIAL = wi_cred);

CREATE EXTERNAL FILE FORMAT csv_fmt WITH (
    FORMAT_TYPE = DELIMITED_TEXT,
    FORMAT_OPTIONS (FIELD_TERMINATOR = ',', STRING_DELIMITER = '"', FIRST_ROW = 2, PARSER_VERSION = '2.0')
);
CREATE EXTERNAL FILE FORMAT parquet_fmt WITH (FORMAT_TYPE = PARQUET, DATA_COMPRESSION = 'org.apache.hadoop.io.compress.SnappyCodec');

-- External tables = a schema over files; no data is copied ---------------------------------------
CREATE EXTERNAL TABLE dbo.sales (
    order_id INT, order_date DATE, customer_id INT, product_id INT, quantity INT, discount_pct INT
) WITH (LOCATION = 'sales/', DATA_SOURCE = raw_lake, FILE_FORMAT = csv_fmt);

CREATE EXTERNAL TABLE dbo.products (
    product_id INT, product_name VARCHAR(100), category VARCHAR(50), unit_price DECIMAL(10,2)
) WITH (LOCATION = 'reference/products.csv', DATA_SOURCE = raw_lake, FILE_FORMAT = csv_fmt);

CREATE EXTERNAL TABLE dbo.customers (
    customer_id INT, name VARCHAR(100), email VARCHAR(200), country VARCHAR(50), signup_date DATE
) WITH (LOCATION = 'reference/customers.csv', DATA_SOURCE = raw_lake, FILE_FORMAT = csv_fmt);

-- Query it like a normal warehouse
SELECT p.category, SUM(s.quantity * p.unit_price * (1 - s.discount_pct / 100.0)) AS revenue
FROM dbo.sales s JOIN dbo.products p ON p.product_id = s.product_id
GROUP BY p.category ORDER BY revenue DESC;

-- CETAS: Create External Table As Select. Materialises results as Parquet in the lake -------------
CREATE EXTERNAL TABLE dbo.revenue_by_country_month
WITH (LOCATION = 'revenue_by_country_month/', DATA_SOURCE = curated_lake, FILE_FORMAT = parquet_fmt)
AS
SELECT c.country, FORMAT(s.order_date, 'yyyy-MM') AS month,
       SUM(s.quantity * p.unit_price * (1 - s.discount_pct / 100.0)) AS revenue
FROM dbo.sales s
JOIN dbo.products p  ON p.product_id = s.product_id
JOIN dbo.customers c ON c.customer_id = s.customer_id
GROUP BY c.country, FORMAT(s.order_date, 'yyyy-MM');

-- Parquet is columnar and compressed: compare how much less this scans than the CSVs
SELECT TOP 20 * FROM dbo.revenue_by_country_month ORDER BY revenue DESC;

-- A view is the usual serving layer for Power BI
CREATE VIEW dbo.v_top_customers AS
SELECT TOP 100 c.customer_id, c.name, c.country, SUM(s.quantity * p.unit_price) AS gross
FROM dbo.sales s JOIN dbo.products p ON p.product_id = s.product_id JOIN dbo.customers c ON c.customer_id = s.customer_id
GROUP BY c.customer_id, c.name, c.country ORDER BY gross DESC;

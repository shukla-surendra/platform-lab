-- Run in Synapse Studio > Develop > New SQL script, Connect to: "Built-in" (serverless), database: master
-- Replace <SA> with your storage account name (terraform output storage_account).
-- Cost: serverless bills per data processed. These files total a few MB => effectively free.

-- 1) Peek at a CSV with no table, no load: schema inferred from the header
SELECT TOP 10 *
FROM OPENROWSET(
    BULK 'https://<SA>.dfs.core.windows.net/raw/reference/customers.csv',
    FORMAT = 'CSV', PARSER_VERSION = '2.0', HEADER_ROW = TRUE
) AS customers;

-- 2) Query a whole folder with a wildcard (12 monthly files as one table). filepath() tells you the source file.
SELECT
    r.filepath(1) AS month_file,
    COUNT(*)      AS orders
FROM OPENROWSET(
    BULK 'https://<SA>.dfs.core.windows.net/raw/sales/sales_*.csv',
    FORMAT = 'CSV', PARSER_VERSION = '2.0', HEADER_ROW = TRUE
) AS r
GROUP BY r.filepath(1)
ORDER BY month_file;

-- 3) Explicit types = less data scanned and fewer surprises (inferred types are all wide varchar for CSV)
SELECT TOP 10 *
FROM OPENROWSET(
    BULK 'https://<SA>.dfs.core.windows.net/raw/sales/sales_*.csv',
    FORMAT = 'CSV', PARSER_VERSION = '2.0', FIRSTROW = 2
) WITH (
    order_id INT, order_date DATE, customer_id INT, product_id INT, quantity INT, discount_pct INT
) AS s;

-- 4) JSON lines: read each line as one string, then parse with JSON_VALUE
SELECT TOP 10
    JSON_VALUE(doc, '$.type')        AS event_type,
    JSON_VALUE(doc, '$.device.os')   AS os,
    CAST(JSON_VALUE(doc, '$.customer_id') AS INT) AS customer_id
FROM OPENROWSET(
    BULK 'https://<SA>.dfs.core.windows.net/raw/events/events.jsonl',
    FORMAT = 'CSV', FIELDTERMINATOR = '0x0b', FIELDQUOTE = '0x0b', ROWTERMINATOR = '0x0a'
) WITH (doc NVARCHAR(MAX)) AS j;

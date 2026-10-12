-- Unity Catalog: layout, access control, masking, volumes.

-- 1. Layout: a catalog per environment, schemas per layer
CREATE CATALOG IF NOT EXISTS prod;
CREATE SCHEMA  IF NOT EXISTS prod.bronze;
CREATE SCHEMA  IF NOT EXISTS prod.silver;
CREATE SCHEMA  IF NOT EXISTS prod.gold;

-- 2. Grants go to GROUPS. A reader needs USE CATALOG + USE SCHEMA + SELECT.
GRANT USE CATALOG ON CATALOG prod              TO `analysts`;
GRANT USE SCHEMA, SELECT ON SCHEMA prod.gold   TO `analysts`;   -- inherits to current and future tables
GRANT ALL PRIVILEGES ON SCHEMA prod.silver     TO `data_engineers`;

-- 3. Column mask: only members of pii_readers see real emails
CREATE OR REPLACE FUNCTION prod.silver.mask_email(email STRING)
  RETURN CASE WHEN is_account_group_member('pii_readers') THEN email ELSE '***@***' END;
ALTER TABLE prod.silver.customers ALTER COLUMN email SET MASK prod.silver.mask_email;

-- 4. Row filter: sales managers see only their region
CREATE OR REPLACE FUNCTION prod.silver.region_filter(region STRING)
  RETURN is_account_group_member('global_sales') OR is_account_group_member(CONCAT('sales_', region));
ALTER TABLE prod.silver.orders SET ROW FILTER prod.silver.region_filter ON (region);

-- 5. Files: volumes govern non-tabular data
CREATE VOLUME IF NOT EXISTS prod.bronze.landing;
GRANT READ VOLUME, WRITE VOLUME ON VOLUME prod.bronze.landing TO `data_engineers`;

-- 6. Tags help find PII and drive policies
ALTER TABLE prod.silver.customers SET TAGS ('domain' = 'crm', 'contains_pii' = 'true');

-- 7. Inspect: who can do what, and what happened
SHOW GRANTS ON TABLE prod.gold.daily_revenue;
SELECT * FROM system.access.audit ORDER BY event_time DESC LIMIT 20;
SELECT usage_date, sku_name, SUM(usage_quantity) AS dbus
FROM system.billing.usage GROUP BY ALL ORDER BY usage_date DESC LIMIT 30;

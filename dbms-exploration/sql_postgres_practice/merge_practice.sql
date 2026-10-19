-- MERGE PRACTICE SCRIPT
-- Purpose: Practice INSERT / UPDATE / DELETE synchronization using MERGE.
-- Dialect: SQL Server-style MERGE.
-- Note: MERGE syntax varies by database. If you use Databricks, Snowflake,
-- Oracle, PostgreSQL, etc., ask for the dialect-specific version.

DROP TABLE IF EXISTS customer_updates;
DROP TABLE IF EXISTS customers;

-- ============================================================
-- 1. TARGET TABLE
-- ============================================================

CREATE TABLE customers (
    customer_id     INT PRIMARY KEY,
    customer_name   VARCHAR(100) NOT NULL,
    email           VARCHAR(150),
    city            VARCHAR(100),
    status          VARCHAR(20),
    credit_limit    DECIMAL(12,2),
    updated_at      TIMESTAMP
);

-- ============================================================
-- 2. SOURCE TABLE
-- ============================================================

CREATE TABLE customer_updates (
    customer_id     INT,
    customer_name   VARCHAR(100),
    email           VARCHAR(150),
    city            VARCHAR(100),
    status          VARCHAR(20),
    credit_limit    DECIMAL(12,2),
    updated_at      TIMESTAMP
);

-- ============================================================
-- 3. TARGET DATA
-- ============================================================

INSERT INTO customers
(customer_id, customer_name, email, city, status, credit_limit, updated_at)
VALUES
(101, 'Amit Sharma',   'amit@example.com',   'Delhi',     'ACTIVE',   50000.00, '2026-09-01 09:00:00'),
(102, 'Rahul Verma',   'rahul@example.com',  'Mumbai',    'ACTIVE',   75000.00, '2026-09-01 09:00:00'),
(103, 'Neha Singh',    'neha@example.com',   'Pune',      'ACTIVE',   60000.00, '2026-09-01 09:00:00'),
(104, 'Vikas Gupta',   'vikas@example.com',  'Noida',     'ACTIVE',   45000.00, '2026-09-01 09:00:00'),
(105, 'Priya Mehta',   'priya@example.com',  'Bangalore', 'INACTIVE', 30000.00, '2026-09-01 09:00:00'),
(106, 'Ravi Kumar',    'ravi@example.com',   'Chennai',   'ACTIVE',   55000.00, '2026-09-01 09:00:00'),
(107, 'Sanjay Jain',   'sanjay@example.com', 'Jaipur',    'ACTIVE',   40000.00, '2026-09-01 09:00:00'),
(108, 'Pooja Shah',    'pooja@example.com',  'Ahmedabad', 'ACTIVE',   65000.00, '2026-09-01 09:00:00');

-- ============================================================
-- 4. SOURCE / INCOMING DATA
-- ============================================================
-- Deliberately contains:
--   101 -> unchanged
--   102 -> UPDATE
--   103 -> UPDATE
--   104 -> unchanged
--   105 -> UPDATE
--   109 -> INSERT
--   110 -> INSERT
--
-- IDs 106, 107, 108 are absent from the source.
-- They can be used to practice "NOT MATCHED BY SOURCE" logic.

INSERT INTO customer_updates
(customer_id, customer_name, email, city, status, credit_limit, updated_at)
VALUES
(101, 'Amit Sharma',   'amit@example.com',   'Delhi',      'ACTIVE',   50000.00, '2026-09-07 09:00:00'),
(102, 'Rahul Verma',   'rahul@example.com',  'Bangalore',  'ACTIVE',   90000.00, '2026-09-07 09:00:00'),
(103, 'Neha Singh',    'neha.new@example.com','Pune',      'ACTIVE',   80000.00, '2026-09-07 09:00:00'),
(104, 'Vikas Gupta',   'vikas@example.com',  'Noida',      'ACTIVE',   45000.00, '2026-09-07 09:00:00'),
(105, 'Priya Mehta',   'priya@example.com',  'Bangalore',  'ACTIVE',   50000.00, '2026-09-07 09:00:00'),
(109, 'Ankit Patel',   'ankit@example.com',  'Hyderabad',  'ACTIVE',   70000.00, '2026-09-07 09:00:00'),
(110, 'Sneha Kapoor',  'sneha@example.com', 'Kolkata',    'ACTIVE',   65000.00, '2026-09-07 09:00:00');

-- ============================================================
-- 5. INSPECT INITIAL DATA
-- ============================================================

SELECT * FROM customers ORDER BY customer_id;
SELECT * FROM customer_updates ORDER BY customer_id;

-- ============================================================
-- MERGE PRACTICE EXERCISES
-- ============================================================

-- we use a MERGE query when we want to synchronize one table with 
-- another—typically by doing INSERT + UPDATE (and sometimes DELETE) in a single statement.
-- Think of it as:
-- “If the record already exists, update it; if it doesn't exist, insert it.”

-- IMPORTANT:
-- Reset/re-run the DDL + INSERT section before each exercise
-- if you want to practice each MERGE independently.
--
-- Do NOT immediately look at the solutions below.
-- Try writing each MERGE yourself first.

-- ============================================================
-- EXERCISE 1: BASIC UPSERT
-- ============================================================
-- Requirement:
-- Match customers using customer_id.
-- If matched:
--     update customer_name, email, city, status, credit_limit.
-- If not matched:
--     insert the new customer.

-- TODO: Write MERGE here.
MERGE INTO customers AS target
USING customer_updates AS source
ON target.customer_id = source.customer_id

WHEN MATCHED THEN
    UPDATE SET
        customer_name = source.customer_name,
        email         = source.email,
        city          = source.city,
        status        = source.status,
        credit_limit  = source.credit_limit,
        updated_at    = source.updated_at

WHEN NOT MATCHED THEN
    INSERT (
        customer_id,
        customer_name,
        email,
        city,
        status,
        credit_limit,
        updated_at
    )
    VALUES (
        source.customer_id,
        source.customer_name,
        source.email,
        source.city,
        source.status,
        source.credit_limit,
        source.updated_at
    );

-- ============================================================
-- EXERCISE 2: UPDATE ONLY WHEN DATA HAS CHANGED
-- ============================================================
-- Requirement:
-- Update the target only when at least one of these changes:
-- customer_name, email, city, status, credit_limit.
--
-- Why?
-- Avoid unnecessary updates when source and target contain
-- identical data.

-- TODO: Write MERGE here.


-- ============================================================
-- EXERCISE 3: UPDATE ONLY IF SOURCE IS NEWER
-- ============================================================
-- Requirement:
-- Match on customer_id.
-- Update only when source.updated_at > target.updated_at.
-- Insert new customers.

-- TODO: Write MERGE here.


-- ============================================================
-- EXERCISE 4: CONDITIONAL UPDATE
-- ============================================================
-- Requirement:
-- If customer exists:
--   - update city and email
--   - update credit_limit only if source credit_limit > target credit_limit
--   - update status
--
-- If customer does not exist:
--   insert the complete record.

-- TODO: Write MERGE here.


-- ============================================================
-- EXERCISE 5: CONDITIONAL INSERT
-- ============================================================
-- Requirement:
-- Insert only customers from the source whose status = 'ACTIVE'.
-- Existing customers should still be updated.

-- TODO: Write MERGE here.


-- ============================================================
-- EXERCISE 6: DELETE WHEN MATCHED
-- ============================================================
-- Requirement:
-- If a customer exists in both tables:
--   - if source.status = 'INACTIVE', delete the target record
--   - otherwise update it
--
-- If customer does not exist:
--   insert it.

-- TODO: Write MERGE here.


-- ============================================================
-- EXERCISE 7: NOT MATCHED BY SOURCE
-- ============================================================
-- Requirement:
-- Synchronize the target with the source.
-- Customers that exist in the target but NOT in the source
-- should be marked INACTIVE rather than deleted.
--
-- Hint:
-- SQL Server supports WHEN NOT MATCHED BY SOURCE.

-- TODO: Write MERGE here.


-- ============================================================
-- EXERCISE 8: DELETE STALE CUSTOMERS
-- ============================================================
-- Requirement:
-- Customers missing from the source should be deleted
-- from the target.
--
-- Be careful: this is destructive synchronization.

-- TODO: Write MERGE here.


-- ============================================================
-- EXERCISE 9: SOURCE FILTERING
-- ============================================================
-- Requirement:
-- Only process source records where credit_limit >= 60000.
--
-- Existing qualifying customers -> update.
-- New qualifying customers -> insert.
--
-- Hint:
-- You can filter the source dataset in the USING clause.

-- TODO: Write MERGE here.


-- ============================================================
-- EXERCISE 10: NULL-SAFE CHANGE DETECTION
-- ============================================================
-- Requirement:
-- Update a row only if the source and target are different.
-- Handle NULL values correctly when comparing columns.
--
-- Practice specifically:
--   email
--   city
--   status
--   credit_limit
--
-- Think about why:
--     target.email <> source.email
-- is not sufficient when NULL is possible.

-- TODO: Write MERGE here.


-- ============================================================
-- EXERCISE 11: AUDIT / TIMESTAMP UPDATE
-- ============================================================
-- Requirement:
-- Whenever a target row is updated, set updated_at to the
-- current timestamp.
--
-- New records should use the source timestamp or current
-- timestamp according to your chosen design.

-- TODO: Write MERGE here.


-- ============================================================
-- EXERCISE 12: HARD INTERVIEW-STYLE MERGE
-- ============================================================
-- Requirement:
--
-- 1. Match using customer_id.
--
-- 2. If matched:
--      Update only when source.updated_at > target.updated_at.
--
-- 3. If matched and source.status = 'INACTIVE':
--      Delete the customer.
--
-- 4. If not matched:
--      Insert only ACTIVE customers.
--
-- 5. Customers in target but absent from source:
--      Mark them INACTIVE.
--
-- Think carefully about the order and interaction of the
-- conditions.

-- TODO: Write MERGE here.


-- ============================================================
-- SOLUTIONS
-- ============================================================
-- The following solutions are intentionally separated from
-- the exercises. Try the exercises first.
--
-- ============================================================
-- SOLUTION 1: BASIC UPSERT
-- ============================================================

/*
MERGE INTO customers AS target
USING customer_updates AS source
ON target.customer_id = source.customer_id

WHEN MATCHED THEN
    UPDATE SET
        customer_name = source.customer_name,
        email         = source.email,
        city          = source.city,
        status        = source.status,
        credit_limit  = source.credit_limit,
        updated_at    = source.updated_at

WHEN NOT MATCHED BY TARGET THEN
    INSERT
    (
        customer_id,
        customer_name,
        email,
        city,
        status,
        credit_limit,
        updated_at
    )
    VALUES
    (
        source.customer_id,
        source.customer_name,
        source.email,
        source.city,
        source.status,
        source.credit_limit,
        source.updated_at
    );
*/


-- ============================================================
-- SOLUTION 2: UPDATE ONLY WHEN DATA CHANGED
-- ============================================================

/*
MERGE INTO customers AS target
USING customer_updates AS source
ON target.customer_id = source.customer_id

WHEN MATCHED AND
(
       target.customer_name <> source.customer_name
    OR target.email         <> source.email
    OR target.city          <> source.city
    OR target.status        <> source.status
    OR target.credit_limit  <> source.credit_limit
)
THEN
    UPDATE SET
        customer_name = source.customer_name,
        email         = source.email,
        city          = source.city,
        status        = source.status,
        credit_limit  = source.credit_limit,
        updated_at    = source.updated_at

WHEN NOT MATCHED BY TARGET THEN
    INSERT
    (
        customer_id, customer_name, email, city,
        status, credit_limit, updated_at
    )
    VALUES
    (
        source.customer_id, source.customer_name, source.email, source.city,
        source.status, source.credit_limit, source.updated_at
    );
*/


-- ============================================================
-- SOLUTION 3: UPDATE ONLY IF SOURCE IS NEWER
-- ============================================================

/*
MERGE INTO customers AS target
USING customer_updates AS source
ON target.customer_id = source.customer_id

WHEN MATCHED AND source.updated_at > target.updated_at
THEN
    UPDATE SET
        customer_name = source.customer_name,
        email         = source.email,
        city          = source.city,
        status        = source.status,
        credit_limit  = source.credit_limit,
        updated_at    = source.updated_at

WHEN NOT MATCHED BY TARGET THEN
    INSERT
    (
        customer_id, customer_name, email, city,
        status, credit_limit, updated_at
    )
    VALUES
    (
        source.customer_id, source.customer_name, source.email, source.city,
        source.status, source.credit_limit, source.updated_at
    );
*/


-- ============================================================
-- SOLUTION 4: CONDITIONAL UPDATE
-- ============================================================

/*
MERGE INTO customers AS target
USING customer_updates AS source
ON target.customer_id = source.customer_id

WHEN MATCHED THEN
    UPDATE SET
        city         = source.city,
        email        = source.email,
        status       = source.status,
        credit_limit =
            CASE
                WHEN source.credit_limit > target.credit_limit
                THEN source.credit_limit
                ELSE target.credit_limit
            END,
        updated_at   = source.updated_at

WHEN NOT MATCHED BY TARGET THEN
    INSERT
    (
        customer_id, customer_name, email, city,
        status, credit_limit, updated_at
    )
    VALUES
    (
        source.customer_id, source.customer_name, source.email, source.city,
        source.status, source.credit_limit, source.updated_at
    );
*/


-- ============================================================
-- SOLUTION 5: CONDITIONAL INSERT
-- ============================================================

/*
MERGE INTO customers AS target
USING customer_updates AS source
ON target.customer_id = source.customer_id

WHEN MATCHED THEN
    UPDATE SET
        customer_name = source.customer_name,
        email         = source.email,
        city          = source.city,
        status        = source.status,
        credit_limit  = source.credit_limit,
        updated_at    = source.updated_at

WHEN NOT MATCHED BY TARGET
     AND source.status = 'ACTIVE'
THEN
    INSERT
    (
        customer_id, customer_name, email, city,
        status, credit_limit, updated_at
    )
    VALUES
    (
        source.customer_id, source.customer_name, source.email, source.city,
        source.status, source.credit_limit, source.updated_at
    );
*/


-- ============================================================
-- SOLUTION 6: DELETE WHEN MATCHED
-- ============================================================

/*
MERGE INTO customers AS target
USING customer_updates AS source
ON target.customer_id = source.customer_id

WHEN MATCHED AND source.status = 'INACTIVE'
THEN DELETE

WHEN MATCHED THEN
    UPDATE SET
        customer_name = source.customer_name,
        email         = source.email,
        city          = source.city,
        status        = source.status,
        credit_limit  = source.credit_limit,
        updated_at    = source.updated_at

WHEN NOT MATCHED BY TARGET THEN
    INSERT
    (
        customer_id, customer_name, email, city,
        status, credit_limit, updated_at
    )
    VALUES
    (
        source.customer_id, source.customer_name, source.email, source.city,
        source.status, source.credit_limit, source.updated_at
    );
*/


-- ============================================================
-- SOLUTION 7: MARK TARGET-ONLY CUSTOMERS INACTIVE
-- ============================================================

/*
MERGE INTO customers AS target
USING customer_updates AS source
ON target.customer_id = source.customer_id

WHEN MATCHED THEN
    UPDATE SET
        customer_name = source.customer_name,
        email         = source.email,
        city          = source.city,
        status        = source.status,
        credit_limit  = source.credit_limit,
        updated_at    = source.updated_at

WHEN NOT MATCHED BY TARGET THEN
    INSERT
    (
        customer_id, customer_name, email, city,
        status, credit_limit, updated_at
    )
    VALUES
    (
        source.customer_id, source.customer_name, source.email, source.city,
        source.status, source.credit_limit, source.updated_at
    )

WHEN NOT MATCHED BY SOURCE THEN
    UPDATE SET
        status = 'INACTIVE',
        updated_at = GETDATE();
*/


-- ============================================================
-- SOLUTION 8: DELETE TARGET-ONLY CUSTOMERS
-- ============================================================

/*
MERGE INTO customers AS target
USING customer_updates AS source
ON target.customer_id = source.customer_id

WHEN MATCHED THEN
    UPDATE SET
        customer_name = source.customer_name,
        email         = source.email,
        city          = source.city,
        status        = source.status,
        credit_limit  = source.credit_limit,
        updated_at    = source.updated_at

WHEN NOT MATCHED BY TARGET THEN
    INSERT
    (
        customer_id, customer_name, email, city,
        status, credit_limit, updated_at
    )
    VALUES
    (
        source.customer_id, source.customer_name, source.email, source.city,
        source.status, source.credit_limit, source.updated_at
    )

WHEN NOT MATCHED BY SOURCE THEN
    DELETE;
*/


-- ============================================================
-- SOLUTION 9: SOURCE FILTERING
-- ============================================================

/*
MERGE INTO customers AS target
USING
(
    SELECT *
    FROM customer_updates
    WHERE credit_limit >= 60000
) AS source
ON target.customer_id = source.customer_id

WHEN MATCHED THEN
    UPDATE SET
        customer_name = source.customer_name,
        email         = source.email,
        city          = source.city,
        status        = source.status,
        credit_limit  = source.credit_limit,
        updated_at    = source.updated_at

WHEN NOT MATCHED BY TARGET THEN
    INSERT
    (
        customer_id, customer_name, email, city,
        status, credit_limit, updated_at
    )
    VALUES
    (
        source.customer_id, source.customer_name, source.email, source.city,
        source.status, source.credit_limit, source.updated_at
    );
*/


-- ============================================================
-- SOLUTION 10: NULL-SAFE CHANGE DETECTION
-- ============================================================
-- SQL Server does not treat NULL = NULL as TRUE.
-- INTERSECT is one approach for null-safe comparison.

 /*
MERGE INTO customers AS target
USING customer_updates AS source
ON target.customer_id = source.customer_id

WHEN MATCHED AND EXISTS
(
    SELECT
        target.customer_name,
        target.email,
        target.city,
        target.status,
        target.credit_limit
    EXCEPT
    SELECT
        source.customer_name,
        source.email,
        source.city,
        source.status,
        source.credit_limit
)
THEN
    UPDATE SET
        customer_name = source.customer_name,
        email         = source.email,
        city          = source.city,
        status        = source.status,
        credit_limit  = source.credit_limit,
        updated_at    = source.updated_at

WHEN NOT MATCHED BY TARGET THEN
    INSERT
    (
        customer_id, customer_name, email, city,
        status, credit_limit, updated_at
    )
    VALUES
    (
        source.customer_id, source.customer_name, source.email, source.city,
        source.status, source.credit_limit, source.updated_at
    );
*/


-- ============================================================
-- SOLUTION 11: AUDIT / TIMESTAMP UPDATE
-- ============================================================

/*
MERGE INTO customers AS target
USING customer_updates AS source
ON target.customer_id = source.customer_id

WHEN MATCHED THEN
    UPDATE SET
        customer_name = source.customer_name,
        email         = source.email,
        city          = source.city,
        status        = source.status,
        credit_limit  = source.credit_limit,
        updated_at    = GETDATE()

WHEN NOT MATCHED BY TARGET THEN
    INSERT
    (
        customer_id, customer_name, email, city,
        status, credit_limit, updated_at
    )
    VALUES
    (
        source.customer_id, source.customer_name, source.email, source.city,
        source.status, source.credit_limit, GETDATE()
    );
*/


-- ============================================================
-- SOLUTION 12: HARD INTERVIEW-STYLE MERGE
-- ============================================================
-- Note: Exact semantics of multiple MERGE branches vary by engine.
-- This solution demonstrates SQL Server-style ordering.

 /*
MERGE INTO customers AS target
USING customer_updates AS source
ON target.customer_id = source.customer_id

WHEN MATCHED AND source.status = 'INACTIVE'
THEN DELETE

WHEN MATCHED AND source.updated_at > target.updated_at
THEN
    UPDATE SET
        customer_name = source.customer_name,
        email         = source.email,
        city          = source.city,
        status        = source.status,
        credit_limit  = source.credit_limit,
        updated_at    = source.updated_at

WHEN NOT MATCHED BY TARGET
     AND source.status = 'ACTIVE'
THEN
    INSERT
    (
        customer_id, customer_name, email, city,
        status, credit_limit, updated_at
    )
    VALUES
    (
        source.customer_id, source.customer_name, source.email, source.city,
        source.status, source.credit_limit, source.updated_at
    )

WHEN NOT MATCHED BY SOURCE
THEN
    UPDATE SET
        status = 'INACTIVE',
        updated_at = GETDATE();
 */


-- ============================================================
-- VERIFICATION QUERIES
-- ============================================================

-- Check target after MERGE
-- SELECT * FROM customers ORDER BY customer_id;

-- Check source
-- SELECT * FROM customer_updates ORDER BY customer_id;

-- Find records in target but not source
-- SELECT t.*
-- FROM customers t
-- LEFT JOIN customer_updates s
--     ON t.customer_id = s.customer_id
-- WHERE s.customer_id IS NULL;

-- Find records in source but not target
-- SELECT s.*
-- FROM customer_updates s
-- LEFT JOIN customers t
--     ON s.customer_id = t.customer_id
-- WHERE t.customer_id IS NULL;

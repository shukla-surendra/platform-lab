-- Version 1: MERGE
BEGIN;

MERGE INTO customers c
USING (VALUES
    ('Alice Chen', 'alice@example.com', 'Canada', '2025-11-02'::date),
    ('Sam Novak', 'newuser@example.com', 'USA', '2026-04-01'::date)
) AS feed(name, email, country, signup_date)
ON c.email = feed.email
WHEN MATCHED THEN
    UPDATE SET country = feed.country
WHEN NOT MATCHED THEN
    INSERT (name, email, country, signup_date) VALUES (feed.name, feed.email, feed.country, feed.signup_date);

SELECT name, email, country FROM customers WHERE email IN ('alice@example.com', 'newuser@example.com') ORDER BY email;

ROLLBACK;

-- Version 2: INSERT ... ON CONFLICT -- same result, needs a real unique
-- constraint on `email` (already exists via schema.sql's UNIQUE) rather
-- than an arbitrary join condition.
BEGIN;

INSERT INTO customers (name, email, country, signup_date) VALUES
    ('Alice Chen', 'alice@example.com', 'Canada', '2025-11-02'),
    ('Sam Novak', 'newuser@example.com', 'USA', '2026-04-01')
ON CONFLICT (email) DO UPDATE SET country = EXCLUDED.country;

SELECT name, email, country FROM customers WHERE email IN ('alice@example.com', 'newuser@example.com') ORDER BY email;

ROLLBACK;

-- Run before ANALYZE: note the estimated rows= is likely wildly off from
-- the actual rows= (default selectivity guess, no real stats yet).
EXPLAIN ANALYZE SELECT * FROM orders WHERE order_date > '2026-03-01';

-- Refresh statistics for this table.
ANALYZE orders;

-- Run again: the estimate should now match reality much more closely.
EXPLAIN ANALYZE SELECT * FROM orders WHERE order_date > '2026-03-01';

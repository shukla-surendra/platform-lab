-- Natural choice: Seq Scan, cost 1.23 -- cheaper than the index on a table this small.
EXPLAIN SELECT * FROM orders WHERE customer_id = 5;

-- Force the index to compare costs directly (diagnostic only -- never
-- leave this set in a real session/production).
SET enable_seqscan = off;
EXPLAIN SELECT * FROM orders WHERE customer_id = 5;
RESET enable_seqscan;

-- Uses the index (compares against the stored, raw value).
EXPLAIN SELECT * FROM customers WHERE email = 'alice@example.com';

-- Cannot use the index -- LOWER(email) is not what the index is sorted by.
EXPLAIN SELECT * FROM customers WHERE LOWER(email) = 'alice@example.com';

-- The fix: an expression index matching the exact wrapped form used above.
CREATE INDEX ON customers (LOWER(email));
EXPLAIN SELECT * FROM customers WHERE LOWER(email) = 'alice@example.com';
-- Still Seq Scan -- table's too small for the planner to prefer the index
-- (cost 1.15 vs the index's 8.15). It's usable, just not worth it here.

-- Prove it's genuinely usable by forcing the planner's hand (diagnostic
-- only -- never leave this set in a real session/production):
SET enable_seqscan = off;
EXPLAIN SELECT * FROM customers WHERE LOWER(email) = 'alice@example.com';
RESET enable_seqscan;

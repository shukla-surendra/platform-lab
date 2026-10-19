-- Anti-join: LEFT JOIN guarantees every customer appears at least once;
-- filtering on the right side's key being NULL keeps only the customers
-- who never matched an order row at all.
SELECT c.name
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
WHERE o.order_id IS NULL;

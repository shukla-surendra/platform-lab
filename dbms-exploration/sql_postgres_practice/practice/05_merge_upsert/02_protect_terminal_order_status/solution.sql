BEGIN;

SELECT order_id, status FROM orders WHERE order_id IN (1, 4, 12);

MERGE INTO orders o
USING (VALUES (1, 'shipped'), (4, 'delivered'), (12, 'shipped')) AS feed(order_id, new_status)
ON o.order_id = feed.order_id
WHEN MATCHED AND o.status NOT IN ('delivered', 'cancelled') THEN
    UPDATE SET status = feed.new_status
WHEN MATCHED THEN
    DO NOTHING;

SELECT order_id, status FROM orders WHERE order_id IN (1, 4, 12) ORDER BY order_id;

ROLLBACK;

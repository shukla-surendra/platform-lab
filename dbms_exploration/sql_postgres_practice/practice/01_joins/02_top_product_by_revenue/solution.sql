-- unit_price is snapshotted on order_items, deliberately not re-read from
-- products.price -- see problem.md for why that matters.
SELECT p.name, SUM(oi.quantity * oi.unit_price) AS revenue
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.product_id, p.name
ORDER BY revenue DESC
LIMIT 5;

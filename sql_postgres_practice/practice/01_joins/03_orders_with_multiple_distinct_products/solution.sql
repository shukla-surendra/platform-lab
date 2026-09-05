SELECT order_id, COUNT(DISTINCT product_id) AS distinct_products
FROM order_items
GROUP BY order_id
HAVING COUNT(DISTINCT product_id) > 1
ORDER BY order_id;

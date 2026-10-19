WITH order_totals AS (
    SELECT o.order_id, o.customer_id, o.order_date, SUM(oi.quantity * oi.unit_price) AS total
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    GROUP BY o.order_id, o.customer_id, o.order_date
)
SELECT
    customer_id, order_id, order_date, total,
    SUM(total) OVER (PARTITION BY customer_id ORDER BY order_date) AS running_total
FROM order_totals
WHERE customer_id = 1
ORDER BY order_date;

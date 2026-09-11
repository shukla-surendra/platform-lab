WITH order_totals AS (
    SELECT o.order_id, o.customer_id, SUM(oi.quantity * oi.unit_price) AS total
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    GROUP BY o.order_id, o.customer_id
),
ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY total DESC) AS rn
    FROM order_totals
)
SELECT c.name, r.order_id, r.total
FROM ranked r
JOIN customers c ON c.customer_id = r.customer_id
WHERE r.rn = 1
ORDER BY c.name;

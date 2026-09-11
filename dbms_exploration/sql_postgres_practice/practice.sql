SELECT
    employee_id,
    department,
    salary,
    RANK() OVER (
        PARTITION BY department
        ORDER BY salary DESC
    ) AS rnk,
    DENSE_RANK() OVER (
        PARTITION BY department
        ORDER BY salary DESC
    ) AS dense_rnk,
    ROW_NUMBER() OVER (
        PARTITION BY department
        ORDER BY salary DESC
    ) AS row_num
FROM employees;


--second HIGHEST SALARY in each DEPARTMENT
WITH ranked AS (
    SELECT *,
           DENSE_RANK() OVER (
               PARTITION BY department
               ORDER BY salary DESC
           ) AS rnk
    FROM employees
)
SELECT *
FROM ranked
WHERE rnk = 2;




SELECT
    EXTRACT(MONTH FROM order_date) AS month,
    SUM(amount) AS total_sales
FROM orders
GROUP BY EXTRACT(MONTH FROM order_date)
ORDER BY month;


-- How do you find the top 3 customers by revenue for each month?

-- find revenue group by month and customer
SELECT
    EXTRACT(MONTH FROM order_date) AS month,
    customer_id,
    SUM(amount) AS revenue
FROM orders
GROUP BY
    EXTRACT(MONTH FROM order_date),
    customer_id;

-- then rank
SELECT
    month,
    customer_id,
    revenue,
    ROW_NUMBER() OVER (
        PARTITION BY month
        ORDER BY revenue DESC
    ) AS rn
FROM (
    SELECT
        EXTRACT(MONTH FROM order_date) AS month,
        customer_id,
        SUM(amount) AS revenue
    FROM orders
    GROUP BY
        EXTRACT(MONTH FROM order_date),
        customer_id
) t;

--final top 3
SELECT
    month,
    customer_id,
    revenue
FROM (
    SELECT
        month,
        customer_id,
        revenue,
        ROW_NUMBER() OVER (
            PARTITION BY month
            ORDER BY revenue DESC
        ) AS rn
    FROM (
        SELECT
            EXTRACT(MONTH FROM order_date) AS month,
            customer_id,
            SUM(amount) AS revenue
        FROM orders
        GROUP BY
            EXTRACT(MONTH FROM order_date),
            customer_id
    ) t
) ranked
WHERE rn <= 3
ORDER BY month, revenue DESC;
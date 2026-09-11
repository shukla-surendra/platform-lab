```sql
 CREATE TABLE orders (
    id BIGINT NOT NULL,
    customer_id BIGINT NOT NULL,
    order_date DATE NOT NULL,
    amount NUMERIC(12,2) NOT NULL
) PARTITION BY RANGE (order_date);
```



```sql
CREATE TABLE orders_2024
PARTITION OF orders
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE orders_2025
PARTITION OF orders
FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

CREATE TABLE orders_2026
PARTITION OF orders
FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
```

```
partition_lab=# \d
                  List of relations
 Schema |    Name     |       Type        |  Owner
--------+-------------+-------------------+----------
 public | orders      | partitioned table | postgres
 public | orders_2024 | table             | postgres
 public | orders_2025 | table             | postgres
 public | orders_2026 | table             | postgres
(4 rows)
```

```sql
INSERT INTO orders VALUES
(1, 101, '2024-05-10', 500),
(2, 102, '2025-06-15', 700),
(3, 103, '2026-07-20', 900),

(4, 104, '2028-01-15', 1200),
(5, 105, '2028-04-22', 1500),
(6, 106, '2028-09-10', 1800),

(7, 107, '2029-02-05', 2100),
(8, 108, '2029-06-18', 2400),
(9, 109, '2029-11-25', 2700),

(10, 110, '2030-03-12', 3000),
(11, 111, '2030-07-20', 3300),
(12, 112, '2030-12-05', 3600);
```


```
partition_lab=# SELECT tableoid::regclass, *
FROM orders;
  tableoid   | id | customer_id | order_date | amount
-------------+----+-------------+------------+--------
 orders_2024 |  1 |         101 | 2024-05-10 | 500.00
 orders_2025 |  2 |         102 | 2025-06-15 | 700.00
 orders_2026 |  3 |         103 | 2026-07-20 | 900.00
(3 rows)
```

```
partition_lab=# INSERT INTO orders VALUES
(1, 101, '2024-05-10', 500),
(2, 102, '2025-06-15', 700),
(3, 103, '2026-07-20', 900),

(4, 104, '2028-01-15', 1200),
(5, 105, '2028-04-22', 1500),
(6, 106, '2028-09-10', 1800),

(7, 107, '2029-02-05', 2100),
(8, 108, '2029-06-18', 2400),
(9, 109, '2029-11-25', 2700),

(10, 110, '2030-03-12', 3000),
(11, 111, '2030-07-20', 3300),
(12, 112, '2030-12-05', 3600);
ERROR:  no partition of relation "orders" found for row
DETAIL:  Partition key of the failing row contains (order_date) = (2028-01-15).
```

```sql
CREATE TABLE orders_2028
PARTITION OF orders
FOR VALUES FROM ('2028-01-01') TO ('2029-01-01');

CREATE TABLE orders_2029
PARTITION OF orders
FOR VALUES FROM ('2029-01-01') TO ('2030-01-01');

CREATE TABLE orders_2030
PARTITION OF orders
FOR VALUES FROM ('2030-01-01') TO ('2031-01-01');
```
```sql
INSERT INTO orders VALUES
(1, 101, '2024-05-10', 500),
(2, 102, '2025-06-15', 700),
(3, 103, '2026-07-20', 900),

(4, 104, '2028-01-15', 1200),
(5, 105, '2028-04-22', 1500),
(6, 106, '2028-09-10', 1800),

(7, 107, '2029-02-05', 2100),
(8, 108, '2029-06-18', 2400),
(9, 109, '2029-11-25', 2700),

(10, 110, '2030-03-12', 3000),
(11, 111, '2030-07-20', 3300),
(12, 112, '2030-12-05', 3600);
```

```
partition_lab=# select * from orders;
 id | customer_id | order_date | amount
----+-------------+------------+---------
  1 |         101 | 2024-05-10 |  500.00
  1 |         101 | 2024-05-10 |  500.00
  2 |         102 | 2025-06-15 |  700.00
  2 |         102 | 2025-06-15 |  700.00
  3 |         103 | 2026-07-20 |  900.00
  3 |         103 | 2026-07-20 |  900.00
  4 |         104 | 2028-01-15 | 1200.00
  5 |         105 | 2028-04-22 | 1500.00
  6 |         106 | 2028-09-10 | 1800.00
  7 |         107 | 2029-02-05 | 2100.00
  8 |         108 | 2029-06-18 | 2400.00
  9 |         109 | 2029-11-25 | 2700.00
 10 |         110 | 2030-03-12 | 3000.00
 11 |         111 | 2030-07-20 | 3300.00
 12 |         112 | 2030-12-05 | 3600.00
(15 rows)
```

```
partition_lab=# select * from orders_2030;
 id | customer_id | order_date | amount
----+-------------+------------+---------
 10 |         110 | 2030-03-12 | 3000.00
 11 |         111 | 2030-07-20 | 3300.00
 12 |         112 | 2030-12-05 | 3600.00
(3 rows)
```


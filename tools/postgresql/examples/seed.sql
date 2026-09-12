-- One running schema and dataset used throughout sql-tutorial-zero-to-hero.md.
-- Deliberately includes the messy real-world cases a tutorial needs to be honest about:
-- a customer with a NULL city, a customer who has never ordered anything, a product
-- that's never been ordered, and orders in more than one status.

DROP TABLE IF EXISTS order_items, orders, products, customers, employees CASCADE;

CREATE TABLE customers (
    customer_id  INT PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    email        VARCHAR(150) UNIQUE NOT NULL,
    city         VARCHAR(50),
    signup_date  DATE NOT NULL
);

CREATE TABLE products (
    product_id  INT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    category    VARCHAR(50) NOT NULL,
    price       NUMERIC(10, 2) NOT NULL
);

CREATE TABLE orders (
    order_id     INT PRIMARY KEY,
    customer_id  INT NOT NULL REFERENCES customers(customer_id),
    order_date   DATE NOT NULL,
    status       VARCHAR(20) NOT NULL
);

CREATE TABLE order_items (
    order_item_id  SERIAL PRIMARY KEY,
    order_id       INT NOT NULL REFERENCES orders(order_id),
    product_id     INT NOT NULL REFERENCES products(product_id),
    quantity       INT NOT NULL,
    unit_price     NUMERIC(10, 2) NOT NULL
);

CREATE TABLE employees (
    emp_id      INT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    manager_id  INT REFERENCES employees(emp_id),
    salary      NUMERIC(10, 2) NOT NULL,
    department  VARCHAR(50) NOT NULL
);

INSERT INTO customers (customer_id, name, email, city, signup_date) VALUES
    (1, 'Ava Chen',   'ava@example.com',  'Austin',  '2024-01-15'),
    (2, 'Liam Patel', 'liam@example.com', 'Seattle', '2024-02-20'),
    (3, 'Maya Ortiz', 'maya@example.com', 'Austin',  '2024-03-05'),
    (4, 'Noah Kim',   'noah@example.com', NULL,      '2024-04-10'),
    (5, 'Zoe Baker',  'zoe@example.com',  'Denver',  '2024-05-01');  -- never places an order

INSERT INTO products (product_id, name, category, price) VALUES
    (101, 'Wireless Mouse',       'Electronics',     25.00),
    (102, 'Mechanical Keyboard',  'Electronics',     85.00),
    (103, 'Standing Desk',        'Furniture',      350.00),
    (104, 'Desk Lamp',            'Furniture',       40.00),
    (105, 'Notebook',             'Office Supplies',  5.00),
    (106, 'Webcam',               'Electronics',     60.00);  -- never ordered

INSERT INTO orders (order_id, customer_id, order_date, status) VALUES
    (1001, 1, '2024-06-01', 'completed'),
    (1002, 1, '2024-06-15', 'completed'),
    (1003, 2, '2024-06-03', 'completed'),
    (1004, 2, '2024-07-01', 'pending'),
    (1005, 3, '2024-06-20', 'completed'),
    (1006, 3, '2024-07-10', 'cancelled'),
    (1007, 4, '2024-06-25', 'completed');

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
    (1001, 101, 2, 25.00),
    (1001, 105, 3, 5.00),
    (1002, 102, 1, 85.00),
    (1003, 103, 1, 350.00),
    (1003, 104, 2, 40.00),
    (1004, 101, 1, 25.00),
    (1005, 102, 1, 85.00),
    (1005, 105, 5, 5.00),
    (1006, 104, 1, 40.00),
    (1007, 101, 1, 25.00),
    (1007, 102, 1, 85.00);

INSERT INTO employees (emp_id, name, manager_id, salary, department) VALUES
    (1, 'Grace Lee',  NULL, 220000, 'Executive'),
    (2, 'Sam Rivera', 1,    165000, 'Engineering'),
    (3, 'Priya Nair', 1,    158000, 'Sales'),
    (4, 'Tom Walsh',  2,    142000, 'Engineering'),
    (5, 'Ella Fox',   2,    171000, 'Engineering'),  -- earns more than her manager, Sam
    (6, 'Ben Osei',   3,     96000, 'Sales');

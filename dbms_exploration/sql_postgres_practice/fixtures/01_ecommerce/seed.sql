-- 10 customers -- #10 (Priya Shah) deliberately has zero orders.
INSERT INTO customers (name, email, country, signup_date) VALUES
('Alice Chen',      'alice@example.com',   'USA',    '2025-11-02'),
('Bilal Ahmed',     'bilal@example.com',   'UK',     '2025-11-15'),
('Carla Ruiz',      'carla@example.com',   'Spain',  '2025-12-01'),
('Dmitri Ivanov',   'dmitri@example.com',  'Russia', '2025-12-10'),
('Emma Novak',      'emma@example.com',    'Poland', '2026-01-03'),
('Farid Hossain',   'farid@example.com',   'USA',    '2026-01-05'),
('Grace Kim',       'grace@example.com',   'Korea',  '2026-01-20'),
('Hiro Tanaka',     'hiro@example.com',    'Japan',  '2026-02-01'),
('Ines Costa',      'ines@example.com',    'Brazil', '2026-02-14'),
('Priya Shah',      'priya@example.com',   'India',  '2026-03-01');

-- 12 products across 4 categories.
INSERT INTO products (name, category, price) VALUES
('Wireless Mouse',        'Electronics', 25.00),
('Mechanical Keyboard',   'Electronics', 89.00),
('USB-C Hub',             'Electronics', 39.00),
('Noise Cancelling Headphones', 'Electronics', 199.00),
('Standing Desk',         'Home',        349.00),
('Desk Lamp',             'Home',        29.00),
('Ergonomic Chair',       'Home',        259.00),
('Coffee Mug',            'Home',         12.00),
('Deep Work',             'Books',        18.00),
('Designing Data-Intensive Applications', 'Books', 45.00),
('Wool Sweater',          'Apparel',      59.00),
('Running Shoes',         'Apparel',      79.00);

-- 18 orders across Jan-Apr 2026, spread across customers 1-9 (never 10).
-- product_id order: Mouse=1 Keyboard=2 Hub=3 Headphones=4 Desk=5 Lamp=6
--                    Chair=7 Mug=8 DeepWork=9 DDIA=10 Sweater=11 Shoes=12
INSERT INTO orders (customer_id, order_date, status) VALUES
(1, '2026-01-05', 'delivered'),   -- order 1
(1, '2026-02-10', 'delivered'),   -- order 2
(2, '2026-01-08', 'delivered'),   -- order 3
(3, '2026-01-12', 'cancelled'),   -- order 4
(3, '2026-03-01', 'delivered'),   -- order 5
(4, '2026-01-15', 'delivered'),   -- order 6
(5, '2026-02-02', 'shipped'),     -- order 7
(5, '2026-02-20', 'delivered'),   -- order 8
(5, '2026-03-15', 'delivered'),   -- order 9
(6, '2026-01-25', 'delivered'),   -- order 10
(7, '2026-02-05', 'delivered'),   -- order 11
(7, '2026-04-01', 'pending'),     -- order 12
(8, '2026-02-18', 'delivered'),   -- order 13
(9, '2026-03-10', 'delivered'),   -- order 14
(1, '2026-03-20', 'delivered'),   -- order 15
(2, '2026-03-22', 'delivered'),   -- order 16
(4, '2026-04-02', 'shipped'),     -- order 17
(6, '2026-04-05', 'delivered');   -- order 18

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 1, 1, 25.00), (1, 2, 1, 89.00),
(2, 4, 1, 199.00),
(3, 9, 2, 18.00),
(4, 5, 1, 349.00),
(5, 6, 2, 29.00), (5, 8, 3, 12.00),
(6, 7, 1, 259.00),
(7, 3, 1, 39.00),
(8, 11, 1, 59.00), (8, 12, 1, 79.00),
(9, 10, 1, 45.00),
(10, 1, 2, 25.00),
(11, 4, 1, 199.00), (11, 3, 1, 39.00),
(12, 2, 1, 89.00),
(13, 9, 1, 18.00), (13, 10, 1, 45.00),
(14, 12, 2, 79.00),
(15, 7, 1, 259.00), (15, 6, 1, 29.00),
(16, 1, 1, 25.00),
(17, 5, 1, 349.00),
(18, 8, 4, 12.00);

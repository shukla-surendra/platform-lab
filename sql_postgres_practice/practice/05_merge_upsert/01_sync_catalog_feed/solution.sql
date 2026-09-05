BEGIN;

SELECT name, price FROM products WHERE name IN ('Wireless Mouse', 'Mechanical Keyboard', 'Webcam HD');

MERGE INTO products AS p
USING (VALUES
    ('Wireless Mouse', 'Electronics', 22.00),
    ('Mechanical Keyboard', 'Electronics', 95.00),
    ('Webcam HD', 'Electronics', 49.00)
) AS feed(name, category, price)
ON p.name = feed.name
WHEN MATCHED THEN
    UPDATE SET price = feed.price
WHEN NOT MATCHED THEN
    INSERT (name, category, price) VALUES (feed.name, feed.category, feed.price);

SELECT name, price FROM products WHERE name IN ('Wireless Mouse', 'Mechanical Keyboard', 'Webcam HD') ORDER BY name;

ROLLBACK;  -- change to COMMIT to keep the change

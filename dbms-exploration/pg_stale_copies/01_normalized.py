"""
01 — Store it ONCE, join on read. Nothing can go stale.

Scenario: categories have several attributes (name, path, tax rate, return days) and
every product belongs to 1-2 categories. Now "Phones" is renamed and its tax drops.

Story: one price board for the whole shop. Shelves hold only a pointer ("category_id").
The database assembles the page at read time with a JOIN, so every read sees the
current master record. Change the board once, done.

Many-to-many (a product in several categories) = a link table, product_categories.
Postgres joins are cheap with indexes, so normalizing costs little on reads.
"""
from common import pg, show

db = pg()
db.execute("""
DROP TABLE IF EXISTS product_categories, products, categories CASCADE;
CREATE TABLE categories (
    id text PRIMARY KEY, name text NOT NULL, path text NOT NULL,
    tax_rate int NOT NULL, return_days int NOT NULL);
CREATE TABLE products (id int PRIMARY KEY, name text NOT NULL, price int NOT NULL);
CREATE TABLE product_categories (                      -- the many-to-many link
    product_id int REFERENCES products(id), category_id text REFERENCES categories(id),
    PRIMARY KEY (product_id, category_id));
CREATE INDEX ON product_categories (category_id);
INSERT INTO categories VALUES
    ('phones', 'Phones', 'Electronics > Phones', 18, 7),
    ('laptops', 'Laptops', 'Electronics > Laptops', 18, 10),
    ('sale', 'Sale', 'Offers > Sale', 0, 0);
INSERT INTO products SELECT g, 'product' || g, 1000 + g % 500 FROM generate_series(1, 20000) g;
INSERT INTO product_categories SELECT g, CASE WHEN g % 2 = 1 THEN 'phones' ELSE 'laptops' END FROM generate_series(1, 20000) g;
INSERT INTO product_categories SELECT g, 'sale' FROM generate_series(4, 20000, 4) g;
""")

# ONE row changes. That's the whole update.
r = db.execute("UPDATE categories SET name = 'Mobile Phones', tax_rate = 12 WHERE id = 'phones'")
show("rows updated", r.rowcount)

PRODUCT_PAGE = """
SELECT p.name, p.price, c.name, c.tax_rate
FROM products p
JOIN product_categories pc ON pc.product_id = p.id
JOIN categories c ON c.id = pc.category_id
WHERE p.id = %s"""
for row in db.execute(PRODUCT_PAGE, (1,)):
    show("product 1 page", row)
for row in db.execute(PRODUCT_PAGE, (4,)):
    show("product 4 page", row)


"""
Real output:

rows updated                           1
product 1 page                         ('product1', 1001, 'Mobile Phones', 12)
product 4 page                         ('product4', 1004, 'Laptops', 18)
product 4 page                         ('product4', 1004, 'Sale', 0)
"""

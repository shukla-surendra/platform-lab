"""
03 — When you DO copy for speed: keep the copy in sync automatically.

Sometimes even Postgres denormalizes, e.g. a search/listing table read millions of
times, so it stores category data next to the product (a jsonb column). Then the copies
can go stale again (the same problem as MongoDB embedding, see
mongo_explore/stale_copies/). Two ways Postgres helps:

A) Trigger: updating a category rewrites the copies IN THE SAME TRANSACTION.
   Never stale, but every category update pays for the fan-out (MongoDB: a fan-out update).
B) Materialized view: a stored query result. Stale until REFRESH. Cheap to read,
   you choose when to pay (like a background sync job, on a schedule).
"""
from common import pg, show

db = pg()
db.execute("""
DROP MATERIALIZED VIEW IF EXISTS product_listing;
ALTER TABLE products ADD COLUMN IF NOT EXISTS categories_cache jsonb;
UPDATE products p SET categories_cache = (
    SELECT jsonb_agg(jsonb_build_object('id', c.id, 'name', c.name, 'tax', c.tax_rate))
    FROM product_categories pc JOIN categories c ON c.id = pc.category_id WHERE pc.product_id = p.id);

CREATE OR REPLACE FUNCTION sync_category_copies() RETURNS trigger AS $$
BEGIN
    UPDATE products p SET categories_cache = (
        SELECT jsonb_agg(jsonb_build_object('id', c.id, 'name', c.name, 'tax', c.tax_rate))
        FROM product_categories pc JOIN categories c ON c.id = pc.category_id WHERE pc.product_id = p.id)
    WHERE p.id IN (SELECT product_id FROM product_categories WHERE category_id = NEW.id);
    RETURN NEW;
END $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS categories_sync ON categories;
CREATE TRIGGER categories_sync AFTER UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION sync_category_copies();

CREATE MATERIALIZED VIEW product_listing AS
    SELECT p.id, p.name, c.name AS category, c.tax_rate
    FROM products p JOIN product_categories pc ON pc.product_id = p.id JOIN categories c ON c.id = pc.category_id;
""")

db.execute("UPDATE categories SET name = 'Smartphones', tax_rate = 5 WHERE id = 'phones'")

show("A) jsonb copy (trigger)", db.execute("SELECT categories_cache FROM products WHERE id = 1").fetchone()[0])
show("B) materialized view", db.execute("SELECT category, tax_rate FROM product_listing WHERE id = 1").fetchone())
db.execute("REFRESH MATERIALIZED VIEW product_listing")
show("B) after REFRESH", db.execute("SELECT category, tax_rate FROM product_listing WHERE id = 1").fetchone())

with db.cursor() as cur:
    cur.execute("EXPLAIN ANALYZE UPDATE categories SET tax_rate = 6 WHERE id = 'phones'")
    show("cost of 1 category update (trigger)", [r[0] for r in cur.fetchall() if "Trigger" in r[0] or "Execution" in r[0]])


"""
Real output:

A) jsonb copy (trigger)                [{'id': 'phones', 'tax': 5, 'name': 'Smartphones'}]
B) materialized view                   ('Mobile Phones', 12)
B) after REFRESH                       ('Smartphones', 5)
cost of 1 category update (trigger)    ['Trigger categories_history: time=0.040 calls=1', 'Trigger categories_sync: time=50.886 calls=1', 'Execution Time: 50.946 ms']
"""

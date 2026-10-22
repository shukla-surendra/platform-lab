"""
02 — Snapshots and history are still your job.

Normalizing (01) makes "live" data easy, but an invoice must NOT change when the tax
changes. Two standard tools:

1. Snapshot columns: the order line COPIES tax_rate at purchase (MongoDB does the
   same, see mongo_explore/stale_copies/03).
2. History table + trigger: every change to a category is kept with valid_from/valid_to
   ("slowly changing dimension type 2"), so you can ask "what was it on that date?".
"""
from common import pg, show

db = pg()
db.execute("""
DROP TABLE IF EXISTS order_lines, category_history CASCADE;
CREATE TABLE order_lines (
    id serial PRIMARY KEY, product_id int, category_id text,
    tax_rate int NOT NULL,                       -- SNAPSHOT: copied, never updated
    ordered_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE category_history (
    category_id text, name text, tax_rate int,
    valid_from timestamptz NOT NULL, valid_to timestamptz);  -- NULL valid_to = current

CREATE OR REPLACE FUNCTION keep_history() RETURNS trigger AS $$
BEGIN
    UPDATE category_history SET valid_to = now() WHERE category_id = NEW.id AND valid_to IS NULL;
    INSERT INTO category_history VALUES (NEW.id, NEW.name, NEW.tax_rate, now(), NULL);
    RETURN NEW;
END $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS categories_history ON categories;
CREATE TRIGGER categories_history AFTER INSERT OR UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION keep_history();
UPDATE categories SET name = 'Phones', tax_rate = 18 WHERE id = 'phones';  -- reset after 01, starts history
""")

# buy product 1 at today's tax (copy it into the order line)
db.execute("""INSERT INTO order_lines (product_id, category_id, tax_rate)
              SELECT 1, id, tax_rate FROM categories WHERE id = 'phones'""")
db.execute("SELECT pg_sleep(0.1)")
db.execute("UPDATE categories SET name = 'Mobile Phones', tax_rate = 12 WHERE id = 'phones'")

show("category now", db.execute("SELECT name, tax_rate FROM categories WHERE id='phones'").fetchone())
show("invoice (snapshot)", db.execute("SELECT tax_rate FROM order_lines").fetchone())
show("category AS OF the order time", db.execute("""
    SELECT h.name, h.tax_rate FROM order_lines o JOIN category_history h
      ON h.category_id = o.category_id
     AND o.ordered_at >= h.valid_from AND (h.valid_to IS NULL OR o.ordered_at < h.valid_to)""").fetchone())
for row in db.execute("SELECT name, tax_rate, valid_to IS NULL AS current FROM category_history WHERE category_id='phones' ORDER BY valid_from"):
    show("history", row)


"""
Real output:

category now                           ('Mobile Phones', 12)
invoice (snapshot)                     (18,)
category AS OF the order time          ('Phones', 18)
history                                ('Phones', 18, False)
history                                ('Mobile Phones', 12, True)
"""

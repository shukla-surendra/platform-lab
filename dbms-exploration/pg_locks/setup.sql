-- One tiny table used by every lesson: a shop's stock.
CREATE TABLE products (
    id     int PRIMARY KEY,
    name   text NOT NULL,
    price  int  NOT NULL,
    stock  int  NOT NULL
);

INSERT INTO products VALUES
    (1, 'pen',      10, 100),
    (2, 'notebook', 50,  20),
    (3, 'bag',     900,   5);

-- An "orders" table pointing at products (needed for lesson 04: foreign keys take locks too).
CREATE TABLE orders (
    id          serial PRIMARY KEY,
    product_id  int REFERENCES products(id),
    qty         int NOT NULL
);

-- A job queue (lesson 04: SKIP LOCKED).
CREATE TABLE jobs (
    id      int PRIMARY KEY,
    status  text NOT NULL DEFAULT 'pending'
);
INSERT INTO jobs SELECT g, 'pending' FROM generate_series(1, 5) g;

CREATE EXTENSION pg_stat_statements;

-- interview.md Q4 (write skew): at least one doctor must stay on call.
CREATE TABLE doctors (
    name     text PRIMARY KEY,
    on_call  bool NOT NULL
);
INSERT INTO doctors VALUES ('alice', true), ('bob', true);

-- interview.md Q6-Q7: lists row locks (they're not in pg_locks).
CREATE EXTENSION pgrowlocks;

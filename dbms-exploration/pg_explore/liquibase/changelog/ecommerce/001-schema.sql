--liquibase formatted sql

--changeset surendra:ecommerce-001-create-schema
CREATE SCHEMA IF NOT EXISTS ecommerce;
--rollback DROP SCHEMA IF EXISTS ecommerce CASCADE;

--changeset surendra:ecommerce-002-create-customers
CREATE TABLE ecommerce.customers (
    customer_id   SERIAL PRIMARY KEY,
    first_name    VARCHAR(50) NOT NULL,
    last_name     VARCHAR(50) NOT NULL,
    email         VARCHAR(150) UNIQUE NOT NULL,
    phone         VARCHAR(20),
    city          VARCHAR(80),
    country       VARCHAR(80),
    signup_date   DATE NOT NULL
);
--rollback DROP TABLE ecommerce.customers;

--changeset surendra:ecommerce-003-create-categories
CREATE TABLE ecommerce.categories (
    category_id    SERIAL PRIMARY KEY,
    category_name  VARCHAR(80) NOT NULL UNIQUE
);
--rollback DROP TABLE ecommerce.categories;

--changeset surendra:ecommerce-004-create-products
CREATE TABLE ecommerce.products (
    product_id      SERIAL PRIMARY KEY,
    product_name    VARCHAR(120) NOT NULL,
    category_id     INT REFERENCES ecommerce.categories(category_id),
    unit_price      NUMERIC(10, 2) NOT NULL,
    stock_quantity  INT NOT NULL DEFAULT 0,
    created_at      DATE NOT NULL
);
--rollback DROP TABLE ecommerce.products;

--changeset surendra:ecommerce-005-create-orders
CREATE TABLE ecommerce.orders (
    order_id      SERIAL PRIMARY KEY,
    customer_id   INT NOT NULL REFERENCES ecommerce.customers(customer_id),
    order_date    DATE NOT NULL,
    status        VARCHAR(15) NOT NULL CHECK (status IN ('pending', 'shipped', 'delivered', 'cancelled'))
);
--rollback DROP TABLE ecommerce.orders;

--changeset surendra:ecommerce-006-create-order-items
CREATE TABLE ecommerce.order_items (
    order_item_id  SERIAL PRIMARY KEY,
    order_id       INT NOT NULL REFERENCES ecommerce.orders(order_id),
    product_id     INT NOT NULL REFERENCES ecommerce.products(product_id),
    quantity       INT NOT NULL CHECK (quantity > 0),
    unit_price     NUMERIC(10, 2) NOT NULL
);
--rollback DROP TABLE ecommerce.order_items;

--changeset surendra:ecommerce-007-create-payments
CREATE TABLE ecommerce.payments (
    payment_id      SERIAL PRIMARY KEY,
    order_id        INT NOT NULL REFERENCES ecommerce.orders(order_id),
    payment_method  VARCHAR(20) NOT NULL,
    amount          NUMERIC(10, 2) NOT NULL,
    payment_date    DATE NOT NULL,
    status          VARCHAR(15) NOT NULL CHECK (status IN ('completed', 'failed', 'refunded'))
);
--rollback DROP TABLE ecommerce.payments;

--changeset surendra:ecommerce-008-create-indexes
CREATE INDEX idx_ecommerce_products_category_id ON ecommerce.products(category_id);
CREATE INDEX idx_ecommerce_orders_customer_id ON ecommerce.orders(customer_id);
CREATE INDEX idx_ecommerce_order_items_order_id ON ecommerce.order_items(order_id);
CREATE INDEX idx_ecommerce_order_items_product_id ON ecommerce.order_items(product_id);
CREATE INDEX idx_ecommerce_payments_order_id ON ecommerce.payments(order_id);
--rollback DROP INDEX IF EXISTS idx_ecommerce_products_category_id;
--rollback DROP INDEX IF EXISTS idx_ecommerce_orders_customer_id;
--rollback DROP INDEX IF EXISTS idx_ecommerce_order_items_order_id;
--rollback DROP INDEX IF EXISTS idx_ecommerce_order_items_product_id;
--rollback DROP INDEX IF EXISTS idx_ecommerce_payments_order_id;

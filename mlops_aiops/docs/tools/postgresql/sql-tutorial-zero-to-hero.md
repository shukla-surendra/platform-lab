# SQL, Zero to Hero (PostgreSQL)

Part of [`README.md`](README.md)'s PostgreSQL section, but different in purpose from the
rest of it. The other six files assume SQL fluency and go deep on mechanism, patterns, and
production operations. This file assumes **nothing** — it starts at "what is a table" and
builds, in order, up through joins, subqueries, window functions, and recursive CTEs, using
one running example the whole way through so each new idea sits on top of the last instead
of introducing a new toy schema every time.

Unlike the rest of this section, every single query below was actually run against a real
PostgreSQL 16 instance, and the output shown is the real output — not illustrative. You can
reproduce all of it yourself.

## Setup

```bash
docker run --name pg-tutorial -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=shop \
    -p 15432:5432 -d postgres:16

docker cp examples/seed.sql pg-tutorial:/seed.sql
docker exec pg-tutorial psql -U postgres -d shop -f /seed.sql
docker exec -it pg-tutorial psql -U postgres -d shop   # drop into a live prompt
```

[`examples/seed.sql`](examples/seed.sql) creates and populates everything used below: five
customers, six products, seven orders, eleven order line items, and a six-person employee
hierarchy. It's deliberately not a clean, tidy dataset — one customer has a `NULL` city, one
customer has never placed an order, one product has never been ordered, and orders exist in
three different statuses. Real data has exactly these kinds of edge cases, and a tutorial
that hides them teaches you to write queries that break the first time you touch real data.
Re-running `seed.sql` at any point resets everything back to this original state — several
sections below modify data on purpose, and the next section assumes a fresh reset happened
first.

## 1. First principles: what you're actually querying

A **relational database** stores data as **tables** — a table is a grid: fixed **columns**
(each with a declared type — a number, text, a date, ...) and any number of **rows**, each
row one record. `customers`, `products`, `orders`, and `order_items` in the seed data are
four such tables. The word "relational" refers to how tables relate to each other by
storing another table's identifying value — `orders.customer_id` doesn't repeat a customer's
name and email inside every order row; it stores a reference to a row in `customers`, and a
**join** (section 4) is how you ask for both pieces of information back together. This is
the whole reason relational databases avoid duplicating data everywhere: a customer's name
is stored in exactly one place, and every table that needs to refer to that customer just
holds a small reference to it.

A **primary key** (`customer_id` on `customers`, `order_id` on `orders`, ...) is the column
(or columns) that uniquely identifies a row — no two rows in the same table can share one,
and PostgreSQL enforces that automatically once a column is declared `PRIMARY KEY`. A
**foreign key** (`orders.customer_id REFERENCES customers(customer_id)`) is what makes a
reference to another table's primary key an *enforced* fact rather than just a convention —
PostgreSQL will refuse to insert an order for a customer that doesn't exist:

```
$ INSERT INTO orders (order_id, customer_id, order_date, status)
  VALUES (9999, 999, '2024-08-01', 'pending');
ERROR:  insert or update on table "orders" violates foreign key constraint "orders_customer_id_fkey"
DETAIL:  Key (customer_id)=(999) is not present in table "customers".
```

That's not a bug or an annoyance to work around — it's the database actively protecting you
from ever ending up with an order that points at a customer who doesn't exist. Constraints
generally (primary key, foreign key, `UNIQUE`, `NOT NULL`, `CHECK`) are the database
*refusing to store data that would already be wrong* — far cheaper to catch here than to
discover later as a bug in application logic that assumed the data was always valid.

## 2. `SELECT`, `WHERE`, `ORDER BY`, `LIMIT` — reading data

```sql
SELECT name, city FROM customers WHERE city = 'Austin' ORDER BY name;
```
```
    name    |  city
------------+--------
 Ava Chen   | Austin
 Maya Ortiz | Austin
(2 rows)
```

`SELECT` names the columns you want back (`SELECT *` means "all of them," useful while
exploring, worth avoiding in real application code — see
[`README.md`](README.md#indexing-beyond-the-default-b-tree)'s covering-index section for
exactly why fetching columns you don't need has a real cost). `WHERE` filters *which rows*
qualify, evaluated per row before anything is returned. `ORDER BY` sorts the result — without
it, **a table's row order is not guaranteed to mean anything**, a genuinely common beginner
misconception; if an order matters, it has to be requested explicitly, every time.

Combining conditions, and a numeric range:

```sql
SELECT name, price FROM products WHERE category = 'Electronics' AND price > 30 ORDER BY price DESC;
```
```
        name         | price
---------------------+-------
 Mechanical Keyboard | 85.00
 Webcam               | 60.00
(2 rows)
```

Pattern matching with `LIKE`/`ILIKE` (`ILIKE` is PostgreSQL's case-insensitive variant; `%`
matches any run of characters):

```sql
SELECT name FROM products WHERE name ILIKE '%desk%';
```
```
     name
---------------
 Standing Desk
 Desk Lamp
(2 rows)
```

Notice it matched "Desk Lamp" too, not just "Standing Desk" — `ILIKE '%desk%'` means "contains
the substring 'desk' anywhere, in any case," not "starts with." This is exactly the kind of
detail worth confirming against real output instead of assuming, which is the entire reason
this tutorial runs everything for real.

`LIMIT n` caps how many rows come back — cheap and useful while exploring a table, but
**not** a safe way to paginate through a large result set (see
[`query-patterns.md`](query-patterns.md#the-nth-highest-value)'s `LIMIT`/`OFFSET` coverage,
and [`storage-internals.md`](storage-internals.md) for why `OFFSET` on a large table gets
progressively slower rather than staying flat).

## 3. Aggregation: `GROUP BY` and `HAVING`

An aggregate function collapses many rows into one number: `COUNT(*)`, `SUM(col)`,
`AVG(col)`, `MIN(col)`, `MAX(col)`. Used alone, it collapses the *entire* table into one row.
`GROUP BY` changes that: it collapses rows into one group *per distinct value* of whatever
you group by, and the aggregate then runs once per group instead of once overall.

```sql
SELECT status, COUNT(*) AS order_count FROM orders GROUP BY status ORDER BY status;
```
```
  status   | order_count
-----------+-------------
 cancelled |           1
 completed |           5
 pending   |           1
(3 rows)
```

```sql
SELECT category, ROUND(AVG(price), 2) AS avg_price, COUNT(*) AS num_products
FROM products GROUP BY category ORDER BY avg_price DESC;
```
```
    category     | avg_price | num_products
-----------------+-----------+--------------
 Furniture       |    195.00 |            2
 Electronics     |     56.67 |            3
 Office Supplies |      5.00 |            1
(3 rows)
```

**`WHERE` filters rows before grouping happens; `HAVING` filters groups after aggregation
happens.** This is the single most important distinction in this section, and the reason
`HAVING` exists at all: `WHERE` can't reference an aggregate result (`WHERE COUNT(*) > 1` is
invalid — at the point `WHERE` runs, no aggregation has happened yet to produce a count),
because filtering on "how many rows ended up in this group" is only a question that makes
sense *after* grouping.

```sql
SELECT c.customer_id, c.name, COUNT(o.order_id) AS total_orders
FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name
HAVING COUNT(o.order_id) >= 2
ORDER BY total_orders DESC;
```
```
 customer_id |    name    | total_orders
-------------+------------+--------------
           2 | Liam Patel |            2
           3 | Maya Ortiz |            2
           1 | Ava Chen   |            2
(3 rows)
```

## 4. Joins: combining rows from more than one table

The mental model first, before any syntax: a join looks at two tables and, for every
possible pairing of a row from the left table with a row from the right table, keeps the
pairing if the `ON` condition is true. Different join *types* differ only in what happens to
a row that has **no** match on the other side.

| Type | Keeps |
|---|---|
| `INNER JOIN` | Only pairs where both sides match |
| `LEFT JOIN` | Every row from the left table — unmatched right-side columns come back `NULL` |
| `RIGHT JOIN` | Mirror of `LEFT JOIN` |
| `FULL OUTER JOIN` | Every row from both sides, `NULL`-padded either direction |
| `CROSS JOIN` | Every possible pairing, no condition at all |

### `INNER JOIN` — only rows that match on both sides

```sql
SELECT c.name, o.order_id, o.order_date
FROM customers c
INNER JOIN orders o ON c.customer_id = o.customer_id
ORDER BY c.name, o.order_date;
```
```
    name    | order_id | order_date
------------+----------+------------
 Ava Chen   |     1001 | 2024-06-01
 Ava Chen   |     1002 | 2024-06-15
 Liam Patel |     1003 | 2024-06-03
 Liam Patel |     1004 | 2024-07-01
 Maya Ortiz |     1005 | 2024-06-20
 Maya Ortiz |     1006 | 2024-07-10
 Noah Kim   |     1007 | 2024-06-25
(7 rows)
```

Notice **Zoe Baker isn't in this output at all** — she has zero orders, so she never has a
matching row on the right side, and an `INNER JOIN` silently drops her. This is the exact
behavior an `INNER JOIN` is *for*, but it's also the most common source of a beginner's
"where did my rows go" bug: reach for `INNER JOIN` when you only care about rows that
genuinely have a counterpart on both sides, and reach for `LEFT JOIN` the moment "show me
everyone, including ones with nothing on the other side" is actually the question.

### `LEFT JOIN` — every row on the left, matched or not

```sql
SELECT c.name, o.order_id
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
ORDER BY c.name;
```
```
    name    | order_id
------------+----------
 Ava Chen   |     1001
 Ava Chen   |     1002
 Liam Patel |     1003
 Liam Patel |     1004
 Maya Ortiz |     1005
 Maya Ortiz |     1006
 Noah Kim   |     1007
 Zoe Baker  |
(8 rows)
```

Zoe Baker is back, with `order_id` as `NULL` — she genuinely has no order, and `NULL` is
PostgreSQL's honest way of saying "no value," not zero and not an empty string. This
"unmatched row comes back with `NULL`s" behavior is also the mechanism behind a genuinely
useful pattern: finding rows on the left that have **no** counterpart on the right at all —
an anti-join:

```sql
SELECT c.name
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_id IS NULL;
```
```
   name
-----------
 Zoe Baker
(1 row)
```

The same shape works from the other table, for a different real question — "which products
has nobody ever ordered":

```sql
SELECT p.name AS product_name
FROM products p
LEFT JOIN order_items oi ON p.product_id = oi.product_id
WHERE oi.product_id IS NULL;
```
```
 product_name
--------------
 Webcam
(1 row)
```

`RIGHT JOIN` and `FULL OUTER JOIN` follow the identical logic, just from the other side (or
both sides) — worth knowing they exist, rarely needed in practice, since almost any
`RIGHT JOIN` can be rewritten as a `LEFT JOIN` by swapping which table is written first,
which most people find more readable.

### Self-joins — joining a table to itself

There's no special syntax for this — you join a table to itself and just give the two
"copies" different aliases, so the database (and you) can tell which one you mean in each
column reference. `employees.manager_id` refers back to another row in the *same*
`employees` table — finding each employee's manager means conceptually treating `employees`
as two separate tables, one standing in for "the employee," one for "their manager":

```sql
SELECT e.name AS employee, m.name AS manager, e.salary, m.salary AS manager_salary
FROM employees e
JOIN employees m ON e.manager_id = m.emp_id
ORDER BY e.name;
```
```
  employee  |  manager   |  salary   | manager_salary
------------+------------+-----------+----------------
 Ben Osei   | Priya Nair |  96000.00 |      158000.00
 Ella Fox   | Sam Rivera | 171000.00 |      165000.00
 Priya Nair | Grace Lee  | 158000.00 |      220000.00
 Sam Rivera | Grace Lee  | 165000.00 |      220000.00
 Tom Walsh  | Sam Rivera | 142000.00 |      165000.00
```

And now that both salaries are sitting in the same row, comparing them is a plain `WHERE`:

```sql
SELECT e.name AS employee, m.name AS manager
FROM employees e
JOIN employees m ON e.manager_id = m.emp_id
WHERE e.salary > m.salary;
```
```
 employee |  manager
----------+------------
 Ella Fox | Sam Rivera
(1 row)
```

### `CROSS JOIN` — every possible pairing

```sql
SELECT count(*) AS cross_join_rows FROM customers CROSS JOIN products;
```
```
 cross_join_rows
-----------------
              30
```

5 customers × 6 products = 30 — every customer paired with every product, with no condition
at all. Rarely what you actually want against real tables of any size (it grows
multiplicatively — a million-row table crossed with another million-row table is a trillion
rows), but it's the honest, literal explanation of what a `JOIN` fundamentally is before an
`ON` condition narrows it down: every other join type is a `CROSS JOIN` with a filter applied.

## 5. Subqueries: a query inside a query

A subquery is a complete `SELECT` used as part of a larger query, wherever a single value,
a list of values, or a whole result set is expected. Four shapes cover almost every real use:

**A scalar subquery** — returns exactly one value, used anywhere a single value would go:

```sql
SELECT name, price FROM products
WHERE price > (SELECT AVG(price) FROM products);
```
```
     name      | price
---------------+--------
 Standing Desk | 350.00
(1 row)
```

**A subquery inside `IN`** — returns a list, used to filter against membership in that list:

```sql
SELECT name FROM customers
WHERE customer_id IN (SELECT customer_id FROM orders WHERE status = 'cancelled');
```
```
    name
------------
 Maya Ortiz
(1 row)
```

(See [`query-patterns.md`](query-patterns.md#not-in-vs-not-exists--the-null-trap) before
using the *negated* form, `NOT IN` — it has a real, silent-failure `NULL` trap that `IN`
itself doesn't.)

**A correlated subquery** — references a column from the *outer* query, so it effectively
re-runs once per outer row rather than once total:

```sql
SELECT c.name,
       (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.customer_id) AS order_count
FROM customers c
ORDER BY order_count DESC;
```
```
    name    | order_count
------------+-------------
 Ava Chen   |           2
 Liam Patel |           2
 Maya Ortiz |           2
 Noah Kim   |           1
 Zoe Baker  |           0
(5 rows)
```

Zoe Baker correctly shows `0`, not a missing row — because this subquery is a
`SELECT COUNT(*)`, an aggregate over zero matching rows, which returns `0`, not `NULL` (the
same principle behind [`query-patterns.md`](query-patterns.md#the-nth-highest-value)'s
`MAX()`-wrapping trick).

**A subquery in `FROM`** (a "derived table") — a subquery treated as if it were itself a
table, given an alias, then queried like any other table:

```sql
SELECT category, product_count FROM (
    SELECT category, COUNT(*) AS product_count FROM products GROUP BY category
) AS category_summary
WHERE product_count > 1;
```
```
  category   | product_count
-------------+---------------
 Furniture   |             2
 Electronics |             3
(2 rows)
```

This is doing something you *couldn't* do with a plain `HAVING` here — filtering on the
aggregated result as though it were an ordinary column, useful once the filtering logic gets
more complex than a single `HAVING` clause can express cleanly. A CTE (section 12) is
usually a more readable way to write the same thing once there's more than one layer of this.

## 6. Set operations: combining whole result sets

`UNION` stacks the results of two `SELECT`s with the same number/type of columns into one
result, removing duplicate rows; `UNION ALL` does the same but keeps duplicates (and is
cheaper — no deduplication pass required, worth defaulting to whenever you already know the
two sides can't overlap).

```sql
SELECT name FROM customers WHERE city = 'Austin'
UNION
SELECT name FROM customers WHERE customer_id IN (SELECT customer_id FROM orders WHERE status = 'pending');
```
```
    name
------------
 Liam Patel
 Ava Chen
 Maya Ortiz
(3 rows)
```

`INTERSECT` (rows appearing in *both* result sets) and `EXCEPT` (rows in the first set but
*not* the second — set subtraction) follow the identical shape; see
[`query-patterns.md`](query-patterns.md#exclusive-membership-bought-x-never-bought-y) for a
real, worked `EXCEPT` example.

## 7. `NULL`: the value that means "no value"

`NULL` isn't zero, isn't an empty string, and isn't "false" — it means *unknown/absent*, and
it behaves unlike every other value in SQL specifically because of that. The single most
important consequence, seen directly:

```sql
SELECT name, city FROM customers WHERE city != 'Austin';
```
```
    name    |  city
------------+---------
 Liam Patel | Seattle
 Zoe Baker  | Denver
(2 rows)
```

**Noah Kim — whose `city` is `NULL` — is silently missing**, even though "his city is not
Austin" is intuitively true. The reason: comparing `NULL` to anything, including with `!=`,
doesn't evaluate to `true` or `false` — it evaluates to `NULL` (unknown), and `WHERE` only
keeps rows where the condition is `true`. `unknown` isn't `true`, so the row is dropped, with
no error or warning. This is the exact same mechanism behind
[`query-patterns.md`](query-patterns.md#not-in-vs-not-exists--the-null-trap)'s much more
damaging `NOT IN` trap — it's worth internalizing here, on a single simple `!=`, before
meeting the more dangerous version.

The fix, when `NULL` should genuinely be included in a "not equal to" comparison:

```sql
SELECT name, city FROM customers WHERE city IS DISTINCT FROM 'Austin';
```
```
    name    |  city
------------+---------
 Liam Patel | Seattle
 Noah Kim   |
 Zoe Baker  | Denver
(3 rows)
```

`IS DISTINCT FROM` (and its counterpart `IS NOT DISTINCT FROM`) treats `NULL` as a real,
comparable value instead of collapsing to `unknown` — the only equality-style operator in
SQL that does. `IS NULL` / `IS NOT NULL` are the direct, simplest tools for "does this column
have a value at all":

```sql
SELECT name, city FROM customers WHERE city IS NULL;
```
```
   name   | city
----------+------
 Noah Kim |
(1 row)
```

And `COALESCE(value, fallback)` — returns the first non-`NULL` argument, the standard way to
substitute a display-friendly default:

```sql
SELECT name, COALESCE(city, 'Unknown') AS city FROM customers ORDER BY customer_id;
```
```
    name    |  city
------------+---------
 Ava Chen   | Austin
 Liam Patel | Seattle
 Maya Ortiz | Austin
 Noah Kim   | Unknown
 Zoe Baker  | Denver
(5 rows)
```

## 8. A practical function toolkit

**Strings** — `||` (or `CONCAT`) joins text; `UPPER`/`LOWER` change case; `LENGTH` counts
characters:

```sql
SELECT name || ' (' || city || ')' AS label FROM customers WHERE city IS NOT NULL ORDER BY name LIMIT 3;
```
```
        label
----------------------
 Ava Chen (Austin)
 Liam Patel (Seattle)
 Maya Ortiz (Austin)
```

**Dates** — `EXTRACT(field FROM date)` pulls out a component; arithmetic with `INTERVAL` is
native, no manual day-counting required:

```sql
SELECT order_date, EXTRACT(MONTH FROM order_date) AS order_month,
       order_date + INTERVAL '30 days' AS follow_up_date
FROM orders ORDER BY order_date LIMIT 3;
```
```
 order_date | order_month |   follow_up_date
------------+-------------+---------------------
 2024-06-01 |           6 | 2024-07-01 00:00:00
 2024-06-03 |           6 | 2024-07-03 00:00:00
 2024-06-15 |           6 | 2024-07-15 00:00:00
```

**Numbers** — `ROUND(value, decimals)`, and `::type` casts a value from one type to another:

```sql
SELECT ROUND(AVG(price), 2) AS avg_price FROM products;
```
```
 avg_price
-----------
     94.17
```

```sql
SELECT name, price, price::int AS price_rounded_int FROM products ORDER BY product_id LIMIT 3;
```
```
        name         | price  | price_rounded_int
---------------------+--------+-------------------
 Wireless Mouse      |  25.00 |                25
 Mechanical Keyboard |  85.00 |                85
 Standing Desk       | 350.00 |               350
```

One easy mistake worth showing directly rather than just warning about: mixing a bare column
with an aggregate function, with no `GROUP BY`, is a real error, not a quirky edge case:

```
$ SELECT ROUND(AVG(price), 2) AS avg_price, price::int AS price_as_int FROM products;
ERROR:  column "products.price" must appear in the GROUP BY clause or be used in an aggregate function
```

The reason is the same logic as section 3's `WHERE`/`HAVING` distinction: `AVG(price)`
collapses every row into one number, but a bare `price` in the same `SELECT` list is still
asking for one value *per row* — the database has no way to reconcile "one row" and "many
rows" in the same result, so it refuses rather than silently pick one arbitrary row's price.

## 9. Changing data: `INSERT`, `UPDATE`, `DELETE`, and `RETURNING`

```sql
INSERT INTO customers (customer_id, name, email, city, signup_date)
VALUES (6, 'Kai Sato', 'kai@example.com', 'Portland', '2024-08-01')
RETURNING customer_id, name;
```
```
 customer_id |   name
-------------+----------
           6 | Kai Sato
(1 row)
```

`RETURNING` hands back the row(s) actually affected, in the same statement — the standard
way to get a newly generated ID or confirm exactly what changed, without a second round-trip
`SELECT` immediately afterward.

```sql
UPDATE products SET price = price * 1.10 WHERE category = 'Electronics'
RETURNING name, price;
```
```
        name         | price
---------------------+-------
 Wireless Mouse      | 27.50
 Mechanical Keyboard | 93.50
 Webcam               | 66.00
```

```sql
DELETE FROM customers WHERE customer_id = 6 RETURNING name;
```
```
   name
----------
 Kai Sato
(1 row)
```

A constraint actively refusing bad data, seen directly (the `UNIQUE` constraint on
`customers.email` from section 1's schema):

```
$ INSERT INTO customers (customer_id, name, email, city, signup_date)
  VALUES (7, 'Dup Email', 'ava@example.com', 'Miami', '2024-08-01');
ERROR:  duplicate key value violates unique constraint "customers_email_key"
DETAIL:  Key (email)=(ava@example.com) already exists.
```

From here on, this tutorial assumes `seed.sql` has been re-run to reset the electronics
price bump above — do that now if following along.

## 10. Window functions: per-row calculations that can still see other rows

`GROUP BY` collapses rows — you lose the individual rows and keep only the aggregate. A
**window function** is the alternative for a real, common need: *keep every individual row,
but let each one see a calculation across a related set of rows* (its "window"). The syntax
signal is `OVER (...)`.

```sql
SELECT name, department, salary,
       RANK()       OVER (PARTITION BY department ORDER BY salary DESC) AS rank_in_dept,
       DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS dense_rank_in_dept,
       ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS row_num_in_dept
FROM employees
ORDER BY department, salary DESC;
```
```
    name    | department  |  salary   | rank_in_dept | dense_rank_in_dept | row_num_in_dept
------------+-------------+-----------+--------------+--------------------+-----------------
 Ella Fox   | Engineering | 171000.00 |            1 |                  1 |               1
 Sam Rivera | Engineering | 165000.00 |            2 |                  2 |               2
 Tom Walsh  | Engineering | 142000.00 |            3 |                  3 |               3
 Grace Lee  | Executive   | 220000.00 |            1 |                  1 |               1
 Priya Nair | Sales       | 158000.00 |            1 |                  1 |               1
 Ben Osei   | Sales       |  96000.00 |            2 |                  2 |               2
(6 rows)
```

Every row survives — unlike `GROUP BY department`, which would have collapsed each
department down to one row. `PARTITION BY` restarts the ranking for each department
independently, the window-function equivalent of `GROUP BY`'s grouping; `ORDER BY` inside
`OVER (...)` decides the ranking order within each partition. This dataset has no salary
ties, so `RANK`, `DENSE_RANK`, and `ROW_NUMBER` all agree here — they only diverge on ties
(`RANK` skips the next number after a tie, `DENSE_RANK` doesn't, `ROW_NUMBER` breaks ties
arbitrarily); see [`README.md`](README.md#window-functions) for the full explanation of when
each is the right one to reach for.

**A running total**, built on real order totals:

```sql
SELECT order_id, order_date, SUM(total) OVER (ORDER BY order_date) AS running_total
FROM (
    SELECT o.order_id, o.order_date, SUM(oi.quantity * oi.unit_price) AS total
    FROM orders o JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.status = 'completed'
    GROUP BY o.order_id, o.order_date
) o
ORDER BY order_date;
```
```
 order_id | order_date | running_total
----------+------------+---------------
     1001 | 2024-06-01 |         65.00
     1003 | 2024-06-03 |        495.00
     1002 | 2024-06-15 |        580.00
     1005 | 2024-06-20 |        690.00
     1007 | 2024-06-25 |        800.00
(5 rows)
```

This works because `ORDER BY` inside `OVER (...)`, with no explicit frame, defaults to
"everything from the start of the partition up through the current row" — which is exactly
what makes a `SUM()` into a *running* total instead of a grand total repeated on every row.
This default is easy to trip over the moment the data isn't perfectly clean — see
[`README.md`](README.md#window-functions) for the `ROWS` vs `RANGE` distinction this default
quietly depends on, which matters the moment there are gaps or duplicate rows per period.

**Looking at neighboring rows** — `LAG` looks backward, `LEAD` looks forward, both within the
ordered window:

```sql
SELECT name, salary,
       LAG(salary)  OVER (ORDER BY salary) AS next_lowest_salary,
       LEAD(salary) OVER (ORDER BY salary) AS next_highest_salary
FROM employees
ORDER BY salary;
```
```
    name    |  salary   | next_lowest_salary | next_highest_salary
------------+-----------+--------------------+---------------------
 Ben Osei   |  96000.00 |                    |           142000.00
 Tom Walsh  | 142000.00 |           96000.00 |           158000.00
 Priya Nair | 158000.00 |          142000.00 |           165000.00
 Sam Rivera | 165000.00 |          158000.00 |           171000.00
 Ella Fox   | 171000.00 |          165000.00 |           220000.00
 Grace Lee  | 220000.00 |          171000.00 |
(6 rows)
```

The first row has no "previous" and the last has no "next" — `LAG`/`LEAD` correctly return
`NULL` at the edges rather than erroring, which is exactly the property
[`query-patterns.md`](query-patterns.md#slowly-changing-dimensions-data-warehousing) relies
on to detect "this is the currently active record" using `LEAD` returning `NULL`.

## 11. CTEs: naming a subquery so a complex query reads top to bottom

A `WITH` clause (Common Table Expression) names a subquery so it can be referenced later in
the same statement — functionally similar to a derived table (section 5), but written before
the main query instead of nested inside it, and usable more than once. The real value is
readability once a query has more than one logical step:

```sql
WITH completed_orders AS (
    SELECT order_id, customer_id FROM orders WHERE status = 'completed'
),
order_totals AS (
    SELECT co.order_id, co.customer_id, SUM(oi.quantity * oi.unit_price) AS total
    FROM completed_orders co
    JOIN order_items oi ON co.order_id = oi.order_id
    GROUP BY co.order_id, co.customer_id
)
SELECT c.name, ot.order_id, ot.total
FROM order_totals ot
JOIN customers c ON c.customer_id = ot.customer_id
ORDER BY ot.total DESC;
```
```
    name    | order_id | total
------------+----------+--------
 Liam Patel |     1003 | 430.00
 Maya Ortiz |     1005 | 110.00
 Noah Kim   |     1007 | 110.00
 Ava Chen   |     1002 |  85.00
 Ava Chen   |     1001 |  65.00
(5 rows)
```

Each `WITH` block is a named, self-contained step — filter to completed orders, then compute
totals from that filtered set, then join to customer names — read in the same order you'd
explain the logic out loud, instead of nested nesting where the innermost, first-evaluated
piece is buried at the bottom of the query.

### Recursive CTEs: the one thing a plain `JOIN` genuinely can't do

A fixed number of `JOIN`s only works when you know in advance how many levels deep the data
goes. The `employees` table's manager hierarchy doesn't have a fixed depth — some chains are
2 levels, some are 3, and in general you don't know until you've walked the whole tree.
`WITH RECURSIVE` solves exactly this, and only this:

```sql
WITH RECURSIVE org_chart AS (
    -- Anchor: the root of the hierarchy (no manager)
    SELECT emp_id, name, manager_id, 1 AS depth, name::text AS chain
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    -- Recursive step: join the CTE back to itself to find the next level down
    SELECT e.emp_id, e.name, e.manager_id, oc.depth + 1, oc.chain || ' -> ' || e.name
    FROM employees e
    JOIN org_chart oc ON e.manager_id = oc.emp_id
)
SELECT depth, name, chain FROM org_chart ORDER BY depth, name;
```
```
 depth |    name    |                chain
-------+------------+--------------------------------------
     1 | Grace Lee  | Grace Lee
     2 | Priya Nair | Grace Lee -> Priya Nair
     2 | Sam Rivera | Grace Lee -> Sam Rivera
     3 | Ben Osei   | Grace Lee -> Priya Nair -> Ben Osei
     3 | Ella Fox   | Grace Lee -> Sam Rivera -> Ella Fox
     3 | Tom Walsh  | Grace Lee -> Sam Rivera -> Tom Walsh
(6 rows)
```

Walk through what actually happened, because it's worth being able to narrate this, not just
run it: the **anchor** (everything before `UNION ALL`) found the one row with no manager —
Grace Lee, depth 1. The **recursive member** (everything after `UNION ALL`) then joined
`employees` back against the CTE's *own results so far*, finding everyone whose manager was
already in the result — Priya Nair and Sam Rivera, both now depth 2. PostgreSQL repeats that
recursive step again, this time finding Priya's and Sam's reports (Ben Osei, Ella Fox, Tom
Walsh, depth 3), and again after that — finding nothing new, at which point it stops. The
`chain` column (carried forward and extended at each step) makes that iteration visible in
the output, one arrow added per level.

`README.md`'s [recursive CTE section](README.md#recursive-ctes) covers the one thing this
small, clean tree doesn't need but a real graph often does: **cycle prevention**, required
the moment relationships can point back on themselves (a bidirectional friend graph, for
example) rather than strictly downward like a management chain.

## 12. Indexes: why some queries are fast and others aren't

An index is a separate, ordered structure PostgreSQL maintains alongside a table
specifically so it can find matching rows without checking every single row — see
[`storage-internals.md`](storage-internals.md) for what an index physically is. What matters
at this level is what it actually changes in practice, seen directly with `EXPLAIN`:

```sql
EXPLAIN SELECT * FROM orders WHERE customer_id = 1;
```
```
                       QUERY PLAN
--------------------------------------------------------
 Seq Scan on orders  (cost=0.00..20.38 rows=4 width=70)
   Filter: (customer_id = 1)
```

`Seq Scan` means PostgreSQL is reading every row in the table and checking each one against
the filter. Adding an index:

```sql
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
```

...and re-running the identical query:

```
                      QUERY PLAN
-------------------------------------------------------
 Seq Scan on orders  (cost=0.00..1.09 rows=1 width=70)
   Filter: (customer_id = 1)
```

**It's still a `Seq Scan`, even with the index now available.** This is real output, not an
error, and it's the single most important lesson about indexes a beginner tutorial usually
skips: an index existing doesn't force PostgreSQL to use it. `orders` only has 7 rows here —
reading all 7 sequentially is already so cheap (cost `1.09`) that the planner correctly
decides an index lookup would cost *more*, not less. Forcing the comparison directly proves
it:

```sql
SET enable_seqscan = off;
EXPLAIN SELECT * FROM orders WHERE customer_id = 1;
```
```
                                      QUERY PLAN
--------------------------------------------------------------------------------------
 Index Scan using idx_orders_customer_id on orders  (cost=0.13..8.15 rows=1 width=70)
   Index Cond: (customer_id = 1)
```

`8.15` versus `1.09` — the index scan is genuinely *more expensive* on a table this small,
because using an index means one lookup into the index structure *plus* a separate trip to
fetch the actual row, while scanning 7 rows sequentially is close to free. This is exactly
the "low selectivity"/small-table reasoning from
[`README.md`](README.md#diagnosing-a-slow-query-explain-analyze-and-statistics) — indexes
pay off once a table is large enough, and specifically once a query is selective enough
(matching a small fraction of a large table), that skipping most of the table is a genuine
win rather than adding an extra hop for no benefit. Believing "an index always makes a query
faster" is a common, understandable, and wrong intuition — the query planner's job is
exactly to make this cost trade-off correctly, per query, based on real table size and
statistics, not to blindly prefer whichever index exists.

## 13. Transactions: grouping statements so they succeed or fail together

A transaction (`BEGIN` ... `COMMIT`) groups multiple statements into a single all-or-nothing
unit — either every statement in it takes effect, or (via `ROLLBACK`) none of them do, as if
none had ever run:

```sql
BEGIN;
UPDATE products SET price = price - 5 WHERE product_id = 101;
SELECT product_id, price FROM products WHERE product_id = 101;
```
```
 product_id | price
------------+-------
        101 | 20.00
(1 row)
```

Inside the open transaction, the price genuinely shows `20.00` — this connection has already
made the change. Then:

```sql
ROLLBACK;
SELECT product_id, price FROM products WHERE product_id = 101;
```
```
 product_id | price
------------+-------
        101 | 25.00
(1 row)
```

Back to `25.00`, exactly as if the `UPDATE` never happened. This matters the moment more than
one statement needs to succeed together as a single logical unit — the canonical example
being a funds transfer (debit one account, credit another): if the process crashes between
the two `UPDATE`s outside a transaction, the money has simply vanished from the system; inside
one, either both updates land or neither does. See
[`concurrency-and-locking.md`](concurrency-and-locking.md) for what happens when *multiple*
transactions run concurrently against the same data — isolation levels, locking, and
deadlocks are all questions that only exist once you go from "one transaction" to "many
transactions at once."

## Where to go from here

This file covered SQL as a language. The rest of this section covers PostgreSQL as an
*engine* — read them in this order as the natural next steps, each one meaningfully deeper
than the last:

1. [`README.md`](README.md) — how joins are physically executed, the query optimizer, and
   the indexing/window-function/CTE detail this tutorial only introduced.
2. [`concurrency-and-locking.md`](concurrency-and-locking.md) — what actually happens when
   many transactions touch the same data at once.
3. [`query-patterns.md`](query-patterns.md) — forty real query shapes (gaps-and-islands,
   fraud detection, sessionization, and more), each with the trap a first attempt usually
   falls into.
4. [`storage-internals.md`](storage-internals.md) — the physical model (pages, WAL,
   checkpoints) that explains *why* the rules in the other files are true.
5. [`production-and-scaling.md`](production-and-scaling.md) and
   [`backup-recovery-and-replication.md`](backup-recovery-and-replication.md) — running
   PostgreSQL for real, at scale, without losing data.
6. [`security-and-access-control.md`](security-and-access-control.md) — who's allowed to see
   and do what, and how PostgreSQL actually enforces it.

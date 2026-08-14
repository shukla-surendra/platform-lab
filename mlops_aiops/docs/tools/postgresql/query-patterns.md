# PostgreSQL: Query Pattern Library

Part of [`README.md`](README.md)'s PostgreSQL section — see its top note on sourcing. Each
entry below is a real, recurring query shape: the problem, why the obvious first attempt
usually fails, and the correct mechanism. Organized roughly by concept, not difficulty.

## Self-joins

### The manager's paycheck (self-joins)

A single `employees` table (`emp_id`, `name`, `salary`, `manager_id` referencing `emp_id`
on the same table) needs to find every employee earning more than their own manager. The
table has to be conceptually treated as two tables — one row-set standing in for
"employees," a second for "managers" — joined to each other:

```sql
SELECT e.name AS employee_name
FROM employees e
JOIN employees m ON e.manager_id = m.emp_id
WHERE e.salary > m.salary;
```

## Window functions: ranking, ties, and edge cases

### The Nth-highest value

Finding the second-highest distinct salary, returning `NULL` (not an empty result) if fewer
than two distinct salaries exist:

```sql
SELECT MAX(salary) AS second_highest_salary
FROM (
    SELECT DISTINCT salary FROM salaries ORDER BY salary DESC LIMIT 1 OFFSET 1
) AS subquery;
```

`ORDER BY salary DESC LIMIT 1 OFFSET 1` on its own returns an **empty result set**, not
`NULL`, when there's no second-highest row — wrapping it in `MAX()` converts "no rows" into
a genuine `NULL`, since an aggregate over zero rows returns `NULL` rather than nothing.
`DISTINCT` matters too: without it, two employees tied for the highest salary would make the
"second highest" query return the same value as the highest.

An equivalent, and often clearer, form uses `DENSE_RANK()` (not `RANK()` — `RANK()` would
skip rank 2 entirely if two employees tie for rank 1):

```sql
SELECT MAX(salary) AS second_highest_salary
FROM (
    SELECT salary, DENSE_RANK() OVER (ORDER BY salary DESC) AS rank
    FROM salaries
) ranked_salaries
WHERE rank = 2;
```

### Consecutive-day streaks

Finding users who logged in for 5+ consecutive days. `LAG()` alone can confirm whether
*yesterday* was consecutive, but can't group an entire streak of arbitrary length — the
mechanism is subtracting a sequential row number from a sequential date:

```sql
WITH unique_logins AS (
    SELECT DISTINCT user_id, login_date::date AS login_date FROM user_logins
),
numbered_logins AS (
    SELECT user_id, login_date,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS rn
    FROM unique_logins
),
streak_groups AS (
    SELECT user_id, login_date,
           (login_date - rn * INTERVAL '1 day') AS streak_anchor
    FROM numbered_logins
)
SELECT user_id, MIN(login_date) AS streak_start, MAX(login_date) AS streak_end,
       COUNT(*) AS streak_length
FROM streak_groups
GROUP BY user_id, streak_anchor
HAVING COUNT(*) >= 5;
```

For consecutive dates, `date - row_number` produces the exact same "anchor" value for every
row in the streak — subtracting a strictly-increasing integer from strictly-increasing dates
only stays constant while both increase in lockstep, i.e. exactly while the streak holds.
The moment a day is skipped, the anchor shifts, naturally starting a new group. This is the
same mechanism as gaps-and-islands, below — a streak is just an island where the group also
needs to be at least 5 long.

### Running totals — the missing `ORDER BY` trap

```sql
SELECT sales_rep_id, sales_month, revenue,
       SUM(revenue) OVER (PARTITION BY sales_rep_id ORDER BY sales_month) AS running_total
FROM monthly_sales;
```

Omitting `ORDER BY` inside `OVER (...)` here doesn't error — it silently returns the *grand
total* for that rep on every row, because without an `ORDER BY` the window frame defaults to
the entire partition rather than "everything up to and including the current row." See
[`README.md`](README.md#window-functions) for the underlying frame-default rule.

### First-touch / last-touch attribution — the `LAST_VALUE` frame trap

Returning each user's first and last marketing-channel touch in one row:

```sql
SELECT DISTINCT user_id,
    FIRST_VALUE(channel) OVER (PARTITION BY user_id ORDER BY visit_time) AS first_touch,
    LAST_VALUE(channel) OVER (
        PARTITION BY user_id ORDER BY visit_time
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS last_touch
FROM user_visits;
```

`LAST_VALUE(channel) OVER (PARTITION BY user_id ORDER BY visit_time)` **without** the
explicit frame almost always returns the wrong answer — usually just the current row's own
value. The reason is the same implicit default covered in `README.md`: an `ORDER BY` inside
`OVER (...)` limits the frame to end at the current row, so `LAST_VALUE` never actually sees
past it. Getting the true last value of the entire partition requires explicitly overriding
the frame with `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`.

### True rolling averages — `RANGE` vs `ROWS`, with real gaps

```sql
SELECT metric_date, value,
    AVG(value) OVER (
        ORDER BY metric_date
        RANGE BETWEEN INTERVAL '29 days' PRECEDING AND CURRENT ROW
    ) AS rolling_30d_avg
FROM daily_metrics;
```

See [`README.md`](README.md#window-functions) for the general rule — `ROWS BETWEEN 29
PRECEDING` counts physical rows, which is wrong the instant the data has gaps (a 29-*row*
window can span 45 calendar days if weekends are missing). `RANGE` with an `INTERVAL` looks
at actual calendar distance regardless of row density, correctly averaging only the rows
genuinely within the last 30 days — even if that's fewer than 30 rows.

### Ordered-set aggregates: exact median

```sql
SELECT city, PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sale_price) AS median_price
FROM home_sales
GROUP BY city;
```

`AVG()` is skewed by outliers; a manual median requires `ROW_NUMBER()`, a per-group row
count, and `CASE` logic to average the two middle rows on an even count. `PERCENTILE_CONT`
(continuous percentile) is a native ordered-set aggregate that handles the even/odd-count
math internally — `0.5` is the median, but any percentile (`0.95` for a p95 latency-style
metric) works the same way.

## Set operations and conditional aggregation

### Exclusive membership (bought X, never bought Y)

Finding customers who bought a 'Laptop' but never a 'Mouse'. Because each row in `orders`
represents a single product, a single-row filter like `WHERE product_name = 'Laptop' AND
product_name != 'Mouse'` is always true or always false per row — it can't express "look at
this customer's *entire* purchase history." The fix is either set subtraction or aggregation
across the full history:

```sql
-- Set-difference form
SELECT customer_id FROM orders WHERE product_name = 'Laptop'
EXCEPT
SELECT customer_id FROM orders WHERE product_name = 'Mouse';

-- Conditional-aggregation form
SELECT customer_id
FROM orders
GROUP BY customer_id
HAVING SUM(CASE WHEN product_name = 'Laptop' THEN 1 ELSE 0 END) > 0
   AND SUM(CASE WHEN product_name = 'Mouse'  THEN 1 ELSE 0 END) = 0;
```

### `NOT IN` vs `NOT EXISTS` — the `NULL` trap

Finding users who have never made a purchase:

```sql
-- Fails silently the moment purchases.user_id contains even one NULL
SELECT user_id FROM users
WHERE user_id NOT IN (SELECT user_id FROM purchases);

-- Correct — booleans, not three-valued comparisons
SELECT u.user_id FROM users u
WHERE NOT EXISTS (SELECT 1 FROM purchases p WHERE p.user_id = u.user_id);
```

SQL uses three-valued logic (`TRUE`/`FALSE`/`NULL`, i.e. "unknown"). `NOT IN (SELECT ...)`
expands to a chain of `id != 1 AND id != 2 AND id != NULL AND ...` — comparing anything to
`NULL` yields `NULL` (unknown), and an `AND` chain containing even one `NULL` collapses the
entire expression to `NULL`, silently returning **zero rows** regardless of how many users
genuinely never purchased. `NOT EXISTS` evaluates boolean existence directly and is
completely unaffected by `NULL`s on the other side. The same distinction is why a `LEFT JOIN
... WHERE right.key IS NULL` anti-join pattern also works correctly where `NOT IN` fails.

### `EXISTS()` vs `COUNT(*) > 0` — a real performance gap, not just a style choice

```sql
-- Forces Postgres to scan every matching row just to report "more than zero"
SELECT count(*) FROM invoices WHERE user_id = 999;

-- Stops at the first match
SELECT EXISTS (SELECT 1 FROM invoices WHERE user_id = 999) AS has_invoices;
```

If a check only needs a boolean presence answer (e.g. deciding whether to render a
"Download Invoice" button), `COUNT(*)` on a customer with 50,000 invoices does 50,000 rows
of work to answer "yes." `EXISTS` lets the planner stop scanning the instant it finds a
single matching row, turning an O(n) scan into effectively O(1).

### Pivoting rows into columns with `FILTER`

```sql
SELECT student_id,
    COUNT(*) FILTER (WHERE status = 'Present') AS total_present,
    COUNT(*) FILTER (WHERE status = 'Absent')  AS total_absent,
    COUNT(*) FILTER (WHERE status = 'Late')    AS total_late
FROM attendance
GROUP BY student_id;
```

Equivalent to `SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END)`, but the
PostgreSQL-native `FILTER (WHERE ...)` clause (9.4+) is more readable and is specifically
optimized by the planner rather than relying on the `CASE` expression being compiled down to
something equivalent.

### `ROLLUP` and `GROUPING SETS` — multi-level aggregation in one pass

Returning per-country revenue, per-region subtotals, and a grand total in a single query:

```sql
SELECT
    COALESCE(region, 'Grand Total') AS region,
    COALESCE(country, 'Region Total') AS country,
    SUM(revenue) AS total_revenue
FROM regional_sales
GROUP BY ROLLUP (region, country)
ORDER BY region, country;
```

The brute-force alternative — three separate `GROUP BY` queries glued together with `UNION
ALL` — scans the underlying table three times. `ROLLUP` (hierarchical subtotals: by region,
by region+country, and the grand total) and `GROUPING SETS` (an arbitrary, explicit list of
grouping combinations) compute every level of aggregation in a single pass. `COALESCE` is
needed because the subtotal/grand-total rows come back with genuine `NULL`s in the columns
that were rolled up — `COALESCE` relabels them for display.

## Time-based and hierarchical patterns

### Gaps and islands

Finding the distinct start/end dates of every continuous "active" period for a subscriber,
where activity can start, stop, and resume:

```sql
WITH numbered_days AS (
    SELECT user_id, active_date,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY active_date) AS rn
    FROM daily_active_status
),
island_groups AS (
    SELECT user_id, active_date,
           (active_date - rn * INTERVAL '1 day') AS island_id
    FROM numbered_days
)
SELECT user_id, MIN(active_date) AS period_start, MAX(active_date) AS period_end,
       COUNT(*) AS total_active_days
FROM island_groups
GROUP BY user_id, island_id
ORDER BY user_id, period_start;
```

`GROUP BY active_date` alone can't work — the data spans disconnected date ranges that
aren't a single group. The mechanism (identical to the streak-detection pattern above): for
a contiguous run of dates, `date − row_number` produces the same constant value throughout
the run, because both sides increase by exactly one in lockstep. The instant there's a gap,
the row number keeps incrementing by one but the date jumps by more than one day, so the
anchor value shifts — naturally partitioning the data into "islands" that can be grouped on.

### Recursive hierarchy traversal (org chart)

```sql
WITH RECURSIVE org_tree AS (
    SELECT emp_id, name, manager_id, 1 AS depth
    FROM employees WHERE manager_id IS NULL

    UNION ALL

    SELECT e.emp_id, e.name, e.manager_id, ot.depth + 1
    FROM employees e
    INNER JOIN org_tree ot ON e.manager_id = ot.emp_id
)
SELECT * FROM org_tree ORDER BY depth, emp_id;
```

See [`README.md`](README.md#recursive-ctes) for the anchor/`UNION ALL`/recursive-member
structure this depends on. Forgetting the anchor member (a starting query that does *not*
reference the CTE itself) is the most common way this breaks.

### Date-range overlap detection

Finding users who held two subscriptions active at the same time:

```sql
SELECT DISTINCT s1.user_id
FROM subscriptions s1
INNER JOIN subscriptions s2
    ON s1.user_id = s2.user_id AND s1.sub_id != s2.sub_id
WHERE s1.start_date <= s2.end_date AND s1.end_date >= s2.start_date;
```

Two real mistakes recur here. First, complex nested `BETWEEN` conditions ("start A is
between start B and end B, or end A is...") usually miss the case where one subscription's
range completely swallows the other's — the general, foolproof overlap test for two ranges
is simply `Start_A <= End_B AND End_A >= Start_B`. Second, forgetting `s1.sub_id !=
s2.sub_id` in the join condition makes every subscription match itself, registering as a
false overlap.

The PostgreSQL-native equivalent uses actual range types and the overlap operator (`&&`)
instead of hand-written boundary logic — and it correctly handles the "checkout on the same
day as another check-in" edge case via the range's inclusivity flags:

```sql
SELECT DISTINCT b1.room_id
FROM hotel_bookings b1
INNER JOIN hotel_bookings b2
    ON b1.room_id = b2.room_id AND b1.booking_id != b2.booking_id
WHERE daterange(b1.check_in, b1.check_out, '[)') && daterange(b2.check_in, b2.check_out, '[)');
```

`'[)'` tells Postgres the range is inclusive of the start date but exclusive of the end date
— exactly matching "checking out on day X and someone else checking in on day X is not a
real overlap."

### Filling missing dates (time-series gap-filling)

Computing total revenue for *every* day in a month, showing `0` for days with no
transactions rather than silently omitting them:

```sql
WITH calendar AS (
    SELECT generate_series('2024-01-01'::date, '2024-01-31'::date, INTERVAL '1 day')::date AS calendar_date
)
SELECT c.calendar_date, COALESCE(SUM(dr.amount), 0) AS total_revenue
FROM calendar c
LEFT JOIN daily_revenue dr ON c.calendar_date = dr.transaction_date
GROUP BY c.calendar_date
ORDER BY c.calendar_date;
```

Grouping directly by `transaction_date` makes days with zero activity vanish from the
result entirely, which breaks any downstream chart or report expecting one row per day.
`generate_series()` produces the full expected calendar independent of what data exists,
then a `LEFT JOIN` back to the real data preserves every calendar day. `COALESCE(SUM(...), 0)`
is required too — without it, days with no matching rows report `NULL`, not `0`.

### Downsampling high-frequency data (`date_bin`)

Rolling up clickstream data into fixed 15-minute buckets:

```sql
SELECT date_bin('15 minutes', click_time, '2024-01-01 00:00:00'::timestamp) AS interval_start,
       COUNT(*) AS total_clicks
FROM clickstream
GROUP BY interval_start
ORDER BY interval_start;
```

`date_bin` (PostgreSQL 14+) replaces the older, more error-prone pattern of extracting
minutes and dividing (`EXTRACT(MINUTE FROM click_time) / 15`) and manually reconstructing a
bucketed timestamp — it forces arbitrary timestamps into uniform buckets natively.

### Bill-of-materials recursive cost rollup

Calculating the total build cost of a product made of sub-assemblies, made of
sub-components, each with its own base cost and required quantity:

```sql
WITH RECURSIVE build_tree AS (
    SELECT a.parent_part_id, a.child_part_id, a.quantity_required AS total_qty
    FROM assemblies a
    WHERE a.parent_part_id = 100

    UNION ALL

    SELECT a.parent_part_id, a.child_part_id, bt.total_qty * a.quantity_required AS total_qty
    FROM assemblies a
    INNER JOIN build_tree bt ON a.parent_part_id = bt.child_part_id
)
SELECT SUM(bt.total_qty * c.base_cost) AS total_build_cost
FROM build_tree bt
INNER JOIN components c ON bt.child_part_id = c.part_id;
```

The recursive member's job is strictly to compute the total *quantity* of every leaf
component required, by multiplying the running quantity down each level of the tree —
joining to the `components` cost table happens once, at the very end, after the tree is
fully expanded. Trying to join in the cost table *inside* the recursive member (to keep a
running cost total instead of a running quantity) is the common mistake — it multiplies
join complexity and tends to duplicate rows.

### Graph traversal with cycle detection

Finding everyone within 3 degrees of separation of a given user in a bidirectional social
graph, without looping forever:

```sql
WITH RECURSIVE network AS (
    SELECT friend_id, 1 AS depth, ARRAY[user_id, friend_id] AS path_visited
    FROM connections WHERE user_id = 1

    UNION ALL

    SELECT c.friend_id, n.depth + 1, n.path_visited || c.friend_id
    FROM connections c
    INNER JOIN network n ON c.user_id = n.friend_id
    WHERE n.depth < 3
      AND c.friend_id != ALL(n.path_visited)   -- cycle breaker
)
SELECT DISTINCT friend_id FROM network;
```

A bidirectional graph (user 1 connects to user 2, user 2 connects back to user 1) causes
infinite recursion in a naive recursive CTE. Building a `path_visited` array as the
recursion walks the graph, and filtering with `!= ALL(path_visited)` on every recursive
step, forces the traversal to skip any node it's already seen — the same mechanism used for
degrees-of-separation / shortest-path queries generally.

### Chaining CTEs: sessionization

Grouping a raw stream of page-view events into "sessions," where a new session starts only
after a 30+ minute gap:

```sql
WITH time_diffs AS (
    SELECT user_id, view_timestamp,
           LAG(view_timestamp) OVER (PARTITION BY user_id ORDER BY view_timestamp) AS prev_timestamp
    FROM page_views
),
session_flags AS (
    SELECT user_id, view_timestamp,
        CASE
            WHEN prev_timestamp IS NULL THEN 1
            WHEN EXTRACT(EPOCH FROM (view_timestamp - prev_timestamp)) / 60 > 30 THEN 1
            ELSE 0
        END AS is_new_session
    FROM time_diffs
),
session_identifiers AS (
    SELECT user_id, view_timestamp,
           SUM(is_new_session) OVER (PARTITION BY user_id ORDER BY view_timestamp) AS session_id
    FROM session_flags
)
SELECT user_id, session_id, MIN(view_timestamp) AS session_start,
       MAX(view_timestamp) AS session_end, COUNT(*) AS pages_viewed
FROM session_identifiers
GROUP BY user_id, session_id
ORDER BY user_id, session_start;
```

No single window function solves this in one pass — the mechanism is chaining three CTEs
like pipeline stages: (1) compute the time delta since the previous event, (2) turn that
delta into a boolean "new session started here" flag, (3) take a **cumulative sum** of that
flag. Because the running sum only increases at a session boundary, every row within the
same session ends up with the identical integer — a ready-made `session_id` to `GROUP BY`.

### Strict, chronologically-ordered funnel analysis

Counting how many users signed up, then (strictly afterward) added an item to cart, then
(strictly afterward) purchased:

```sql
WITH step_1 AS (
    SELECT user_id, MIN(event_time) AS signup_time
    FROM user_events WHERE event_name = 'signup' GROUP BY user_id
),
step_2 AS (
    SELECT u.user_id, MIN(e.event_time) AS cart_time
    FROM step_1 u
    INNER JOIN user_events e ON u.user_id = e.user_id
    WHERE e.event_name = 'add_to_cart' AND e.event_time > u.signup_time
    GROUP BY u.user_id
),
step_3 AS (
    SELECT u.user_id, MIN(e.event_time) AS purchase_time
    FROM step_2 u
    INNER JOIN user_events e ON u.user_id = e.user_id
    WHERE e.event_name = 'purchase' AND e.event_time > u.cart_time
    GROUP BY u.user_id
)
SELECT (SELECT COUNT(*) FROM step_1) AS total_signups,
       (SELECT COUNT(*) FROM step_2) AS total_carts,
       (SELECT COUNT(*) FROM step_3) AS total_purchases;
```

Plain conditional aggregation (`COUNT(CASE WHEN event_name = 'purchase' THEN 1 END)`) without
checking timestamps will miscount: a user who buys as a guest and *then* signs up later would
be falsely counted as having passed through the funnel in order. Chaining each step as its
own CTE, requiring each subsequent step's timestamp to be strictly greater than the previous
step's, enforces genuine chronological order.

## Fraud/anomaly detection with `LAG`

Finding cards used twice at the same merchant within 10 minutes:

```sql
WITH lagged_transactions AS (
    SELECT card_id, merchant_id, tx_timestamp,
        LAG(tx_timestamp) OVER (
            PARTITION BY card_id, merchant_id ORDER BY tx_timestamp
        ) AS previous_tx_time
    FROM transactions
)
SELECT DISTINCT card_id
FROM lagged_transactions
WHERE tx_timestamp - previous_tx_time <= INTERVAL '10 minutes';
```

Two mechanisms combine here: window functions can't be referenced directly in a `WHERE`
clause, so `LAG()` has to be computed in a CTE (or subquery) first, then filtered in the
outer query; and subtracting one `TIMESTAMP` from another in Postgres yields an `INTERVAL`
directly, so comparing against `INTERVAL '10 minutes'` is natural and readable rather than
requiring manual unit conversion.

## `LATERAL` joins

### Top-N-per-group (`LATERAL` joins)

Returning, for every customer, only their 3 most recent orders — full row details, not just
an aggregate:

```sql
SELECT c.name, recent_orders.order_id, recent_orders.order_date, recent_orders.total
FROM customers c
CROSS JOIN LATERAL (
    SELECT o.order_id, o.order_date, o.total
    FROM orders o
    WHERE o.customer_id = c.customer_id
    ORDER BY o.order_date DESC
    LIMIT 3
) recent_orders;
```

A standard `JOIN`'s right-hand subquery is evaluated independently of the left table;
`LATERAL` lets the subquery reference columns from the left-hand row, effectively acting as
a per-row `FOR EACH` loop. A `ROW_NUMBER() OVER (PARTITION BY customer_id ...)` CTE
alternative forces Postgres to scan and sort the *entire* `orders` table before filtering
down to the top 3 per customer; `LATERAL`, backed by an index on `(customer_id, order_date)`,
does an index lookup per customer and stops after 3 rows — for large tables, often
dramatically faster than the window-function equivalent.

## Deduplication

### Deleting duplicate rows, keeping the oldest

```sql
DELETE FROM mailing_list
WHERE id IN (
    SELECT id FROM (
        SELECT id, ROW_NUMBER() OVER (PARTITION BY email ORDER BY created_at ASC) AS row_num
        FROM mailing_list
    ) ranked_emails
    WHERE row_num > 1
);
```

An equivalent form using Postgres's internal row identifier:

```sql
DELETE FROM mailing_list
WHERE id NOT IN (
    SELECT DISTINCT ON (email) id FROM mailing_list ORDER BY email, created_at ASC
);
```

The real risk here is deleting *everything* — a naive self-join delete without a strict,
deterministic tie-breaker (the primary key, or a `ROW_NUMBER()`) can wipe out the row meant
to be kept along with the actual duplicates. `ROW_NUMBER()` guarantees exactly one row per
`email` gets `row_num = 1` (the keeper), with every other row flagged for deletion.

## Arrays and JSONB

### Array containment for multi-item filters

Finding orders that contain *both* product 101 and 102:

```sql
SELECT order_id
FROM order_items
GROUP BY order_id
HAVING ARRAY_AGG(product_id) @> ARRAY[101, 102];
```

Equivalent to the more standard `WHERE product_id IN (101, 102) GROUP BY order_id HAVING
COUNT(DISTINCT product_id) = 2`, but `ARRAY_AGG` combined with the containment operator
(`@>`) reads more directly and extends cleanly if the required-item list grows (contains
101, 102, 105, *and* 109 — no change in structure needed).

### JSONB containment and key/element checks

Finding users with 'SQL' anywhere in a JSONB `skills` array (`attributes` column, e.g.
`{"role": "engineer", "skills": ["Python", "SQL", "Go"]}`):

```sql
-- The "contains" operator — the fast, native way
SELECT user_id, name FROM users WHERE attributes @> '{"skills": ["SQL"]}';

-- The "has element" operator on an extracted array
SELECT user_id, name FROM users WHERE attributes->'skills' ? 'SQL';
```

Treating a JSONB column as a plain string (`WHERE attributes::TEXT LIKE '%"SQL"%'`) is slow,
breaks the moment key ordering or whitespace in the stored JSON changes, and — critically —
can never use a GIN index. `@>` (contains) and `?` (has key/element) are the native operators
GIN indexing is actually built around.

### Deep, atomic JSONB mutation

Toggling one nested key inside a JSONB column (`preferences = {"theme": "dark",
"notifications": {"email": true, "sms": false}}`) without a read-modify-write race:

```sql
UPDATE users
SET preferences = jsonb_set(
    preferences,
    '{notifications, sms}',   -- path to the key, as a text array
    'true'::jsonb
)
WHERE id = 123;
```

Pulling the whole JSON document into application code, changing one field in memory, and
writing the entire document back creates a real race condition: if another transaction
changes a *different* key (e.g. `theme`) in the same window, that update gets silently
overwritten by the first transaction's stale copy of the whole document. `jsonb_set` mutates
only the specific leaf path, atomically, inside the database — two concurrent updates to
different keys both succeed cleanly.

### Flattening JSONB arrays into rows (ETL)

Extracting every individual item ID out of a JSON array field, one row per item (a common
first step when ingesting event payloads from a queue):

```sql
SELECT log_id,
       (jsonb_array_elements(request_payload->'purchased_items')->>'id')::int AS item_id
FROM api_logs
WHERE request_payload ? 'purchased_items';
```

`jsonb_array_elements()` is a set-returning function — it behaves like an implicit join,
expanding one row's array into multiple output rows. Extracting a Kafka-style event's
`actions` array of plain strings uses the `_text` variant instead
(`jsonb_array_elements_text`), which matters because the non-`_text` form returns each
element still wrapped in JSON double quotes (`"login"` instead of `login`), silently
corrupting anything downstream that expects a plain string.

### Dynamic pivoting with `JSONB_OBJECT_AGG`

Turning an entity-attribute-value table (`user_properties(user_id, property_key,
property_value)`) into one JSON object per user:

```sql
SELECT user_id, JSONB_OBJECT_AGG(property_key, property_value) AS user_settings
FROM user_properties
GROUP BY user_id;
```

A hand-written `CASE WHEN property_key = 'theme' THEN ...` pivot breaks the moment a new
property is introduced. `JSONB_OBJECT_AGG` dynamically pivots arbitrary key/value rows into
a single JSON object per group in one pass, with no schema change required as new keys
appear.

## Upserts and synchronization

### `INSERT ... ON CONFLICT` (upsert) — avoiding a check-then-act race

Incrementing a login counter, inserting a new row only if the user doesn't already exist:

```sql
INSERT INTO user_profiles (user_id, username)
VALUES (42, 'sql_wizard')
ON CONFLICT (user_id)
DO UPDATE SET login_count = user_profiles.login_count + 1;
```

A hand-rolled "`SELECT` to check existence, then `INSERT` or `UPDATE`" has a genuine race
condition under concurrent load: between the check and the write, another process may have
already inserted the row, causing a unique-constraint crash. `ON CONFLICT` pushes the
existence check down into the database's own unique index, making the whole operation
atomic.

### `MERGE` (PostgreSQL 15+) — conditional insert/update/delete in one statement

Syncing a `target_inventory` table against a `source_updates` delta feed, where each source
row specifies its own operation:

```sql
MERGE INTO target_inventory t
USING source_updates s
    ON t.item_id = s.item_id
WHEN MATCHED AND s.operation = 'DELETE' THEN
    DELETE
WHEN MATCHED AND s.operation = 'UPDATE' THEN
    UPDATE SET quantity = t.quantity + s.qty_change
WHEN NOT MATCHED AND s.operation = 'INSERT' THEN
    INSERT (item_id, quantity) VALUES (s.item_id, s.qty_change);
```

`INSERT ... ON CONFLICT` cannot express a conditional `DELETE` — before `MERGE`, that
required a PL/pgSQL function or multiple separate statements inside a transaction. `MERGE`
evaluates its `WHEN` clauses sequentially against a single scan/join of the source and
target, and can insert, update, *and* delete in one atomic statement.

Also useful with `RETURNING` inside a CTE for atomic archival — moving rows out of a hot
table while guaranteeing nothing is lost:

```sql
WITH deleted_users AS (
    DELETE FROM active_users
    WHERE last_login < CURRENT_DATE - INTERVAL '1 year'
    RETURNING user_id
)
INSERT INTO archived_users (user_id, archived_date)
SELECT user_id, CURRENT_DATE FROM deleted_users;
```

PostgreSQL allows `INSERT`/`UPDATE`/`DELETE` statements *inside* a CTE — the `DELETE ...
RETURNING` acts like a `SELECT`, piping the deleted rows' IDs directly into the following
`INSERT`, in a single query block with no separate `BEGIN`/`COMMIT` needed for atomicity.

## Lock-free queue consumption (`FOR UPDATE SKIP LOCKED`)

Handing out the next 5 available tickets to a buyer, safely under massive concurrent
traffic, without forcing buyers to queue behind each other:

```sql
SELECT ticket_id
FROM event_tickets
WHERE event_id = 101 AND status = 'available'
ORDER BY ticket_id
LIMIT 5
FOR UPDATE SKIP LOCKED;
```

Plain `SELECT ... LIMIT 5` followed by an `UPDATE` lets two concurrent buyers read the same 5
rows and race to claim them. Adding `FOR UPDATE` alone fixes the race but forces every other
concurrent buyer to wait for the first one's transaction to finish. `SKIP LOCKED` instead
tells Postgres: give me 5 available rows, but if another transaction currently has row X
locked, just skip it and move to the next one — enabling genuinely parallel, lock-free
throughput. See [`concurrency-and-locking.md`](concurrency-and-locking.md#table-level-vs-row-level-locks)
for how this fits alongside `FOR UPDATE`/`FOR SHARE` generally.

## Full-text and spatial search

### Native full-text search (`tsvector`/`tsquery`)

Finding support tickets whose description mentions "database" and "crash," regardless of
spacing, capitalization, or verb tense:

```sql
ALTER TABLE documents
ADD COLUMN search_vector tsvector
GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || body)) STORED;

CREATE INDEX documents_search_idx ON documents USING GIN (search_vector);

SELECT title,
    ts_rank(search_vector, websearch_to_tsquery('english', 'running shoes')) AS relevance_score,
    ts_headline('english', body, websearch_to_tsquery('english', 'running shoes')) AS snippet
FROM documents
WHERE search_vector @@ websearch_to_tsquery('english', 'running shoes')
ORDER BY relevance_score DESC
LIMIT 10;
```

`description ILIKE '%database%' AND description ILIKE '%crash%'` forces a sequential scan
(bypassing any index) and fails outright on plurals or tense ("crashed" won't match a search
for "crash"). `tsvector` parses text into lexemes (root words, stop words removed);
`tsquery` parses search input the same way, so `@@` matches on meaning rather than exact
substrings, and the whole comparison can use a GIN index. `websearch_to_tsquery` additionally
understands search-engine-style input directly (`"running shoes" -Nike` means: match the
exact phrase "running shoes," excluding documents containing "Nike").

### Spatial queries (PostGIS)

Finding restaurants within a 5km radius of a GPS point, closest first:

```sql
CREATE EXTENSION postgis;
CREATE TABLE restaurants (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255),
    location GEOGRAPHY(Point, 4326)
);
CREATE INDEX restaurants_location_gix ON restaurants USING GIST (location);

SELECT name,
    ST_Distance(location, ST_MakePoint(-73.985, 40.748)::geography) AS distance_meters
FROM restaurants
WHERE ST_DWithin(location, ST_MakePoint(-73.985, 40.748)::geography, 5000)
ORDER BY distance_meters ASC
LIMIT 10;
```

Coordinates are 2D data, which a standard B-Tree (built for 1D, sortable data) can't index
usefully. Filtering with `WHERE ST_Distance(...) < 5000` calculates the exact trigonometric
distance to *every* row before filtering — bypassing the spatial index entirely and scanning
the whole table. `ST_DWithin` is written specifically to use a GiST spatial index: it draws a
cheap bounding box around the search radius first, discarding the vast majority of rows via
fast integer comparisons, and only runs the expensive trigonometric distance calculation on
the small number of rows that fall inside the box.

### Finding which polygon contains a point (geofencing)

```sql
SELECT z.zone_name
FROM delivery_zones z
INNER JOIN couriers c ON ST_Contains(z.geom, c.location)
WHERE c.courier_id = 42;
```

Hand-written latitude/longitude bounding-box math (`lat BETWEEN x AND y`) only works for
perfect rectangles — real delivery zones and geofences are irregular polygons. `ST_Contains`
mathematically evaluates whether a point geometry falls inside a polygon geometry of
arbitrary complexity.

## Slowly changing dimensions (data warehousing)

Transforming an append-only log of raw salary updates into a proper Slowly Changing
Dimension (Type 2) table — each row valid for a specific date range, with the current row's
`valid_to` left open-ended:

```sql
SELECT emp_id, salary,
       update_timestamp AS valid_from,
       LEAD(update_timestamp) OVER (PARTITION BY emp_id ORDER BY update_timestamp) AS valid_to
FROM raw_salary_updates;
```

`LEAD()` looks at the next chronological row for the same employee and pulls its timestamp
back as the current row's expiration date — Postgres's `LEAD()` naturally returns `NULL` on
the last row for each employee, which is exactly the "still currently active" signal a Type
2 dimension needs, with no self-join required.

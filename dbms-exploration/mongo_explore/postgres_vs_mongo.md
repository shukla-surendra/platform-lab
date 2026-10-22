# Postgres vs MongoDB — and when to use which

Locks details for Postgres: [../pg_locks/](../pg_locks/README.md).

## Side by side

| | PostgreSQL | MongoDB |
|---|---|---|
| Data unit | row in a table (fixed columns) | document (nested JSON/BSON, any shape) |
| Schema | enforced by the DB (`ALTER TABLE` to change) | flexible; optional `$jsonSchema` validation |
| Design starts from | the data (normalize, 3NF) | the queries (access patterns) |
| Relationships | foreign keys + JOINs (fast, planner picks the strategy) | embed, or reference + `$lookup` (limited, slower at scale) |
| Atomic unit | any transaction, any number of rows | 1 document always; multi-doc transactions since 4.0 (replica set needed, slower, 60 s default limit) |
| Concurrency | MVCC; row locks; writers **wait** for each other | MVCC (WiredTiger); doc-level; conflicting transactions **fail fast** with `WriteConflict` → retry (09) |
| Isolation | Read Committed default; up to Serializable | snapshot inside transactions; no Serializable |
| Query language | SQL (standard, very expressive: window functions, CTEs, ...) | MQL + aggregation pipeline |
| Integrity | FKs, CHECK, UNIQUE, exclusion constraints | unique indexes, `$jsonSchema`; **no foreign keys** |
| Scale-out writes | single primary; sharding via Citus / partitioning by hand | built-in sharding (shard key) |
| High availability | streaming replication + external failover (Patroni, cloud) | built-in replica set with automatic election |
| JSON | `jsonb` + GIN index: very good | native, everything is JSON |
| Max record | 1 GB per field, rows effectively unlimited via TOAST | **16 MB per document** |
| Analytics | strong (SQL, window functions, parallel query) | aggregation pipeline is OK; not a warehouse |

## When to use what — decision matrix

Score your project; the column with more ✅ usually wins.

| If your project has… | Postgres | Mongo |
|---|:-:|:-:|
| Money, inventory, bookings: correctness across many records | ✅ | |
| Many relationships, ad-hoc reporting, "join anything with anything" | ✅ | |
| Queries you don't know yet (analysts, BI tools) | ✅ | |
| Strong constraints (FKs, uniqueness across tables) | ✅ | |
| Data naturally shaped like a document (catalog item, CMS page, user profile, game state) | | ✅ |
| Shape changes often / differs per record (product attributes per category) | ➖ (jsonb works) | ✅ |
| Known, stable access patterns, mostly "get by key / list by owner" | ➖ | ✅ |
| Huge write volume needing horizontal sharding from day 1 | ➖ (Citus) | ✅ |
| Event/IoT/log ingestion with TTL expiry | ➖ (partitions) | ✅ (TTL, time-series collections) |
| Team knows SQL, small team, one DB for everything | ✅ | |

Default advice: **start with Postgres** (with `jsonb` for flexible parts) unless the data is
clearly document-shaped with known access patterns, or you need built-in sharding. Many real
systems use both: Postgres for orders/payments, Mongo for catalog/content/activity feeds.

## Same task, both databases

| Task | Postgres | Mongo |
|---|---|---|
| user's last 20 orders | `SELECT * FROM orders WHERE user_id=42 ORDER BY created_at DESC LIMIT 20` + index `(user_id, created_at DESC)` | `find({userId:42}).sort({createdAt:-1}).limit(20)` + index `{userId:1, createdAt:-1}` |
| order with items | JOIN `orders` + `order_items` | one document, items embedded |
| safe stock decrement | `UPDATE ... SET stock = stock-1 WHERE id=3 AND stock>0` | `updateOne({_id:3, stock:{$gt:0}}, {$inc:{stock:-1}})` |
| revenue by city | `GROUP BY city` | `$group: {_id: "$city"}` |
| add a field | `ALTER TABLE ADD COLUMN` (lock, lesson pg_locks/06) | just start writing it; old docs simply lack it |
| transfer between 2 accounts | normal transaction | multi-doc transaction + retry on `TransientTransactionError` |

## Fast/slow in each

| | Postgres | Mongo |
|---|---|---|
| Fast | joins with good indexes, aggregates, complex filters, constraints | single-document read/write by key, embedded reads, horizontal writes |
| Slow / painful | huge single-table write rates on one node, frequent schema changes on huge tables | `$lookup`-heavy queries, multi-doc transactions, unbounded documents, queries the schema wasn't designed for |

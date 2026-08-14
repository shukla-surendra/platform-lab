# PostgreSQL: Concurrency, Transactions, and Locking

Part of [`README.md`](README.md)'s PostgreSQL section — see its top note on how this content
is sourced. This file covers what happens when many transactions touch the same data at
once: MVCC (the mechanism underneath almost everything else here), isolation levels and the
anomalies they prevent, table- and row-level locking, deadlocks, and the maintenance burden
(`VACUUM`, bloat, transaction ID wraparound) MVCC creates as a consequence. For the physical
storage detail underneath MVCC — what a row version actually looks like on disk, and why
`VACUUM`/index-only scans can skip whole pages cheaply — see
[`storage-internals.md`](storage-internals.md).

## MVCC: PostgreSQL never updates a row in place

Multi-Version Concurrency Control is the single idea that explains most of PostgreSQL's
locking behavior, its `UPDATE` cost, and its need for `VACUUM`.

When a transaction runs `UPDATE`, Postgres does **not** modify the existing row on disk:

1. It writes an entirely new, complete version of the row.
2. It marks the old version's `xmax` (a hidden system column — the transaction ID that
   deleted/updated it) rather than deleting it immediately.
3. Any transaction that started *before* the `UPDATE` committed keeps reading the old version
   — this is what gives readers a consistent snapshot without blocking writers.
4. Once no running transaction could still need the old version, `VACUUM` (background
   autovacuum, or a manual `VACUUM`) removes it and reclaims the space.

A direct consequence: **`UPDATE` is physically closer to `DELETE` + `INSERT` than to an
in-place write.** Every column index pointing at the row would normally need updating to
point at the new physical location — except for **HOT (Heap-Only Tuple) updates**: if the
updated column isn't part of any index, and there's free space on the same disk page
(controlled by a table's `fillfactor`), Postgres writes the new version on the same page and
leaves every index untouched. Frequently-updated, non-indexed columns (a `view_count`, a
`last_modified` timestamp) are exactly where HOT updates matter — updating an indexed column
constantly defeats HOT and multiplies write amplification.

### `VACUUM`, bloat, and autovacuum tuning

Because dead row versions aren't removed synchronously, a table under heavy `UPDATE` traffic
accumulates **bloat** — dead tuples piling up faster than the background `autovacuum`
process reclaims them. A table that logically holds 10,000 live rows but gets updated 50
times a second can grow to tens of gigabytes of mostly-dead data; simple `SELECT` queries
start timing out because Postgres has to scan past millions of dead rows to find the live
ones.

- **Immediate fix**: `VACUUM FULL table_name` physically rebuilds the table and reclaims the
  disk space — but it takes an `ACCESS EXCLUSIVE` lock for the duration, blocking all reads
  and writes on that table. Not something to run against a live table without a maintenance
  window.
- **Root-cause fix**: tune autovacuum to run more aggressively on hot tables. The default
  trigger (`autovacuum_vacuum_scale_factor = 0.2`, i.e. wait until 20% of a table has
  changed) is sized for small databases — on a billion-row table, that's 200 million changed
  rows before autovacuum even starts, by which point the vacuum itself becomes a slow,
  disruptive operation. Lowering the scale factor (e.g. to `0.01`) or setting a flat
  `autovacuum_vacuum_threshold` (e.g. trigger after 100,000 updates) makes autovacuum run
  often, in small, cheap increments, instead of rarely in one enormous one:

  ```sql
  ALTER TABLE user_balances SET (
      autovacuum_vacuum_scale_factor = 0.0,
      autovacuum_vacuum_threshold = 500
  );
  ```

- If a table is genuinely deletion-heavy at scale (e.g. dropping months of old data), range
  **partitioning** turns an O(n) `DELETE` (which locks rows and generates dead tuples for
  `VACUUM` to clean up) into an O(1) `DROP TABLE partition_name` — see
  [`production-and-scaling.md`](production-and-scaling.md) for the full pattern, including
  the "soft delete" (`is_deleted = true`) anti-pattern this replaces.

### Transaction ID wraparound

Every row's `xmin`/`xmax` hidden columns are 32-bit transaction IDs (XIDs) — a hard ceiling
of roughly 2.1 billion. If a database processes that many transactions without action, the
counter wraps back to zero, and a brand-new transaction's ID can appear to be numerically
*older* than genuinely old data — making that data look like it happened in the future and
therefore instantly invisible. PostgreSQL prevents this with **freezing**: as part of
routine vacuuming, rows older than a threshold get their `xmin` rewritten to a special
`FrozenXID`, which is always treated as older than every real transaction ID, permanently.
The operationally relevant metric is `age(datfrozenxid)` — if it approaches 2 billion,
PostgreSQL will refuse all writes and shut itself down rather than risk data corruption.
`autovacuum_freeze_max_age` controls how aggressively old data gets frozen before that limit
is reached; it needs monitoring on any long-lived, high-write production database.

## Transactions and isolation levels

A transaction (`BEGIN` ... `COMMIT`/`ROLLBACK`) is a single logical unit of work. Within one,
`SAVEPOINT` acts as an internal checkpoint — useful for a large batch script where a failure
partway through shouldn't discard everything already done:

```sql
BEGIN;
UPDATE users SET status = 'ACTIVE' WHERE id = 1;
SAVEPOINT user_1_done;

UPDATE users SET status = 'ACTIVE' WHERE id = 2;  -- suppose this fails
ROLLBACK TO SAVEPOINT user_1_done;                -- reverts only user 2's change

COMMIT;  -- commits the successful part
```

### The four classic anomalies

| Anomaly | What happens |
|---|---|
| Dirty read | Transaction A reads data Transaction B wrote but hasn't committed yet — if B rolls back, A read data that never really existed |
| Non-repeatable read | Transaction A reads a row; Transaction B updates and commits it; A re-reads the same row and gets a different value |
| Phantom read | Transaction A runs a query; Transaction B inserts a new row matching A's filter and commits; A re-runs the exact same query and a new row appears |
| Serialization anomaly / write skew | A set of transactions each individually respects a business rule, but running them concurrently violates a rule that spans multiple rows |

**Write skew**, worked concretely: a hospital scheduling system requires at least one doctor
on call at all times. Two doctors are both currently on call. At the same instant, both
request to go off call. Each transaction independently checks `SELECT count(*) FROM
schedule WHERE on_call = true` (returns 2, so "safe to go off call"), then updates its own
row to `false`. Both commit successfully — now zero doctors are on call, violating the rule,
even though neither transaction touched the other's row and standard row-level locking
(`SELECT ... FOR UPDATE`) wouldn't have caught it, since the two transactions never lock the
same row. This is exactly the anomaly `SERIALIZABLE` isolation is designed to catch (below);
the alternative fix is forcing the check itself through a single shared row (a single-row
`on_call_status` table, locked with `SELECT ... FOR UPDATE`) so the "how many are on call"
read is serialized against every other check.

### The four SQL standard isolation levels, and how Postgres actually implements them

| Isolation level | Dirty read | Non-repeatable read | Phantom read | Serialization anomaly |
|---|---|---|---|---|
| Read Uncommitted | (allowed by spec) | Allowed | Allowed | Allowed |
| Read Committed (Postgres default) | Prevented | Allowed | Allowed | Allowed |
| Repeatable Read | Prevented | Prevented | Prevented (stronger than the SQL standard requires) | Allowed |
| Serializable | Prevented | Prevented | Prevented | Prevented |

Postgres deviates from the standard in ways worth knowing explicitly:

1. **`Read Uncommitted` doesn't actually exist in Postgres.** Requesting it silently upgrades
   to `Read Committed` — MVCC's snapshot model makes a genuine dirty read physically
   impossible; a transaction can only ever see committed data.
2. **`Repeatable Read` is stronger than the SQL standard's minimum.** The standard permits
   phantom reads at this level; Postgres's implementation takes a full snapshot of the
   database at the moment the transaction starts, so rows inserted by other transactions
   afterward simply don't exist from this transaction's point of view — phantoms are
   prevented as a side effect of how the snapshot works, not by extra locking.
3. **`Serializable` uses Serializable Snapshot Isolation (SSI), not heavy locking.** Older
   databases achieved serializable consistency by aggressively locking tables, which
   destroys throughput. Postgres instead watches for read/write dependency cycles between
   concurrent transactions; if two transactions' behavior would violate serializability, it
   lets one commit and forces a serialization error on the other, requiring the application
   to retry. Any code using `SERIALIZABLE` must be wrapped in retry logic for this reason —
   it's a designed, expected outcome, not an edge case to work around.

By default Postgres runs `Read Committed`, which is the right balance for most application
workloads (every individual statement sees the latest committed data). Elevating to
`Serializable` matters specifically for financial transfers and anything else where a
write-skew-shaped bug is unacceptable:

```sql
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
UPDATE accounts SET balance = balance - 100 WHERE id = 'A';
UPDATE accounts SET balance = balance + 100 WHERE id = 'B';
COMMIT;
```

`REPEATABLE READ` alone (without `SERIALIZABLE`) is the right level for a use case like "read
a balance, do application-side math, read it again — guarantee the second read matches the
first even if another transaction deposits and commits in between," without needing to block
that other transaction with `SELECT ... FOR UPDATE`:

```sql
BEGIN;
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SELECT balance FROM accounts WHERE account_id = 42;
-- ... application does math ...
SELECT balance FROM accounts WHERE account_id = 42;  -- guaranteed identical to the first read
COMMIT;
```

## Table-level vs. row-level locks

Every statement takes *some* lock, even a plain `SELECT` (`ACCESS SHARE`, the weakest lock,
which only conflicts with the strongest table-level locks like `ACCESS EXCLUSIVE`, taken by
things like `DROP TABLE` or a non-concurrent `ALTER TABLE`). The practically important
distinction is between a lock scoped to specific rows and one that blocks an entire table.

- **`FOR UPDATE`** — locks the selected rows for the duration of the transaction, blocking
  any other transaction from updating or locking the same rows until this one commits or
  rolls back.
- **`FOR SHARE`** — a weaker read lock: multiple transactions can hold it on the same rows
  simultaneously, but none can update those rows while any `FOR SHARE` lock is held.
- **`FOR NO KEY UPDATE`** — locks a row for update without blocking a foreign key check from
  another transaction that only needs to verify the row still exists (finer-grained than
  plain `FOR UPDATE`, useful when many transactions update non-key columns on the same
  parent row concurrently).
- **`SKIP LOCKED`** — instead of waiting for a lock, skip any row that's currently locked by
  another transaction and take the next available one. This is the actual production
  mechanism behind job queues and ticket/inventory-style "grab N available items, safely, in
  parallel" problems — see
  [`query-patterns.md`](query-patterns.md#lock-free-queue-consumption-for-update-skip-locked)
  for the full worked example. Without it, `FOR UPDATE` alone forces every concurrent
  consumer to queue up behind whichever one locked the rows first, which under real traffic
  serializes what should be parallel work.

**An unindexed foreign key is a common, non-obvious cause of table-wide lock contention.**
Postgres does not automatically create an index on a foreign-key column. Deleting a row from
the parent table (`users`) forces Postgres to scan the *entire* child table (`orders`) to
verify no orphaned rows would be left behind — and that scan takes locks as it goes,
frequently escalating into contention or deadlocks under concurrent write load. Any foreign
key column should get a manually-created B-Tree index as a matter of course.

## Deadlocks

A deadlock happens when two transactions each hold a lock the other is waiting for, with no
way for either to proceed. Concretely: Transaction A locks item 10 then tries to lock item
20; Transaction B (running at the same time, moving stock the opposite direction) locks item
20 then tries to lock item 10. Neither can continue — Postgres detects the cycle and forcibly
aborts one transaction with `ERROR: deadlock detected`.

**The fix is deterministic lock ordering, not a retry loop.** A retry loop makes the error
non-fatal but does nothing about the underlying contention (and a heavier fix — wrapping the
whole operation in `LOCK TABLE ... IN EXCLUSIVE MODE` — kills all parallelism on that table,
trading a correctness bug for a throughput one). The actual fix: always acquire locks on
multiple rows in the same, fixed order across every transaction that could touch them —
typically by sorting the row IDs numerically before issuing the updates:

```sql
-- Every transaction updates the smaller ID first, always
BEGIN;
UPDATE warehouse_stock SET quantity = quantity - 5 WHERE item_id = 10;
UPDATE warehouse_stock SET quantity = quantity + 5 WHERE item_id = 20;
COMMIT;
```

If both Transaction A and Transaction B follow this rule, they can never form a cycle — one
of them will always be first to lock item 10, and the other will simply wait its turn instead
of deadlocking.

## Advisory locks: application-level coordination without a table

`pg_try_advisory_lock(key)` and `pg_advisory_unlock(key)` are locks on an arbitrary 64-bit
integer the application chooses — they don't touch any table or row, live entirely in
Postgres's memory, and are non-blocking (`pg_try_advisory_lock` returns `true`/`false`
immediately rather than waiting in a queue). They're the right tool for coordinating between
identical worker processes without adding a separate distributed-locking system:

```sql
-- Worker 1:
SELECT pg_try_advisory_lock(9999);  -- returns true; proceeds to run the job

-- Worker 2, a moment later:
SELECT pg_try_advisory_lock(9999);  -- returns false; a worker is already running it, exits
```

The common alternative — a `job_locks` table with an `is_running` boolean flag — has a real
failure mode: if the process holding the lock crashes mid-job, the flag stays `true` forever
and the job never runs again until a human intervenes. An advisory lock is released
automatically the moment the holding session disconnects (crash included), which is exactly
the property a "only one of these five identical cron workers should run this" pattern
needs.

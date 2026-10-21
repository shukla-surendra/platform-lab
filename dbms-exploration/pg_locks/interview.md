# Postgres locks — hard interview questions

Read lessons 01–10 first. Every answer here has a **"say this"** line (what to answer in the
interview, out loud) and a **proof** captured from this lab (Postgres 16).

| # | Question | Level |
|:-:|---|---|
| 1 | [Is `UPDATE stock = stock - 1` safe without `FOR UPDATE`?](#1) | ⭐⭐ |
| 2 | [What happens in READ COMMITTED when the row changed while you waited?](#2) | ⭐⭐⭐ |
| 3 | [Same thing in REPEATABLE READ?](#3) | ⭐⭐⭐ |
| 4 | [What is write skew? Which isolation level stops it?](#4) | ⭐⭐⭐⭐ |
| 5 | [Does Postgres have gap / next-key locks like MySQL?](#5) | ⭐⭐⭐⭐ |
| 6 | [Where are row locks stored? Why aren't they in `pg_locks`?](#6) | ⭐⭐⭐⭐ |
| 7 | [What is a MultiXact?](#7) | ⭐⭐⭐⭐ |
| 8 | [Does Postgres do lock escalation?](#8) | ⭐⭐⭐ |
| 9 | [Why do you get `FOR NO KEY UPDATE` instead of `FOR UPDATE`?](#9) | ⭐⭐⭐ |
| 10 | [How can an idle transaction hurt a table it never touched?](#10) | ⭐⭐⭐⭐ |
| 11 | [`ADD COLUMN ... DEFAULT`: instant or table rewrite?](#11) | ⭐⭐⭐ |
| 12 | [How do you add a constraint to a huge table without downtime?](#12) | ⭐⭐⭐ |
| 13 | [What if `CREATE INDEX CONCURRENTLY` fails?](#13) | ⭐⭐⭐ |
| 14 | [Advisory locks: session vs transaction, and the PgBouncer trap](#14) | ⭐⭐⭐⭐ |
| 15 | [`SELECT ... JOIN ... FOR UPDATE`: which tables get locked?](#15) | ⭐⭐⭐ |

---

<a id="1"></a>
## 1. Is `UPDATE stock = stock - 1` safe without `FOR UPDATE`?

**Say this:** "Yes, if the math happens **in SQL**. It's lost if the app reads the value,
computes it, and writes it back. That pattern is called *lost update*."

Proof. Two sessions each run: `SELECT stock` (gets 5) → app computes 4 → `UPDATE SET stock = 4`.
```
two sales of a bag, starting stock 5  →  final stock: 4      ← one sale lost
```
`SET stock = stock - 1` is safe because the second `UPDATE` waits for the row lock, then
re-reads the **latest** row before applying `- 1`.

Fixes for read-then-write in the app: `SELECT ... FOR UPDATE`, an atomic `UPDATE`, optimistic
locking (`UPDATE ... WHERE id = 3 AND version = 7`, then check the row count), or `REPEATABLE READ`
plus retry.

<a id="2"></a>
## 2. READ COMMITTED: the row changed while you waited. What happens?

**Say this:** "After the lock is free, Postgres **re-checks the WHERE clause on the new version**
of the row. If it no longer matches, the row is skipped. It doesn't error."

Proof. Stock = 1. A sets stock to 0 (not committed yet). B runs:
```sql
UPDATE products SET stock = stock - 1 WHERE id = 3 AND stock > 0;
```
```
UPDATE 0          ← B waited, A committed 0, B re-checked "stock > 0" → false → skipped
```
No negative stock. Trap: the re-check only looks at **that row**. Rows that *started* matching
because of A's change are not found (B's scan already happened). That can surprise you with
`UPDATE ... WHERE status = 'x'`.

<a id="3"></a>
## 3. Same in REPEATABLE READ?

**Say this:** "It throws a serialization error instead of re-checking. The app must **retry
the whole transaction**."

```
BEGIN ISOLATION LEVEL REPEATABLE READ;
UPDATE products SET stock = stock - 1 WHERE id = 3;
ERROR:  could not serialize access due to concurrent update
```
Error code `40001`. Your app needs a retry loop for REPEATABLE READ / SERIALIZABLE.

<a id="4"></a>
## 4. What is write skew? Which level stops it?

**Story:** a hospital rule says *at least one doctor must be on call*. Alice and Bob are both
on call. Each checks "count on call = 2, fine, I'll go home" and updates **their own row**.
They touch different rows, so no row lock ever conflicts.

```sql
BEGIN ISOLATION LEVEL ...;
SELECT count(*) FROM doctors WHERE on_call;               -- both see 2
UPDATE doctors SET on_call = false WHERE name = 'alice';  -- Bob updates 'bob'
COMMIT;
```
```
REPEATABLE READ:  alice COMMIT, bob COMMIT   →  alice f, bob f    ← nobody on call!
SERIALIZABLE:     alice COMMIT
                  bob ERROR: could not serialize access due to read/write dependencies
                             among transactions
                  HINT: The transaction might succeed if retried.  →  alice f, bob t ✅
```

**Say this:** "Only SERIALIZABLE stops write skew. Without it, lock what you **read**:
`SELECT ... FOR UPDATE` on the rows the decision depends on, or one shared lock row."

<a id="5"></a>
## 5. Does Postgres have gap / next-key locks like MySQL InnoDB?

**Say this:** "No. InnoDB blocks inserts into a range with gap locks. Postgres never blocks for
that. In SERIALIZABLE it uses **SIRead (predicate) locks**. They never make anyone wait; they
only record what you read, so Postgres can abort a transaction at commit if the schedule
wasn't serializable."

Proof — a serializable read shows up in `pg_locks` like this:
```
 locktype | relation |    mode
----------+----------+------------
 relation | doctors  | SIReadLock      ← no index, so it covers the whole table; can be page/tuple level
```
Follow-up: below SERIALIZABLE, a phantom insert can't be stopped by locking rows (the row
doesn't exist yet). Options: a unique constraint, an exclusion constraint, an advisory lock,
or SERIALIZABLE.

<a id="6"></a>
## 6. Where are row locks stored? Why aren't they in `pg_locks`?

**Say this:** "In the **row itself**: the locker's transaction ID is written into the row's
`xmax` field. Shared memory couldn't hold millions of row locks. A waiter waits on the
locker's **transaction ID** lock, not on the row."

Proof. Lock all 3 rows with `FOR UPDATE`, then look at `pg_locks`:
```
   locktype    |   relation    | transactionid |      mode
---------------+---------------+---------------+-----------------
 relation      | products      |               | RowShareLock     ← table-level only
 relation      | products_pkey |               | RowShareLock
 transactionid |               |           797 | ExclusiveLock    ← "my transaction"
 virtualxid    |               |               | ExclusiveLock
                                       -- no rows listed!
SELECT xmax FROM products WHERE id = 1;   → 797     ← there it is, inside the row
```
This is why waits say *"waiting for ShareLock on transaction 777"* (lesson 07). To list row
locks, use the `pgrowlocks` extension (next question).

Consequence: `SELECT ... FOR UPDATE` **writes to disk** (it dirties the page and creates WAL).

<a id="7"></a>
## 7. What is a MultiXact?

**Say this:** "When **several transactions** lock the same row (e.g. two `FOR SHARE`), there's
only one `xmax` slot. So Postgres stores a *MultiXact ID* there, which points to a list of
transactions. It's stored in `pg_multixact/` and has its own wraparound limit."

Proof (`pgrowlocks`): two sessions hold `FOR SHARE` on row 2, a third updates row 1:
```
 locked_row | locker | multi |   xids    |       modes       |    pids
------------+--------+-------+-----------+-------------------+-------------
 (0,25)     |      3 | t     | {798,800} | {Share,Share}     | {4260,4261}   ← MultiXact #3
 (0,26)     |    799 | f     | {799}     | {"No Key Update"} | {4259}
```
Where it bites: foreign keys. Many concurrent child inserts each take `FOR KEY SHARE` on the
same parent row → heavy MultiXact use → `pg_multixact` grows and MultiXact wraparound vacuums
start.

<a id="8"></a>
## 8. Does Postgres do lock escalation (row locks → table lock)?

**Say this:** "No. SQL Server and DB2 escalate to save lock memory. Postgres doesn't need to,
because row locks live in the row (Q6). Updating 10 million rows still takes only one
`RowExclusiveLock` on the table."

Trap follow-up: the lock table in shared memory *can* fill up with **object** locks, e.g. one
transaction touching thousands of partitions or tables:
`ERROR: out of shared memory — HINT: You might need to increase max_locks_per_transaction.`

<a id="9"></a>
## 9. Why `FOR NO KEY UPDATE` instead of `FOR UPDATE`?

**Say this:** "A normal `UPDATE` that doesn't change a key column takes the weaker
`FOR NO KEY UPDATE`. It doesn't conflict with `FOR KEY SHARE`, which foreign key checks
take. So you can insert child rows while someone updates a non-key column of the parent.
`FOR UPDATE` (or `DELETE`, or changing the key) would block them."

Proof: the `pgrowlocks` output above shows a plain `UPDATE ... SET stock` as `"No Key Update"`.
Lesson 04 measured it: renaming product → child insert 1 ms; deleting product → child insert
1978 ms.

Trap: `SELECT ... FOR UPDATE` "to be safe" on a parent row **blocks all child FK inserts**.
Use `FOR NO KEY UPDATE` if you won't change the key.

<a id="10"></a>
## 10. How can an idle transaction hurt a table it never touched?

**Say this:** "The open transaction holds a snapshot (`backend_xmin`). VACUUM can't remove dead
rows newer than the **oldest snapshot in the whole database**, whatever table they're in. So
tables bloat, indexes bloat, and queries slow down."

Proof. A session opens a REPEATABLE READ transaction, reads `products`, then goes idle. Then:
```
 pid  |        state        | backend_xmin
------+---------------------+--------------
 4323 | idle in transaction |          802

DELETE FROM events;          -- a DIFFERENT table
VACUUM (VERBOSE) events;
tuples: 0 removed, 10000 remain, 10000 are dead but not yet removable
removable cutoff: 802                                          ← held back by pid 4323

-- after that session ends:
tuples: 10000 removed, 0 remain, 0 are dead but not yet removable
```
Other things that hold the horizon back: replication slots, `hot_standby_feedback` on replicas,
and prepared transactions (`pg_prepared_xacts`).

<a id="11"></a>
## 11. `ADD COLUMN ... DEFAULT`: instant or rewrite?

**Say this:** "It always takes ACCESS EXCLUSIVE, but **for how long** depends on the default.
Since PG 11, a constant (or stable) default is stored in the catalog, so it's instant. A
**volatile** default (`random()`, `clock_timestamp()`, `gen_random_uuid()`) rewrites the whole
table while holding the lock."

Proof on a 2-million-row table (the file number changes = new copy of the table):
```
ADD COLUMN a int   DEFAULT 0;         Time:   0.751 ms   filenode 16460 → 16460
ADD COLUMN b float DEFAULT random();  Time: 582.896 ms   filenode 16460 → 16465  (rewritten)
```
Other rewrites to watch: `ALTER COLUMN TYPE` (most type changes), `VACUUM FULL`, `CLUSTER`.

<a id="12"></a>
## 12. Add a constraint to a huge table without downtime?

**Say this:** "Two steps. `ADD CONSTRAINT ... NOT VALID` takes a brief ACCESS EXCLUSIVE but
skips checking existing rows. Then `VALIDATE CONSTRAINT` scans the table under only SHARE
UPDATE EXCLUSIVE, so reads and writes keep going."

```
ADD CONSTRAINT pos CHECK (id > 0) NOT VALID   → AccessExclusiveLock,       1.003 ms
VALIDATE CONSTRAINT pos                       → ShareUpdateExclusiveLock, 74.065 ms (the scan)
```
Same for foreign keys. For `NOT NULL` on old versions: add `CHECK (col IS NOT NULL) NOT VALID`,
validate it, then `SET NOT NULL` (PG 12+ skips the scan when a valid CHECK proves it).

<a id="13"></a>
## 13. What if `CREATE INDEX CONCURRENTLY` fails?

**Say this:** "It leaves an **INVALID** index behind. Queries don't use it, but every write
still has to maintain it. Drop it with `DROP INDEX CONCURRENTLY` and retry. Also: CIC can't run
inside a transaction, and it waits for **every** transaction older than it (even ones on other
tables) to finish."

```
CREATE UNIQUE INDEX CONCURRENTLY u_email ON u(email);
ERROR:  could not create unique index "u_email"
DETAIL:  Key (email)=(a@x) is duplicated.

 indexrelid | indisvalid
------------+------------
 u_email    | f              ← left behind, costs writes, helps nothing

BEGIN; CREATE INDEX CONCURRENTLY x ON u(email);
ERROR:  CREATE INDEX CONCURRENTLY cannot run inside a transaction block
```
Find leftovers: `SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid;`

<a id="14"></a>
## 14. Advisory locks: session vs transaction, and the PgBouncer trap

**Say this:** "`pg_advisory_xact_lock` is released at COMMIT. `pg_advisory_lock` (session)
stays until you call unlock or **disconnect**, so COMMIT doesn't release it."

```
BEGIN; SELECT pg_advisory_xact_lock(1); SELECT pg_advisory_lock(2); COMMIT;
-- what's still held:
 objid |     mode
-------+---------------
     2 | ExclusiveLock          ← the session lock survived COMMIT; lock 1 is gone
```
Trap: with PgBouncer in **transaction pooling** mode, your next transaction may run on a
*different* server connection. A session advisory lock then stays on a connection someone
else is now using, and your `unlock` runs on the wrong one. Use the `_xact_` versions behind
a transaction pooler.

<a id="15"></a>
## 15. `SELECT ... JOIN ... FOR UPDATE`: which tables get locked?

**Say this:** "Plain `FOR UPDATE` locks the matching rows in **every** table of the join. Use
`FOR UPDATE OF orders` to lock only the table you'll change, otherwise you block unrelated
writers on the other tables."

```sql
SELECT o.id FROM orders o JOIN products p ON p.id = o.product_id FOR UPDATE OF o;
```
```
 relation |      mode
----------+-----------------
 orders   | RowShareLock      ← rows locked here
 products | AccessShareLock   ← only read; its rows aren't locked
```
Related trap: `FOR UPDATE` doesn't work with `GROUP BY`, `DISTINCT`, aggregates, or on the
nullable side of an outer join (`ERROR: FOR UPDATE is not allowed with GROUP BY clause`, `... cannot be applied to the nullable side of an outer join`).

---

## Rapid-fire (one-liners)

- **Does `SELECT` block `TRUNCATE`?** Yes. `TRUNCATE` needs ACCESS EXCLUSIVE, which conflicts with SELECT's ACCESS SHARE.
- **Does `VACUUM` (plain) block writes?** No (SHARE UPDATE EXCLUSIVE). `VACUUM FULL` blocks everything.
- **Can two `VACUUM`s run on one table?** No, SHARE UPDATE EXCLUSIVE conflicts with itself. That's on purpose.
- **Are locks released at the end of a statement?** No, at the end of the transaction (except `ROLLBACK TO SAVEPOINT`, which drops the locks taken after the savepoint).
- **Deadlock timeout = how long until the deadlock is killed?** No. It's how long a waiter waits before Postgres *checks* for a deadlock. The check is expensive, so it isn't run immediately.
- **Which transaction does Postgres kill in a deadlock?** The one whose check found the cycle. It's not chosen by cost or age, so don't rely on which one dies.
- **Is `NOWAIT` the same as `lock_timeout = 0`?** No. `lock_timeout = 0` means *wait forever*. `NOWAIT` fails immediately, and only for that statement's row/table lock.
- **Do readers on a replica take locks on the primary?** No, but replaying an ACCESS EXCLUSIVE from the primary conflicts with replica queries → `canceling statement due to conflict with recovery`.

Further reading: [README](README.md) · [doubt.md](doubt.md) · [cheatsheet.sql](cheatsheet.sql)

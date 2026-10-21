# Postgres locks — doubts

Glossary:
- **Shared lock** — "others like me may join" (many readers together).
- **Exclusive lock** — "only me" (one writer).
- **MVCC** — Postgres keeps old row versions, so plain readers never wait for writers.
- **Blocker** — the session holding a lock someone else wants.
- **idle in transaction** — a session that ran `BEGIN` and went quiet, still holding its locks.

## Q1. What is "inclusive" vs "exclusive" lock?

The word is **shared**, not inclusive. Shared = many can hold it together (like many people
reading one book). Exclusive = only one holder (one person writing in it). Every Postgres
lock level sits somewhere between "very shared" (`ACCESS SHARE`, plain `SELECT`) and "very
exclusive" (`ACCESS EXCLUSIVE`, `ALTER TABLE`). See [01](01_shared_vs_exclusive.md).

## Q2. Are there column-level locks?

No. An `UPDATE` writes a whole new copy of the row, so the smallest lock is the row. Two
updates to different columns of the same row still wait (measured: 1972 ms). See [03](03_no_column_locks.md).

## Q3. Plain SELECT takes no row lock — can I make a SELECT lock things?

**Yes.** You add the lock on purpose. Pick by *what* you want to protect:

| You want to lock… | Write this | Others can still… |
|---|---|---|
| the rows you read, because you'll change them | `SELECT ... FOR UPDATE` | read ✅, change/lock those rows ⏳ |
| the rows you read, so they just stay the same | `SELECT ... FOR SHARE` | read ✅, also `FOR SHARE` ✅, change ⏳ |
| the whole table, so nobody writes to it | `LOCK TABLE products IN SHARE MODE;` then `SELECT` | read ✅, write ⏳ |
| the whole table, so nobody even reads it | `LOCK TABLE products IN ACCESS EXCLUSIVE MODE;` | nothing ⏳ |
| an *idea* ("only one nightly job at a time"), not a row | `SELECT pg_advisory_lock(42);` | anyone asking for lock 42 ⏳ |

All of them (except session advisory locks) are released at `COMMIT`/`ROLLBACK`, so they only
make sense inside `BEGIN ... COMMIT`.

Real runs (A holds the lock, B tries):
```
-- A: BEGIN; LOCK TABLE products IN SHARE MODE;
B: SELECT count(*) FROM products;                  Time: 0.486 ms      ← reads fine
B: UPDATE products SET ... WHERE id = 1;           Time: 2034.619 ms   ← waited for A

-- A: SELECT pg_advisory_lock(42);
B: SELECT pg_try_advisory_lock(42);  → f           Time: 0.269 ms      ← "no", without waiting
B: SELECT pg_advisory_lock(42);                    Time: 1979.748 ms   ← waited for A
```

Add `NOWAIT` (fail at once) or `SKIP LOCKED` (skip busy rows) to `FOR UPDATE/SHARE` if you
don't want to wait. The full row lock demo is in [04](04_select_for_update.md).

Small correction to "SELECT takes no lock": a plain `SELECT` does take the weakest **table**
lock (`ACCESS SHARE`, lesson [05](05_table_locks.md)). It only stops `ALTER/DROP` from running
mid-read. It takes **no row** locks.

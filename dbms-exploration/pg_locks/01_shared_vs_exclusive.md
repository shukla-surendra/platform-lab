# 01 — Shared vs exclusive

## Story: the library book

- Many people can **read** the same reference book at a table together. → **shared** lock
- Only **one** person can take the book home to **write notes in it**, and while they have it,
  nobody else can take it home. → **exclusive** lock

(You might hear "inclusive" — the correct word is **shared**. Shared = "others like me can
join". Exclusive = "only me".)

## The rule

|                     | someone holds **shared** | someone holds **exclusive** |
|---------------------|:------------------------:|:---------------------------:|
| I want **shared**   | ✅ go ahead               | ⏳ wait                      |
| I want **exclusive**| ⏳ wait                   | ⏳ wait                      |

That's all a lock is: a note saying "I'm using this", plus this table of who may join.

## Where Postgres uses it

Postgres has many lock *levels* (lesson 04 has 4 for rows, lesson 05 has 8 for tables), but
every one of them is just a point between "very shared" and "very exclusive":

```
very shared ◄─────────────────────────────────────────► very exclusive
ACCESS SHARE   ...   SHARE   ...   EXCLUSIVE   ACCESS EXCLUSIVE
(plain SELECT)                                  (ALTER TABLE, DROP)
```

## Two facts that surprise people

1. **A lock lives until the transaction ends** (`COMMIT` or `ROLLBACK`), not until the
   statement ends. A forgotten open transaction keeps its locks forever.
2. **Plain `SELECT` doesn't take row locks at all.** Postgres keeps old versions of rows
   (this is called *MVCC*), so a reader just looks at the last committed version instead of
   waiting. Lesson 02 proves it. If you *want* a SELECT to lock rows, you ask for it
   explicitly: `SELECT ... FOR UPDATE` (lesson 04, and Q3 in [doubt.md](doubt.md)).

Next: [02_row_locks_update.md](02_row_locks_update.md)

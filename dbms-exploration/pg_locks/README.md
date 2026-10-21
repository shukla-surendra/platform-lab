# Postgres locks, in small steps

10 short lessons, one idea each. Every lesson uses **one tiny shop table** and shows
**real output** captured from Postgres 16, so you can read it without running anything.

```bash
cd dbms-exploration/pg_locks
docker compose up -d --wait          # Postgres 16 on localhost:5434, table already loaded
docker compose exec postgres psql -U lab -d shop     # open a session ("terminal A")
```

Most lessons need **two sessions at the same time**: open two terminals and run the
`psql` line above in each. They're called **A** and **B** in the lessons.

## Files

| File | One idea |
|---|---|
| [01_shared_vs_exclusive.md](01_shared_vs_exclusive.md) | "Shared" vs "exclusive": the only two words you really need |
| [02_row_locks_update.md](02_row_locks_update.md) | Two people updating the **same row** wait; different rows don't; readers never wait |
| [03_no_column_locks.md](03_no_column_locks.md) | Postgres has **no column locks**: different columns, same row, still wait |
| [04_select_for_update.md](04_select_for_update.md) | Locking rows on purpose: `FOR UPDATE`, `FOR SHARE`, `NOWAIT`, `SKIP LOCKED` |
| [05_table_locks.md](05_table_locks.md) | The 8 table lock levels, which command takes which, what blocks what |
| [06_ddl_pileup.md](06_ddl_pileup.md) | Why one `ALTER TABLE` can freeze a whole app (the #1 real-world lock outage) |
| [07_deadlock.md](07_deadlock.md) | Two transactions waiting on each other forever, and how Postgres breaks it |
| [08_who_is_blocking.md](08_who_is_blocking.md) | See running queries, how long they've run, who blocks whom |
| [09_kill.md](09_kill.md) | Stop a query (`cancel`) or kick a session (`terminate`) |
| [10_timeouts_and_logs.md](10_timeouts_and_logs.md) | Safety timeouts, where the logs are, slowest-query stats |
| [cheatsheet.sql](cheatsheet.sql) | All the "management" queries in one copy-paste file |
| [doubt.md](doubt.md) | Your questions + answers, as you ask them |
| [interview.md](interview.md) | 15 hard interview questions (isolation, write skew, MultiXact, migrations...) with real proof |

`setup.sql` creates the tables, `docker-compose.yml` starts Postgres with lock/slow-query
logging turned on (used in lesson 10).

## The whole topic on one screen

```
                    what is locked?
          ┌──────────────┬──────────────┬─────────────────────┐
          │   ROW        │   COLUMN     │   TABLE             │
          ├──────────────┼──────────────┼─────────────────────┤
 who takes│ UPDATE,      │ doesn't      │ every SQL command   │
 it?      │ DELETE,      │ exist in     │ (even SELECT takes  │
          │ SELECT...FOR │ Postgres     │ the weakest one)    │
          │ UPDATE/SHARE │              │                     │
          ├──────────────┼──────────────┼─────────────────────┤
 blocks   │ other writers│      –       │ depends on level:   │
 whom?    │ of that row. │              │ ALTER TABLE blocks  │
          │ NEVER plain  │              │ even plain SELECT   │
          │ SELECT.      │              │                     │
          └──────────────┴──────────────┴─────────────────────┘
```

**Rule to remember:** in Postgres, *readers don't block writers and writers don't block
readers*. Only writer-vs-writer on the same row, and schema changes, make people wait.

Reset the lab any time: `docker compose down && docker compose up -d --wait`.

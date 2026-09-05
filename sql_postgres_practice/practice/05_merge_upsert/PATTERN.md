# Pattern: MERGE & Upsert

## What problem does this solve?

"Sync a batch of incoming rows: update the ones that already exist, insert
the ones that don't" — as **one atomic statement**, not a separate
`UPDATE` then `INSERT` with a race condition in between. Read
`../../docs/06_merge_and_upsert.md` first — this file assumes that mental
model (a join between target and source, branching per matched/unmatched
row).

## How to recognize it

- "Sync," "upsert," "update-or-insert," "reconcile a feed/batch against
  the table."
- "Update X, but only if <condition>, otherwise leave it alone" — a
  conditional update that plain `UPDATE ... WHERE` can express for the
  *matched* rows, but `MERGE` also handles the not-matched (insert) case
  in the same statement.

## The general template

```sql
MERGE INTO target_table AS t
USING (VALUES (...), (...), ...) AS source(col1, col2, ...)
ON t.key = source.key
WHEN MATCHED [AND <condition>] THEN
    UPDATE SET col = source.col
WHEN NOT MATCHED THEN
    INSERT (col1, col2, ...) VALUES (source.col1, source.col2, ...);
```

For a simple upsert with no conditional branching and a real unique
constraint on the match column, `INSERT ... ON CONFLICT (col) DO UPDATE
SET x = EXCLUDED.x` is the shorter Postgres-specific alternative — see the
theory doc's comparison table for when to prefer which.

## Common pitfalls

- Using `ON CONFLICT` against a column with no unique constraint/index —
  Postgres needs a real constraint to detect the conflict; it can't infer
  one from an arbitrary `WHERE`-style condition the way `MERGE`'s `ON`
  clause can.
- Assuming `MERGE n` counts every source row — it only counts rows that
  had an action applied; a `WHEN MATCHED THEN DO NOTHING` branch doesn't
  add to the count.
- Forgetting branch order matters when multiple `WHEN MATCHED` clauses
  exist — the first one whose condition is true wins; a catch-all
  `WHEN MATCHED THEN ...` with no condition must come *after* any
  conditional ones, or it'll shadow them entirely.

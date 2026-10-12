# Lesson 3: schema enforcement and evolution

**Idea:** Delta rejects writes that don't match the table schema; `mergeSchema` opts in to adding columns; `CHECK` constraints reject bad rows.

**Run:** `uv run python lessons/03_schema_enforcement_evolution/lesson.py`

**Watch for:**
- an extra column fails until `mergeSchema` is set
- a type mismatch still fails even with `mergeSchema`
- one bad row fails the **whole** write (atomic): the good row isn't written either

**Exercise:** add a `NOT NULL` constraint on `kind` and try to append a null.

Concepts: [Delta Lake](../../docs/02-delta-lake.md)

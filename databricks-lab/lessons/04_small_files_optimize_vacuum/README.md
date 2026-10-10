# Lesson 4: small files, OPTIMIZE and VACUUM

**Idea:** many small writes create many small files; `OPTIMIZE` compacts them; `VACUUM` physically deletes unreferenced files, which also ends time travel to those versions.

**Run:** `uv run python lessons/04_small_files_optimize_vacuum/lesson.py`

**Watch for:**
- file count before and after `OPTIMIZE`
- old files still on disk after `OPTIMIZE` until `VACUUM`
- time travel breaking after an aggressive `VACUUM`

**Exercise:** run `DESCRIBE HISTORY` and find the OPTIMIZE entry; read its `numRemovedFiles` / `numAddedFiles` metrics.

Concepts: [Delta Lake](../../docs/02-delta-lake.md), [Spark performance](../../docs/03-spark-internals-and-performance.md)

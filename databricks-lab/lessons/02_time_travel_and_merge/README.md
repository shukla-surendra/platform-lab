# Lesson 2: versions, MERGE and time travel

**Idea:** every write is a numbered version, `MERGE` upserts by key, and old versions can be read or restored.

**Run:** `uv run python lessons/02_time_travel_and_merge/lesson.py`

**Watch for:**
- `MERGE` fails when the source has duplicate keys; deduplicating first fixes it
- `DESCRIBE HISTORY` operation metrics (rows inserted/updated, files rewritten)
- `RESTORE` is a new commit, not a rewind of the log

**Exercise:** change the merge to `whenMatchedUpdate` with a condition `s.updated_at > t.updated_at` so stale rows never overwrite newer ones.

Concepts: [Delta Lake](../../docs/02-delta-lake.md)

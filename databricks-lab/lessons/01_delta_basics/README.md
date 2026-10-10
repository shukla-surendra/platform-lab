# Lesson 1: what a Delta table physically is

**Idea:** a Delta table is a folder of Parquet files plus a `_delta_log/` folder of JSON commits.
The log, not the folder listing, defines which files are the current table.

**Run:** `uv run python lessons/01_delta_basics/lesson.py`

**Watch for:**
- each write adds Parquet files and one new numbered JSON file in `_delta_log`
- the actions in each commit (`commitInfo`, `metaData`, `protocol`, `add`)

**Hidden files:** run `ls -a` inside the table and inside `_delta_log`. The dot-files ending in `.crc` are Hadoop checksums, and `NNNN.crc` (no dot) is Delta's version checksum. See [Anatomy of a table folder](../../docs/02-delta-lake.md#anatomy-of-a-table-folder-every-file-you-will-see).

**Exercise:** open a commit JSON by hand and find the `add` entry for a Parquet file, with its
`size` and `stats`.

Concepts: [Delta Lake](../../docs/02-delta-lake.md)

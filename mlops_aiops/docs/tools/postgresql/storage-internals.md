# PostgreSQL: Storage Internals

Part of [`README.md`](README.md)'s PostgreSQL section. Scope note: this isn't written for
someone who administers PostgreSQL as their primary job — it's written for the level of
understanding a principal-level engineer is expected to carry: not the literal byte layout
of a page header, but enough of the physical model that decisions in the other four files
stop looking like a list of rules to memorize and start looking like consequences of a small
number of physical facts. Every one of those "rules" — why `VACUUM` exists, why a random
UUID primary key hurts, why a huge `JSONB` column slows down queries that don't even select
it, why replication can lose data under some settings and not others — is downstream of the
handful of ideas below.

## Why start here

[`concurrency-and-locking.md`](concurrency-and-locking.md) explained that an `UPDATE`
writes a whole new row version instead of touching the old one in place, and that `VACUUM`
exists to clean up what's left behind. That's true, but stated as a rule to accept on faith.
The question a principal engineer should be able to answer, and this file answers, is: new
row version *stored where, exactly*, and *why does that make cleanup necessary rather than
optional*? The answer is the same for every mechanism in this file: PostgreSQL stores data
in fixed-size pages, and almost everything else follows from what a fixed-size page can and
can't do cheaply.

## The page: the atomic unit of everything

PostgreSQL reads and writes data in **8KB pages** (`BLCKSZ`, configurable only at compile
time — in practice, always 8KB). This single fact is worth sitting with, because so much
else is just its consequence:

- A single row is never split across pages. If a row's total data won't fit in a page, that
  data has to go somewhere else entirely — this is exactly why **TOAST** exists (below).
- Every read from disk pulls in a full 8KB page, not just the bytes a query happens to need
  — this is why `shared_buffers` caches whole pages, why a query that touches one row out of
  a thousand on the same page still pays for reading the whole page, and why physically
  ordering a table on the column you range-query most (or partitioning by it) has a real,
  measurable effect: it determines how many *pages*, not how many *rows*, a query has to
  touch.
- A page holds a **header**, a growing array of **line pointers** (small, fixed-size slots
  that each point to one row version's actual bytes within the page), and the row data
  itself, which fills in from the opposite end of the page. The gap between the two growing
  ends is the page's free space — this is exactly what `fillfactor` reserves headroom in,
  specifically so a **HOT update** (mentioned in `concurrency-and-locking.md`) has room to
  write a new row version on the *same* page without touching any index.

## A row version (tuple), and why it's bigger than it looks

Every row version on disk carries a hidden header most people never see in `SELECT *`
output: `xmin` (the transaction ID that created this version), `xmax` (the transaction ID
that deleted/superseded it — zero if it's still current), and a handful of status bits. This
header is the literal mechanism behind MVCC: "is this row version visible to my transaction"
is answered by comparing `xmin`/`xmax` against the reading transaction's own snapshot, not
by any locking. It's also literally why a narrow table (few small columns) still has real
per-row overhead — roughly 23+ bytes of hidden header on top of whatever the actual columns
cost, which matters when reasoning about disk sizing for tables with a huge row count and
few columns (an events/telemetry table being the common case).

## TOAST: what happens when a value is too big for a page

A page is 8KB; PostgreSQL still lets you store a `JSONB` document, a `TEXT` blob, or an
array that's megabytes in size in a single column. The mechanism that reconciles these two
facts is **TOAST** (The Oversized-Attribute Storage Technique), and it activates
automatically, silently, per-column, once a row's on-page size would exceed roughly 2KB
(`TOAST_TUPLE_THRESHOLD`):

1. PostgreSQL first tries **compressing** the oversized value in place.
2. If it's still too large after compression, the value is moved **out-of-line** into a
   separate, hidden TOAST table associated with the parent table, and the main row keeps
   only a small pointer to it.

This is the concrete, physical reason a table with one huge `JSONB` or `TEXT` column
performs worse than intuition suggests, even for queries that never select that column:
fetching a row's other, small columns still requires reading its base page, and if the query
*does* touch the large column, that's a second, separate I/O against the TOAST table — a
row that "looks like one row" is physically two reads. It's also the reason
[`production-and-scaling.md`](production-and-scaling.md#zero-downtime-ddl-more-generally)'s
covering-index pattern (`INCLUDE (col)`) is specifically valuable for small, frequently-read
columns and not a general substitute for good schema design around genuinely large payload
columns.

Four storage strategies exist per-column (`ALTER TABLE t ALTER COLUMN c SET STORAGE ...`),
worth knowing exist even if the defaults are usually correct: `PLAIN` (never compress, never
move out-of-line — for fixed-size types where TOAST can't help, like `INT`), `EXTENDED`
(the default for `TEXT`/`JSONB`/etc. — compress first, then move out-of-line if still too
big), `EXTERNAL` (skip compression, move out-of-line directly — trades disk space for faster
substring access on large text), and `MAIN` (compress, but prefer keeping it in-line even if
large — for values that should stay in-line if at all possible).

## The visibility map and the freeze map: why `VACUUM` and index-only scans are fast at all

A naive "does this row still need cleaning up, or is it still visible to some in-flight
transaction" check would mean scanning every row of every page on every `VACUUM` run — on a
huge, mostly-static table, that's enormous wasted work for pages where nothing has changed
since the last pass. PostgreSQL avoids this with the **visibility map**: a compact bitmap,
one bit per page, marking whether *every* row on that page is definitely visible to every
possible transaction (no pending cleanup work, no concurrent transaction that could still
need an older version).

This one bitmap does two jobs that look unrelated but come from the same fact:

- **`VACUUM` can skip pages the visibility map already marks clean**, which is why routine
  autovacuum on a large, append-mostly table (where most pages never change again) stays
  cheap — it's not re-scanning the whole table every time, just the pages that have actually
  changed.
- **An index-only scan can skip visiting the heap page at all** for a page marked
  all-visible, because it already knows every row on that page would pass a normal
  visibility check — it can trust the index's own copy of the columns it needs. This is the
  mechanism `README.md`'s covering-index section depends on: a covering index alone doesn't
  guarantee an index-only scan happens — the visibility map for the relevant pages has to
  actually be up to date, which is itself another reason a table needs healthy, regular
  vacuuming, not just the right indexes.

A related bitmap, the **freeze map**, tracks which pages have already been frozen (see
[`concurrency-and-locking.md`](concurrency-and-locking.md#transaction-id-wraparound)) so
routine vacuuming doesn't have to re-check pages that are already safely frozen against
transaction ID wraparound.

## WAL: why every write happens twice

**Write-Ahead Logging** is the rule that a description of a change must be durably written
to the WAL (Write-Ahead Log) *before* the actual data page it affects is allowed to be
written to disk. Stated as a rule, that sounds like arbitrary overhead. Stated as the
problem it solves, it's the only way to get both real performance and crash safety at the
same time:

- Modifying data pages in place, synced to disk on every single transaction, would mean
  scattered random writes across the whole table file on every commit — slow.
- Deferring those page writes and batching them (which PostgreSQL does — dirty pages sit in
  `shared_buffers` and get flushed later) is fast, but creates a real risk: if the server
  crashes before a dirty page is flushed, that committed change is gone.
- The WAL resolves the conflict: the *log* of the change (small, sequential, cheap to write
  and `fsync`) is what actually has to be durable before a transaction can report success.
  The full data page write can be deferred and batched safely, because after a crash,
  PostgreSQL can **replay the WAL** to reconstruct any change that was logged but never made
  it into the actual data file.

This single mechanism is also, not coincidentally, the entire basis for physical replication
(a replica is a process continuously replaying a copy of the same WAL stream — see
[`backup-recovery-and-replication.md`](backup-recovery-and-replication.md#streaming-replication)),
and for point-in-time recovery (restoring an old backup and replaying WAL forward to any
exact moment — same file, same mechanism).

### Checkpoints: why WAL doesn't grow forever

If PostgreSQL kept every WAL record ever written, both disk usage and crash-recovery time
(replaying the *entire* WAL history since the server was first created) would be unbounded.
A **checkpoint** is the periodic operation that writes every currently-dirty page in
`shared_buffers` out to the actual data files and records "everything up to this WAL
position is now durably reflected in the data files themselves." After a checkpoint, WAL
older than that point is no longer needed for crash recovery (though it may still be needed
for replication or point-in-time recovery — a separate retention concern) and can be
recycled.

This creates a real, tunable trade-off, not a "set it and forget it" default:

- **Checkpoints too infrequent** (`checkpoint_timeout` too high, `max_wal_size` too generous)
  means more WAL accumulates between checkpoints, which means longer crash-recovery time
  (more WAL to replay after an unclean shutdown) and more disk consumed by retained WAL.
- **Checkpoints too frequent** cause a real, felt production symptom: a **checkpoint spike**
  — a burst of write I/O as a large batch of dirty pages all get flushed at once, briefly
  starving normal query I/O. `checkpoint_completion_target` (spreading the checkpoint's I/O
  across most of the interval until the next one, rather than doing it all at once) is the
  standard mitigation, not eliminating checkpoints, since eliminating them isn't an option.

## Going one level deeper on the query planner

[`README.md`](README.md#diagnosing-a-slow-query-explain-analyze-and-statistics) covered the
operational symptoms of a bad plan. The planner's actual decision process is a **cost
model**: every candidate plan gets assigned a numeric cost from a small set of tunable
constants — `seq_page_cost` (cost of reading one page sequentially, the baseline, defaulted
to `1.0`), `random_page_cost` (cost of a random-access page read — defaulted higher than
sequential, reflecting spinning-disk-era physics; on all-SSD/NVMe storage, lowering this
toward `1.1`–`1.5` is a legitimate, common production tuning step, since the real
random-vs-sequential penalty on SSDs is much smaller than the historical default assumes),
and `cpu_tuple_cost`/`cpu_operator_cost` (per-row CPU work). The planner picks whichever
candidate plan has the lowest total estimated cost — which is exactly why *bad estimates*,
not a broken planner, are the real cause of almost every "why did Postgres pick a terrible
plan" incident.

Those estimates come from **`pg_statistic`** (populated by `ANALYZE`, which autovacuum runs
automatically after enough rows change). Two specific columns of that statistics data
explain most surprising planner decisions:

- **`n_distinct`** — the estimated number of distinct values in a column. A wildly wrong
  estimate here (common on very high-cardinality columns, or right after a bulk load before
  `ANALYZE` has run) directly produces a wrong selectivity estimate, which is the root cause
  behind the "why is Postgres ignoring my index" family of problems covered in `README.md`.
- **`default_statistics_target`** — how many histogram buckets `ANALYZE` builds per column
  (100 by default). Raising it for a specific high-cardinality, frequently-filtered column
  (`ALTER TABLE t ALTER COLUMN c SET STATISTICS 500;`) gives the planner a finer-grained
  distribution to estimate from, at the cost of a slightly more expensive `ANALYZE` — a real,
  narrow tuning lever, not something to raise globally without reason.

**Extended statistics** (`CREATE STATISTICS`) exist to fix a specific, common blind spot: the
planner's default cost model assumes columns are statistically *independent* of each other.
For two genuinely correlated columns (`city = 'New York'` and `state = 'NY'`), the planner
multiplies each column's individual selectivity together — producing a combined estimate far
lower than reality, because in truth, knowing the city already tells you the state with
near-certainty. `CREATE STATISTICS stats_name (dependencies) ON city, state FROM addresses;`
(followed by `ANALYZE`) tells the planner to actually measure the real correlation between
those columns instead of assuming independence — directly relevant any time a multi-column
filter's estimated row count is visibly, persistently wrong in `EXPLAIN ANALYZE` output even
after routine `ANALYZE` and correct indexing.

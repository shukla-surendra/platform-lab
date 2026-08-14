# PostgreSQL: Production Operations and Scaling

Part of [`README.md`](README.md)'s PostgreSQL section — see its top note on sourcing. This
file covers what changes once PostgreSQL is running in production on AWS at real scale:
RDS vs. Aurora, connection pooling, parameter tuning, monitoring, schema lifecycle
(primary-key overflow, partitioning, zero-downtime DDL), replication and stale reads, and
zero-downtime strategies for migrating a live, actively-written table. For the underlying
mechanics RDS Multi-AZ and Aurora failover are actually built on — streaming replication,
replication slots, `synchronous_commit`, and HA orchestration in a self-managed deployment —
see [`backup-recovery-and-replication.md`](backup-recovery-and-replication.md).

## RDS vs. Aurora

**Standard RDS PostgreSQL** runs community PostgreSQL on EC2-managed infrastructure with
network-attached EBS storage. **Aurora PostgreSQL** is AWS's storage-layer reimplementation
— the compute layer speaks the PostgreSQL wire protocol, but the underlying storage engine
is a proprietary, distributed, self-healing layer replicated across multiple Availability
Zones. Practical differences that matter when choosing between them:

- **High availability**: standard RDS Multi-AZ creates a synchronous standby in another data
  center — on primary failure, AWS repoints DNS to the standby in roughly 60 seconds. Aurora
  achieves faster failover because its storage layer is already shared/replicated
  independently of any single compute instance.
- **Cross-region disaster recovery**: an asynchronous read replica in a second region
  (`us-west-2`, say, if `us-east-1` goes down entirely) is the standard RDS pattern.
  **Aurora Global Database** replicates an entire cluster across multiple AWS regions with
  sub-second replication latency, enabling both disaster recovery and genuine global read
  scaling.
- **Fast cloning**: Aurora supports copy-on-write cloning — a terabyte-scale production
  database can be cloned in minutes without duplicating the underlying data storage,
  producing a safe, near-free sandbox for testing a risky schema migration against real
  production data before running it for real.

## Connection pooling

Postgres's `max_connections` parameter should generally be kept relatively low (e.g.
200–500) and application traffic routed through a pooler — PgBouncer or AWS RDS Proxy —
rather than raising the limit to match raw application connection counts, since each
Postgres connection is a real OS process with real memory overhead.

**PgBouncer's pooling modes are not interchangeable — the choice changes what SQL features
work:**

- **Session pooling** — a client holds its database connection for the life of its own
  session. Every session-scoped feature (`PREPARE` statements, session-level advisory locks,
  `SET LOCAL`/`SET`) works normally, but pooling efficiency is limited to however many
  concurrent client sessions actually exist.
- **Transaction pooling** — a server connection is assigned to a client only for the
  duration of a single transaction, then immediately handed to a different client the moment
  it commits. This is what makes 50 real database connections serve 10,000 concurrent
  clients — but because the next query might run on an entirely different physical
  connection, anything tied to session state breaks: prepared statements, session-level
  advisory locks, and `SET LOCAL` for anything meant to persist beyond one transaction.
  Mandatory for high-throughput, stateless REST APIs; incompatible with code that assumes a
  stable session.

## Parameter tuning (`postgresql.conf` / RDS Parameter Groups)

- **`shared_buffers`** — Postgres's internal page cache. A commonly cited starting point is
  roughly 25% of total instance RAM.
- **`work_mem`** — memory allocated *per operation* (a sort, a hash join) before it spills to
  disk as temp files. `temp_files` showing up in the logs is the concrete signal that a
  workload's sorts/joins are exceeding this and paying a real disk-I/O cost — the trigger to
  carefully raise it.
- **`max_connections`** — kept relatively low (see connection pooling above), with a pooler
  absorbing the actual application-side connection count.
- **`statement_timeout`** — a global ceiling (e.g. 30,000ms) so a single rogue analytics
  query can't hold resources indefinitely and take down production traffic.

## Monitoring

- **AWS Performance Insights** — a visual dashboard of Database Load measured in Average
  Active Sessions (AAS); the direct way to see which specific SQL queries are consuming CPU
  or waiting on locks right now.
- **CloudWatch metrics worth alarming on**: `CPUUtilization` (a spike usually means a missing
  index); `FreeableMemory` (a drop risks Postgres swapping to disk); `EBSByteBalance%` /
  `BurstBalance` (standard RDS storage runs on an I/O credit system — exhausting it collapses
  disk throughput); `ReplicaLag` (critical for any workload routing reads to replicas — a lag
  spike means users can write something and not see it reflected back for seconds, a real
  stale-read UX bug, not just a metrics concern).
- **`pg_stat_statements`** and **`auto_explain`** — see [`README.md`](README.md#diagnosing-a-slow-query-explain-analyze-and-statistics)
  for what each records and why they matter more than reactive debugging.

## Schema and data lifecycle at scale

### Primary key choice: sequential vs. random UUIDs

Random UUIDs (UUIDv4) as a primary key destroy B-Tree index performance at scale: because
every generated value is uniformly random, every `INSERT` writes to a random, unpredictable
location in the index's B-Tree, causing constant page fragmentation and random disk I/O.
Sequential identifiers — auto-incrementing integers, or time-sortable UUID variants like
UUIDv7 or Snowflake IDs — keep index inserts sequential, avoiding this fragmentation
entirely, while still giving a UUID's benefit of not leaking a guessable row count.

### Running out of primary keys (integer overflow)

A `SERIAL`/`INT` primary key is bound to a 32-bit signed integer — a hard ceiling around
2.14 billion. Once a sequence tries to generate past that ceiling, Postgres throws `ERROR:
nextval: reached maximum value of sequence` on every single subsequent `INSERT` — an
immediate, hard production outage, not a graceful degradation.

Migrating a live, multi-billion-row table from `INT` to `BIGINT` cannot be done with a
direct `ALTER TABLE ... ALTER COLUMN id TYPE BIGINT` — that statement takes an `ACCESS
EXCLUSIVE` lock and rewrites the entire table on disk, taking the application offline for
however long that rewrite takes (hours, on a 100GB+ table). The zero-downtime pattern:

1. **Add a new, nullable `BIGINT` column** (`ALTER TABLE events ADD COLUMN new_id BIGINT;`)
   — adding a nullable column is a metadata-only operation and completes instantly.
2. **Dual-write via a trigger** so every new `INSERT` automatically copies `id` into
   `new_id`.
3. **Backfill historical rows in small batches** (e.g. 10,000 rows at a time,
   `UPDATE events SET new_id = id WHERE new_id IS NULL AND id BETWEEN 1 AND 10000`, pausing
   between batches) so the backfill never holds a large lock or overwhelms I/O in one shot.
4. **Build the new unique index concurrently** (`CREATE UNIQUE INDEX CONCURRENTLY
   events_new_id_idx ON events(new_id);`) so the table stays readable and writable while the
   index builds.
5. **Swap the columns in a single fast transaction**: drop the old primary key constraint,
   rename `id` to `old_id`, rename `new_id` to `id`, attach the new primary key using the
   already-built index. This step is the only one that briefly locks the table, and it's
   fast because all the expensive work (the index build, the backfill) already happened
   beforehand.
6. Finally, reset the sequence to continue generating `BIGINT` values starting above the old
   ceiling, and attach it to the new column.

### Zero-downtime DDL more generally

- **Adding an index**: never run plain `CREATE INDEX` on a production table — it locks the
  table for writes for the duration of the build. `CREATE INDEX CONCURRENTLY` takes longer
  to build but allows normal reads and writes to continue throughout.
- **Adding a constraint**: `ALTER TABLE ... ADD CONSTRAINT` validates every existing row
  under a heavy lock. The safe pattern: add the constraint as `NOT VALID` first (a metadata-
  only change, milliseconds), then run `VALIDATE CONSTRAINT` in a separate transaction, which
  checks existing rows in the background without holding a heavy lock the whole time.

### Table partitioning

Partitioning is a **physical division of data disguised as a single logical table** — the
application queries one table name, and Postgres routes each read or write to the correct
underlying physical partition.

```sql
CREATE TABLE user_events (
    event_id BIGSERIAL,
    user_id BIGINT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL
) PARTITION BY RANGE (created_at);

CREATE TABLE user_events_2026_06 PARTITION OF user_events
    FOR VALUES FROM ('2026-06-01 00:00:00Z') TO ('2026-07-01 00:00:00Z');
CREATE TABLE user_events_2026_07 PARTITION OF user_events
    FOR VALUES FROM ('2026-07-01 00:00:00Z') TO ('2026-08-01 00:00:00Z');

-- Indexing the parent automatically cascades to every current and future partition (PG 11+)
CREATE INDEX user_events_user_id_idx ON user_events (user_id);
```

Three real benefits: **partition pruning** — a query for July 2026 data touches only the
July partition, ignoring every other partition entirely, as long as the partition key
appears in the `WHERE` clause; **O(1) deletion of old data** — `DROP TABLE
user_events_2025_12` instantly reclaims disk space with zero vacuuming overhead, versus a
`DELETE ... WHERE created_at < ...` that locks rows and generates a wave of dead tuples for
`VACUUM` to clean up later; **targeted autovacuum** — vacuuming thirty 30GB monthly
partitions independently is far cheaper and less disruptive than vacuuming one 1TB table as
a single unit.

**Partition pruning silently fails to help if the partition key is missing from the
query.** A query like `SELECT * FROM customer_orders WHERE order_total > 10000` — omitting
the partition key (`region`, say) entirely — forces Postgres to scan every single partition
sequentially, completely defeating the purpose of partitioning:

```sql
-- Triggers pruning — only the 'US' partition is scanned
SELECT * FROM customer_orders WHERE region = 'US' AND order_total > 10000;
```

If a query genuinely needs to search across all regions, the options are running the query
in parallel across partitions or making sure a standard index exists on the filtered column
*within* each individual partition — there's no way around scanning broadly if the
partition key genuinely isn't part of the filter.

**Real gotchas with partitioned tables**, all consequences of the same underlying rule
(Postgres cannot cheaply guarantee global uniqueness across partitions without checking
every one of them):

- **The primary key must include the partition key.** `PRIMARY KEY (event_id)` alone isn't
  valid on a table partitioned by `created_at` — it has to be
  `PRIMARY KEY (event_id, created_at)`.
- **There's no default partition unless you create one, and a rogue row with no matching
  partition hard-fails the `INSERT`.** A `DEFAULT` partition can act as a catch-all, but
  becomes an anti-pattern at real scale (everything not yet explicitly partitioned funnels
  into one unbounded table).
- **Other tables can't easily hold a foreign key pointing at a partitioned table**, since the
  referenced key now includes the partition column — this can force real data-model changes
  in related tables.

Manually running `CREATE TABLE ... PARTITION OF ...` at midnight every month isn't a
sustainable operational pattern — `pg_partman` is the standard extension for automating
partition creation/retirement on a schedule in production.

## Distributed transactions across services

Coordinating a write that spans two separate databases (e.g. an `Order Service` on Postgres
and a `Payment Service` on Aurora, where a failed payment must prevent the order from being
created) can't use a single `BEGIN`/`COMMIT` since there's no shared transaction boundary
across two different database engines.

- **Two-Phase Commit (2PC)** — a coordinator asks both databases to "prepare" the
  transaction; only if both agree does it send a final "commit." Guarantees strict
  consistency, but locks resources across the network for the duration and introduces a
  single point of failure (the coordinator) — generally avoided at real scale.
- **Saga pattern** — the modern default for microservices. Each service executes its own
  local transaction and emits an event (via a message broker) to the next service. If a
  downstream step fails, a **compensating transaction** undoes the effect of the earlier
  step (e.g. `UPDATE orders SET status = 'CANCELLED' WHERE id = 1`) rather than relying on a
  distributed rollback. This trades strict ACID consistency for eventual consistency and
  higher availability — the standard tradeoff for cross-service writes.

## Replication and stale reads

Asynchronous replication works by shipping the **WAL (Write-Ahead Log)** — when a write hits
the primary, Postgres appends the change to its WAL before touching the actual table files;
the primary streams that WAL to each replica, which replays it to update its own state. This
is inherently asynchronous: a replica can genuinely lag behind the primary by seconds under
load.

**"Read-Your-Own-Writes" (RYOW)** is the standard application-layer fix for the resulting UX
bug (a user updates their profile, reloads, and the page — routed to a lagging replica —
still shows the old data). Two implementation strategies:

- **Stateful (Redis-backed)**: immediately after a write commits, cache a short-lived flag
  (`SET user:12345:force_primary true EX 5`, a TTL slightly above the observed p99
  replication lag). The read-routing layer checks this flag on every read for that user;
  if it's set, route to the primary; otherwise, route to a replica as normal.
- **Stateless (cookie/JWT-backed)**: the write response attaches a timestamp header; the
  client sends it back on the next read; the routing layer compares it to the current time
  and routes to the primary if the gap is still within the expected lag window.

Design considerations either approach has to answer explicitly: what happens if the cache
backing the stateful approach goes down (fail toward the replica, to protect the primary
from being flooded with all read traffic, unless strict correctness genuinely outweighs
availability for that read path); how the TTL is chosen (slightly above the observed p99
replication lag, not an arbitrary round number — too generous a TTL just wastes replica
capacity by routing more reads to the primary than necessary); and that this pattern is
scoped specifically to a user seeing *their own* write, not a general substitute for eventual
consistency elsewhere in the system (User B seeing User A's comment a moment late is normal
and expected; routing every read to the primary to avoid that would eliminate the benefit of
having replicas at all).

## Moving large volumes of data safely

### Basic approaches and their real costs

- **`INSERT INTO target SELECT ... FROM source`** — fine for a few hundred thousand rows into
  an existing table, but on tens of millions of rows it runs as one giant transaction: it
  bloats memory (shared buffers), generates a large amount of WAL, and holds locks on both
  the source and target tables for as long as it takes to finish. If it fails at 99%
  complete, the entire operation rolls back.
- **`CREATE TABLE AS SELECT` (CTAS)** — very fast for creating a new table from an existing
  one (minimal WAL overhead), but it copies **only the raw data** — no indexes, no primary
  key, no constraints. Those all need to be created manually afterward.
- **`COPY`** — the fastest native bulk-loading mechanism, bypassing much of the standard SQL
  parsing/transaction overhead and streaming data directly into the table's data pages.
  Source and target can even be piped through standard Unix pipes without an intermediate
  file:

  ```bash
  psql -c "COPY (SELECT * FROM source_table WHERE condition) TO STDOUT" | \
  psql -c "COPY target_table FROM STDIN"
  ```

- **Handling duplicates during a sync** — a blind `INSERT ... SELECT` crashes on the first
  unique-constraint collision if the target already holds some of the rows;
  `ON CONFLICT (id) DO UPDATE SET amount = EXCLUDED.amount` (where `EXCLUDED` refers to the
  row that was proposed for insertion but conflicted) makes it an idempotent upsert instead.

### The production sequence for moving hundreds of millions of rows into a live table

1. **Drop non-unique indexes on the target first** — otherwise every one of hundreds of
   millions of inserted rows forces a B-Tree rebalance, crawling write throughput.
2. **Disable foreign keys and triggers temporarily**
   (`ALTER TABLE target_table DISABLE TRIGGER ALL;`) — otherwise every inserted row pays for
   a validation check it doesn't need mid-migration.
3. **Batch the copy in chunks** (e.g. 50,000 rows at a time via keyset pagination —
   `WHERE id > last_max_id LIMIT 50000` — not `OFFSET`, for the same reason covered in
   [`README.md`](README.md); see also the query-patterns library) to keep individual locks
   short and avoid a single enormous WAL spike.
4. **Recreate indexes concurrently** once the data is fully copied — building an index once
   over a static 500-million-row table is exponentially cheaper than maintaining it through
   500 million individual inserts.
5. **Re-enable triggers.**
6. **Run `ANALYZE target_table`** so the query planner's statistics reflect the new table
   size before real traffic hits it.

## Zero-downtime migration of a live, actively-written table

Moving a 1TB, actively-written table into a newly partitioned replacement without taking the
application offline is a different problem from a one-time bulk copy: the batch copy itself
might take 12 hours, and the live application keeps inserting, updating, and deleting rows
in the source table the entire time. A naive "run the batch copy, then catch up anything
where `updated_at > copy_start_time`" approach genuinely loses data — it can't detect **hard
deletes** (a row deleted from the source during the 12 hours is simply gone, with no trace
for a delta query to find), and it can miss updates from a long-running transaction that
started before the delta query ran but committed after, landing outside the delta window.

Three architectures actually solve this, differing in what they trade against each other:

- **Native logical replication** — create a `PUBLICATION` on the old table and a
  `SUBSCRIPTION` on the new one; Postgres takes an initial snapshot, copies it over, then
  streams every subsequent `INSERT`/`UPDATE`/`DELETE` from the WAL to the new table in near
  real time. Once fully caught up, flip application traffic to the new table and drop the
  old one. The least application code involved, but needs sufficient permissions on managed
  RDS (not always available depending on the hosting tier).
- **Outbox/audit-queue pattern** — if logical replication isn't available, create an empty
  `migration_changelog` table and attach a trigger to the old table that records every
  `INSERT`/`UPDATE`/`DELETE` (primary key + action type) as it happens. Run the 12-hour batch
  copy as normal; once it finishes, a "catch-up" worker replays everything the changelog
  captured during the batch window, run repeatedly until the queue is empty.
- **Application dual-write** — the application code itself writes every new/updated order to
  *both* the old and new table synchronously (an `UPSERT` if the row doesn't yet exist in the
  new table). The batch copy runs in the background using `ON CONFLICT DO NOTHING`, so it
  never overwrites fresher data the dual-write path already wrote. Once the batch finishes,
  drop the old table and remove the dual-write code path. The most invasive of the three (it
  touches application code, not just database/infra), but requires no special database
  permissions.

## Adjacent failure-mode concepts worth knowing

A handful of broader distributed-systems concepts came up directly attached to PostgreSQL
operational discussions, worth keeping here even though they're not Postgres-specific
mechanisms on their own:

- **Quorum commit for synchronous replication** — a single synchronous replica creates a
  real availability risk: if it crashes, the primary can no longer commit anything, because
  it's waiting indefinitely for an acknowledgment that will never come (this is the CAP
  theorem's availability/consistency tradeoff, made concrete). Configuring
  `synchronous_standby_names = 'FIRST 2 (replica1, replica2, replica3)'` against three
  replicas means a write only needs acknowledgment from *any two* of the three — the
  database stays available and loses zero data even if one specific replica dies.
- **Split-brain and STONITH** — if a network partition cuts a standby off from its primary,
  the standby may promote itself believing the primary is dead, while the original primary
  (still healthy, just unreachable from the standby) keeps accepting writes from
  application servers that can still reach it. Two primaries now accept independent,
  conflicting writes — a "split-brain" that's mathematically impossible to merge once the
  network reconnects. STONITH ("Shoot The Other Node In The Head") is the blunt, effective
  fix: before a standby is allowed to promote itself, it issues a hardware/cloud-API-level
  command to physically cut power or sever the network interface of the original primary,
  guaranteeing two primaries can never coexist.
- **Bloom filters, as used inside Postgres** — a Bloom filter is a probabilistic structure
  that answers "definitely not present" or "probably present" using a tiny, fixed amount of
  memory relative to the dataset size. Postgres uses this idea both inside BRIN indexes and
  inside hash joins over large tables: checking a Bloom filter that fits entirely in CPU
  cache can instantly rule out a UUID that isn't in the dataset at all, without touching disk.
- **Cache stampede / thundering herd mitigation** — if a cache (e.g. Redis, fronting a heavy
  Postgres aggregate query) crashes and restarts empty, every one of thousands of concurrent
  requests can hit the database simultaneously trying to rebuild the same cached value at
  once, exhausting connections or crashing the database outright. The standard defenses:
  application-level request deduplication (the first request to see a cache miss acquires an
  in-process or distributed lock and runs the real query; every other concurrent request for
  the same key waits on that single in-flight result instead of firing its own query), and
  jittering cache TTLs (randomizing expiry by roughly ±20%) so a large batch of cache entries
  written at the same moment don't all expire — and all get requeried — simultaneously.

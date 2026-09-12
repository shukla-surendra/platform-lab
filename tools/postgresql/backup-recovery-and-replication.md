# PostgreSQL: Backup, Recovery, and Replication Mechanics

Part of [`README.md`](README.md)'s PostgreSQL section. [`production-and-scaling.md`](production-and-scaling.md)
covered RDS/Aurora's managed version of most of this (Multi-AZ, cross-region replicas,
Aurora cloning) — this file is what those managed features are actually built on top of,
which matters even on a fully managed database: knowing the underlying mechanism is what
lets a principal engineer reason correctly about what a managed failover actually guarantees
(and doesn't), rather than trusting the marketing description of the feature.

## Two fundamentally different kinds of backup

The first-principles question to ask before picking a backup tool: **do you want a
description of the data, or a copy of the files?** PostgreSQL's two backup mechanisms answer
that question differently, and the answer determines almost everything else about how each
one behaves.

- **Logical backup (`pg_dump` / `pg_dumpall`)** — connects to the database like a client and
  produces a script of SQL statements (`CREATE TABLE`, `COPY` or `INSERT`, `CREATE INDEX`,
  ...) that, if replayed, recreate the same objects and data. Because it's just SQL, it's
  portable across PostgreSQL versions and even different hardware architectures, and it can
  selectively dump a single table or schema. Its real cost shows up on **restore**: rebuilding
  a large database means re-running every `INSERT`/`COPY` and rebuilding every index from
  scratch, which is slow, and — because a `pg_dump` run takes a **consistent snapshot as of
  when it started**, not a live view — any restore reflects the database exactly as it was at
  that one instant, with no way to move the recovery point forward or backward.
- **Physical backup (`pg_basebackup`, or a filesystem/EBS snapshot)** — a byte-for-byte copy
  of the actual data directory: the page files, not a description of their contents. Restore
  is comparatively fast (copy the files back, start Postgres), but a physical backup taken
  while the database is live and being written to is **not, by itself, a consistent
  snapshot** — files are being copied while other files elsewhere in the directory are still
  changing. `pg_basebackup` handles this by bracketing the copy between an internal "start
  backup" and "stop backup" call and including the WAL generated during the copy itself;
  Postgres replays that WAL on startup from the restored files to reach an actually
  consistent state. A physical backup is therefore never really "just the files" — it's
  always the files *plus* the WAL segments generated during the copy, and it only becomes
  restorable once both are present together.

Neither is strictly better — a `pg_dump` is the right tool for "move this schema to a
different PostgreSQL major version" or "extract one table"; a physical backup is the right
foundation for restoring a large production database quickly and for point-in-time recovery,
below.

## Point-in-time recovery (PITR): restoring to *any* moment, not just backup time

A single physical backup, by itself, only lets you restore to the exact moment the backup
finished. **Continuous WAL archiving** is what turns that single fixed point into the
ability to restore to *any* moment since the backup was taken: configuring `archive_mode =
on` and an `archive_command` continuously copies each completed WAL segment somewhere
durable (S3, another disk) as it's generated, independent of when the next base backup runs.

Recovery, then, is a two-step replay: restore the most recent base backup taken *before* the
target moment, then replay the archived WAL segments forward from that backup's timestamp up
to the exact target time (`recovery_target_time`) — potentially seconds before some
destructive event (an accidental `DROP TABLE`, a bad migration) rather than only to whatever
moment the last scheduled backup happened to run.

This is the mechanism behind two numbers that matter far more to the business than "do we
have backups":

- **RPO (Recovery Point Objective)** — how much data, in the worst case, can be lost. Driven
  directly by how frequently WAL is archived/shipped off the primary — if WAL archiving
  fails silently for an hour before anyone notices, the real RPO for that window just became
  an hour, no matter how good the backup schedule is.
- **RTO (Recovery Time Objective)** — how long a full recovery actually takes. Driven by how
  *much* WAL has to be replayed after restoring the base backup — a backup taken once a week
  means recovering from a Friday incident might mean replaying six days of WAL, which can
  take a very long time. Frequent base backups exist specifically to keep RTO bounded, not
  because the backups themselves are more valuable individually.

Neither of these numbers is a property of "having backups" in the abstract — they're
properties of the *specific* backup frequency and WAL-archiving reliability actually
configured, which is the reason RPO/RTO are the numbers worth stating and defending
explicitly in a design review rather than "yes, we have backups."

## Streaming replication

A replica is, mechanically, nothing more than a second PostgreSQL process continuously doing
what crash recovery does — replaying WAL — except the WAL is arriving live over a network
connection from the primary rather than being read from local archived files after a crash.
This is why streaming replication and crash recovery share so much of the same code path,
and why understanding WAL (see [`storage-internals.md`](storage-internals.md#wal-why-every-write-happens-twice))
is what actually explains replication rather than treating it as a separate feature.

`hot_standby = on` additionally allows the replica to serve read-only queries *while* it
continues replaying incoming WAL — this is what makes a replica useful for read scaling and
not just disaster recovery, and it's also exactly why replica reads can be stale (see
[`production-and-scaling.md`](production-and-scaling.md#replication-and-stale-reads) for the
application-level fix): a query on the replica sees whatever state replay has reached *so
far*, which is always at least slightly behind the primary.

### Replication slots: why they exist, and their real failure mode

Without a replication slot, the primary has no persistent record of "how far behind is this
specific replica," and its own WAL-retention decisions (recycling old segments once a
checkpoint no longer needs them locally) are made independent of any replica's progress. If
a replica falls far enough behind — or disconnects for a while — the primary can recycle a
WAL segment the replica still needed, permanently breaking that replica's ability to catch
up; it now has to be rebuilt entirely from a fresh base backup.

A **replication slot** fixes this by having the replica register itself with the primary,
which then retains WAL until that specific slot confirms it has received it — guaranteeing a
temporarily disconnected replica can always resume cleanly, no matter how long it was gone.

That guarantee is also the hazard: a slot for a replica that's gone permanently (decommissioned,
crashed and never coming back) still tells the primary "keep retaining WAL for this consumer
forever." An orphaned replication slot is a genuine, real production incident — the primary's
disk fills with retained WAL it will never actually ship to anyone, with no automatic
recovery, until someone notices and drops the slot manually. Any HA design that uses
replication slots needs monitoring on slot lag specifically for this reason.

### `synchronous_commit`: the actual durability/latency dial

[`production-and-scaling.md`](production-and-scaling.md#adjacent-failure-mode-concepts-worth-knowing)
covered quorum commit (`synchronous_standby_names`) as an availability mechanism. The
matching `synchronous_commit` setting is the durability dial — it controls exactly *what*
"commit succeeded" is allowed to mean, and each level trades latency for a different,
specific durability guarantee:

| Level | What "commit" waits for | What can be lost on primary failure |
|---|---|---|
| `off` | Nothing — the client is told "committed" before the WAL record is even flushed to local disk | Recently committed transactions, even with no replica involved at all |
| `local` | The local WAL flush to disk on the primary only | Anything not yet replicated to a standby |
| `remote_write` | A synchronous standby has *received* the WAL (written to its OS, not necessarily flushed) | Data if the standby crashes before its own OS flush |
| `on` (the default with a sync standby) | A synchronous standby has flushed the WAL to its own durable storage | Nothing, under a single-standby failure |
| `remote_apply` | A synchronous standby has flushed *and replayed* the WAL, so a query against the standby would immediately see the committed data | Nothing, and eliminates the brief window where a promoted standby might not yet reflect its own most recent received WAL |

`off` is a legitimate, deliberate choice for workloads where a handful of the most recent
transactions being lost on an ungraceful crash is genuinely acceptable in exchange for
materially lower write latency (a high-volume metrics/logging table is the common real
case) — the point isn't that `off` is wrong, it's that using it without having deliberately
decided the durability trade-off is acceptable is the actual mistake.

### Cascading replication

A replica can itself be the WAL source for another, downstream replica, rather than every
replica connecting directly to the primary. This matters operationally once a replica fleet
gets large: it spreads the network/CPU cost of serving the WAL stream across multiple nodes
instead of concentrating all of it on the primary, at the cost of the downstream replica
being one additional hop (and therefore slightly more lag) behind the true primary.

## High-availability orchestration: why failover needs a coordinator, not a script

A naive HA setup — "if the standby can't reach the primary, promote itself" — recreates
[`production-and-scaling.md`](production-and-scaling.md#adjacent-failure-mode-concepts-worth-knowing)'s
split-brain scenario almost immediately: a standby that can't reach the primary due to a
network partition, rather than an actual primary failure, will promote itself while the
original primary — still healthy, just unreachable from the standby specifically — keeps
accepting writes from application servers that can still reach it. Two primaries, diverging
independently, with no way to merge the result once the network heals.

The tools that solve this properly all share the same underlying idea: **failover decisions
need a single, externally-agreed-upon source of truth about who the leader is**, not a
decision each node makes unilaterally based on its own limited view of the network.

- **Patroni** — the current standard for self-managed PostgreSQL HA. Delegates leader
  election to an external, proven distributed consensus store (etcd, Consul, or ZooKeeper) —
  Patroni itself doesn't invent its own consensus protocol; it uses one that's already
  battle-tested for exactly this problem. Every node continuously checks in with the
  consensus store; a standby is only allowed to promote itself once it can prove, via the
  consensus store, that it genuinely holds the leader lock — which a network-partitioned
  node specifically cannot do, closing the exact hole that causes split-brain in a naive
  setup.
- **repmgr** — lighter-weight, doesn't require running a separate consensus store, and is
  correspondingly easier to operate for smaller deployments — but its failover decision-making
  is weaker precisely because it lacks that same external, agreed-upon source of truth,
  making it comparatively more exposed to split-brain-shaped failure modes under a genuine
  network partition.
- **pgpool-II** — adds connection pooling and basic query load-balancing on top of a
  Postgres cluster; its built-in automatic failover capability exists but is generally
  considered less robust than Patroni's for the same reason repmgr is — treat pgpool
  primarily as a pooling/routing layer, and pair it with a dedicated HA tool rather than
  relying on it as the HA mechanism by itself.

## Major version upgrades

- **`pg_upgrade`** — the standard in-place upgrade tool. It doesn't dump and reload actual
  data (which would be slow at scale); when the on-disk page format is compatible between
  the two versions, it can operate in `--link` mode, hard-linking the existing data files
  into the new version's data directory rather than copying them — a dramatic speedup. Its
  real cost is dominated by the **catalog** (the number of tables/indexes/objects, not the
  amount of data in them), which is why two databases with wildly different data sizes but a
  similar number of objects can take a similar amount of downtime to upgrade — a
  non-obvious, frequently-surprising fact worth planning around explicitly rather than
  estimating downtime from data volume alone. It still requires a maintenance window; the
  database is offline for the duration.
- **Logical-replication-based upgrade** — for a near-zero-downtime upgrade of a large,
  continuously-written production database: stand up a new instance running the target
  PostgreSQL version, use logical replication (see
  [`production-and-scaling.md`](production-and-scaling.md#zero-downtime-migration-of-a-live-actively-written-table)
  for the same underlying mechanism applied to a single-table migration) to replicate live
  data into it, let it fully catch up, then cut application traffic over. More moving parts
  and operational complexity than `pg_upgrade`, but the downtime is reduced to the time it
  takes to redirect traffic, not the time it takes to upgrade the whole database in place.

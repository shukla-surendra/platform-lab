How PostgreSQL physical streaming replication is actually set up and how it works underneath -
independent of Docker. Every step below is the same whether the primary and standby are two
containers, two VMs, or two bare-metal boxes on a rack.

## The idea

Every write on the primary is first recorded in the **WAL (write-ahead log)** before it's applied
to the actual data files - that's how Postgres survives a crash. Streaming replication just ships
that same WAL, record for record, to another Postgres process (the **standby**) which replays it
against its own copy of the data files. The standby ends up in the same state as the primary, a
few milliseconds behind.

```
   PRIMARY                                   STANDBY
 ┌──────────────┐                         ┌──────────────┐
 │  client write │                         │              │
 │      │        │                         │              │
 │      ▼        │                         │              │
 │  WAL record    │   WAL sender  ──────►  │  WAL receiver │
 │  appended to    │   process              │   process     │
 │  pg_wal/        │                        │      │        │
 │      │          │                        │      ▼        │
 │      ▼          │                        │  startup      │
 │  applied to      │                        │  process      │
 │  heap/index files │                        │  replays WAL  │
 │                   │                        │  into its own │
 │                   │                        │  heap/index   │
 └──────────────┘                         └──────────────┘
```

Two Postgres background processes make this happen: **walsender** on the primary (one per
connected standby) and **walreceiver** on the standby (one, talking to whichever primary it's
following).

## Step 1 - turn on WAL shipping on the primary

`postgresql.conf` on the primary:

```
wal_level = replica          # 'replica' (or 'logical') writes enough WAL to replay on another node
max_wal_senders = 10         # how many walsender processes / concurrent standbys allowed
max_replication_slots = 10   # ceiling on replication slots (see step 5)
hot_standby = on             # lets a standby accept read-only queries while replaying
```

`wal_level = minimal` is not enough - it strips out information not needed for crash recovery on
the same node, which is exactly the information a standby needs to replay WAL on a *different*
copy of the files. This is the one setting that requires a primary restart; the rest can often be
reloaded.

## Step 2 - give the standby a way to authenticate

A dedicated role with the `REPLICATION` attribute - not a superuser, just this one privilege:

```sql
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'replpass';
```

And an entry in `pg_hba.conf` so that role is allowed to open a *replication* connection (a
special libpq connection mode, distinct from a normal SQL connection) from the standby's address:

```
# TYPE  DATABASE     USER         ADDRESS          METHOD
host    replication  replicator   10.0.0.0/24       md5
```

`DATABASE` here is the literal keyword `replication`, not a real database name - the replication
protocol doesn't connect "to" a database, it streams WAL for the whole cluster.

## Step 3 - clone the primary's data directory onto the standby

A standby can't replay WAL against nothing - it needs a byte-for-byte starting copy of the
primary's data directory, taken at a *specific, known point* in the WAL stream, so replay can pick
up exactly where the copy left off. That's what `pg_basebackup` does:

```
pg_basebackup -h primary-host -U replicator -D /var/lib/postgresql/data -Fp -Xs -P -R
```

- `-D` - destination directory, becomes the standby's `PGDATA`.
- `-Fp` - plain format (a real directory tree, not a single tarball).
- `-Xs` - stream the WAL generated *during* the backup alongside it, so the copy is immediately
  self-consistent even if the backup takes a while on a busy primary.
- `-P` - progress output.
- `-R` - the important one: writes `standby.signal` and appends `primary_conninfo` (and
  `primary_slot_name`, if `-S` was given) into `postgresql.auto.conf` on the standby. This is what
  turns a plain copy of the data directory into a standby that knows where to reconnect.

Internally, `pg_basebackup` puts the primary into backup mode, copies every file under `PGDATA`
(and each tablespace) while the primary keeps taking writes, then takes it out of backup mode.
The copy is not transactionally consistent on its own - it's consistent *once WAL from the backup
window is replayed on top of it*, which is exactly what the standby does the moment it starts.

## Step 4 - mark the copied directory as a standby

Two files control this, both usually written for you by `-R` above:

- **`standby.signal`** - an empty file in `PGDATA`. Its mere presence is the switch: on startup,
  Postgres sees it and enters standby mode instead of normal primary startup. (Before Postgres 12
  this was a `standby_mode = on` line inside `recovery.conf`; that file's gone, folded into
  `postgresql.conf` / `postgresql.auto.conf` plus this signal file.)
- **`primary_conninfo`** - a libpq connection string (host, port, user, password/sslmode) telling
  the standby's walreceiver where to connect: `primary_conninfo = 'host=primary-host port=5432 user=replicator password=replpass'`.

## Step 5 - (optional but usual in practice) pin WAL with a replication slot

Without a slot, the primary only keeps as much old WAL as `wal_keep_size` allows. If a standby is
down or lagging past that, the primary can recycle WAL the standby still needs - the standby is
now unrecoverable via streaming and has to be rebuilt from a fresh base backup.

A **replication slot** is a bookmark on the primary that says "don't recycle WAL past the point
this specific standby has confirmed receiving," tracked per-slot regardless of whether the standby
is currently connected:

```sql
SELECT pg_create_physical_replication_slot('standby1_slot');
```

and on the standby, `primary_slot_name = 'standby1_slot'` in `postgresql.auto.conf` (or pass
`-S standby1_slot` to `pg_basebackup -R`, which does both sides at once). The cost is symmetric:
now a permanently-down standby makes the primary's `pg_wal` grow without bound instead of the
standby falling behind, so slots need monitoring (`pg_replication_slots`), not just standbys.

## Step 6 - start the standby, and what happens on boot

1. Postgres starts, reads `PGDATA`, sees `standby.signal` → enters standby/recovery mode instead
   of normal startup.
2. It first replays whatever WAL is already present locally (from the `-Xs` stream captured during
   the base backup) to reach a **consistent state** - the exact point the base backup was taken.
3. It opens a replication connection to `primary_conninfo` and starts the **walreceiver** process.
4. The walreceiver asks the primary to start streaming from the LSN (log sequence number) the
   standby last replayed. On the primary, a matching **walsender** process wakes up and begins
   pushing WAL records over that connection as they're generated - not polling, the primary
   actively pushes on every WAL flush.
5. The standby's **startup process** continuously replays incoming WAL against its own heap/index
   files, in the same order the primary applied it.
6. Once caught up, this is steady state: every commit on the primary produces WAL, which streams
   to the standby in near real time and gets replayed, keeping the standby a few milliseconds
   behind.

While all this is happening, `hot_standby = on` (step 1) lets client sessions run read-only queries
against the standby concurrently with replay - reads see a consistent snapshot that's simply a bit
older than the primary's.

## Step 7 - async vs sync

By default this is **asynchronous**: the primary commits and returns to the client as soon as the
WAL is written locally, without waiting for any standby to confirm. A crash on the primary between
that local commit and the standby receiving the WAL loses the last transaction(s) on failover.

Setting, on the primary:

```
synchronous_standby_names = 'FIRST 1 (standby1, standby2)'
```

(where `standby1`/`standby2` are each standby's `application_name`, set via `primary_conninfo`)
makes commits **synchronous**: the primary blocks the client's `COMMIT` until at least one of the
named standbys confirms it has received (or written/flushed/applied, depending on
`synchronous_commit`) the WAL. This trades commit latency for a guarantee that a promoted standby
never loses an acknowledged transaction. With more than one standby listed you can also express
quorum, e.g. `ANY 1 (standby1, standby2)` vs requiring a specific one.

## Step 8 - watching it run

On the primary, one row per connected standby:

```sql
SELECT client_addr, application_name, state, sync_state, sent_lsn, write_lsn, flush_lsn, replay_lsn
FROM pg_stat_replication;
```

`sent_lsn` vs `replay_lsn` on a given row is exactly how far that standby is lagging, in WAL bytes.

On the standby:

```sql
SELECT pg_is_in_recovery();                 -- true on any standby
SELECT status, received_lsn, latest_end_lsn -- walreceiver's own view
FROM pg_stat_wal_receiver;
```

## Step 9 - failover (the reason any of this exists)

If the primary dies, a standby is promoted:

```
pg_ctl promote -D /var/lib/postgresql/data
```

This removes `standby.signal`, ends recovery, and the standby starts accepting writes as a new
primary, on a new **timeline** (Postgres increments a timeline ID every promotion so it can tell
WAL histories that diverged after a failover apart). Any other standbys that were following the
old primary need to be repointed (`primary_conninfo`) at the new one, and will need their WAL
history reconciled with the new timeline - either they're close enough that timeline-following
streaming handles it automatically, or they need rebuilding from a fresh base backup. Postgres
itself does not pick a new primary for you; that orchestration (detecting the failure, choosing
which standby is most caught-up, promoting it, repointing the rest) is what tools like Patroni,
repmgr, or a cloud provider's managed layer exist to automate.

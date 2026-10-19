Streaming physical replication: one primary, two async read replicas.

```
docker compose up -d
```

The primary runs with `wal_level=replica`, `max_wal_senders=10`, `max_replication_slots=10`. An
init script (`primary/init-replica-user.sh`) creates a `replicator` role with the `REPLICATION`
attribute and opens `pg_hba.conf` for replication + normal connections from the replica's network.

Each replica has no data of its own. `replica/replica-entrypoint.sh` runs before Postgres starts:
if `PGDATA` is empty it takes a base backup from the primary with `pg_basebackup -R`, which both
copies the primary's data directory and writes `standby.signal` + `primary_conninfo` for it. Only
then does it hand off to the normal `docker-entrypoint.sh postgres`. `replica1` and `replica2` are
two independent services running that same script against the same primary - nothing links them
to each other, they just both point `-h primary`.

```
docker exec -it pg-primary psql -U postgres -d replica_lab
docker exec -it pg-replica1 psql -U postgres -d replica_lab
docker exec -it pg-replica2 psql -U postgres -d replica_lab
```

```
replica_lab=# SELECT client_addr, state, sync_state, replay_lsn FROM pg_stat_replication ORDER BY client_addr;
 client_addr |   state   | sync_state | replay_lsn
-------------+-----------+------------+------------
 172.19.0.3  | streaming | async      | 0/9000000
 172.19.0.4  | streaming | async      | 0/9000000
(2 rows)
```

Write on the primary, read it back on the replica:

```sql
CREATE TABLE accounts (id serial PRIMARY KEY, name text, balance numeric(12,2));
INSERT INTO accounts (name, balance) VALUES ('alice', 100), ('bob', 250);
```

```
replica_lab=# SELECT * FROM accounts ORDER BY id;
 id | name  | balance
----+-------+---------
  1 | alice |  100.00
  2 | bob   |  250.00
(2 rows)
```

Both replicas are hot standbys - readable, but reject writes - and both see every row written on
the primary:

```
replica_lab=# SELECT * FROM accounts ORDER BY id;   -- on replica1 and replica2, same result
 id | name  | balance
----+-------+---------
  1 | alice |  100.00
  2 | bob   |  250.00
(2 rows)

replica_lab=# INSERT INTO accounts (name, balance) VALUES ('carol', 50);
ERROR:  cannot execute INSERT in a read-only transaction
```

```
replica_lab=# SELECT pg_is_in_recovery();
 pg_is_in_recovery
--------------------
 t
(1 row)
```

This setup streams WAL without replication slots, so if either replica is down long enough for the
primary to recycle WAL it needs, that replica falls behind for good and has to be rebuilt from a
fresh base backup. A named slot per replica (`pg_basebackup -R -S <name>` plus
`CREATE_REPLICATION_SLOT` on the primary) pins the WAL the primary must retain for that specific
standby, at the cost of primary disk filling up if the standby stays down. `max_wal_senders=10` and
`max_replication_slots=10` on the primary are the ceiling on how many replicas like this it can
serve at once - two is well under that.

Async vs sync: this lab uses async replication (the default) - the primary commits without waiting
for either replica to acknowledge, so a crash on the primary right after commit can lose the last
transaction(s). Setting `synchronous_standby_names` on the primary (e.g. `'FIRST 1 (replica1, replica2)'`)
makes it wait for at least one named replica to confirm before a commit returns, trading latency for
zero data loss on failover - and with two replicas you can require quorum from either one, not just
a single fixed standby.

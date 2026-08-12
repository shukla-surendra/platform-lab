# Redis

**Category:** in-memory data store (cache, message broker, primitive toolkit)

## What it is

An in-memory key-value store — but "key-value" undersells it. Every
value has a *type* (string, hash, list, set, sorted set, and more), and
each type ships its own set of atomic operations. That's the real
reason Redis shows up everywhere in system design: it isn't just a
cache with a GET/SET API, it's a small toolbox of server-side data
structures, each one a genuine building block for a specific class of
problem — a sorted set alone directly *is* a leaderboard, a sliding-window
rate limiter, and a priority queue, without you reimplementing any of
those on top of a plain key-value store.

Everything below was built and verified against Redis 7.4 running in
Docker on this machine — every command, every script, every replication
check actually ran.

## Running it

```bash
cd mlops_aiops/docs/tools/redis
docker compose up -d
```

This starts two containers: `redis-lab-primary` (port `16379` on the
host) and `redis-lab-replica` (replicating from the primary, no
published port — reach it via `docker exec` or from another container on
the same compose network). Tear down with `docker compose down -v` (the
`-v` also drops the primary's persisted data volume).

```bash
docker exec redis-lab-primary redis-cli PING
# PONG
```

Every command below runs the same way: `docker exec redis-lab-primary
redis-cli <COMMAND>`. If you have `redis-cli` installed locally instead,
`redis-cli -p 16379 <COMMAND>` reaches the same primary directly.

## The data structures, hands-on

### Strings — the default, and counters

```
$ docker exec redis-lab-primary redis-cli SET user:1:name ana
OK
$ docker exec redis-lab-primary redis-cli GET user:1:name
ana
$ docker exec redis-lab-primary redis-cli SET counter 10
OK
$ docker exec redis-lab-primary redis-cli INCR counter
11
```

`INCR`/`INCRBY`/`DECR` are **atomic** — the read-modify-write happens
entirely inside Redis's single-threaded command execution, so two
clients incrementing the same counter concurrently never lose an update
the way a naive "GET, add 1 in your app, SET" round trip would under a
race. This atomicity is the actual mechanism behind rate limiters,
view counters, and inventory decrements — not a side detail.

Expiry attaches to *any* key, string or otherwise:

```
$ docker exec redis-lab-primary redis-cli SET session:abc user_1 EX 30
OK
$ docker exec redis-lab-primary redis-cli TTL session:abc
(integer) 30
```

`EX 30` = expire in 30 seconds; `PX` is the millisecond version. This is
the entire mechanism behind Redis-as-a-session-store: write the session,
attach a TTL matching the session lifetime, and expired sessions clean
themselves up with no separate reaper process.

### Hashes — an object, not a whole extra key per field

```
$ docker exec redis-lab-primary redis-cli HSET user:1 name ana age 32
(integer) 2
$ docker exec redis-lab-primary redis-cli HGETALL user:1
name
ana
age
32
```

The alternative — separate keys `user:1:name`, `user:1:age` — works but
means "delete this user" is now N separate `DEL` calls instead of one,
and there's no atomic "give me the whole object" read. A hash groups
related fields under one key with one TTL, one delete, one fetch.

### Lists — queues, via push/pop from either end

```
$ docker exec redis-lab-primary redis-cli RPUSH queue:jobs job1 job2
(integer) 2
$ docker exec redis-lab-primary redis-cli LPUSH queue:jobs job0
(integer) 3
$ docker exec redis-lab-primary redis-cli LRANGE queue:jobs 0 -1
job0
job1
job2
```

`RPUSH` (right/tail) + `LPOP` (left/head) is a FIFO work queue.
`BLPOP`/`BRPOP` are the blocking versions — a worker calls `BLPOP
queue:jobs 0` and the connection just waits (instead of polling) until
something is pushed, which is exactly the "simple job queue" Redis is
commonly reached for before reaching for a dedicated broker like
RabbitMQ or Kafka.

### Sets — uniqueness and set algebra, server-side

```
$ docker exec redis-lab-primary redis-cli SADD tags:post1 rust systems
(integer) 2
$ docker exec redis-lab-primary redis-cli SADD tags:post2 rust web
(integer) 2
$ docker exec redis-lab-primary redis-cli SINTER tags:post1 tags:post2
rust
```

`SINTER`/`SUNION`/`SDIFF` compute set algebra *inside Redis*, without
pulling both sets over the network into your application first — worth
naming as a real advantage when the sets are large: the computation
happens where the data already lives.

### Sorted sets — the one to actually understand cold

```
$ docker exec redis-lab-primary redis-cli ZADD leaderboard 2200 bo 1500 ana
(integer) 2
$ docker exec redis-lab-primary redis-cli ZREVRANGE leaderboard 0 -1 WITHSCORES
bo
2200
ana
1500
```

A sorted set is a set where every member also has a floating-point
**score**, and Redis keeps the whole structure ordered by that score at
all times (internally: a skip list plus a hash map, giving O(log N)
insert/update/rank and O(log N + M) range reads). This single structure
is the mechanism behind three different interview-favorite patterns —
worked through in full, with the reasoning for *why* the sorted set is
the right primitive for each, in
[`fundamentals/system_design_foundation/00_prerequisite_concepts/25_redis_as_a_system_design_primitive.md`](../../../../fundamentals/system_design_foundation/00_prerequisite_concepts/25_redis_as_a_system_design_primitive.md):

- **Leaderboards** — the score IS the rank; `ZREVRANGE`/`ZREVRANK` are
  direct reads, no sorting-on-read over the whole player base.
- **Sliding-window rate limiters** — score the member by its own
  request timestamp; `ZREMRANGEBYSCORE` evicts anything outside the
  window, `ZCARD` counts what's left.
- **Priority queues / delayed jobs** — score by "ready at" timestamp or
  priority; `ZRANGEBYSCORE key -inf now` pulls everything due now.

## Persistence: RDB and AOF, actually inspected

```
$ docker exec redis-lab-primary redis-cli CONFIG GET save
save
"60 1"
$ docker exec redis-lab-primary redis-cli CONFIG GET appendonly
appendonly
"yes"
$ docker exec redis-lab-primary redis-cli BGSAVE
Background saving started
$ docker exec redis-lab-primary ls /data/
appendonlydir
dump.rdb
```

Two independent, combinable persistence mechanisms, and the trade-off
between them is the actual interview-worthy content, not just "Redis can
save to disk":

- **RDB (`dump.rdb`)** — a point-in-time binary snapshot, taken on a
  schedule (`save 60 1` here means "snapshot if at least 1 key changed
  in the last 60 seconds") or on demand (`BGSAVE`, forked so it doesn't
  block the main event loop). Compact, fast to restart from — and loses
  everything written since the last snapshot if the process dies.
- **AOF (`appendonlydir/`)** — every write command is logged, and replayed
  in order on restart. `appendonly yes` here means every write since
  the container started is durable, not just the last snapshot. Slower
  to restart from (replaying a long log takes longer than loading one
  binary blob) and the file grows without bound until Redis
  periodically rewrites/compacts it in the background.

Production systems commonly run both: AOF for durability, RDB snapshots
for fast recovery and portable backups — exactly the config this
compose file starts with.

## Replication: primary/replica, watched live

```bash
docker exec redis-lab-primary redis-cli SET greeting "hello from primary"
docker exec redis-lab-replica redis-cli GET greeting
# hello from primary   <- propagated automatically

docker exec redis-lab-replica redis-cli INFO replication | grep master_link_status
# master_link_status:up

docker exec redis-lab-replica redis-cli SET blocked nope
# (error) READONLY You can't write against a read only replica.
```

All three lines above were run against this exact compose setup. The
replica rejecting a direct write isn't a bug to work around — it's the
whole point: replicas exist to scale *reads* and provide failover
targets, and allowing direct replica writes would mean the primary could
silently diverge from what its replicas believe is true. (Redis
replication is asynchronous by default — a write is acknowledged to the
client the instant the primary applies it, before any replica has
necessarily received it. That's the same sync-vs-async replication trade
covered in [Part 2 of the prerequisite-concepts
series](../../../../fundamentals/system_design_foundation/00_prerequisite_concepts/02_data_and_consistency.md#sync-vs-async-replication-the-same-fsync-trade-off-at-cluster-scale)
— faster writes, at the cost of a real window where a primary failure
loses the last, not-yet-replicated write.)

## Pub/Sub: fire-and-forget messaging

```bash
docker exec redis-lab-primary redis-cli SUBSCRIBE notifications &
docker exec redis-lab-primary redis-cli PUBLISH notifications "deploy started"
# 1                              <- one subscriber received it
```

Redis pub/sub delivers a message to whoever is subscribed *at the
moment it's published* — there is no backlog, no persistence, no replay
for a subscriber that connects a second late. That's a genuine,
deliberate limitation, not an oversight: it's the right tool for
ephemeral fan-out (cache-invalidation notices to multiple app servers,
live dashboard updates) and the *wrong* tool the moment a message must
survive a subscriber being briefly offline — that's what a real message
queue (Kafka, RabbitMQ, or Redis's own **Streams** type, which *does*
persist and support consumer groups) is for.

## When it breaks: production scenarios

The commands above are Redis working as intended.
[`production-scenarios.md`](production-scenarios.md) covers the other half — memory
fragmentation and OOM surprises, why `DEL` on a big key blocks everyone, replication buffer
overflows forcing a full resync, `CROSSSLOT` errors and hash tags, cache penetration/avalanche
(distinct from stampede), and why keyspace notifications are lossy by construction — each
one explained by mechanism and checked against a live instance, not just named.

## Runnable examples

Each script in [`examples/`](examples/) was run against this exact
compose setup and its asserted expectations passed:

| Script | Pattern | Redis primitive |
|---|---|---|
| [`cache_aside.py`](examples/cache_aside.py) | Cache-aside (check cache, fall through on miss, populate) | `GET` / `SET ... EX` |
| [`sliding_window_rate_limiter.py`](examples/sliding_window_rate_limiter.py) | Rate limiting by request count per rolling window | Sorted set (`ZADD`/`ZREMRANGEBYSCORE`/`ZCARD`) |
| [`leaderboard.py`](examples/leaderboard.py) | Ranked scoreboard, live rank + top-N lookups | Sorted set (`ZADD`/`ZREVRANGE`/`ZREVRANK`) |
| [`distributed_lock.py`](examples/distributed_lock.py) | Mutual exclusion across processes, safe release | `SET NX PX` + Lua compare-and-delete |

```bash
pip install redis
export REDIS_HOST=localhost REDIS_PORT=16379
python3 examples/cache_aside.py
```

## What it's used for, and where the theory lives

The *why* behind each pattern above — cache placement strategies,
eviction policies, cache stampede, the sorted-set-as-leaderboard/rate-
limiter/priority-queue derivations, and why the multi-instance Redlock
distributed-lock algorithm is genuinely contested rather than a settled
default — is covered at interview depth in:

- [`15_caching.md`](../../../../fundamentals/system_design_foundation/00_prerequisite_concepts/15_caching.md) —
  caching patterns and invalidation in general (not Redis-specific).
- [`25_redis_as_a_system_design_primitive.md`](../../../../fundamentals/system_design_foundation/00_prerequisite_concepts/25_redis_as_a_system_design_primitive.md) —
  Redis's own data structures as system-design building blocks.
- [`system_design_practice/05_design_distributed_cache/tutorial.md`](../../../../fundamentals/system_design_practice/05_design_distributed_cache/tutorial.md) —
  Redis Cluster sharding (hash slots) at scale.
- [`system_design_practice/07_design_rate_limiter_at_scale/tutorial.md`](../../../../fundamentals/system_design_practice/07_design_rate_limiter_at_scale/tutorial.md) —
  why "one Redis instance, one counter" breaks down at real scale.

This README stays hands-on and operational on purpose — commands you can
run, output you can check against what's shown here. The linked docs are
where the trade-offs and "why this and not X" reasoning live.

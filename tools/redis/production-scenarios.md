# Redis in Production: Scenarios Worth Understanding Cold

Everything in [`README.md`](README.md) is Redis working as intended. This doc is the other
half: the specific ways it breaks, degrades, or surprises people running it for real — each
one explained by mechanism, not just named. Several of the concrete facts below (config
defaults, error text, slot behavior) were checked directly against a running Redis 7.4
instance rather than assumed; where that matters, it's noted inline.

## Memory

### Fragmentation inflates real memory past your logical dataset size

Redis's allocator (jemalloc) doesn't always hand freed memory back to the OS cleanly —
especially after a workload that repeatedly changes value sizes (grow a hash, shrink it,
grow a different one). The result: Redis's actual process memory (`used_memory_rss`) can sit
well above what the stored data logically accounts for (`used_memory`).

**How you'd notice it**: `INFO memory`'s `mem_fragmentation_ratio` field —
`used_memory_rss / used_memory`. Confirmed present in a live instance:

```
$ redis-cli INFO memory | grep -E "used_memory:|used_memory_rss:|mem_fragmentation_ratio"
used_memory:1044488
used_memory_rss:8847360
mem_fragmentation_ratio:8.79
```

(That 8.79 is from a nearly-empty instance, where Redis's own baseline process overhead
dominates a tiny dataset — not representative of a loaded system. On a real, populated
instance, Redis's own guidance treats a ratio comfortably above 1.0 — commonly cited as 1.5
or higher — as worth investigating.) A ratio meaningfully above 1.0 means the OOM killer can
end the process well before your logical dataset would justify it — the metric to check
*before* assuming "we just need more RAM."

**The fix**: `MEMORY PURGE` (Redis 4.0+, forces jemalloc to release what it can back to the
OS) as a stopgap; for a workload that structurally causes heavy fragmentation (constantly
resizing large values), sizing `maxmemory` with real fragmentation headroom rather than
against the raw dataset size, and watching the ratio in monitoring rather than only
`used_memory`.

### `noeviction` is the actual default — writes fail before anything gets evicted

Verified directly:

```
$ redis-cli CONFIG GET maxmemory-policy
maxmemory-policy
noeviction
$ redis-cli CONFIG GET maxmemory
maxmemory
0
```

Two separate facts stack here. First, `maxmemory` itself defaults to `0` — unlimited — so
this scenario only bites once someone (or a managed service like ElastiCache, which
typically *does* set a cap) actually configures a memory ceiling. Second, once that ceiling
exists, the default eviction policy is `noeviction` — hit the limit, and Redis doesn't evict
anything to make room. It starts **rejecting writes** with an OOM error, while reads keep
working normally. A service that never load-tested past its cache's memory ceiling discovers
this in production as "writes are failing but the health check is green" — reads look fine
because reads never needed the room.

**The fix**: if the intent is genuinely "cache, evict the coldest thing when full," that has
to be chosen explicitly — `allkeys-lru` or `allkeys-lfu`. `volatile-lru`/`volatile-lfu` only
evict keys that have a TTL set; if most keys in the dataset never got one, that policy has
nothing to evict either, and behaves like `noeviction` in practice despite the name
suggesting otherwise.

### `BGSAVE`'s fork can transiently double memory, at the worst possible moment

`BGSAVE` (and a replica's initial full sync) works by forking the process — the child writes
a stable point-in-time snapshot while the parent keeps serving live writes. Every memory page
the parent modifies *during that window* gets copy-on-written: duplicated, not shared,
between parent and child. A high write-rate workload during the fork can push memory well
above steady-state for the snapshot's duration.

**Why it's a real production story, not just theory**: this is exactly how a *scheduled
backup* becomes the outage — everything's within budget until a `BGSAVE` (cron-scheduled, or
triggered by a replica attaching and needing a full sync) lands during a traffic spike, and
the copy-on-write overhead is what actually pushes the box into OOM, not the traffic itself.

**The fix**: size `maxmemory` with real fork/COW headroom, not just the dataset — a common
rule of thumb is leaving enough spare RAM to tolerate a meaningful fraction of the dataset
being rewritten during a snapshot window; stagger `BGSAVE` schedules and replica attachment
away from known traffic peaks where operationally possible.

## The single-threaded core, beyond "one slow command blocks everyone"

### `DEL` on a big value blocks like any other command — `UNLINK` doesn't

Deleting a key is O(size of the value) — freeing a set with millions of members takes real,
measurable time, and that time runs on the same single thread as every other command.
`UNLINK` reclaims the memory on a background thread instead, so the command returns
immediately. Verified:

```
$ redis-cli SET bigkey hello
OK
$ redis-cli UNLINK bigkey
(integer) 1
$ redis-cli EXISTS bigkey
(integer) 0
```

**The fix, stated as a habit**: if a key *could plausibly* be big — anything user-generated,
anything that grows unboundedly — `UNLINK` should be the reflex over `DEL`, not a special
case reached for only after a blocking-delete incident.

### Even background expiration can block, unless you opt out of it

Also verified — this one is easy to miss:

```
$ redis-cli CONFIG GET lazyfree-lazy-expire
lazyfree-lazy-expire
no
```

By default, when Redis's active-expire cycle (or a lazy expire-on-access) decides a key is
gone, freeing that key's memory happens **synchronously**, on the main thread — same cost
model as `DEL`. A large expired value (a big cached blob, a huge sorted set past its TTL)
frees on the same single thread every other command is waiting behind. Setting
`lazyfree-lazy-expire yes` (and its siblings — `lazyfree-lazy-eviction`,
`lazyfree-lazy-server-del`) moves that specific class of delete onto Redis's background
thread pool, the same mechanism `UNLINK` uses explicitly.

## Replication and failover

### The replication backlog is tiny by default — a replica that falls behind forces a full resync

```
$ redis-cli CONFIG GET repl-backlog-size
repl-backlog-size
1048576
```

One megabyte, by default. That buffer holds the recent stream of writes a temporarily
disconnected replica can catch up on incrementally when it reconnects. Under real write
volume, 1MB is easy to exceed if a replica is disconnected for more than a few seconds (a
network blip, a GC pause, a restart). Once the buffer has wrapped past what the replica still
needs, incremental catch-up is no longer possible — the only recovery is a **full resync**:
the entire dataset, streamed again, which is itself expensive and can trigger the fork/COW
memory spike above on the primary.

**The failure mode this creates**: a replica with marginal network conditions can end up in a
resync loop — falls behind, forces a full resync, falls behind again *during* the resync
(because a full resync takes real time, during which more writes accumulate), repeats. From
the outside this looks like "replication is just broken," when the actual root cause is an
undersized backlog for the write rate.

**The fix**: size `repl-backlog-size` against actual write throughput and realistic
replica-disconnect durations, not the default — this is one of the more commonly
under-tuned settings in a real deployment.

### A network partition can produce two primaries, briefly

If a primary is partitioned from Sentinel (or Cluster's failure-detection gossip) but is
**still reachable by some clients**, Sentinel/Cluster can promote a replica to primary on the
healthy side of the partition — while the original, partitioned-off primary keeps accepting
writes from whatever clients can still reach it directly. Two nodes, both believing they're
the primary, diverging, until the partition heals and one side's writes are reconciled or
discarded.

This isn't a bug — it's the concrete, observable shape of the availability-over-consistency
choice Redis's replication model makes under a partition. It's worth having actually pictured
once: "split-brain" stops being an abstract term the moment you can describe which clients
would still be writing to the stranded primary, and what happens to those writes.

## Cluster-specific

### `CROSSSLOT` errors, and hash tags as the fix

Redis Cluster shards across 16,384 hash slots. A multi-key operation only works if every key
involved lands in the *same* slot. Verified directly (single node, all slots owned):

```
$ redis-cli CLUSTER KEYSLOT "user:42:profile"
(integer) 9133
$ redis-cli CLUSTER KEYSLOT "user:42:settings"
(integer) 4554
$ redis-cli MGET "user:42:profile" "user:42:settings"
(error) CROSSSLOT Keys in request don't hash to the same slot
```

Two keys that obviously belong together, landing in different shards, breaking any
multi-key command that touches both. The fix is a **hash tag** — wrapping the part of the key
that should determine placement in `{}` — which forces only that substring to be hashed:

```
$ redis-cli CLUSTER KEYSLOT "user:{42}:profile"
(integer) 8000
$ redis-cli CLUSTER KEYSLOT "user:{42}:settings"
(integer) 8000
```

Same slot, confirmed. Any keys that need to be touched together in a transaction, a Lua
script, or a multi-key command need this designed in from the start — retrofitting hash tags
onto a running cluster means the keys physically have to move to new slots.

## Cache-pattern failures, distinct from stampede

Two failure shapes that are easy to conflate with cache stampede (one hot key expiring under
concurrent load) but have different causes and different fixes:

**Cache penetration** — repeated requests for a key that doesn't exist in the cache *or* the
underlying database, so every single request bypasses the cache and hits the slow path, every
time, because there's never anything to cache. Often either an attacker deliberately probing
nonexistent IDs to bypass the cache layer, or a buggy client stuck retrying a bad ID forever.
The fix is caching the *negative* result too (a short-TTL "not found" marker), or a Bloom
filter in front of the cache that can cheaply reject an obviously-nonexistent key before it
ever reaches the database.

**Cache avalanche** — many *different* keys expiring at the same moment, not one hot key. The
classic cause is a deploy that warms the entire cache at once with an identical TTL — hours
later, everything expires together, and the resulting wave of simultaneous misses hits the
database as one coordinated spike. The fix is jittering TTLs (`base_ttl +
random(0, jitter)`) so expirations spread out instead of landing in lockstep.

## Notifications and expiration timing

### Expired keys aren't purged the instant they expire

Redis uses **lazy expiration** (a key is actually deleted the next time something touches
it) plus a background **active-expire cycle** that periodically samples a small random batch
of keys carrying a TTL and purges whichever have expired:

```
$ redis-cli CONFIG GET active-expire-effort
active-expire-effort
1
```

(`active-expire-effort` ranges 1-10, trading CPU spent on the cycle against how promptly
expired keys actually get purged.) Practical consequence: `DBSIZE` and reported memory usage
can both be meaningfully inflated by keys that are logically expired but not yet physically
purged — especially with a large keyspace where much of it sees little read traffic (nothing
is touching those keys to trigger lazy expiration, and the active cycle only samples a
fraction each pass).

### Keyspace notifications are opt-in *and* lossy — both facts matter

```
$ redis-cli CONFIG GET notify-keyspace-events
notify-keyspace-events
(empty)
```

Disabled by default — confirmed. Turning it on (to react to `expired` events, a common
pattern for things like cart-abandonment logic) doesn't change the underlying delivery
mechanism: keyspace notifications are published over the same pub/sub system the hands-on
lab's [README already covers as fire-and-forget](README.md#pubsub-fire-and-forget-messaging)
— no persistence, no backlog, no replay. A consumer that's disconnected for even a moment
when a key expires simply never learns it happened. This is a lossy pattern by construction,
not a configuration mistake to fix — if "every expiration must eventually be handled" is a
real requirement, the correct design uses Redis as the *source* of an event that a durable
system (a Stream, a real queue) then delivers reliably, not keyspace notifications as the
delivery mechanism itself.

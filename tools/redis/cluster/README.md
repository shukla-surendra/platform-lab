# Redis Cluster — Sharded Redis, Hands-On and at Interview Depth

A real 6-node Redis Cluster (3 masters, 3 replicas) running in Docker, plus the mechanics
you need to be able to talk through cold in a system design interview: hash slots, the
gossip protocol, failover, live resharding, and the consistency trade-offs that come from
async replication. Every command and number below was run against the exact compose setup
in this folder — nothing here is theoretical.

This is the companion lab for
[`system_design_practice/05_design_distributed_cache/tutorial.md`](../../../../../system_design_practice/05_design_distributed_cache/tutorial.md)
(the interview case-study framing) and
[`25_redis_as_a_system_design_primitive.md`](../../../../../system_design_foundation/00_prerequisite_concepts/25_redis_as_a_system_design_primitive.md)
(why Redis's data structures matter) — this doc is specifically about the *sharding* layer:
what changes once one Redis instance becomes six that have to agree on who owns what.

If you haven't already, [`system_design_foundation/consistent_hashing/`](../../../../../system_design_foundation/consistent_hashing/)
is worth reading first — Redis Cluster's hash slots are a specific, opinionated variant of
that same idea, and the contrast is the fastest way to understand *why* Redis chose slots
over a continuous ring.

## Quickstart

```bash
cd mlops_aiops/docs/tools/redis/cluster
docker compose up -d          # starts 6 redis nodes, auto-forms the cluster, starts a client container
docker compose logs cluster-init   # confirm: "[OK] All 16384 slots covered."

docker exec redis-cluster-client python cluster_basics.py
docker exec redis-cluster-client python crossslot_and_hashtags.py
bash examples/failover_demo.sh

docker compose down -v        # tear down
```

### Why a client container

Each node's `--cluster-announce-ip` is a real Docker-network IP (`172.30.0.11`–`.16`), not
`localhost` — because **`cluster-announce-ip` must be a literal IPv4/IPv6 address**, Redis
rejects a hostname there outright (`FATAL CONFIG FILE ERROR ... Cluster announce IP must be
a valid IPv4 or IPv6 address` — hit this while building this lab; see the commit history of
this file's `docker-compose.yml` for the fix). That means when a client follows a `MOVED`
redirect, it's told to reconnect to `172.30.0.12:7002` — an address only reachable from
*inside* the same Docker network, not from your Mac/Linux host's `localhost`. The `client`
service in `docker-compose.yml` solves this the way a real client would in production
(a VPC-internal service talking to a VPC-internal cluster): it just lives on the same
network. `docker exec redis-cluster-client python <script>.py` runs code there. The node
ports are still mapped to the host (`7001`–`7006`) for `redis-cli -p 700X <command>`
single-node inspection — just not for anything that needs to follow a cross-node redirect.

## The Problem, Precisely

A single Redis instance is bounded by one machine's RAM and one core's throughput (Redis is
single-threaded for command execution — see
[`25_redis_as_a_system_design_primitive.md`](../../../../../system_design_foundation/00_prerequisite_concepts/25_redis_as_a_system_design_primitive.md#the-mechanism-that-makes-that-atomicity-free-a-single-threaded-core)).
Sentinel (Redis's other clustering story) solves *availability* — automatic failover for one
primary/replica set — but does nothing about *capacity*: it's still one primary taking every
write. Redis Cluster solves the actual scaling problem: split the keyspace across N
independent primaries, each running its own single-threaded event loop, so total capacity
scales roughly linearly with node count, while still getting Sentinel-like automatic
failover for each shard individually.

## Hash Slots: A Fixed, Discrete Alternative to a Continuous Ring

**The mechanism**: Redis Cluster doesn't hash a key directly to a node. It hashes every key
to one of exactly **16,384 fixed slots** (`CRC16(key) % 16384`), and separately tracks which
node owns which slots — a plain integer-range-to-node mapping the cluster gossips around,
not a hash-ring position. From this lab's own `cluster-init` run:

```
Master[0] -> Slots 0 - 5460       (5461 slots)  -> 172.30.0.11:7001
Master[1] -> Slots 5461 - 10922   (5462 slots)  -> 172.30.0.12:7002
Master[2] -> Slots 10923 - 16383  (5461 slots)  -> 172.30.0.13:7003
```

**Why 16,384 specifically, not 2^32 or a continuous ring** — three concrete engineering
reasons, not an arbitrary number:

1. **The slot bitmap has to be gossiped in every heartbeat.** Each node's slot ownership is
   sent as a bitmap in cluster-bus messages. A 16,384-bit bitmap is 2KB — cheap to include
   in every gossip packet between every pair of nodes, constantly. A 32-bit hash space would
   need a 512MB bitmap per message, which is a non-starter at any realistic gossip frequency.
2. **Redis's own author has said clusters were never meant to scale past ~1,000 nodes** —
   16,384 gives ~16 slots-per-node of headroom even near that ceiling, comfortably discrete
   without being wastefully huge.
3. **Discrete integer ranges make resharding a bookkeeping operation, not a recompute.**
   Moving load means reassigning *slot numbers* between two nodes — an O(1) metadata update
   for the mapping itself — rather than repositioning points on a continuous ring and
   recomputing which keys now fall in which arc.

**Contrast with [`consistent_hashing/`](../../../../../system_design_foundation/consistent_hashing/)
in this repo**: that implementation places virtual points on a continuous ring and does a
`bisect` to find the next clockwise node — elegant, general-purpose, no coordination needed
between nodes to know the mapping (any client can compute it independently, as long as it
knows the full node list). Redis Cluster instead has a **fixed, small, enumerable set of
partitions** with an explicit owner-per-partition table that the cluster itself maintains
and gossips — closer in spirit to explicit shard assignment than a pure hash ring. The
practical payoff: you can ask *any* node "who owns slot 6000?" and get an authoritative
answer (`CLUSTER KEYSLOT <key>`, `CLUSTER SHARDS`), and migrating slot 6000 is an explicit,
observable, resumable operation on one well-defined unit — not a side effect of one node's
ring position shifting.

## The Gossip Protocol: How 6 Nodes Agree on Cluster State Without a Coordinator

**The problem, precisely**: there's no external coordinator (no ZooKeeper, no etcd) telling
nodes who owns what slot or who's alive. The cluster has to reach and maintain that agreement
entirely among the nodes themselves, cheaply, continuously, while tolerating individual node
failures.

**The mechanism**: every node opens a second TCP port — the **cluster bus**, always
`client-port + 10000` (`7001` client / `17001` bus in this lab) — and continuously exchanges
`PING`/`PONG` gossip messages with a random subset of other nodes, piggybacking each
message with what it currently believes about the rest of the cluster (slot ownership,
which nodes it thinks are up/down, config epochs). Over time this converges the whole
cluster on one shared view without any single node ever talking to all the others directly
on every tick — the same amortized, eventually-consistent propagation strategy gossip
protocols use everywhere (Cassandra, Consul, SWIM-based systems).

**Failure detection has two states, not one**, and this distinction is exactly what makes
failover safe rather than trigger-happy:

- **PFAIL ("possibly failed")** — one node stops getting a timely reply from another
  (`cluster-node-timeout`, 5000ms in this lab) and marks it PFAIL *locally*. This alone
  changes nothing cluster-wide — it's one node's private suspicion.
- **FAIL** — a node's PFAIL becomes cluster-wide FAIL only once a **majority of known
  masters** also report that same node as PFAIL/FAIL within a window (gossiped in their own
  heartbeats). Only a FAIL state triggers failover.

This live in this lab's own failover run (`examples/failover_demo.sh`, killing
`redis-cluster-1` at `172.30.0.11:7001`):

```
[3] 172.30.0.11 (old master) now marked: fail
[4] 172.30.0.15 (was a replica) is now: master
```

**Why require a majority, not just one node's opinion**: a single node's belief that a peer
is down could just as easily mean *that node* has a network problem (it's partitioned away
from an otherwise-healthy peer). Requiring majority agreement is the same core idea as
quorum-based consensus elsewhere — it converts "one observer's suspicion" into "the cluster
as a whole agrees this node is unreachable," which is a much safer bar for triggering an
automatic promotion that a client-visible write is about to depend on.

## Failover: What Actually Happens to the Replica

Once a master is FAILed, **one of its replicas** (there can be several) elects itself:

1. Each replica of the dead master increments its own **epoch** and requests votes from
   every master node it can reach.
2. Masters vote once per epoch, for the first replica that asks — first-past-the-post, not
   "best" replica by any data-freshness metric (though replicas *do* delay their vote
   request briefly, proportional to how stale their own replication offset is, so a replica
   with more up-to-date data gets a head start over a further-behind one).
3. Once a replica collects votes from a majority of masters, it promotes itself, updates the
   slot ownership it now claims via a new config epoch, and gossips that out.

This lab's cluster state after failover (replica `172.30.0.15:7005` promoted to own slots
`0-5460`, the old master `172.30.0.11:7001` now flagged `fail`):

```
569635ab...cc9765 172.30.0.11:7001@17001 master,fail - ...
337b7fb4...7a7f63f7 172.30.0.15:7005@17005 master - 0 ... 7 connected 0-5460
```

And a write against the *new* master, right after promotion, both preserves the old data and
accepts new writes — confirmed live in this lab:

```
GET failover-test-key -> 'written-before-failover'
new write after failover succeeded — cluster is fully writable again
```

**When the old master (`redis-cluster-1`) restarts, it does not reclaim its slots** — it
rejoins as a *replica* of the node that already promoted, because that node's config epoch
is now higher. This is deliberate: without it, two nodes could each believe they own the
same slots at once (a split-brain write conflict) the moment the old master came back before
it heard about the promotion. Also confirmed live:

```
569635ab...cc9765 172.30.0.11:7001@17001 myself,slave 337b7fb4...7a7f63f7 0 ...
```

## The Consistency Trade-Off This Buys: Async Replication, and What Can Go Wrong

**Replication master→replica is asynchronous by default.** A `SET` returns success to the
client as soon as the *master* has applied it — the replica gets it over the replication
link a moment later, not as part of the same round trip. This is a real, nameable data-loss
window: if the master crashes in the gap between "acknowledged the write to the client" and
"replicated it to the replica that gets promoted," that write is gone. This is precisely why
Redis Cluster is **AP, not CP**, in CAP terms
([Part 13 covers this trade-off's general shape](../../../../../system_design_foundation/00_prerequisite_concepts/13_cap_theorem_and_pacelc.md)) —
it favors staying available and accepting writes over guaranteeing every acknowledged write
survives every possible failure.

Two knobs narrow — but don't eliminate — that window:

- **`min-replicas-to-write <N>` / `min-replicas-max-lag <seconds>`**: a master refuses
  writes if it doesn't have at least N replicas connected within that lag bound. This
  doesn't make replication synchronous; it just refuses to accept new writes when the safety
  margin has already degraded, trading some availability back for a smaller loss window.
- **`WAIT <numreplicas> <timeout>`**: a client can block after a write until it's confirmed
  propagated to N replicas — opt-in synchronous behavior per-call, at the cost of latency.

**Cluster-wide, "how many nodes can I lose" also has a hard floor**: since each slot range
lives on exactly one primary (plus its replicas), losing a primary *and every one of its
replicas at once* (not simultaneous unrelated single failures — literally the same
availability-zone or rack going down) loses that slot range's data entirely, and by default
the cluster stops serving traffic at all once `cluster-require-full-coverage` (default: yes)
detects any slot has no reachable owner — an explicit design choice to fail closed rather
than silently serve a cluster with holes in its keyspace.

## Resharding: Moving Slot Ownership Live, Without a Maintenance Window

**The mechanism**: resharding moves whole slots — never individual keys as a top-level
concept — from one node to another, one slot at a time, while the cluster keeps serving
traffic for every other slot the entire time. For one slot being migrated:

1. The source node marks the slot `MIGRATING <target>`; the target marks it
   `IMPORTING <source>`.
2. Keys already in that slot are copied across one at a time (`CLUSTER GETKEYSINSLOT`,
   `MIGRATE` per key) — a live operation the cluster is fully available during.
3. **Mid-migration, a client's request for a key not yet moved gets served normally by the
   source.** A request for a key *already* moved gets an **`ASK`** redirect (not `MOVED`) —
   the crucial distinction being `ASK` is a one-time, this-request-only redirect (the slot
   isn't fully reassigned yet, so the client shouldn't update its long-lived slot cache),
   while `MOVED` (used for normal, already-settled ownership) means "update your slot map
   permanently, this owner is now authoritative."
4. Once every key is moved, ownership of the whole slot flips to the target, and the cluster
   gossips the update — from then on, `MOVED` is what routes to it.

**Why this distinction (`ASK` vs `MOVED`) matters enough to be its own protocol detail**: a
client that treated every redirect as permanent (`MOVED`-style) would cache a slot→node
mapping mid-migration and then send *every future request for that slot* to the target
before migration finished — including keys not yet copied there, which the target doesn't
have. `ASK`'s one-shot semantics keep the client bouncing correctly between source and
target for the whole migration window, without ever needing to know migration is even
in progress.

## Try it yourself: reshard live

```bash
# Move 100 slots from node 1 (172.30.0.11:7001) to node 2 (172.30.0.12:7002)
docker exec -it redis-cluster-1 redis-cli --cluster reshard 172.30.0.11:7001 \
  --cluster-from <node-1-id> --cluster-to <node-2-id> \
  --cluster-slots 100 --cluster-yes
# get node IDs first:
docker exec redis-cluster-1 redis-cli -p 7001 cluster myid
docker exec redis-cluster-2 redis-cli -p 7002 cluster myid
```

Run `cluster_basics.py` again afterward — the key-count split across the three masters
shifts to reflect the new slot boundary, live, with the cluster never having gone down.

## CROSSSLOT and Hash Tags

Covered hands-on in [`examples/crossslot_and_hashtags.py`](examples/crossslot_and_hashtags.py)
— run it and read the assertions, they carry the explanation. The one-paragraph version:
any command touching multiple keys (`MSET`, `MGET`, a Lua script, a `MULTI`/`EXEC`
transaction) requires every key involved to hash to the *same* slot, because the command has
to be served by one node that actually holds all the data. A `{substring}` **hash tag** in a
key forces Redis to hash only that substring, so `{order:1001}:status` and
`{order:1001}:items` collide onto the same slot deliberately — the standard pattern for
"these keys must always be co-located," at the direct cost of losing automatic even
distribution for that key family (every key sharing a hash tag lands on one node, by
design — a hot hash-tag is a self-inflicted hot-key problem).

## Redis Cluster vs. the Alternatives — the Comparison Interviewers Actually Want

| Approach | Solves capacity? | Solves availability? | Coordination needed | Where it fits |
|---|---|---|---|---|
| **Single Redis + Sentinel** | No — one primary takes all writes | Yes — Sentinel quorum promotes a replica on failure | Sentinel processes (separate from the data nodes) | Small-to-medium datasets, availability matters, throughput doesn't need to scale past one core |
| **Redis Cluster** (this lab) | Yes — N independent primaries | Yes — per-shard, same failover idea as Sentinel but built into the data nodes themselves | None external — nodes gossip directly | Default choice once one primary's throughput/RAM is the actual bottleneck |
| **Client-side sharding** (app hashes key → picks connection) | Yes, in principle | No — no automatic failover; app owns detecting a dead shard | None — but *all* coordination logic lives in application code, duplicated per client language/service | Legacy / when you specifically want zero cluster-protocol dependency; loses live resharding, `ASK`/`MOVED`, and cross-shard multi-key safety entirely |
| **Proxy-based (Twemproxy, Envoy w/ Redis filter)** | Yes | Partial — proxy can route around a dead shard, but the proxy itself is a new single point unless it's also made highly available | A proxy tier, kept in sync with shard topology | When you need sharding for a Redis version/deployment that predates or can't run Cluster mode, or want to keep clients simple (proxy hides topology entirely) |

**The interview-ready one-liner**: Sentinel buys you *availability* for one primary;
Cluster buys you *both capacity (via sharding) and availability (per-shard failover)*, at
the cost of every client needing to be slot/redirect-aware (or sit behind a proxy that is).

## Common Interview Questions, Answered Crisply

**"How does Redis Cluster shard data?"** — 16,384 fixed hash slots, `CRC16(key) % 16384`;
each node owns a contiguous or non-contiguous set of slot ranges; a client asks any node
"who owns this slot" (or maintains its own cached slot map) and gets routed directly, or
redirected via `MOVED`/`ASK` if it guesses wrong.

**"What happens when a master dies?"** — its peers detect it (PFAIL → majority-agreed FAIL,
via gossip over the cluster bus), one of its replicas wins a majority vote among masters and
promotes itself, claims the dead master's slots under a new config epoch, and the old master
(if it comes back) rejoins as a replica rather than reclaiming ownership.

**"Is Redis Cluster CP or AP?"** — AP. Replication is asynchronous by default, so there's a
real window where an acknowledged write can be lost on failover; `WAIT` and
`min-replicas-to-write` narrow that window but don't make it synchronous by default. By
further default (`cluster-require-full-coverage`), the cluster refuses to serve *any*
traffic if any slot has no reachable owner — availability is explicitly sacrificed at the
whole-cluster level to avoid silently serving a keyspace with holes in it.

**"How do you add capacity without downtime?"** — resharding: move slot ownership (and the
keys in those slots) from existing nodes to a new one, one slot at a time, with the cluster
serving every other slot throughout. `MIGRATING`/`IMPORTING` mark the slot mid-move; `ASK`
redirects route around it correctly while it's happening.

**"Why can't I `MSET` two arbitrary keys?"** — CROSSSLOT: a multi-key command needs every
key to be servable by one node, and two arbitrary keys almost certainly hash to two
different slots (and possibly two different nodes). Hash tags (`{tag}`) are the fix when
keys genuinely need to be co-located.

**"What's the difference between `MOVED` and `ASK`?"** — `MOVED` means permanent, update
your cached slot map. `ASK` means "this one key is mid-migration, retry it at the target
just this once" — the client must *not* cache an `ASK` redirect as the new permanent owner.

## Files in This Lab

| File | What it is |
|---|---|
| `docker-compose.yml` | 6 Redis nodes (static IPs on a dedicated bridge network — required, since `cluster-announce-ip` must be a real IP), a one-shot `cluster-init` container that runs `redis-cli --cluster create`, and a `client` container for python/redis-cli work that needs to follow cross-node redirects. |
| `examples/cluster_basics.py` | Connects via one seed node, writes 300 keys, shows they land on all 3 masters via hash-slot routing alone. |
| `examples/crossslot_and_hashtags.py` | Reproduces a CROSSSLOT failure, then fixes it with a hash tag and proves both keys land on the same slot/node. |
| `examples/failover_demo.sh` | Kills a live master mid-cluster, watches gossip detect it and a replica promote, confirms data survives and the cluster stays writable, then shows the old master rejoin as a replica. |

# Prerequisite Concepts, Part 25: Redis — Data Structures as System Design Primitives

[Part 24](24_cardinality.md) closed out this series with a piece of shared vocabulary rather
than a mechanism. This part goes back to mechanism, but for a technology this series has
already named repeatedly without ever explaining *why* it keeps coming up: [Part 15 named
Redis as "the near-universal default distributed
cache"](15_caching.md#real-tools-modern-defaults), the [distributed-cache case
study](../../system_design_practice/05_design_distributed_cache/tutorial.md) is literally
titled "Design a Distributed Cache (Redis Cluster)," and the [rate-limiter case
study](../../system_design_practice/07_design_rate_limiter_at_scale/tutorial.md) starts from
"one Redis instance, one counting algorithm" as its given. Every one of those docs treats
Redis-the-cache as the starting point. This part asks the question underneath that: what is
Redis actually built out of, mechanically, that makes it the default answer to caching,
leaderboards, rate limiting, locking, and lightweight pub/sub all at once — four genuinely
different problems, one tool. (A companion hands-on lab —
[`mlops_aiops/docs/tools/redis/`](../../../../mlops_aiops/docs/tools/redis/README.md) — runs
every command and pattern in this doc against a real Redis instance; this doc is the *why*,
that lab is the *how*.)

## In Plain English

A plain key-value store is a wall of labeled lockers — each locker holds one thing, and
opening it is the only operation you get. Redis is closer to a workshop where each locker
comes with its own built-in tool already inside: one locker's "thing" is a number that knows
how to increment itself safely no matter how many people reach for it at once; another's is a
list that already knows how to act like a queue; another's is a set of items that stays
sorted by a score you assign, and can tell you instantly who's in 1st place versus 100th
without you ever running a sort. The value isn't just storage — each value type ships with
its own specialized, atomic operations, done on Redis's own server rather than requiring you
to fetch the raw data and do the work yourself.

## The Problem, Precisely

A generic key-value cache (Memcached is the clean example — [already named as Redis's
simpler sibling in Part 15](15_caching.md#real-tools-modern-defaults)) solves exactly one
problem: get this blob of bytes back quickly, given its key. That's genuinely enough for pure
caching. It stops being enough the moment an application needs to *do something* to the
data structure it's storing — increment a counter without a race, keep a small set of
recent items ranked by score, hand off one job to exactly one of several waiting workers —
because a plain key-value store forces every one of those into a read-modify-write round
trip: fetch the whole blob, change it in your application, write the whole blob back. Under
concurrent access, that round trip is a race condition waiting to happen (two clients read
the same old value, both compute an update from it, the second write silently clobbers the
first). Redis's actual contribution is closing that gap: give the server itself
type-specific operations — `INCR`, `ZADD`, `LPUSH`, `SADD` — so the read-modify-write
happens as one atomic step *inside* Redis, not as three separate steps split across a network
round trip.

## The Mechanism That Makes That Atomicity Free: A Single-Threaded Core

**The problem, precisely**: atomicity usually costs something — a database achieves it with
locks or MVCC machinery ([Part 17 covers exactly this
machinery](17_isolation_and_concurrency_control.md)), and locks mean some requests wait on
others. Redis's commands are atomic essentially for free, and the reason is structural, not
magic.

**The mechanism**: Redis executes commands **one at a time, on a single thread**. There is no
possibility of two commands interleaving mid-execution, because there is only ever one
command actually running against the data at any instant — the "read, modify, write" inside
`INCR` or `ZADD` simply can't be interrupted by another client's command, the same way a
single line of straight-line code in any single-threaded program can't be interrupted by
another function call. Network I/O — accepting new connections, reading incoming requests,
writing responses back — is handled separately (Redis 6+ can parallelize this specific part
across a few I/O threads), but **command execution against the data itself stays
single-threaded**, and that's the part that actually matters for the atomicity guarantee.

**Why it matters practically, both ways**: this is precisely why `INCR counter` is safe under
any amount of concurrent load with zero application-level locking — and precisely why a
single slow command is a real, self-inflicted outage risk. `KEYS *` on a database with
millions of keys, or `SMEMBERS` on a set with a million members, blocks *every other client*
for as long as that one command takes to run, because there is no second thread to serve them
on while the first command executes. This is a genuine, named operational gotcha, not
theoretical — production Redis guidance is built around it: prefer `SCAN` (an
incremental, cursor-based iteration that never blocks the whole server for long) over `KEYS`
in any code path that isn't a one-off debugging session, and be deliberate about which
commands can touch how much data in one call.

## Sorted Sets: One Structure, Three Interview Patterns

**The problem, precisely**: a recurring shape in system design interviews is "maintain a
ranked view over a changing collection, and answer both 'who's in the top N' and 'where does
this specific item rank' quickly, as the underlying values keep changing." A plain list or
array answers neither efficiently without re-sorting on every read.

**The mechanism**: a Redis **sorted set** (`ZADD`/`ZRANGE`/`ZRANK` and friends) is a set
where every member also carries a floating-point **score**, and Redis keeps the whole
structure ordered by that score continuously — internally, a **skip list** (a linked
structure with multiple "express lane" levels, letting a search skip past many elements at
once) paired with a hash map (for O(1) "does this member exist, and what's its current
score" lookups). The combination gives O(log N) insert, update, and rank-lookup, and O(log N
+ M) for reading M consecutive ranked elements — genuinely fast at any collection size that
fits in memory, and *maintained continuously on every write*, not recomputed on read.

That one structure is the actual mechanism behind three separate interview-favorite patterns:

- **Leaderboards.** The score *is* the rank. `ZREVRANGE board 0 9 WITHSCORES` returns the top
  10, already sorted, in one O(log N + 10) call; `ZREVRANK board player_id` returns one
  specific player's current rank, also O(log N) — no separate "sort everyone" step, ever,
  because the structure never stops being sorted.
- **Sliding-window rate limiting.** Score each request by its own timestamp; a request is
  allowed if fewer than the limit's worth of entries fall inside the trailing window.
  Enforcing that is `ZREMRANGEBYSCORE key -inf (now - window)` (evict anything older than the
  window) followed by `ZCARD key` (count what's left) — this is the concrete Redis mechanism
  behind the **"sliding window log"** row in [the rate-limiter worked example's algorithm
  table](../01_ml_system_design/00_interview_framework_fundamentals.md#worked-example-design-a-rate-limiter),
  which names the algorithm and its O(requests)-memory trade-off but doesn't show the
  implementation — this is that implementation.
  [The rate-limiter case
  study](../../system_design_practice/07_design_rate_limiter_at_scale/tutorial.md) picks up
  from here and asks the harder question this local mechanism doesn't answer on its own: what
  happens when the limit has to hold globally across multiple regions, not just against one
  Redis instance.
- **Priority queues and delayed jobs.** Score a job by its priority, or by the Unix timestamp
  it should become eligible to run; `ZRANGEBYSCORE queue -inf now LIMIT 0 1` atomically pulls
  the single highest-priority (or now-eligible) job. This is a lighter-weight alternative to
  a dedicated priority-queue service for workloads that don't yet justify one.

## Pub/Sub: Fire-and-Forget, Not a Queue

**The problem, precisely**: sometimes a system needs to notify several interested parties
that something just happened — a cache was invalidated, a live score changed — without any
of them needing to poll for it.

**The mechanism**: `PUBLISH channel message` sends the message to every client currently
subscribed to that channel via `SUBSCRIBE`, and that's the entire feature. Redis does not
store the message anywhere once delivered; a client that wasn't subscribed at the instant of
publish simply never sees it, and there is no backlog to catch up on later.

**Why it matters practically**: that lack of persistence is a deliberate design point, not a
missing feature, and it's exactly what makes pub/sub the *wrong* tool the moment a message
must survive a subscriber being briefly offline. [Part 18's message-queue
primer](18_message_queues_and_event_driven_semantics.md) covers the durable, replayable
alternative in full — a real broker (Kafka, RabbitMQ) or Redis's own separate **Streams**
type (`XADD`/`XREAD`/consumer groups — genuinely persistent, genuinely replayable, structurally
closer to a lightweight Kafka than to pub/sub, despite living in the same Redis instance).
The decision rule is simple once named: reach for pub/sub for cheap, ephemeral fan-out where a
missed message is truly fine (a live dashboard tick, a cache-invalidation ping other servers
will naturally recover from on their own next read); reach for Streams or a real broker the
moment "this message must eventually be processed, even if the consumer was down when it was
sent" becomes a real requirement.

## Distributed Locks: `SET NX`, Fencing Tokens, and a Genuinely Contested Algorithm

**The problem, precisely**: mutual exclusion — ensuring only one process at a time performs
some action — inside one machine is a solved problem (an OS mutex). Across *multiple*
machines, with no shared memory, it's structurally harder, and it's a favorite place for an
interview to probe how carefully a candidate reasons about failure modes rather than just
reciting a command.

**The single-instance mechanism**: `SET lock:resource token NX PX 5000` acquires a lock
atomically — `NX` means "only set if the key doesn't already exist" (so a second acquirer's
`SET` simply fails, cleanly, no separate check-then-set race), and `PX 5000` attaches a
5-second auto-expiry, so a holder that crashes without releasing the lock doesn't wedge it
forever. `token` must be a value unique to *this specific acquisition* (a UUID, not a fixed
string) — releasing the lock must then be a **compare-and-delete**, checking that the stored
token still matches before deleting, run as a single atomic Lua script rather than a
GET-then-DEL from application code. Skip that check, and a real, concrete bug appears: holder
A's lock expires under load right as A is still mid-operation; holder B legitimately acquires
the now-free lock; A finally finishes and calls a plain `DEL`, deleting **B's** live lock, not
its own — two holders now believe they exclusively hold the same lock at the same time,
which is the exact failure mutual exclusion exists to prevent. (The single-instance
implementation and this exact race are worked through, executed, and asserted against in
[`distributed_lock.py`](../../../../mlops_aiops/docs/tools/redis/examples/distributed_lock.py).)

**Redlock, and why it's a genuinely open argument, not settled trivia**: the single-instance
lock above has an obvious weak point — if that one Redis instance goes down, every lock it
was holding vanishes with it. **Redlock** is Redis's own proposed fix: acquire the same lock,
independently, against N separate Redis instances (typically 5), and consider the lock held
only if a majority acquired it within a bounded time. This is a genuinely **disputed**
algorithm in the distributed-systems community, worth being able to summarize both sides of
precisely because most candidates only know one exists, not why it's controversial:
**Martin Kleppmann's public critique** (2016) argued Redlock's safety can still be violated
by an ordinary process pause — a garbage-collection stall or a slow disk write can make a
lock holder believe it still holds the lock well past its actual expiry, and resume writing
to the protected resource after another process has already, correctly, acquired the same
lock — meaning Redlock provides *efficiency* (usually only one holder at a time) without a
provable safety guarantee (a mathematically airtight promise of exclusivity) under real-world
timing faults. **Salvatore Sanfilippo (Redis's creator)** defended Redlock as adequate for
the vast majority of real use cases, where "usually correct, with a bounded risk window" is
an acceptable trade for the availability Redlock buys over a single point of failure.

**The practically important resolution, regardless of which side is "more right"**: production
systems that genuinely need airtight safety don't lean on lock mutual exclusion alone at
all — they add a **fencing token**: the lock grants a monotonically increasing number on
each acquisition, and the *protected resource itself* (the database, the file store) is
required to reject any write carrying a token lower than the highest one it has already
seen. This makes correctness depend on a simple, verifiable integer comparison at the point
of actual effect, not on trusting that no two processes can simultaneously believe they hold
the lock — which sidesteps Kleppmann's exact critique regardless of whether Redlock's
probability-of-safety is "good enough" for a given system. Naming fencing tokens
specifically, unprompted, is a strong staff-level signal in this exact question.

## Persistence and Replication: The Trade You're Actually Making

**The problem, precisely**: Redis is fundamentally an in-memory store — restart the process
with no persistence configured, and every key is gone. Two independent mechanisms exist to
change that, and — as with [Part 15's write-through vs. write-behind
trade](15_caching.md#cache-placement-patterns) — the choice between them is a real design
decision, not a checkbox.

- **RDB** — periodic point-in-time binary snapshots. Compact, fast to load on restart, and
  loses everything written since the last snapshot if the process dies uncleanly.
- **AOF** — every write command logged and replayed on restart. Configurable durability down
  to "fsync every write" (safest, slowest) or "fsync roughly once per second" (the common
  middle ground — bounded, small loss window instead of zero-loss-but-slow or fast-but-
  unbounded-loss), at the cost of a slower restart (replaying a log takes longer than loading
  one snapshot) and a file that needs periodic background compaction.

Running both together — AOF for durability, RDB for fast recoverability and portable
backups — is the common production default, and it's [the exact config the hands-on lab's
Redis container starts with, with both mechanisms inspected on
disk](../../../../mlops_aiops/docs/tools/redis/README.md#persistence-rdb-and-aof-actually-inspected).

**Replication** is a separate axis, for read scaling and failover rather than durability: a
primary streams its write stream to one or more replicas, **asynchronously by default** — a
write is acknowledged to the client the instant the primary applies it, before any replica
has necessarily received it. That's [Part 2's sync-vs-async replication trade-off, recurring
at this
layer](02_data_and_consistency.md#sync-vs-async-replication-the-same-fsync-trade-off-at-cluster-scale):
faster writes, at the real cost of a window where a primary failure loses whatever hadn't yet
reached a replica. **Redis Sentinel** handles automatic primary failover for a
replication set; **Redis Cluster** is the separate mechanism for sharding data *across* many
primaries once one machine's memory is no longer enough — [the distributed-cache case
study](../../system_design_practice/05_design_distributed_cache/tutorial.md) is the deep-dive
on Cluster's specific hash-slot sharding mechanism, not repeated here.

## When Redis Is the Wrong Choice

Naming this explicitly is itself a staff-level signal — reaching for Redis by default,
everywhere, is exactly the "whatever I've used before, out of habit" failure mode [Part 24's
own self-check
warns against](24_cardinality.md#designing-and-operating-from-first-principles) applied to a
specific tool:

- **The working set has to fit in RAM** (or be actively evicted under a `maxmemory` policy —
  [Part 15's LRU/LFU eviction discussion](15_caching.md#eviction-policies-what-gets-removed-when-the-cache-is-full)
  applies directly here). A dataset that's fundamentally disk-scale doesn't belong primarily
  in Redis.
- **It is not a system of record by default.** Even with AOF, Redis is optimized for speed
  first; a durable primary data store with rich query/transaction guarantees (a relational
  database, in particular) is still the right home for data whose loss would be
  unacceptable, with Redis layered in front as a cache or derived index, not as the source
  of truth.
- **Multi-key transactions are optimistic, and don't roll back on a runtime error.**
  `MULTI`/`EXEC` queues commands and runs them atomically as a batch, but if one queued
  command fails at runtime (wrong type for that key, for instance), the **other commands in
  the batch still execute** — very different from a relational database's transaction
  rollback semantics, and a real, specific gotcha for anyone assuming SQL-transaction
  behavior by analogy.
- **A single expensive command still blocks everyone** — the single-threaded core's
  atomicity advantage, and its operational risk, are the same fact from two angles, as
  covered above.

**Modern landscape, briefly**: **KeyDB** and **Dragonfly** are multi-threaded,
protocol-compatible reimplementations aimed specifically at Redis's single-thread ceiling on
very high-throughput single-node workloads. **Amazon ElastiCache / MemoryDB**, **Azure Cache
for Redis**, and **Upstash** (serverless, pay-per-request Redis) are the managed ways teams
run Redis today rather than operating replication and failover by hand — worth naming as the
current default deployment shape, the same "favor what a principal engineer would actually
reach for in 2025-2026" standard [this folder's own CLAUDE.md
holds every part to](CLAUDE.md#analogies-real-tools-and-current-trends-required-not-decorative).

## Designing and Operating From First Principles

1. Am I using Redis because its data structures actually match this problem's shape
   (ranked data, a queue, a counter needing atomic increment) — or just because it's the
   familiar default cache, for data that a plain key-value store would have served just as
   well?
2. Have I actually named which persistence combination (RDB, AOF, both, neither) this
   specific use case needs, based on what I'm willing to lose on a crash — or left it at
   whatever the default happened to be?
3. If I'm relying on Redis for mutual exclusion across multiple processes, have I reasoned
   about what happens if a lock holder pauses unexpectedly (GC, disk stall) — or am I
   trusting the lock's expiry alone without a fencing token protecting the actual resource?
4. Have I checked whether a command I'm about to run (`KEYS`, `SMEMBERS` on a large
   collection) can block the single-threaded core for long enough to matter under real
   production load — or only discovered that under an actual incident?
5. If I reached for pub/sub, have I confirmed a missed message during a brief subscriber
   outage is genuinely acceptable for this use case — or does it actually need Streams' or a
   real broker's persistence and replay?
6. Am I treating Redis as a system of record anywhere it shouldn't be — could this specific
   dataset's loss actually be tolerated if I'm honest about it, or does it belong in a durable
   primary store with Redis layered in front instead?

## Key Takeaways

- **Redis's real differentiator isn't speed alone — it's typed values with server-side,
  atomic, type-specific operations** (`INCR`, `ZADD`, `LPUSH`), closing the
  read-modify-write race a plain key-value store forces into application code.
- **A single-threaded core is what makes that atomicity free** — no interleaving is possible
  mid-command — and it's also why one expensive command (`KEYS *` on a huge keyspace) can
  block every other client; the same structural fact, cutting both ways.
- **Sorted sets are one structure behind three separate interview patterns**: leaderboards
  (score = rank, always maintained), sliding-window rate limiting
  (`ZREMRANGEBYSCORE`+`ZCARD`), and priority/delayed queues (`ZRANGEBYSCORE ... LIMIT`) — all
  O(log N), all maintained continuously rather than recomputed on read.
- **Pub/sub is fire-and-forget, with no persistence and no replay** — the right tool for
  cheap ephemeral fan-out, the wrong one the moment a message must survive a subscriber being
  briefly offline; Streams or a real broker is the durable alternative.
- **`SET NX PX` gives single-instance mutual exclusion; releasing it safely requires a
  unique token and a compare-and-delete**, not a plain `DEL` — otherwise a delayed holder can
  delete a different, legitimate holder's live lock.
- **Redlock (multi-instance locking) is genuinely disputed, not settled** — Kleppmann's
  critique (a process pause can violate its safety guarantee) versus Sanfilippo's defense
  (adequate for most real use cases) — and production systems that need airtight correctness
  add a fencing token at the protected resource regardless of which side is right.
- **RDB and AOF trade recovery speed against durability window**; replication is async by
  default, trading write latency against a real data-loss window on primary failure — the
  same sync-vs-async trade-off recurring at yet another layer.
- **Redis is not a system of record by default, isn't a fit once data exceeds RAM, and its
  multi-key transactions don't roll back on a runtime error** — three concrete, specific
  reasons it can be the wrong choice, not just "sometimes you don't need a cache."

## Quick Self-Check

- Explain precisely why `INCR` needs no application-level locking to be safe under
  concurrent access — what specific property of Redis's execution model guarantees that?
- Walk through, step by step, how a sorted set answers "what's this player's current rank"
  in O(log N) without ever re-sorting the whole leaderboard.
- What Redis commands implement the "sliding window log" rate-limiting algorithm, and what
  is each one doing?
- Why is deleting a distributed lock with a plain `DEL` unsafe — construct the specific
  sequence of events (which holder does what, in what order) that causes two processes to
  believe they hold the same lock simultaneously.
- What does a fencing token actually protect against that Redlock's majority-acquisition
  guarantee alone does not?
- Why is Redis pub/sub the wrong choice the moment a subscriber might be briefly offline —
  what specifically happens to a message published during that gap?
- Name two concrete reasons Redis might be the wrong default for a given dataset, beyond "the
  data doesn't need to be cached."

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Toolbox-not-cache framing (the default for "why Redis" or "how would you speed this
  up" questions):** "I wouldn't describe Redis as just a fast cache — the actual
  differentiator is typed values with server-side, atomic operations. A sorted set alone
  covers leaderboards, sliding-window rate limiting, and priority queues, because Redis
  does the ranking work on its own server instead of forcing a read-modify-write round
  trip into my application code."
- **Single-threaded-cuts-both-ways framing (good for an atomicity or performance
  follow-up):** "Redis commands are atomic essentially for free because the core executes
  one command at a time on a single thread — no interleaving is even possible. That same
  fact is the operational risk: one expensive command like `KEYS *` on a large keyspace
  blocks every other client for as long as it runs, so I'd always reach for `SCAN` instead
  in any real code path."
- **Fencing-token framing (good for demonstrating you know a "solved" pattern still has an
  open edge):** "I wouldn't lean on Redlock's mutual exclusion alone for something that
  truly can't tolerate two holders — Kleppmann's critique is that a GC pause or disk stall
  can violate its safety guarantee. The fix that sidesteps the argument entirely is a
  fencing token: the protected resource itself rejects any write carrying a token lower
  than the highest it's already seen, so correctness doesn't depend on trusting the lock
  at all."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **sorted set / ZSET** (n.) — a Redis set where every member carries a score, kept
  continuously ordered by that score via a skip list + hash map; the mechanism behind
  leaderboards, sliding-window rate limiters, and priority queues.
- **`SET NX PX`** (command) — atomically acquire a single-instance lock only if absent
  (`NX`), with an auto-expiry (`PX`) so a crashed holder can't wedge it forever.
- **fencing token** (n. phrase) — a monotonically increasing number issued per lock
  acquisition; the protected resource rejects any write carrying a token lower than the
  highest already seen, making correctness independent of the lock's own mutual-exclusion
  guarantee.
- **Redlock** (proper n.) — Redis's multi-instance distributed-locking algorithm (majority
  acquisition across N independent instances); publicly disputed by Kleppmann on safety
  grounds, defended by Sanfilippo as adequate for most real use cases.
- **pub/sub vs. Streams** (n. phrase) — fire-and-forget, no-persistence fan-out versus
  Redis's separate, durable, replayable, consumer-group-capable log type.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…the server does the ranking, not my application"** — a compact way to explain why a
  sorted set beats fetching data and sorting it client-side, without re-deriving skip-list
  mechanics.
- **"…atomic for free, and dangerous for the same reason"** — connects Redis's
  single-threaded core to both its atomicity guarantee and its one-slow-command-blocks-
  everyone risk in a single line.
- **"…correctness shouldn't depend on trusting the lock"** — the fencing-token argument,
  stated as a design principle rather than a memorized fact about Redlock specifically.

---

**Previous:** [Part 24: Cardinality — One Word, Five Meanings, One Underlying Idea](24_cardinality.md)  |  **Next:** [0. The Interview Framework](../01_ml_system_design/00_interview_framework.md)

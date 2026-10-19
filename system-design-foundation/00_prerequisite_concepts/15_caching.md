# Prerequisite Concepts, Part 15: Caching — Trading Freshness for Speed

[Part 6](06_mechanical_sympathy_and_physics_of_latency.md#the-economics-of-machine-cost-is-physics)
already established the storage hierarchy — RAM roughly 100x pricier and faster than SSD,
SSD roughly 10x pricier and faster than cold storage. Caching is what you do *on purpose*
with that hierarchy: deliberately keeping a copy of data at a faster, more expensive tier
than where it authoritatively lives, to avoid paying the slow tier's cost on every request.

## In Plain English

Imagine you look something up in a huge reference book every single time a friend asks you
a common question. Eventually you'd just write the answer on a sticky note and check that
first — much faster than flipping through the book again. The catch: if the real answer in
the book ever changes, your sticky note is now wrong until you update it. That's the entire
trade caching makes: speed, in exchange for a real risk of staleness if you're not careful
about updating the sticky note when the source of truth changes.

## The Problem, Precisely

Fetching the same, unchanged data repeatedly from a slow source — a disk-backed database, a
network call to another service — wastes real time and resources on work whose answer
hasn't moved. A **cache** stores a copy closer (in the storage-hierarchy sense) to where
it's needed, so most requests are served from the fast copy instead of the slow original.

## Where to Cache: The Same Hierarchy, Chosen Deliberately

Caching isn't one layer — a single request in a modern system typically passes through
several, each trading a bit more freshness for a bit more speed: browser cache → CDN edge
cache (Cloudflare, Akamai, Fastly — [already named in Part 13's distributed-systems
catalog](13_cap_theorem_and_pacelc.md#a-catalog-of-popular-modern-distributed-systems-by-the-problem-they-solve))
→ API gateway/application cache (Redis, Memcached) → database's own internal buffer pool
([Part 10's page cache](10_physics_of_persistence.md#fsync-the-physical-line-between-written-and-durable)).
Each layer is the same underlying decision — is this data worth keeping a faster copy of —
made at a different point in the request path.

## Cache Placement Patterns

**Cache-aside (lazy loading)** — the most common pattern: the application checks the cache
first; on a miss, it reads from the source of truth, writes the result into the cache, then
returns it. Simple, and the cache only ever holds data that's actually been requested. The
cost: the very first request after a miss (or after eviction) pays the full slow-path
latency, and nothing automatically keeps the cache in sync if the underlying data changes
through some other path.

**Read-through** — conceptually the same idea, but the caching layer itself owns the
fetch-on-miss logic instead of the application code — the application just asks the cache,
and the cache transparently goes to the source of truth on a miss.

**Write-through** — every write goes to the cache *and* the database synchronously, so the
cache is never stale. The cost is a slower write (two writes, not one) — the same
sync-replication trade [Part 2](02_data_and_consistency.md#sync-vs-async-replication-the-same-fsync-trade-off-at-cluster-scale)
already named, just between a cache and a database instead of between replicas.

**Write-behind (write-back)** — the write lands in the cache immediately and is
acknowledged right away, then flushed to the database asynchronously later. Fast writes, at
the cost of a real durability risk if the cache crashes before that flush happens — exactly
[Part 10's `write()`-returning-success-isn't-durability
gap](10_physics_of_persistence.md#fsync-the-physical-line-between-written-and-durable),
recurring one layer up.

**Write-around** — the write goes straight to the database, deliberately bypassing the
cache, used when the just-written data isn't likely to be read again soon and caching it
would just push out data that actually is being read.

## Eviction Policies: What Gets Removed When the Cache Is Full

A cache is finite ([Part 12's "hundreds of things that can
break"](12_sharding_and_the_vertical_wall.md#the-constraints-that-actually-break-a-partial-list)
applies here too — memory is one of them). When it's full and a new entry needs room, an
eviction policy decides what to remove:

- **LRU (Least Recently Used)** — evict whatever hasn't been accessed for the longest time.
  Implemented efficiently with a doubly-linked list plus a hash map for O(1) access and
  eviction — the exact structure behind [this repo's own LRU Cache LLD
  problem](../../lld/04_lru_cache/problem.md).
- **LFU (Least Frequently Used)** — evict whatever's been accessed the fewest times overall,
  not just least recently. Better for a workload with a stable "hot set" that occasionally
  gets a burst of one-off traffic (LRU would wrongly evict a genuinely popular item just
  because of a temporary spike in unrelated requests); more complex to implement, since it
  needs a running frequency count per entry, not just recency order.
- **TTL (Time To Live)** — expire an entry after a fixed duration regardless of access
  pattern. Simple, and the right choice when staleness tolerance has a known, fixed time
  bound rather than depending on access frequency.

## Cache Invalidation: The Genuinely Hard Part

Knowing *when* a cached value has gone stale is harder than it sounds — hard enough that
it's the subject of a decades-old, still-accurate programming aphorism about how few things
in computing are genuinely difficult.

- **TTL-based invalidation** — simplest: the entry just expires after a fixed time. Either
  wastes freshness (data changed well before the TTL expired, and the cache kept serving the
  old value) or serves stale data during the gap between an actual change and the next
  expiry — a real, named trade, not a bug.
- **Event-based (explicit) invalidation** — the write path itself explicitly deletes or
  updates the affected cache key the moment the underlying data changes. Precise — no
  staleness window at all — but it's a correctness burden: *every* write path that touches
  that data has to remember to invalidate the cache, and missing even one silently
  reintroduces staleness with no error to catch it.

## Cache Stampede (Thundering Herd)

**The failure mode**: a single, popular cache key expires, and many concurrent requests miss
at the same instant — all of them fall through to the slow source simultaneously, hammering
it with a spike of duplicate, redundant work. This is a self-inflicted denial-of-service, and
it's exactly what [the distributed-cache case
study's](../../system_design_practice/05_design_distributed_cache/tutorial.md) own deep-dive
on this failure covers in full.

**Mitigations, by name**: **single-flight / locking** (only one of the concurrent
requesters actually recomputes the value; the rest wait for that one result instead of each
racing to the source independently); **probabilistic early expiration** (refresh a hot key
slightly *before* its real expiry, staggered per-request, so many clients don't all expire
at the exact same millisecond); **stale-while-revalidate** (serve the slightly-stale value
immediately while one background request refreshes it, rather than making every caller wait
on the slow path).

## Real Tools, Modern Defaults

**Redis** is the near-universal default distributed cache in production systems today —
in-memory, supports write-through/write-behind patterns, TTL-based expiration natively, and
doubles as more than a cache (pub/sub, rate-limiting counters, leaderboards) — [Part 25 covers
exactly which Redis data structure backs each of those non-caching uses, and
why](25_redis_as_a_system_design_primitive.md). **Memcached**
is the simpler, purely-cache-shaped alternative, still common where Redis's extra features
aren't needed. At the CDN/edge layer: **Cloudflare, Akamai, Fastly, CloudFront**. At the
application/in-process layer: **Caffeine** (JVM), Python's `functools.lru_cache`. In this
repo's own MLOps context specifically, cache warming for feature stores (keeping a model's
hot features pre-loaded rather than computed on-demand at inference time) is the same
cache-aside/read-through trade-off applied to ML serving latency.

## Designing and Operating From First Principles

1. Have I named which cache placement pattern (cache-aside, write-through, write-behind) I'm
   actually using, or has it just happened by accident of which library's default I picked?
2. If I'm using write-behind for its speed, have I actually accepted the durability window
   it opens — what data would I lose if the cache died right now, before its next flush?
3. Have I named my eviction policy deliberately (LRU vs. LFU vs. TTL) based on the actual
   access pattern of this data, or left it at whatever the cache library defaults to?
4. Do I have an explicit invalidation strategy for this specific cached value, or am I
   relying on a TTL alone and quietly accepting its staleness window as "good enough"
   without having actually decided that?
5. Have I checked whether a single hot key in this cache could produce a thundering herd —
   and if so, which mitigation (single-flight, stale-while-revalidate) am I actually using?

## Key Takeaways

- **Caching is a deliberate choice about the storage hierarchy** [Part 6 already
  established](06_mechanical_sympathy_and_physics_of_latency.md#the-economics-of-machine-cost-is-physics)
  — keeping a copy at a faster, pricier tier than the source of truth, on purpose.
- **A real request usually passes through several cache layers**, not one — browser, CDN,
  application cache, database buffer pool — each the same trade made at a different point.
- **Cache-aside is the common default**; write-through trades write latency for zero
  staleness; write-behind trades a real durability window for write speed — the same
  sync-vs-async trade-off recurring one layer up from replication.
- **LRU and LFU solve different problems**: LRU evicts by recency, LFU by overall frequency
  — LFU tolerates a temporary spike in unrelated traffic better; LRU is simpler and usually
  sufficient.
- **Invalidation is the hard part, not storage** — TTL-based is simple but either wastes
  freshness or serves stale data in a real window; event-based is precise but requires every
  write path to remember to invalidate correctly.
- **Cache stampede is a self-inflicted DoS** from one popular key expiring under concurrent
  load — single-flight, probabilistic early expiration, and stale-while-revalidate are the
  three named fixes.

## Quick Self-Check

- Why does write-behind caching reintroduce the same durability risk `fsync` exists to
  close — what specifically is lost if the cache dies before its next flush?
- Explain a concrete scenario where LFU would keep an item LRU would wrongly evict — what
  access pattern causes the difference?
- Why is cache invalidation harder than cache storage — what makes TTL-based invalidation
  a real trade-off rather than a free simplification?
- Walk through exactly how a cache stampede happens: what has to be true about the timing
  of requests for it to occur, and why does single-flight specifically fix it?
- Why does a real production request typically pass through several different caching
  layers rather than one — name at least three, in order, from client to database.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Hierarchy framing (the default for 'how would you speed this up' questions):** "I'd
  treat caching as a deliberate choice about where in the storage hierarchy this data lives
  — moving a copy to a faster, pricier tier on purpose, and naming exactly which placement
  pattern (cache-aside, write-through, write-behind) and eviction policy I'm using rather
  than defaulting to whatever a library ships with."
- **Invalidation-is-the-hard-part framing (good for a 'how do you keep this fresh' follow-up):**
  "Storing the copy is the easy half — knowing when it's gone stale is the actual problem.
  I'd pick TTL-based invalidation when a bounded staleness window is acceptable, and
  event-based invalidation when it isn't, and be explicit that event-based means every write
  path now has a correctness obligation it didn't have before."
- **Stampede framing (good for demonstrating production experience, not just theory):** "A
  popular key expiring under load isn't a hypothetical — it's a self-inflicted spike that can
  take down the exact system the cache was protecting. I'd default to single-flight or
  stale-while-revalidate for any cache key with meaningfully high read volume, not just
  react to it after it happens once in production."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **cache-aside / read-through** (n. phrases) — application-owned vs. cache-owned
  fetch-on-miss logic; functionally similar, differing in which layer holds the miss logic.
- **write-through / write-behind (write-back)** (n. phrases) — synchronous dual write (no
  staleness, slower writes) versus async-flushed write (fast, real durability window).
- **LRU / LFU** (n., initialisms) — eviction by recency versus eviction by overall access
  frequency; LFU tolerates unrelated traffic spikes better, LRU is simpler.
- **cache stampede / thundering herd** (n. phrases) — many concurrent requests missing on
  the same expired key simultaneously, hammering the source of truth all at once.
- **single-flight** (n. phrase) — letting exactly one concurrent request recompute a value
  while others wait on that result, the direct fix for cache stampede.
- **stale-while-revalidate** (n. phrase) — serving a slightly-stale cached value immediately
  while refreshing it in the background, instead of blocking every caller on the slow path.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…a sticky note versus going back to the book"** — a compact, plain-language way to
  describe the entire caching trade-off without jargon.
- **"…storing the copy is the easy half"** — a fluent way to redirect a caching discussion
  toward invalidation, the part that actually determines correctness.
- **"…the exact same tax, paid one layer up"** — a reusable line connecting write-behind's
  durability window to `fsync`'s durability boundary from Part 10, without re-deriving it.

---

**Previous:** [Part 14: Geospatial Indexing — Finding What's Nearby](14_geospatial_indexing.md)  |  **Next:** [Part 16: Observability — Metrics, Logs, and Traces](16_observability.md)

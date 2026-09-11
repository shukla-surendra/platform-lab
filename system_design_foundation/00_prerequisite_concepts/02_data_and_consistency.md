# Prerequisite Concepts, Part 2: Data Distribution and Consistency

[Part 1](01_performance_and_scale.md) covered how to measure a system and why horizontal
scaling requires statelessness. This part covers what happens to the *state* itself once
it can no longer live on one machine — the first-principles reasoning behind sharding,
replication, indexing, and the consistency trade-offs that follow from splitting data
across many machines.

## Why One Machine Stops Being Enough — Two Different Problems

It's worth separating these explicitly, because the two most common "split the data up"
techniques each solve a *different* one:

- **Problem 1: capacity.** A single machine has finite CPU, RAM, disk, and network
  bandwidth. Past a certain data volume or query rate, no single machine — however
  powerful — can hold or serve it all. **Sharding/partitioning** solves this: split the
  data so each machine holds and serves only a slice of it.
- **Problem 2: durability and availability.** Even a machine that *could* hold all the
  data is a single point of failure — if it dies, the data is gone (or at least
  unreachable) until it's restored. **Replication** solves this: keep copies of the same
  data on multiple machines, so losing one doesn't lose the data or the ability to serve
  it.

**These are orthogonal, and real systems need both, deliberately combined**: shard the
data for capacity, then replicate each shard for durability. Confusing the two — thinking
replication gives you more capacity, or that sharding gives you durability — is a common
first-principles gap; sharding *without* replication just gives you many single points of
failure instead of one.

## Sharding / Partitioning, Briefly

Covered in depth in [Fundamentals](../ml_system_design/00_interview_framework_fundamentals.md#sharding-partitioning)
and extended further in the [distributed systems foundations
tutorial](../../system_design_practice/01_distributed_systems_foundations/tutorial.md#consistent-hashing-advanced-sharding)
(consistent hashing, virtual nodes) — the short version: split data across machines by
some key (range-based, hash-based, or directory-based), and watch for **hot shards**
(uneven access concentrating load on one partition despite even data distribution) as the
recurring failure mode to name proactively.

## Replication: Distributed Truth, GFS, and What "11 Nines" Actually Means

[Fundamentals](../ml_system_design/00_interview_framework_fundamentals.md#replication) covers the short
version: leader-follower replication is the standard pattern (writes go to a leader, reads
can be served from followers, at the cost of replication lag), and multi-leader/leaderless
setups trade that simplicity for higher write availability at the cost of needing an
explicit conflict-resolution strategy. What follows is the mechanism underneath that
summary — the reference architecture nearly every large-scale storage system since has
copied, and the two dials (sync-vs-async, replication-vs-erasure-coding) real systems
actually tune.

### The Problem, Stated Precisely: Distributed Truth

Once data lives on a single machine, that machine is a single point of failure — disk
failure, machine failure, rack failure, or (per the bit-rot discussion in [Part
6](06_mechanical_sympathy_and_physics_of_latency.md#the-invisible-enemy-bit-rot-silent-data-corruption-and-checksums))
a lone copy silently corrupting with nothing to compare it against. "Truth" — the correct
value of the data — has to be reconstructible even if any single copy is lost or corrupted,
which requires more than one copy *and* a protocol for keeping those copies consistent, or
at least for knowing which one to trust when they disagree.

### GFS (2003): The Reference Architecture

**The Google File System** (Ghemawat, Gobioff, Leung, SOSP 2003) is the paper nearly every
subsequent large-scale distributed storage system — HDFS most directly — copied the
blueprint from. It was built to store the massive, mostly-append, rarely-overwritten data
behind Google's crawler and index, which is why its core design choices echo the
append-don't-overwrite theme [Part 10](10_physics_of_persistence.md) already established at
the single-machine level, just applied across a whole cluster:

- **Master (single, metadata-only)** — holds the filesystem namespace and the
  chunk-to-chunkserver mapping, but never the actual file data, so its metadata fits in RAM
  and stays fast. The master's *own* durability uses exactly the WAL pattern from [Part
  10](10_physics_of_persistence.md#the-write-ahead-log-making-durability-affordable): an
  operation log plus periodic checkpoints.
- **Chunkservers (many)** — store the real data, split into large, fixed **64 MB chunks**
  (deliberately huge compared to a typical 4-16 KB filesystem block, because GFS's workload
  is large sequential reads/appends, and bigger chunks mean the master tracks far less
  metadata per byte stored).
- **Replication** — each chunk is replicated (typically **3x**) across different
  chunkservers, spread across racks, so one rack failure can't take out every copy of a
  chunk at once.
- **Data path bypasses the master** — a client asks the master "where's chunk X," then
  talks directly to chunkservers for the actual bytes, keeping the metadata server out of
  the throughput-critical path.
- **Leases for write ordering** — the master temporarily grants one replica a **lease** to
  act as primary for a chunk, ordering concurrent writes and propagating that order to the
  other replicas, without the master mediating every single write.
- **Per-chunk checksums** — each chunkserver checksums and verifies its own chunks on every
  read: the same bit-rot defense from Part 6, applied at cluster scale years before ZFS made
  the equivalent mainstream at the single-machine level.
- **Self-healing at cluster scale** — the master heartbeats chunkservers, detects
  under-replicated chunks when one dies, and automatically re-replicates elsewhere — the
  same self-healing concept as ZFS, just across machines instead of across disks in one
  array.

### Sync vs. Async Replication: The Same fsync Trade-off, at Cluster Scale

This is not a new trade-off — it's [Part 10's `fsync`
argument](10_physics_of_persistence.md#fsync-the-physical-line-between-written-and-durable)
recurring one layer up. **Synchronous replication** doesn't acknowledge a write until other
replicas confirm they have it too — safer (no acknowledged write can vanish), but slower,
and the slowdown scales with the physical distance to those replicas (network propagation
delay, [Part 6](06_mechanical_sympathy_and_physics_of_latency.md#distance-of-data-one-physical-idea-two-different-scales)
/ [Part 9](09_dns_bgp_and_the_edge.md)'s territory). **Asynchronous replication**
acknowledges immediately and copies data to replicas in the background — faster, but a
crash before that background copy completes loses the most recently acknowledged writes.
Real systems pick per hop based on distance: replication *within* a datacenter or region can
often afford synchronous (the propagation delay is small); replication *across* regions —
hundreds or thousands of kilometers — usually can't, which is exactly why cross-region
replication (see GRS below) is inherently asynchronous in practice.

### Quorum-Based Replication: N, W, R

Leaderless replication (Dynamo-style — the model behind Cassandra and DynamoDB) needs its
own consistency mechanism, since there's no single leader to serialize writes through:
define **N** (total replicas of a piece of data), **W** (replicas that must acknowledge a
write before it's considered successful), and **R** (replicas queried on a read). Choosing
**W + R > N** guarantees every read overlaps with at least one replica that saw the most
recent write, so the read is guaranteed to see current data even without a leader — a
tunable dial trading write latency (higher W) against read latency (higher R) against
staleness risk (lower W + R, which drops below the guarantee entirely).

### Erasure Coding: Durability Without 3x Storage

Full replication (N copies) is simple but expensive — 3x replication means 3x the storage
cost of the original data. **Erasure coding** gets similar durability far more cheaply:
split data into **k** data fragments plus **m** parity fragments (Reed-Solomon codes — the
same mathematical family behind NAND/HDD's own internal ECC from [Part 6's bit-rot
section](06_mechanical_sympathy_and_physics_of_latency.md#the-invisible-enemy-bit-rot-silent-data-corruption-and-checksums)),
such that *any* k of the resulting k+m fragments are enough to reconstruct the original
data. This achieves durability comparable to 3x replication at roughly **1.4-1.5x** storage
overhead instead of 3x — the cost is that reconstructing a lost fragment takes more compute
and I/O than reading a plain replica, which is why erasure coding shows up on *cold* data
(S3's infrequent-access tiers, HDFS's erasure-coding mode) where that reconstruction cost is
an acceptable trade for the storage savings, rather than on hot, latency-sensitive data.

### Cloud Analogs: S3 and Azure GRS

- **Amazon S3** advertises "11 nines" (99.999999999%) annual durability for Standard
  storage — meaning that storing 10,000,000 objects, you'd expect to lose one roughly once
  every 10,000 years on average. That number is the direct output of the GFS-style recipe
  above: multiple independent copies (or erasure-coded fragments) across independent
  failure domains, continuous per-object checksumming, and automatic repair — fully
  managed, so the chunkserver-equivalent internals are invisible to the user.
- **Azure Storage's redundancy tiers** make the "how many failure domains" dial explicit and
  named: **LRS** (Locally Redundant Storage) replicates 3x within one datacenter; **ZRS**
  (Zone-Redundant Storage) replicates 3x across separate availability zones in a region;
  **GRS** (Geo-Redundant Storage) takes the LRS-protected data and replicates it *again*,
  asynchronously (per the sync/async argument above — the distance makes synchronous
  replication impractical), to a paired secondary region hundreds of miles away — protecting
  against the entire primary region failing, not just one machine or datacenter. **RA-GRS**
  additionally allows read access to that secondary region's copy during normal operation,
  not just after a failover.

## Indexing: Why Databases Don't Scan Everything

A concept assumed by name in almost every tutorial in this repo, worth actually
understanding from first principles.

**The problem an index solves**: without one, finding a specific row (`WHERE user_id =
12345`) means scanning every row in the table, checking each one — a **full table scan**,
O(n) in table size. Fine for a thousand rows, unusable for a billion.

**The core idea**: maintain a separate, smaller, *sorted* (or otherwise organized)
structure that maps a column's values to the location of the corresponding rows — so
looking a value up means searching the small sorted structure, not the whole table.

- **B-Tree indexes** (the default for most relational databases): a balanced tree
  structure keeping keys sorted, giving O(log n) lookups *and* efficient range queries
  (`WHERE created_at BETWEEN X AND Y`) because sorted order is preserved — you can walk
  sideways through the tree for a range instead of doing n separate lookups.
- **Hash indexes**: map a key directly to a location via a hash function — O(1) average
  lookup for exact-match queries (`WHERE user_id = 12345`), but **can't support range
  queries at all**, since a hash function deliberately scrambles order (a hash index has no
  concept of "the value right after this one").

**The trade-off that makes indexing a genuine design decision, not a free win**: every
index has to be updated on every write that touches its column — more indexes means faster
reads but slower writes and more storage. This is why database schema design involves
deliberately choosing *which* columns get indexed (the ones actually queried against
frequently) rather than indexing everything defensively — an over-indexed table pays a
real, continuous write-latency tax for read speed most of its indexes never actually
deliver.

### Index Shapes: Same Mechanism, Different Coverage

B-Tree vs. hash is *which structure* an index uses; the shapes below are *which columns and
how many* — a second, independent axis worth naming precisely, since interview follow-ups on
indexing usually live here, not in structure choice.

- **Single-column index** (`INDEX (user_id)`) — the default case above: one column, one
  sorted structure, fast exact/range lookups on that column alone.
- **Composite (multi-column) index** (`INDEX (user_id, created_at)`) — a single sorted
  structure keyed on the *combination*, sorted first by the leftmost column, then by the
  next within each tie. **The left-most-prefix rule is the actual interview trap**: this
  index serves `WHERE user_id = ? AND created_at > ?` efficiently (it's a prefix of the sort
  order), but does *nothing* for a query filtering on `created_at` alone — skipping the
  leftmost column means the sortedness the index provides can't be used at all, the same way
  a phone book sorted by (last name, first name) is useless for finding everyone named
  "John."
- **Unique index** — a normal index with a constraint bolted on: every insert/update is
  checked against it, and a duplicate is rejected rather than stored. This is the actual
  mechanism behind an `email` or `username` uniqueness guarantee, and it's precisely the
  **conditional insert** mechanism [the URL Shortener tutorial's key-generation
  deep-dive](../../system_design_practice/11_design_url_shortener/tutorial.md#deep-dive-key-generation-an-access-control-decision-not-an-encoding-one)
  relies on to make random-key collisions safe rather than silent.
- **Covering index** — an index that stores *every column a specific query needs*, not just
  the column(s) it's searched on. A query fully answered by the index never touches the
  underlying table row at all (no second lookup to fetch the rest of the row) — the fastest
  possible read this repo covers, paid for with a larger index (duplicating column data that
  already lives in the table) and the same extra write cost every additional index carries.

**The write-cost consequence, stated as a rule**: every index — of any shape — must be
updated on every write that touches its columns, so "more indexes" is never a free upgrade.
[Part 11's write-amplification axis](11_taxonomy_of_storage_choice.md#5-write-amplification-what-does-this-workload-do-to-the-storage-engines-write-path)
is this exact trade-off, restated per-index rather than per-engine: a write-heavy table with
five indexes pays five update costs on every insert, which is precisely why time-series/log
ingestion tables (extremely high write volume, rarely queried by arbitrary column) are
usually indexed minimally or not at all, trading query flexibility for write throughput on
purpose.

## Pagination: Walking Through an Indexed Result Set

Indexing solves "find the matching rows fast." A separate, equally common question sits
right next to it: once a query matches thousands or millions of rows, how does an API hand
them back a manageable page at a time? Two genuinely different mechanisms answer this, with
a real cost difference between them.

**Offset/limit pagination** (`LIMIT 20 OFFSET 4000`) is the obvious first approach: ask for
20 rows starting at row 4,000. It's simple, and it's exactly what breaks down at scale, for
two separate reasons:

1. **It gets slower with page depth, not just row count.** The database still has to walk
   past all 4,000 skipped rows to find where the requested page starts — even though those
   rows are never returned — so page 200 is measurably more expensive than page 2, on the
   *identical* query, purely because of how far into the result set it sits.
2. **Page drift under concurrent writes.** If a row is inserted or deleted *before* the
   current offset while a user is paging through results, every subsequent page shifts by
   one — a row can be skipped entirely, or shown twice, without the query itself being wrong
   at all. The offset is a position in a list that keeps changing underneath it.

**Cursor-based (keyset) pagination** fixes both problems by asking a different question
entirely: instead of "skip N rows," it asks "give me the next 20 rows *after this specific
key I last saw*" (`WHERE id > $last_seen_id ORDER BY id LIMIT 20`). This is precisely [Part
10's B-tree guided
descent](10_physics_of_persistence.md#b-trees-fully-unpacked-optimizing-for-reads-by-paying-on-writes)
or an LSM-tree's sorted SSTable scan, doing exactly the range-scan work it's already built
for — the query goes straight to the cursor's position via the index, with **no work
proportional to how deep into the result set the page is**. Page 2 and page 200 cost the
same. It also sidesteps page drift: a row inserted somewhere *after* the cursor doesn't
shift anything the user has already seen, since "after this key" is a stable, absolute
position, not a relative offset that moves when the underlying data changes.

**The cost cursor-based pagination pays instead**: it can't jump to an arbitrary page number
("show me page 47 directly") the way offset-based pagination naively can — only "the next
page after where I currently am." For the overwhelming majority of real UIs (infinite
scroll, "load more," API clients paging through results), that's not a real limitation,
since nobody actually needs to jump to page 47 of a search result — which is exactly why
cursor-based pagination is the default in essentially every large-scale API (GitHub,
Twitter/X, Stripe) despite offset/limit being the one taught first.

## CAP Theorem, Briefly

Covered in depth in [Fundamentals](../ml_system_design/00_interview_framework_fundamentals.md#cap-theorem-consistency-models)
— the short version, for continuity: under a network partition, a distributed system must
choose between **C**onsistency (every read sees the latest write) and **A**vailability
(every request gets a response) — you cannot have both. Naming which side a given stateful
component of your design lands on, and why, is exactly the [trade-off vocabulary the
interview framework](../ml_system_design/00_interview_framework.md#the-trade-off-vocabulary-cheat-sheet)
expects you to use fluently.

## The Consistency Spectrum: It's Not Just Strong vs. Eventual

CAP theorem's "C" is really one end of a spectrum, not a binary — worth knowing the
intermediate points by name, since real systems often deliberately choose one of these
rather than either extreme:

| Model | Guarantee | Example |
|---|---|---|
| **Strong consistency** | Every read sees the most recent write, globally, immediately | A bank balance after a transfer |
| **Read-your-own-writes** | You always see your *own* recent writes, but might see stale data from others' writes | You post a comment and see it immediately, even if a friend's feed hasn't updated yet |
| **Monotonic reads** | Once you've seen a value, you never see an *older* one afterward, even from a different replica | A game score goes 10 → 12, never 12 → 10 on a later refresh — no "time travel" backward |
| **Causal consistency** | Writes that are causally related are seen in order by everyone; unrelated writes can appear in any order | A reply to a comment never appears *before* the comment it's replying to |
| **Eventual consistency** | Given enough time with no new writes, all replicas converge to the same value — no ordering guarantee in between | A DNS record change propagating across resolvers over some minutes |

**Why this spectrum matters practically**: "eventual consistency" is often too weak a
guarantee for what a product actually needs (users find "I posted something and can't see
it" jarring), while full strong consistency is often far more expensive than necessary.
Read-your-own-writes is frequently the sweet spot — cheaper to implement than global strong
consistency, but resolves the specific user-facing confusion eventual consistency alone
tends to cause.

## Eventual Consistency, Fully Unpacked

The table above states eventual consistency's guarantee in one line; it's worth being
precise about what that guarantee does and doesn't cover, since it's the weakest useful
consistency model a replicated system can offer and the easiest to misjudge in practice.

**The guarantee, exactly**: *if no new writes occur to a piece of data, all replicas will
eventually converge to the same value.* That's a **liveness** guarantee ("this will
eventually happen"), not a timing guarantee (no bound on how long "eventually" takes) and
not an ordering guarantee (different clients can observe updates arriving in different
sequences while convergence is still in progress).

**The mechanism — how convergence actually happens**:

1. **Async replication** — a write is accepted and acknowledged at one replica immediately,
   then propagated to others in the background ([the same sync-vs-async trade already
   covered
   above](#sync-vs-async-replication-the-same-fsync-trade-off-at-cluster-scale)) — this
   background propagation window is exactly where replica disagreement lives.
2. **Gossip protocols** — nodes periodically exchange state with random peers, spreading
   updates around the cluster with no central coordinator needed.
3. **Read repair / anti-entropy** — a background or read-time process that compares replicas
   and writes the correct value back to whichever one is stale, closing the convergence gap
   faster than gossip alone.
4. **Conflict resolution, for the genuinely hard case**: two replicas each accept a
   *different* write to the same key while disconnected. Three real strategies exist —
   **Last-Write-Wins (LWW)**, the simplest: a timestamp decides, the loser is silently
   discarded, which can quietly lose real data if clocks aren't perfectly synced or both
   writes were meaningful; **vector clocks**, Dynamo's original approach: detect whether two
   versions are causally related or truly concurrent, and if genuinely concurrent, hand
   *both* back to the application to merge, since the database itself can't know which one
   is "right"; and **CRDTs** (Conflict-free Replicated Data Types), data structures
   engineered so concurrent updates merge deterministically with no conflict at all (a
   counter that only ever increments, for example).

**The concrete example this whole series already established**: [Dynamo's shopping
cart](11_taxonomy_of_storage_choice.md#2005-google-and-amazon-hit-the-wall--nosql-begins-with-key-value-stores)
— a write (add to cart) succeeds immediately even mid-partition, favoring Availability. A
read from a *different* replica moments later might not show that item yet. The system only
promises that, given enough time with no further writes, every replica's view of the cart
converges — which is exactly why LWW would be the *wrong* conflict-resolution choice for a
cart specifically (two concurrent adds shouldn't have one silently discarded — vector clocks
or a CRDT-style set union is what Dynamo actually needs here, not last-write-wins).

**It's tunable, not a fixed ceiling**: Cassandra's `ONE`/`QUORUM`/`ALL` consistency levels
([Part 13](13_cap_theorem_and_pacelc.md#pacelc-naming-the-trade-off-cap-leaves-out)) move a
query along the latency-vs-consistency axis at request time — eventual consistency is the
*default*, weakest setting a system like Cassandra ships with, not the only behavior it's
capable of producing.

### In Plain English

Imagine texting a friend "let's meet at 6pm instead of 5pm" in a group chat. It doesn't land
on everyone's phone at the same instant — some friends see it right away, others (bad
signal, phone in a pocket) see it seconds or minutes later. For a little while, asking
different friends "what time are we meeting?" gets different answers depending on who you
ask. But nobody's wrong forever — as long as nobody sends another message changing the plan
again, every phone eventually shows "6pm."

That's the whole idea. A big app doesn't store your data in one place — it's copied across
many servers, for speed and so it doesn't go down if one server dies. When something
changes, it hits *one* server first and confirms back to you immediately — fast. Then it
quietly spreads to the other servers in the background, the same way the group chat message
spreads phone to phone. For a brief window, someone hitting a different server might not see
the change yet. Wait a few seconds, and it's everywhere. **Why build it this way on
purpose**: making every server check in with every other server before confirming anything
back to you would make the app feel sluggish — and for a lot of data, being a few seconds
behind genuinely doesn't hurt anyone, so paying for instant global agreement on every single
change would be waste, not safety.

### Real-World Examples, Both Directions

**Eventually consistent — a brief lag is normal and nobody gets hurt by it**:

| Example | What's actually happening |
|---|---|
| Social media like/view counts | Different viewers can briefly see slightly different counts on the same post before they sync up |
| DNS propagation | A domain's new IP address takes minutes to hours to reach every resolver worldwide — [already named in the spectrum table above](#the-consistency-spectrum-its-not-just-strong-vs-eventual) |
| Messaging apps across your own devices | A message sent from your phone can take a moment to appear on a linked laptop/tablet client |
| Adding an item to an online shopping cart | [Dynamo's textbook case](#eventual-consistency-fully-unpacked) — the add confirms instantly, but a read from a different replica moments later might not show it yet |
| A new blog post reaching search results | Search engines re-index content across data centers on their own schedule, not instantly on publish |
| CDN cache after a website update | Different edge locations around the world refresh their cached copy of a changed file at different times |

**Strongly consistent — everyone must see the exact same, latest value immediately, no lag
tolerated**:

| Example | Why a lag would actually cause harm |
|---|---|
| Bank account balance after a transfer | The textbook case already in the spectrum table above — uncertainty about whether money actually moved is unacceptable |
| Airline/concert seat booking | Two people must never both be told they've booked the same seat |
| Stock exchange order matching | A stale price shown for even a moment could mean a trade executes at the wrong value |
| Flash-sale inventory for a scarce item | Overselling more units than physically exist because two servers each thought stock remained |
| Login/password-change/account-lockout state | Every server checking a login must know *immediately* if a password just changed or an account was just locked — a lag here is a real security hole |
| Distributed lock / leader election (ZooKeeper, etcd) | Two nodes both believing they're "the leader" from stale data causes real, damaging split-brain behavior |

**The pattern underneath both lists, stated plainly**: eventual consistency is the right
choice whenever a brief disagreement is invisible or harmless to the people affected by it;
strong consistency is worth its extra cost whenever that same brief disagreement would mean
real money, safety, or correctness gets violated. Neither list is "the right one" in
general — which list a piece of data belongs on is exactly [Part 11's consistency-model
axis](11_taxonomy_of_storage_choice.md#4-consistency-model--what-does-correct-mean-for-this-data)
asking its question again: what's the actual, concrete cost if two replicas briefly
disagree?

## ACID vs. BASE

Two different philosophies for what guarantees a data store makes about transactions —
worth knowing as named opposites, since interviewers use both terms expecting you to place
a design on this spectrum:

- **ACID** (traditional relational databases): **A**tomicity (a transaction fully succeeds
  or fully fails, never partially), **C**onsistency (a transaction moves the database from
  one valid state to another, per its constraints), **I**solation (concurrent transactions
  don't see each other's uncommitted intermediate state), **D**urability (once committed, a
  write survives a crash). Strong guarantees, generally at the cost of throughput and
  horizontal scalability.
- **BASE** (many distributed/NoSQL systems): **B**asically **A**vailable, **S**oft state
  (state may change over time even without new input, as replicas converge), **E**ventual
  consistency. Weaker guarantees, deliberately traded for availability and horizontal
  scale.

**The practical framing**: ACID vs. BASE is CAP theorem's C-vs-A trade-off, restated as a
design philosophy rather than a single-partition-event decision — a payments ledger
reaches for ACID because a partially-applied transfer is unacceptable; a social media like
counter reaches for BASE because a few seconds of eventual convergence is invisible to
users and the availability win is worth far more than the consistency it costs.

## Idempotency

Introduced in passing in the [ingestion pipeline
tutorial](../ml_system_design/02_ingestion_pipeline.md#idempotency), but foundational enough to
define here explicitly: an operation is **idempotent** if performing it multiple times has
the exact same effect as performing it once.

**Why distributed systems can't avoid needing this**: any network call can fail *after*
the server processed it but *before* the client got the confirmation — the client has no
way to distinguish "it failed" from "it succeeded but the response was lost," so the only
safe client behavior is to retry. **Retries are not optional in a distributed system; they
are inevitable.** If retrying "charge this customer $10" isn't idempotent, a lost
confirmation turns into a double charge. Making it idempotent (e.g., via a client-generated
idempotency key the server deduplicates on) means retrying is always safe, which is what
actually lets a system retry aggressively and reliably instead of walking a tightrope
between "retry and risk duplication" and "don't retry and risk silently dropping work."

## Quick Self-Check

Before moving to [Part 3: Communication & Resilience](03_communication_and_resilience.md),
you should be able to answer these without looking back:

- Why does offset/limit pagination get slower on deeper pages, even though the number of
  rows actually returned never changes?
- A row gets deleted from a result set while a user is on page 3 of an offset-paginated
  list. Why can this cause them to skip a row on page 4, even though nothing about their
  query was wrong?
- Why does cursor-based pagination cost the same for page 2 and page 200 — what specific
  mechanism from Part 10 is doing the work that makes that true?
- Why does sharding a dataset *without* replicating it leave you with more single points
  of failure, not fewer?
- Why can't a hash index support a range query, structurally?
- Where does read-your-own-writes sit between strong and eventual consistency, and what
  specific user-facing problem does it solve that eventual consistency alone doesn't?
- Why is idempotency a prerequisite for safe retries, rather than a nice-to-have?
- In GFS, why does the master hold only metadata and never sit in the actual data path
  between a client and a chunk's bytes — what would break if it did?
- Why is cross-region replication (like Azure's GRS hop to its paired region) inherently
  asynchronous in practice, while within-region replication (LRS/ZRS) can often afford to
  be synchronous — what's the one physical variable that changes between the two?
- In quorum-based replication, why does W + R > N guarantee a read sees the latest write
  even with no leader coordinating — what would break if W + R were only equal to N?
- Why does erasure coding trade more compute/I/O on reconstruction for a much lower storage
  overhead than full replication, and why does that trade-off make sense for cold data but
  not hot, latency-sensitive data?
- Eventual consistency's guarantee has no time bound. Why is that precisely a *liveness*
  guarantee rather than a timing guarantee, and what does that distinction mean in practice
  for a product that needs data to converge within a specific SLA?
- Two replicas each accept a different concurrent write to the same shopping cart while
  partitioned. Why would Last-Write-Wins be the wrong conflict-resolution strategy here,
  specifically — what data does it silently lose that vector clocks or a CRDT wouldn't?
- Why does "Cassandra is eventually consistent" undersell what Cassandra can actually do —
  what's the specific mechanism that lets a single deployment move toward strong consistency
  without switching databases?
- For a like count and a bank balance, name the concrete, real-world cost of a brief replica
  disagreement in each case — why does that cost, not the technology, decide which
  consistency model each one belongs on?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Two-different-problems framing (the default for 'why shard AND replicate'):** "I'd
  separate these explicitly — sharding solves capacity, replication solves durability and
  availability. They're orthogonal, and sharding without replication just gives you many
  single points of failure instead of one, which is a common first-principles gap worth
  naming out loud."
- **Cost-of-the-index framing (good for indexing questions):** "An index isn't a free
  win — every index has to be updated on every write that touches its column, so more
  indexes means faster reads but a real, continuous write-latency tax. I'd only index
  columns actually queried against frequently, not defensively."
- **Spectrum-not-binary framing (good for consistency questions):** "I wouldn't present
  this as strong versus eventual consistency — read-your-own-writes sits in between, and
  it's often the sweet spot: cheaper than global strong consistency, but it resolves the
  specific 'I posted this and can't see it' confusion eventual consistency alone causes."
- **Reference-architecture framing (good for 'how would you build durable distributed
  storage' questions):** "I'd reach for GFS's shape as the default: separate the metadata
  plane from the data plane so a lightweight master never bottlenecks throughput, replicate
  each unit of data across independent failure domains, and checksum everything so
  corruption is detected instead of silently served. S3's '11 nines' and GFS's design are
  the same recipe — replication or erasure coding across independent failures, plus
  continuous integrity checking — just at different points on the managed-vs-self-operated
  spectrum."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **full table scan** (n. phrase) — checking every row to find a match, the O(n) baseline
  an index exists specifically to avoid.
- **offset/limit pagination** (n. phrase) — `LIMIT n OFFSET m`; simple, but cost grows with
  page depth and is vulnerable to page drift when rows are inserted/deleted mid-scroll.
- **cursor-based (keyset) pagination** (n. phrase) — "give me the next page after this key I
  last saw"; constant cost regardless of page depth, and immune to page drift, at the cost
  of not being able to jump to an arbitrary page number.
- **read-your-own-writes** (n. phrase) — a consistency guarantee where you always see your
  own recent writes immediately, even if others temporarily see stale data.
- **soft state** (n. phrase, from BASE) — state that can change over time even without new
  input, as replicas converge toward consistency.
- **idempotency key** (n. phrase) — a deterministic identifier letting a retried operation
  produce the same result as the original, the mechanism that makes retrying safe.
- **eventual consistency** (n. phrase) — [fully unpacked
  above](#eventual-consistency-fully-unpacked): if no new writes occur, all replicas
  eventually converge — a liveness guarantee with no time bound and no ordering guarantee.
- **anti-entropy / read repair** (n. phrases) — a background or read-time process comparing
  replicas and writing the correct value back to whichever is stale, closing the convergence
  gap faster than gossip propagation alone.
- **Last-Write-Wins (LWW)** (n. phrase) — the simplest conflict-resolution strategy for
  concurrent writes to the same key: a timestamp decides, the loser is silently discarded —
  can quietly lose real data when both concurrent writes were meaningful.
- **vector clock** (n. phrase) — a mechanism for detecting whether two versions of a value
  are causally related or genuinely concurrent; when concurrent, hands both back to the
  application to merge rather than guessing which one is "correct."
- **CRDT (Conflict-free Replicated Data Type)** (n. phrase, initialism) — a data structure
  engineered so concurrent updates merge deterministically with no conflict at all, a more
  elegant alternative to LWW/vector-clock-plus-manual-resolution for specific data shapes
  (counters, sets).
- **GFS (Google File System)** (n., proper) — Ghemawat, Gobioff, Leung, SOSP 2003; the
  master/chunkserver, 64 MB chunk, 3x-replication, lease-ordered-write architecture nearly
  every large-scale distributed storage system since (HDFS most directly) copied.
- **chunk** (n.) — GFS's large (64 MB), fixed-size unit of file data, replicated and placed
  independently across chunkservers; deliberately huge to keep the master's metadata small.
- **lease** (n.) — a temporary grant of "you are the primary for this chunk right now,"
  letting one replica order concurrent writes and propagate that order to the others
  without the master mediating every single write.
- **sync / async replication** (n. phrases) — whether a write waits for replica
  acknowledgment before returning (safer, slower, distance-sensitive) or acknowledges
  immediately and replicates in the background (faster, risks losing the newest writes on a
  crash) — the same trade-off as `fsync`, one layer up.
- **quorum (N/W/R)** (n. phrase) — leaderless replication's consistency dial: N total
  replicas, W required write acknowledgments, R replicas read from; W + R > N guarantees a
  read overlaps at least one replica holding the latest write.
- **erasure coding** (n. phrase) — splitting data into k data fragments + m Reed-Solomon
  parity fragments so any k of k+m reconstruct the original, achieving near-3x-replication
  durability at roughly 1.4-1.5x storage overhead, at the cost of reconstruction compute —
  the choice for cold data, not hot.
- **LRS / ZRS / GRS / RA-GRS** (n., initialisms, Azure) — Locally-, Zone-, and
  Geo-Redundant Storage, plus Read-Access GRS: the named dial for how many independent
  failure domains (datacenter, availability zone, paired region) a copy of your data
  survives losing.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…are orthogonal, and real systems need both, deliberately combined"** — a precise
  template for arguing two techniques solve different problems rather than competing
  solutions to the same one.
- **converge** (v.) — for distributed replicas to reach the same value over time.
  *"Given enough time with no new writes, the replicas converge."*
- **"Retries are not optional in a distributed system; they are inevitable"** — a strong,
  quotable line for justifying why idempotency is a foundational requirement, not a
  nice-to-have.

---

**Previous:** [Part 1: Performance & Scale](01_performance_and_scale.md)  |  **Next:** [Part 3: Communication & Resilience](03_communication_and_resilience.md)

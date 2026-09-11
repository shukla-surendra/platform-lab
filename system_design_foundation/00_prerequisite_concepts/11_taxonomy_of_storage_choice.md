# Prerequisite Concepts, Part 11: Taxonomy of Storage — Choosing by First Principles, Not Fashion

[Part 6](06_mechanical_sympathy_and_physics_of_latency.md) established the physics
underneath every storage medium (HDD seek/rotation, SSD write amplification, bit rot).
[Part 10](10_physics_of_persistence.md) established the two dominant storage-engine shapes
(B-tree vs. LSM-tree) and the RUM conjecture governing their trade-offs. [Part 2](02_data_and_consistency.md)
established how data spreads across machines (sharding, replication, GFS, consistency
models). This part doesn't introduce new mechanism — it names the failure mode that makes
all of that prior work useless in practice, and gives the checklist that fixes it: **how a
database actually gets chosen, versus how it should.**

## The Failure Mode: Choosing by Fashion, Not Engineering

At junior level, database selection is very often **not** a first-principles decision at
all — it's one of a small number of unexamined defaults:

- **"It's what I know."** The team (or the individual engineer) has used Postgres, or
  MongoDB, or MySQL before, so that's what gets reached for again — regardless of whether
  this workload's shape resembles the one that choice actually fit last time.
- **"It's what's popular."** A technology is trending, is what a bootcamp curriculum taught,
  or is what a well-known company's engineering blog described — so it must be a safe
  choice, without checking whether that company's scale, access pattern, or consistency
  requirements have anything in common with the workload actually being built.
- **"It's what the last company used."** A genuinely reasonable choice for a *different*
  workload, at a *different* scale, gets carried forward as an assumption rather than
  re-derived.

**Why this is a fashion decision, not an engineering one**: none of these reasons reference
the actual workload at all — not its access pattern, its size, its latency requirements, its
consistency needs, its write shape, or what failures it has to survive. **Every database
embodies a trade-off** — this is not a rhetorical claim, it's the literal content of the
last three parts: B-tree vs. LSM-tree is [the RUM conjecture](10_physics_of_persistence.md#naming-the-trade-off-precisely-write-read-and-space-amplification)
made concrete (no structure minimizes read, write, *and* space cost simultaneously), CAP
theorem forces a consistency-vs-availability choice under partition, and every replication
strategy trades latency against durability against cost. **"Which database is best" is not
a coherent question** until a workload is specified — the coherent question is always
**"which axis am I choosing to optimize, and what am I consciously willing to pay on the
others."**

## A Brief History: Why a Taxonomy Needs to Exist At All

Fashion-driven selection isn't just a junior-engineer habit — it's the reflex left over from
several decades where there genuinely was only one dominant model. **Picking a storage model
that fights a workload's natural shape is the data-model version of [Part 6's mechanical
sympathy](06_mechanical_sympathy_and_physics_of_latency.md#mechanical-sympathy-working-with-the-machine-not-against-it):
fighting the grain instead of working with it** — and the history below is the concrete
story of an entire industry doing exactly that at scale, until it stopped working.

### Codd, 1970: The Paper That Created "The One Model"

Edgar F. Codd, then at IBM, published *"A Relational Model of Data for Large Shared Data
Banks"* (Communications of the ACM, 1970). **The problem it solved**: the databases before
it — IBM's own IMS (hierarchical), the CODASYL network model — made querying mean
physically navigating explicit pointer paths baked into how the data happened to be stored;
the logical question you wanted to ask and the physical path you had to walk were the same
thing. **Codd's insight**: represent everything uniformly as **relations** — tables of
tuples — and query them with declarative predicate logic (state *what* you want, not *how*
to reach it), letting the database engine, not the programmer, figure out the access path.
Codd's own term for this was **data independence**: the first time the logical model was
decoupled from physical storage.

### Normalization and 3NF: Store Every Fact Exactly Once

Codd (and later, with Raymond Boyce) formalized **normal forms** — design rules eliminating
redundancy. **Third Normal Form (3NF)**: every non-key attribute depends on the key, the
whole key, and nothing but the key — no fact stored twice. This isn't an aesthetic
preference; duplicated facts create three concrete, named failure modes: an **update
anomaly** (a fact is duplicated across rows, one copy gets updated, the others don't, and the
data now silently disagrees with itself), an **insert anomaly** (a fact can't be recorded
until an unrelated row happens to exist to attach it to), and a **delete anomaly** (deleting
the one row holding a fact destroys the fact entirely, with no other copy to fall back on).
Normalization is **data integrity enforced by structure**: one source of truth per fact,
referenced by foreign key rather than copied.

### ACID, Fully Unpacked

[Part 2's ACID vs. BASE section](02_data_and_consistency.md#acid-vs-base) named the four
letters; here's each one's actual mechanism:

- **Atomicity** — all-or-nothing. Needs more than [Part 10's
  WAL](10_physics_of_persistence.md#the-write-ahead-log-making-durability-affordable) (which
  only replays *forward*) — an **undo** mechanism is required too, to cleanly roll back a
  transaction that aborts partway through, leaving no partial effect behind.
- **Consistency** — a transaction moves the database between states that satisfy its
  declared constraints (foreign keys, uniqueness, check constraints). **Worth flagging
  explicitly, because it's a genuinely common conflation**: this is a *completely different*
  "C" from CAP theorem's Consistency (linearizable reads across replicas). ACID's C is about
  the schema's own integrity rules never being violated — it's mostly a *consequence* of the
  other three ACID properties plus the declared constraints, not an independent mechanism of
  its own, and it has nothing to do with replica agreement.
- **Isolation** — concurrent transactions behave as if run one at a time, even while
  physically interleaved, at a chosen strength (Read Committed → Repeatable Read →
  Serializable, increasingly strict), enforced via locking (two-phase locking) or **MVCC**
  (multi-version concurrency control — Postgres's approach: keep multiple versions of a row
  so readers never block writers and vice versa).
- **Durability** — already fully covered: `fsync` + write-ahead log, [Part
  10](10_physics_of_persistence.md#fsync-the-physical-line-between-written-and-durable).

### The Join Tax

3NF's entire mechanism is decomposition — splitting one fact across many tables specifically
to guarantee it's stored once. The bill comes due at read time: reconstructing "one order,
with its customer, its line items, its product names" means **joining** several tables back
together — nested-loop, hash, or merge join, real CPU and I/O, multiplying with every
additional table involved. Distributed, it gets far worse: a join across shards living on
different machines means shipping data across the network mid-query — [Part 6/9's
distance-cost
argument](06_mechanical_sympathy_and_physics_of_latency.md#distance-of-data-one-physical-idea-two-different-scales)
applied to query execution itself, not just storage access. This is the exact trade
normalization makes, stated plainly: **integrity now, reconstruction cost later** — a
RUM-conjecture-shaped trade wearing a different name.

### Impedance Mismatch

The friction between how an application naturally models data — objects, nested structures,
inheritance, references — and the relational model's flat, tabular, set-based shape, which
has no native concept of either. Bridging the gap requires an **ORM** (Hibernate,
SQLAlchemy, ActiveRecord), itself a leaky abstraction (the **N+1 query problem** — silently
issuing one query per row instead of one query total — is the classic symptom). This
mismatch, not just scale, is one of the direct historical arguments *for* document
databases: a JSON-shaped document matches an application object's actual shape far more
closely than a normalized relational schema does, with no translation layer required at all.

### ~2005: Google and Amazon Hit the Wall — NoSQL Begins With Key-Value Stores

By the mid-2000s, Google and Amazon were operating at a scale where the relational model's
join-heavy, strongly-consistent, vertically-scaled default became the actual bottleneck, not
a convenience. Two papers mark the moment:

- **Google's Bigtable** (OSDI 2006) — a distributed, structured store built because
  relational engines of the era simply couldn't be sharded to the scale Google's crawl and
  index data required.
- **Amazon's Dynamo** (SOSP 2007) — built explicitly because a shopping cart has to always
  accept a write, even mid-partition; that requirement meant deliberately trading ACID's
  strong consistency for availability — a conscious CAP-theorem choice, not a compromise
  forced by ignorance. Dynamo is also the actual origin of [quorum reads/writes and
  consistent hashing](02_data_and_consistency.md#quorum-based-replication-n-w-r), both
  already documented elsewhere in this repo.

The first practical systems that followed — Riak, Voldemort, and later Cassandra
(explicitly merging Dynamo's distribution model with Bigtable's data model) — were
**key-value stores**: the simplest possible access pattern, chosen first precisely because
it discards both joins and rigid schema, the two things the relational model could no longer
deliver at that scale without becoming the bottleneck itself.

### The Second Child: Document Stores, Born From Impedance Mismatch

Where key-value stores answered a *scale* problem, document databases (MongoDB, CouchDB)
were largely a direct answer to the *impedance mismatch* problem named above: store the
application's actual object shape — nested, JSON-like — with no ORM translation layer and
no join needed to fetch "this one entity plus everything naturally attached to it."
Underneath, most document stores still run on a familiar engine — MongoDB's WiredTiger
defaults to a B-tree, exactly [Part 10's
structure](10_physics_of_persistence.md#b-trees-fully-unpacked-optimizing-for-reads-by-paying-on-writes)
— what changed is the *unit* stored and queried, not the underlying storage physics.

**Relationship management in a document store — two options, both eventually painful**:

- **Embedding** — nest related data directly inside the parent document (a user document
  with its last 10 orders embedded as an array). One read gets the whole shape, no join —
  but it quietly reintroduces exactly what 3NF eliminated: if a fact (a product name)
  appears embedded across thousands of order documents, updating it means touching every
  embedded copy or accepting staleness. The **update anomaly**, back again, just relocated.
- **Referencing** — store just an ID, like a foreign key, and fetch the referenced document
  separately. This avoids duplication, but most document databases historically offered no
  real server-side join, so following a reference means the *application* issues a second
  query, reads an ID from the result, issues a third, and so on. One hop is mildly
  annoying; the failure mode is **multiple hops**, because each additional hop doesn't just
  add one more query — it multiplies: hop 2 needs a lookup for *every* result from hop 1,
  hop 3 for every result from hop 2. The N+1 problem, except now unavoidable and compounding
  per hop instead of per row.

**Why highly interconnected data specifically becomes a nightmare here**: a document model
is excellent when the real-world entity genuinely is a tree with one clear owner — an order
and its line items, a post and its comments (this "one aggregate root, clear ownership
boundary" is literally the Domain-Driven Design "aggregate" pattern, exactly the shape
document stores were built for). It breaks down once the data is actually a **graph, not a
tree** — many-to-many relationships where the *relationships themselves* are what the query
cares about: a social network, a fraud ring linked by shared devices and transfers, a
recommendation path. There, embedding duplicates endlessly and referencing turns into a
combinatorial chain of application-side round trips — neither option is good, because the
document model was never built to answer "how are these things connected," only "give me
this thing and what's nested under it."

### The Myth of "Schema-less": Schema-on-Write vs. Schema-on-Read

Document stores are commonly marketed — and believed, at junior level — as
**schema-less**: throw any JSON shape in, no upfront modeling required, total flexibility
with no downside. This is misleading in a precise, worth-naming way.

**The reality**: data always has a schema, because code that consumes it always has
expectations — `user.email.toLowerCase()` cannot be written without silently assuming
`email` exists and is a string, and that assumption *is* a schema, whether or not any engine
ever wrote it down. The real question was never "schema or no schema" — it's **when is the
schema checked, and who pays when it's wrong**:

- **SQL — schema-on-write.** Column names, types, and constraints are declared upfront and
  enforced by the engine on every write; an `INSERT` violating the schema is rejected
  immediately, before bad data is ever stored. The validation cost is paid **once**,
  centrally, by the writer.
- **NoSQL document stores — schema-on-read.** No engine-enforced structure at write time —
  any shape can be inserted. The schema is **implicit** instead: defined entirely by
  whatever shape the application code *expects* when it later reads the data back,
  undocumented and re-derived independently by every reader.

**The concrete costs this shifts onto reads, not eliminates**:

1. **Schema drift becomes silent and permanent** — documents written by different app
   versions, a buggy client, or a half-finished migration can have genuinely different
   shapes in the *same* collection (some have `phone_number`, some don't; a later redesign
   stores it as `{country_code, number}` instead of a plain string). Every reader must now
   defensively check presence and type, re-implementing per-reader the exact validation a
   relational engine would have done once, centrally, for free.
2. **Migrations never actually finish** — a relational `ALTER TABLE ADD COLUMN` runs once
   and the system is consistent afterward; schema-on-read "migration" usually means
   branching read code that keeps understanding *every historical shape the collection has
   ever contained* — the migration accumulates as permanent read-side complexity instead of
   completing.
3. **No safety net for mistakes at write time** — a schema-on-write engine rejects `INSERT
   INTO users (emial) VALUES (...)` outright, catching a typo at the point of the mistake.
   A schema-on-read store happily persists the typo — the error surfaces later, silently, in
   whatever reader expected `email` and never finds it.

**Why this is nonetheless a legitimate, deliberate trade, not simply "worse"**: it directly
answers the impedance-mismatch and schema-rigidity frustrations already named above — an
application iterating on its data model doesn't need a coordinated migration every time a
field changes, and genuinely heterogeneous data (an event-logging system where different
event types naturally carry different fields) would be fighting its own grain forced into
one rigid table. It's the same **"same tax, just relocated"** pattern already established
for write amplification and the join tax: pay validation once, centrally, at write time — or
pay it repeatedly, decentralized, at read time, for the life of the data. Worth naming as
the tell that this trade is real: mature document databases (MongoDB added JSON Schema
validation around 2018) increasingly offer *optional* write-time enforcement anyway — teams
feeling schema-on-read's pain at scale often end up wanting some of schema-on-write back.

### The Third Child: Graph Databases, Built Specifically for Relationships

A graph database's core structural difference is **index-free adjacency** (Neo4j's own term
for it): each node stores a *direct physical pointer* to its adjacent nodes and
relationships, right in the storage layer — not a foreign key re-resolved through an index
at query time. Walking from a node to its neighbor is a pointer dereference, one hop,
regardless of how many total nodes exist anywhere else in the database. The consequence is
the entire point: **a graph query's cost is proportional to the size of the subgraph
actually touched — not to the size of the whole dataset.** Neither a relational join (cost
tied to table/index size and to how many join steps are written) nor a document reference
chain (cost tied to N sequential application round trips) has that property.

**The concrete example — where SQL screams and a graph database doesn't**: "find everyone
connected to Alice within 4 hops" — the general shape behind both social friend-of-friend
queries and fraud-ring detection.

In SQL, this needs a **recursive CTE** — a self-join repeated once per hop level, with no
way to bound the intermediate result size in advance:

```sql
WITH RECURSIVE friends_of_friends AS (
  SELECT friend_id, 1 AS depth FROM friendships WHERE user_id = 'alice'
  UNION ALL
  SELECT f.friend_id, ff.depth + 1
  FROM friendships f
  JOIN friends_of_friends ff ON f.user_id = ff.friend_id
  WHERE ff.depth < 4
)
SELECT DISTINCT friend_id FROM friends_of_friends;
```

Each recursion level is a full join against the friendships table, and the intermediate
rows can explode combinatorially — if the average person has 200 friends, a naive depth-4
expansion is on the order of 200⁴ paths before dedup. The query planner is reasoning about
join cost at every level, and that cost scales with the table, not with Alice's actual
social neighborhood.

In a graph database (Cypher):

```cypher
MATCH (alice:Person {name: 'Alice'})-[:FRIEND*1..4]-(connection)
RETURN DISTINCT connection
```

One expression, natively supporting a variable-length path. Thanks to index-free adjacency,
the engine just walks stored pointers hop by hop — cost proportional to Alice's actual
traversed neighborhood, indifferent to how many other people exist in the entire database.
Same question, fundamentally different cost model: **join-combinatorics-over-the-whole-table**
versus **pointer-walk-over-the-touched-subgraph** — precisely why this query pattern is the
textbook case for reaching for a graph database instead of writing another recursive
self-join.

**This is the whole doc's thesis, playing out historically before it became a checklist**:
forcing a join-heavy, strongly-consistent, normalized model onto a workload that
fundamentally needed massive horizontal scale and always-on availability was fighting that
workload's grain — exactly like forcing random I/O onto a spinning disk — and the industry's
answer wasn't "a better relational database." Three different children came from three
different frustrations with the same parent: key-value stores from a scale problem, document
stores from an impedance-mismatch problem, graph databases from a relationships-as-first-class
problem neither of the first two solved — each naming that a *different* model fit a
*different* shape.

### NewSQL: The Relational Dream, Reclaimed at Scale

The three children each answered scale by *giving up* a specific piece of Codd's original
dream — joins, schema rigidity, or strong consistency. **NewSQL** (Matthew Aslett, 451
Group, ~2011) asks a different question: keep SQL, ACID, and multi-row transactions, *and*
get horizontal scale and region-failure survival — using a mechanism that simply wasn't
practical to deploy in 1970, or even in 2005. **Google Spanner** (OSDI 2012) and
**CockroachDB** (open-source, explicitly modeled on the Spanner paper) are the flagship
examples.

**The mechanism, precisely — distributed consensus (Raft)**. In a single-leader database,
"did this write commit" is trivially well-defined — the leader decided. Once data is
replicated across machines and regions for real disaster survival, the replicas must
*agree* on the order and content of writes even when some are slow, unreachable, or
crashed. **Raft** (Ongaro & Ousterhout, 2014 — designed to be more understandable than
Paxos while giving equivalent guarantees) solves this:

- Data is split into shards — CockroachDB calls them **ranges**, conceptually the same idea
  as [GFS's chunks](02_data_and_consistency.md#gfs-2003-the-reference-architecture), just
  for a relational engine — each replicated (typically 3x) and managed by its own
  independent Raft group with its own elected leader, critical for horizontal scale since
  there's no single global leader for the whole database.
- Every write to a range must reach a **majority (quorum)** of that range's Raft group
  before it's considered committed — the exact same majority-overlap reasoning already
  documented for [Dynamo-style quorums
  (W+R>N)](02_data_and_consistency.md#quorum-based-replication-n-w-r): any two majorities
  out of N nodes always overlap by at least one, which is what guarantees a newly-elected
  leader after a failure has seen every previously committed write.
- **Spanner adds one more piece beyond plain Raft/Paxos**: **TrueTime**, a
  globally-synchronized clock API backed by GPS and atomic clocks in Google's own
  datacenters, giving a tightly bounded uncertainty window on "what time is it right now" —
  letting Spanner assign globally meaningful commit timestamps and guarantee external
  consistency (linearizability) across the *entire* planet-scale database, not just within
  one consensus group. CockroachDB, without access to that specialized hardware, uses
  **Hybrid Logical Clocks (HLC)** instead — a real, documented architectural difference
  between the two systems.

**The trade-off, made mechanically precise**: in a single-leader system, a write commits as
soon as the leader's local WAL is fsynced — [Part
10](10_physics_of_persistence.md#fsync-the-physical-line-between-written-and-durable),
microseconds to low milliseconds. In a Raft-based NewSQL system, a write **cannot** commit
until a majority of that range's replicas acknowledge — and if the group is deliberately
spread across regions (the entire point, since that's what lets the system survive a whole
region failing), write latency is now bounded below by the **round-trip network time to the
nearest majority of replicas**, not by local disk speed at all. This is [Part 2's
sync-replication
argument](02_data_and_consistency.md#sync-vs-async-replication-the-same-fsync-trade-off-at-cluster-scale)
taken to its logical extreme: consensus *is* synchronous replication, applied per
transaction, with a real agreement protocol instead of ad hoc leader-follower lag.
Concretely: a 3-region deployment (US/Europe/Asia) means every write needs acknowledgment
from at least 2 of 3 regions before committing — a write physically cannot commit faster
than that round trip, often tens to over a hundred milliseconds, no matter how fast the
local CPU or disk is. That's a hard physical floor, not a tunable inefficiency.

**The honest framing**: it's not that NewSQL is "slow" — a Raft group confined to one
region/AZ gets the same consistency guarantees at low-single-digit-millisecond latency,
since quorum round trips stay local. The cost is specifically the price of the
*combination*: strong consistency **and** surviving an entire region's loss, together, on
every single write. NewSQL doesn't cheat that trade — it makes it explicit and pays it
honestly.

### The Newest Arrival: Vector Databases — Similarity Search in High-Dimensional Space

Every branch so far answers some version of "find the row matching this key, range, or
predicate." Around 2018-2023, driven directly by the embeddings behind recommendation
systems and then LLM-based RAG, a genuinely new access pattern arrived that none of them
handle: **given a point in a 768- or 1536-dimensional space, find the K points nearest to
it** — similarity, not equality.

**The problem, precisely**: an embedding model turns unstructured data (text, an image, a
sound clip) into a dense numeric vector, engineered so that *semantic or perceptual
similarity corresponds to geometric closeness* in that high-dimensional space. The query is
never "give me the exact match" — it's "give me the K nearest vectors to this one." A
B-tree's [guided
descent](10_physics_of_persistence.md#b-trees-fully-unpacked-optimizing-for-reads-by-paying-on-writes)
and a hash index's O(1) lookup both assume exact-match or ordered comparison on a handful of
fields — neither generalizes to "nearest neighbor in 1,536 dimensions," and a brute-force
scan computing distance to every stored vector is exactly [Part 2's full table
scan](02_data_and_consistency.md#indexing-why-databases-dont-scan-everything) problem,
transplanted into a completely different geometry.

**Why a k-d tree (the classic spatial index) doesn't just generalize upward**: the **curse
of dimensionality** — as dimensionality grows into the hundreds, the intuitive notion of
"nearby" degrades: distances between points concentrate, and the nearest and farthest
neighbors stop being reliably distinguishable. Exact spatial indexes that work well in 2-3
dimensions decay toward effectively linear scan performance at embedding-model scale, which
is why vector databases universally reach for **Approximate Nearest Neighbor (ANN)**
algorithms instead of an exact index — deliberately trading perfect recall for speed, the
same kind of probabilistic trade [bloom filters](10_physics_of_persistence.md#bloom-filters-precisely-the-probabilistic-math)
already made for set membership, just applied to geometric proximity:

- **HNSW (Hierarchical Navigable Small World graphs)** — the dominant modern approach
  (Pinecone, Weaviate, Qdrant, Milvus, pgvector's HNSW index): a multi-layer graph where
  each vector connects to its approximate nearest neighbors; a search starts at a sparse top
  layer and greedily navigates toward the query vector, descending through denser layers —
  giving roughly O(log n) search instead of O(n), conceptually a skip list built out of
  geometric proximity instead of sorted order.
- **IVF (Inverted File Index)**, often paired with product quantization for memory
  compression (FAISS, many managed vector DBs) — partition the space into clusters via
  k-means, and at query time search only the clusters nearest the query vector instead of
  the whole dataset.

**Where this fits the six axes**: it's a genuinely new sixth access-pattern row (below), the
write shape is usually append-heavy with periodic reindexing (ANN graphs are more expensive
to update incrementally than a B-tree page), and consistency is almost always eventual —
RAG retrieval tolerates a just-inserted document not appearing in results for a moment far
better than it tolerates slow reads.

**The hidden cost worth naming explicitly — embedding-version drift**: this is
[schema-on-read's schema-drift problem](#the-myth-of-schema-less-schema-on-write-vs-schema-on-read),
recurring in a form the database itself has even less hope of catching. If the embedding
model producing vectors is upgraded or retrained, vectors from the old model and vectors
from the new model are **no longer comparable in the same space** — the database will
happily compute a "nearest neighbor" between them and return a confidently wrong answer,
with no error, no constraint violation, nothing a schema (even a document store's implicit
one) could have caught, because the geometry itself silently changed underneath the data.
**NoSQL's flexibility was never actually free — it relocates the discipline of staying
structured from the database engine onto team process, versioning discipline, and code
review; vector databases just make that relocation more consequential, since here the
"structure" being violated isn't a field name, it's the meaning of every number in the
vector.**

## The Six Axes: What "First Principles" Actually Means Here

Six questions, asked *before* naming a technology, not after. Each one maps directly onto
mechanism already established in this repo — this part's job is turning that mechanism into
a decision procedure.

### 1. Access Pattern — How Is the Data Actually Queried?

The single most workload-defining question, and the one fashion-driven selection skips most
often. [Part 2's indexing section](02_data_and_consistency.md#indexing-why-databases-dont-scan-everything)
and [Part 10's B-tree/LSM-tree read paths](10_physics_of_persistence.md#b-trees-fully-unpacked-optimizing-for-reads-by-paying-on-writes)
already did the mechanical work here — this axis is about naming *which* pattern the actual
workload has:

| Pattern | What it means | Structure that fits |
|---|---|---|
| **Point lookup** (`GET key`) | Exact-match retrieval by a known key, no ordering needed | Hash index / pure key-value store — O(1), can't range-query, [Part 2](02_data_and_consistency.md#indexing-why-databases-dont-scan-everything) already names this trade-off |
| **Range scan** (`WHERE created_at BETWEEN X AND Y`) | Retrieval of a contiguous, ordered slice | B-tree or sorted LSM-tree — requires the data to be *kept* in sorted order, which a hash index structurally cannot provide |
| **Multi-predicate / relational** (joins, arbitrary `WHERE` clauses across columns) | Queries that weren't known in advance, spanning multiple entities | Relational (B-tree-backed) with a real query planner — the workload a bootcamp's "just use Postgres" default actually fits, when it fits at all |
| **Analytical scan / aggregation** (`SUM`, `GROUP BY` across millions of rows, few columns) | Reading most of a huge table, but only a handful of its columns | Columnar/OLAP (Parquet, ClickHouse, Snowflake) — [Part 10's scope note](10_physics_of_persistence.md#scope-note--a-third-camp-this-doc-doesnt-cover) already flags this as a third camp, neither B-tree nor LSM-tree |
| **Graph traversal** (multi-hop relationship queries) | "Friends of friends," recommendation paths, fraud rings | Graph database (Neo4j) — adjacency is the primary structure, not a foreign key join reconstructed per query |
| **Similarity search** (k-nearest-neighbor in embedding space) | "Find documents/images semantically similar to this one," RAG retrieval | Vector database (Pinecone, Weaviate, pgvector) with an ANN index (HNSW, IVF) — [detailed below](#the-newest-arrival-vector-databases-similarity-search-in-high-dimensional-space); geometric proximity, not equality or order |

**The question to actually ask**: *do I fetch by exact key, by range, by an arbitrary
predicate I can't predict in advance, by scanning most of the table for an aggregate, or by
walking relationships?* Naming this correctly eliminates most of the field before any other
axis is even considered.

**Turning the table into a diagnostic — the actual question to ask about a real query, and
what the answer implies**:

- *"Do I fetch this by a single known key — a user profile by `user_id`, a product by SKU,
  a session by session token?"* → **Point lookup** → a key-value store (Redis, DynamoDB, or
  a plain hash index) is the direct fit — reaching for a full relational engine here buys
  join capability and a query planner that this specific query never uses.
- *"Do I need 'all orders placed between March 1st and April 1st' or 'the last 50 events for
  this device'?"* → **Range scan** → this requires the data to be *kept in sorted order* on
  the query key, which rules out a pure hash-based key-value store structurally, not just as
  a performance preference — a B-tree or a sorted LSM-tree (sorted SSTables) is required.
- *"Do I need 'find all users named X, in city Y, older than Z, who signed up last month' —
  a predicate I couldn't have hard-coded a single index for in advance?"* → **Multi-predicate
  / relational** → a real query planner that can combine indexes and evaluate arbitrary
  `WHERE` clauses is doing real work here; this is the shape a relational engine is actually
  built for, not just a historical default.
- *"Do I need 'total revenue by region, last quarter' or 'average session length across 500
  million rows,' touching most of a huge table but only two or three of its columns?"* →
  **Analytical scan / aggregation** → a columnar engine, which reads only the touched
  columns off disk instead of full rows, wins by an order of magnitude here — a row-store
  (relational or KV) pays for every untouched column it's forced to read alongside the ones
  that matter.
- *"Do I need 'friends of friends of Alice within 4 hops' or 'is this transaction connected
  to a known fraud ring through any chain of shared devices'?"* → **Graph traversal** → per
  [this doc's own worked example above](#the-third-child-graph-databases-built-specifically-for-relationships),
  this is exactly the case where a graph database's index-free adjacency wins outright
  against a relational self-join or a document reference chain.
- *"Do I need 'find the 10 support articles most semantically similar to this customer's
  question' — where there's no exact keyword match, only meaning?"* → **Similarity search**
  → [detailed above](#the-newest-arrival-vector-databases-similarity-search-in-high-dimensional-space);
  neither a B-tree's ordering nor a hash index's equality generalizes to "nearest in
  high-dimensional space," which is precisely why this pattern needed its own new structure
  (ANN indexes) rather than a cleverer use of an existing one.

**Why "point lookup by ID" is worth calling out as the clearest, most common case**: it's
the single most frequent access pattern in real systems (a user by ID, a product by SKU, a
cache entry by key) and also the one fashion-driven selection most often gets wrong in the
*expensive* direction — reaching for a full relational database, with its query planner,
join engine, and B-tree's [guided-descent 3-4 page
reads](10_physics_of_persistence.md#b-trees-fully-unpacked-optimizing-for-reads-by-paying-on-writes),
to serve a query that a key-value store answers in one hash lookup with none of that
machinery. The relational engine isn't wrong here — it's just answering a harder, more
general question than the one actually being asked, and paying for that generality on every
single request.

### 2. Data Size — Does It Fit on One Machine, and Where in the Storage Hierarchy?

This is [Part 2's capacity problem](02_data_and_consistency.md#why-one-machine-stops-being-enough--two-different-problems)
stated as a question rather than a mechanism: past a certain volume, no single machine holds
or serves it all, and **sharding** becomes necessary — with all the added complexity of
cross-shard queries and rebalancing that a single-node system never has to solve. Just as
important, and more often skipped: **which storage tier does the working set actually need
to live in?** [Part 6's storage-economics
section](06_mechanical_sympathy_and_physics_of_latency.md#the-economics-of-machine-cost-is-physics)
already gave the numbers — RAM runs roughly ~100x pricier per GB than SSD, SSD roughly ~10x
pricier than cold/archival storage — so this axis is really asking: *is my hot working set
small enough to justify RAM's premium (Redis, Memcached), does it need SSD's random-access
speed at a moderate premium, or is most of this data touched rarely enough that cold/archive
tiers are the economically correct answer regardless of how "slow" that sounds in isolation?*

### 3. Latency Budget — What SLA Does Each Request Actually Need?

Every other axis is downstream of this one, because the latency budget determines which
tier of [Part 6's physical hierarchy](06_mechanical_sympathy_and_physics_of_latency.md#hardware-reality-the-abstraction-hides-the-physics-not-the-cost)
is even affordable:

- **Sub-millisecond, real-time** (ad bidding, a feature-flag check, a session lookup on
  every request) — the budget doesn't have room for a disk seek at all, let alone a network
  hop to a remote replica; this forces an in-memory store, and forces **synchronous**
  cross-replica consistency off the table entirely if any replica is more than a few
  milliseconds away ([Part 2's sync/async
  argument](02_data_and_consistency.md#sync-vs-async-replication-the-same-fsync-trade-off-at-cluster-scale)).
- **Tens of milliseconds, interactive** (a page load, an API response) — affords SSD-backed
  reads and same-region synchronous replication, but not a cross-continent round trip
  ([Part 9](09_dns_bgp_and_the_edge.md)'s geography numbers) inside the request path.
- **Seconds to minutes, batch/analytical** (a nightly aggregation, a dashboard refresh) — can
  afford columnar/cold-tier storage and cross-region or even cross-cloud data movement, since
  nothing in the request path is waiting synchronously on it.

**The question to actually ask**: *what's the p99 target for this specific access pattern,
and which physical tier from Part 6 can actually deliver that number* — not "what feels
fast enough," a number with an actual SLA behind it.

### 4. Consistency Model — What Does "Correct" Mean for This Data?

[Part 2's consistency spectrum](02_data_and_consistency.md#the-consistency-spectrum-its-not-just-strong-vs-eventual)
and [ACID vs. BASE](02_data_and_consistency.md#acid-vs-base) already name the options; this
axis is choosing among them deliberately rather than by default. A financial ledger cannot
tolerate a partially-applied transfer — it needs **strong consistency** and **ACID**, full
stop, and the throughput/scalability cost that comes with it is simply the price of
correctness. A social media like-counter can be wrong for a few seconds with zero
user-visible harm — **eventual consistency** and **BASE** aren't a compromise there, they're
the objectively correct choice, since paying for strong consistency would be pure waste.
**The question to actually ask**: *if two replicas of this data briefly disagree, what is
the actual, concrete cost — and is that cost closer to "a customer loses money" or "a UI
counter is off by one for a second"?*

### 5. Write Amplification — What Does This Workload Do to the Storage Engine's Write Path?

This axis is [Part 10's B-tree-vs-LSM-tree trade-off](10_physics_of_persistence.md#naming-the-trade-off-precisely-write-read-and-space-amplification)
applied as a filter, plus [Part 6's SSD write-amplification
tax](06_mechanical_sympathy_and_physics_of_latency.md#write-amplification-precisely-the-waf-formula)
stacked on top of it when the underlying medium is flash. A B-tree pays a random-access
write cost on every update (page rewrite, possible cascading splits) — fine for a
read-heavy, low-update workload, expensive for high-volume writes over an effectively random
keyspace. An LSM-tree defers that cost to background compaction, trading it for read
amplification instead. **Critically, these two amplification sources compound, not
substitute**: a B-tree engine's small random page rewrites, running on an SSD, are exactly
the access pattern that maximizes the SSD's *own* write amplification (scattered small
writes hit many different erase blocks instead of filling one sequentially) — so a
write-heavy, random-key workload on a B-tree-over-SSD stack pays both taxes at once. **The
question to actually ask**: *what's my read/write ratio, is the keyspace being written
effectively random or naturally clustered/sequential, and have I checked which storage
engine that shape actually favors — or picked one before asking?*

### 6. Failure Modes — What, Specifically, Has to Survive?

The axis most often skipped entirely, because "the database handles durability" is treated
as a single, monolithic guarantee rather than several genuinely different ones, each solved
by a different mechanism already covered in this repo:

| Failure class | What it means | Mechanism that actually protects against it |
|---|---|---|
| **Process/machine crash before a write is flushed** | The write was acknowledged but the in-memory structure holding it never made it to the main table | `fsync` + write-ahead log — [Part 10](10_physics_of_persistence.md#the-write-ahead-log-making-durability-affordable) |
| **Single disk/machine failure** | An entire physical copy of the data is gone | Replication — [Part 2](02_data_and_consistency.md#replication-distributed-truth-gfs-and-what-11-nines-actually-means) |
| **Silent bit-level corruption** | Data already durably written quietly goes wrong, with no crash and no error reported | Checksums (+ scrubbing, self-healing) — [Part 6](06_mechanical_sympathy_and_physics_of_latency.md#the-invisible-enemy-bit-rot-silent-data-corruption-and-checksums) |
| **Rack/datacenter failure** | An entire facility becomes unreachable | Multi-rack/multi-AZ replication (GFS's rack-spread, Azure ZRS) — [Part 2](02_data_and_consistency.md#gfs-2003-the-reference-architecture) |
| **Entire region failure** | A geographic region (natural disaster, major outage) goes down | Cross-region replication (Azure GRS, S3 cross-region replication) — [Part 2](02_data_and_consistency.md#cloud-analogs-s3-and-azure-grs) |
| **Human error** (bad migration, accidental `DROP TABLE`, bad deploy) | The data is technically "durable" and perfectly replicated — the *mistake* replicated too | Point-in-time recovery / backups — a genuinely separate mechanism from all of the above, since replication faithfully propagates a human mistake exactly as fast as it propagates a legitimate write |

**The question to actually ask**: *which of these six failure classes am I actually
defending against with this choice, and which am I implicitly assuming "the database
handles" without having verified it does?* Notice that no single mechanism covers every row
— a system can have a flawless WAL and full cross-region replication and *still* lose data
to an unbacked-up bad migration, because replication and backup are answering different
questions.

## The Anti-Pattern, Named Explicitly: Fashion-Driven Selection

Three concrete junior-level patterns, each traceable to skipping one specific axis above:

- **"I'll use MongoDB because it's what I know"** — for a workload that turns out to be
  highly relational, needing multi-table joins and cross-entity transactions. This skips
  **axis 1 (access pattern)**: the schema's actual shape was never checked against what the
  chosen engine is structurally good at.
- **"I'll use Postgres because it's the default"** — for a write-heavy, effectively-random-key
  time-series ingestion workload (device telemetry, event streams). This skips **axis 5
  (write amplification)**: it's [Part 10's worked
  example](10_physics_of_persistence.md#worked-example-the-same-workload-two-engines)
  almost exactly, the textbook case where a B-tree pays a random-write tax an LSM-tree
  simply doesn't.
- **"Everyone at [well-known company] uses this, so it must be safe"** — without checking
  whether that company's *scale*, *consistency needs*, or *failure tolerance* have anything
  in common with the system actually being built. A pattern that's correct at planet-scale,
  eventually-consistent, BASE-style throughput can be actively wrong for a small system that
  actually needed ACID correctness more than it needed that scale.

**The fix in one sentence**: run the six axes as an explicit checklist *before* naming a
technology — the technology choice should be the *last* step, a consequence of the six
answers, never the first.

## Worked Decision Framework: Four Scenarios Through the Six Axes

| Scenario | Access pattern | Data size | Latency budget | Consistency | Write shape | Dominant failure mode | Fits |
|---|---|---|---|---|---|---|---|
| **User session store** | Point lookup by session ID | Small, fits in RAM cluster-wide | Sub-millisecond | Eventual is fine — a stale session read is rarely consequential | Frequent overwrite, small values | Process/node crash (sessions are often acceptably ephemeral) | Redis / Memcached — in-memory, hash-indexed |
| **Financial ledger** | Point lookup + range scan (statement queries) + multi-row transactions | Moderate, single-region | Tens of ms, interactive | Strong — ACID, no partial transfers, ever | Moderate volume, not the bottleneck | All six failure classes matter, especially human error (backups non-negotiable) | Postgres / MySQL — B-tree, ACID, mature backup tooling |
| **IoT telemetry ingestion** | Append-heavy writes, range scan by timestamp | Very large, sharded | Writes: tens of ms; reads: batch-tolerant | Eventual — a delayed sensor reading is not the failure mode to design around | Extremely high volume, near-random device-ID keys | Disk/rack failure at scale (replication factor matters more than any single mechanism) | Cassandra / a wide-column LSM-tree store — [Part 10's textbook LSM case](10_physics_of_persistence.md#worked-example-the-same-workload-two-engines) |
| **Product catalog search / analytics dashboard** | Multi-predicate filtering + aggregation across millions of rows, few columns | Large, read-heavy | Seconds, batch-tolerant | Eventual, refreshed periodically | Write-rarely, bulk-loaded | Region failure (analytics is rarely the record-of-truth copy) | Columnar/OLAP (ClickHouse, Snowflake, Parquet-on-object-storage) — [Part 10's third camp](10_physics_of_persistence.md#scope-note--a-third-camp-this-doc-doesnt-cover) |

**Reading the table correctly**: the "Fits" column is never the starting point — it's what
*falls out* once the other six columns are answered honestly for the actual workload. Two
systems that look superficially similar ("we store records and query them") can land in
completely different rows once latency budget and write shape are actually specified.

## The Golden Hammer Fallacy and Its Antidote: Polyglot Persistence

The worked table above shows four *separate* scenarios landing in four different rows. In
practice, a single real system is rarely just one of those rows — it's usually several of
them at once, which is exactly what makes the difference between the failure mode this doc
opened with and its practical fix worth naming explicitly.

**The Golden Hammer fallacy** is the formal name for the anti-pattern this doc has been
calling fashion-driven selection: "if all you have is a hammer, everything looks like a
nail" (Abraham Maslow, *The Psychology of Science*, 1966 — also called "the law of the
instrument"). In storage terms: an engineer or team becomes deeply fluent in one database,
then reflexively reaches for it on every workload regardless of fit — not because the six
axes were evaluated and it won every time, but because familiarity substituted for
evaluation entirely.

**Polyglot persistence** (Martin Fowler and Pramod Sadalage, *NoSQL Distilled*, ~2011) is
the direct antidote: run the six-axes checklist **per data type within one system**, not
once for the whole application. A real product is rarely one workload — it's session data,
transactional data, high-write telemetry, full-text search, and cold analytical data all at
once, and forcing all of it through a single database is the Golden Hammer fallacy at the
architecture level, not just the individual-engineer level.

**Netflix, concretely** — one of the most publicly documented polyglot-persistence
architectures (via Netflix's own tech blog), with each choice mapping directly onto axes
already established in this doc:

| Data type | Technology | Why (the axes) |
|---|---|---|
| Session/personalization cache | **EVCache** (Netflix's layer on Memcached) | Sub-millisecond latency budget, point lookup, eventual consistency is fine — the "user session store" row above |
| Viewing history, user preferences | **Cassandra** | Enormous write volume across regions, near-random keys, must always accept a write even mid-partition — literally [Dynamo's original motivation](02_data_and_consistency.md#gfs-2003-the-reference-architecture), and Cassandra is Dynamo's distribution model merged with Bigtable's data model, per this doc's own history section |
| Billing / account data | **Relational (MySQL)** | Needs real ACID — a billing mistake is the "someone loses money" case from axis 4, not a candidate for eventual consistency |
| Search | **Elasticsearch** | Multi-predicate, full-text access pattern neither a B-tree nor an LSM-tree is built for |
| Video assets, logs, data lake | **S3 + a big-data analytics stack** | Massive volume, batch-tolerant latency, columnar/analytical access pattern — the cold-tier economics from [Part 6](06_mechanical_sympathy_and_physics_of_latency.md#the-economics-of-machine-cost-is-physics) |

**The nuance worth naming explicitly, so this isn't misread as "more databases is always
better"**: polyglot persistence only works if each technology was chosen by actually running
the six-axes checklist for its specific sub-workload. Adopting five trendy databases across
five teams *without* that discipline isn't polyglot persistence — it's the Golden Hammer
fallacy committed five times in parallel, now with the added operational cost of running
five different systems. **The win comes from the reasoning being deliberate for each data
type, not from the count of technologies in use.**

## Designing and Operating From First Principles

1. Have I named my access pattern precisely (point lookup, range scan, multi-predicate,
   analytical scan, graph traversal) — or am I assuming "a database" handles all of them
   equally well?
2. Do I know whether my data fits comfortably on one machine, and which storage tier (RAM,
   SSD, cold/archive) my actual working set belongs in — or am I defaulting to whatever tier
   my chosen engine happens to use?
3. Have I stated an actual p99 latency number for this workload, and checked which physical
   tier from Part 6 can deliver it — or am I reasoning from a vague sense of "fast enough"?
4. Have I named, concretely, what happens if two replicas briefly disagree — and is that
   cost closer to "someone loses money" or "a counter is off by one" — before picking a
   consistency model?
5. Do I know my read/write ratio and whether my write keyspace is random or
   naturally-ordered — and have I checked whether that shape favors a B-tree or an LSM-tree,
   or picked an engine before asking?
6. Have I named which of the six failure classes (crash, disk, silent corruption, rack,
   region, human error) I'm actually defending against with this choice — and which ones
   I'm implicitly assuming are covered without verifying?
7. If my reason for choosing this technology is "it's what I know" or "it's popular" or
   "it's what my last company used," have I gone back and checked it against the six axes
   anyway — or let familiarity substitute for that check?
8. Am I confident the technology choice came *after* the six answers, not before them?
9. If my system already uses several different databases, was each one chosen by running
   the six axes for its specific sub-workload — or did each team just default to whatever
   was trending when they built their piece (Golden Hammer, committed once per team)?

## Key Takeaways

- **Fashion-driven database selection** — "it's what I know," "it's popular," "it's what my
  last company used" — is a pattern that never references the actual workload at all, which
  is exactly what makes it fashion rather than engineering.
- **Every database embodies a trade-off**: this isn't a slogan, it's the literal content of
  the RUM conjecture, CAP theorem, and every sync-vs-async replication decision already
  covered in this repo — "best database" is incoherent without a specified workload.
- The six axes — **access pattern, data size, latency budget, consistency model, write
  amplification, failure modes** — are the checklist that turns "which database" from a
  fashion question into an engineering one, and each maps directly onto mechanism already
  established in Parts 2, 6, and 10.
- **Access pattern** (point lookup vs. range scan vs. multi-predicate vs. analytical scan
  vs. graph traversal) eliminates most of the field before any other axis is considered.
- **Data size and latency budget together** determine which physical storage tier (RAM,
  SSD, cold/archive) is even affordable, per Part 6's storage economics.
- **Consistency model** should be chosen by naming the concrete cost of two replicas briefly
  disagreeing — not defaulted to "strong" out of caution or "eventual" out of trend-chasing.
- **Write amplification** from the storage engine (B-tree vs. LSM-tree) and from the medium
  (SSD's own WAF) *compound*, not substitute — a write-heavy, random-key workload on a
  B-tree-over-SSD stack pays both taxes simultaneously.
- **Failure modes are six genuinely different classes**, each requiring its own named
  mechanism (WAL/fsync, replication, checksums, multi-rack/AZ spread, cross-region
  replication, backups) — no single guarantee covers all six, and human error specifically
  is not solved by replication at all, since replication faithfully propagates mistakes too.
- The technology name should always be the **last** step of the decision, a consequence of
  the six answers — never the first.
- **The Golden Hammer fallacy** (Maslow, 1966) is fashion-driven selection's formal name:
  reaching for one familiar tool for every problem because familiarity substituted for
  evaluation, not because the six axes were actually run each time.
- **Polyglot persistence** (Fowler & Sadalage, ~2011) is the direct antidote: run the six
  axes *per data type* within one system rather than once for the whole application —
  Netflix's EVCache/Cassandra/MySQL/Elasticsearch/S3 split is a publicly documented example
  of exactly this reasoning applied per sub-workload.
- Polyglot persistence only works if each technology was chosen deliberately for its
  sub-workload — adopted without that discipline, multiple databases is just the Golden
  Hammer fallacy committed once per team, with added operational cost on top.
- **Vector databases** answer a genuinely new access pattern (similarity search in
  high-dimensional embedding space) that no prior structure generalizes to, using
  approximate nearest-neighbor indexes (HNSW, IVF) that trade perfect recall for speed —
  and they inherit schema-on-read's drift problem in a form the engine can't catch at all:
  an embedding-model upgrade silently makes old and new vectors incomparable, with no error.
- **"Flexible" and "schema-less" never eliminate the need for discipline — they relocate
  it.** NoSQL relocates it from the engine to every reader; vector databases relocate it to
  embedding-version governance. The discipline doesn't go away, only its location and who
  pays for it changes.
- **Access patterns are not answered once** — they drift as a system grows, which is the
  real argument for architecting with polyglot seams from the start rather than treating the
  six axes as a one-time checklist run before the first line of code.

## Quick Self-Check

- Why is "which database is best" not a coherent question on its own — what has to be
  specified before it becomes answerable?
- A team picks MongoDB "because it's what we know," and the workload turns out to need
  multi-table joins and cross-entity transactions. Which of the six axes did that decision
  skip, and what would asking it first have surfaced?
- Why do a B-tree's write amplification and an SSD's own write amplification compound
  rather than substitute for a write-heavy, random-key workload — trace the mechanism from
  both Part 6 and Part 10.
- Name a concrete workload where strong consistency is clearly correct, and one where it's
  clearly wasteful — what's the actual test that separates the two cases?
- Why doesn't cross-region replication protect against a human accidentally dropping a
  table — what failure class does it protect against instead, and what mechanism actually
  covers the human-error case?
- For the "IoT telemetry ingestion" scenario in the worked table, name which specific axis
  answer is the one that rules out a B-tree engine most decisively.
- What specific problem did Codd's 1970 relational model solve that the hierarchical/network
  databases before it didn't — what does "data independence" actually mean?
- Name the three anomalies (update, insert, delete) that 3NF normalization exists to
  prevent, and explain why each one is a consequence of storing the same fact more than
  once.
- ACID's "C" and CAP theorem's "C" are both called "Consistency." Explain precisely why
  they are different guarantees, and why conflating them is a common mistake.
- Why does a normalized, join-heavy schema get *disproportionately* more expensive at
  distributed scale rather than just proportionally more expensive — what specific cost does
  a cross-shard join add that a single-machine join doesn't pay?
- What specific, concrete requirement forced Amazon's Dynamo team to trade ACID's strong
  consistency for availability — and was that a compromise forced by ignorance, or a
  deliberate, informed CAP-theorem choice? Defend your answer.
- Why were key-value stores the *first* NoSQL systems to emerge, specifically, rather than
  document stores or graph databases — what two things does a key-value store discard that
  the relational model could no longer deliver at Google/Amazon's scale?
- A document store's "embedding" strategy avoids a join, but reintroduces a specific
  relational anomaly. Which one, and why does embedding recreate it structurally?
- Why does following a "referenced" relationship in a document store multiply round trips
  per hop rather than just adding one query per hop — trace the math for a 3-hop chain.
- What does "index-free adjacency" actually mean at the storage layer, and why does it make
  a graph traversal's cost proportional to the touched subgraph instead of the whole
  dataset?
- For the "find everyone within 4 hops of Alice" query, explain precisely why a SQL
  recursive CTE's cost can explode combinatorially while the equivalent Cypher query's cost
  doesn't — what's the one structural difference responsible?
- Why is "one aggregate root with a clear ownership boundary" (an order and its line items)
  exactly the shape a document store handles well, while a social graph is exactly the shape
  it handles badly — what's the structural distinction between the two (tree vs. graph)?
- Why is "schema-less" a myth rather than a literal description of a document store — if
  there's truly no schema enforced anywhere, why does `user.email.toLowerCase()` still make
  an assumption that counts as one?
- A document collection has some records with `phone_number` as a string and others (written
  after a later redesign) with it as `{country_code, number}`. Whose job was it to prevent
  this, and why didn't schema-on-read prevent it the way schema-on-write would have?
- Why doesn't a schema-on-read migration ever really "finish" the way an `ALTER TABLE ADD
  COLUMN` does — what accumulates instead, and where does it live?
- What's the precise difference between the Golden Hammer fallacy and picking one database
  for a genuinely single-workload system — why isn't using one database always the fallacy?
- Why does adopting five different databases across five teams, without running the six
  axes for each, not actually count as polyglot persistence — what's missing?
- In Netflix's architecture, why does viewing-history data land on Cassandra while billing
  data lands on a relational engine — walk through the specific axis answers (consistency,
  write shape) that separate the two choices?
- Which specific piece of Codd's original relational dream did each NoSQL child give up —
  and which piece(s) does NewSQL refuse to give up, choosing instead to pay for them
  directly?
- Why must a Raft write wait for a *majority* of a range's replicas rather than just one —
  what would break under a single replica failure if only one acknowledgment were required?
- A 3-region CockroachDB/Spanner deployment has a hard write-latency floor set by network
  round-trip time to another region. Why is this a physical limit rather than something
  better hardware or software tuning could remove?
- Why does a Raft group confined to a single region/AZ not pay the same latency cost as a
  cross-region one, even though both use the identical consensus protocol — what's the one
  variable that changed?
- What does Spanner's TrueTime actually add on top of plain Raft/Paxos consensus, and why
  does CockroachDB need a different mechanism (HLC) to approximate the same guarantee
  without Google's specialized clock hardware?
- Why doesn't a B-tree's ordering or a hash index's equality generalize to "nearest neighbor
  in 1,536-dimensional space" — what property of similarity search breaks both structures?
- Explain the curse of dimensionality in your own words, and why it's the reason vector
  databases reach for approximate (not exact) nearest-neighbor algorithms like HNSW.
- An embedding model gets upgraded, and old vectors are never recomputed. The database
  returns confident "nearest neighbor" results mixing old and new vectors, with no error.
  Why doesn't the database catch this — is it a bug, or a structural blind spot?
- Why is "flexible/schema-less systems eliminate the need for discipline" false in both the
  document-store case and the vector-database case — what does each one actually relocate
  the discipline *to*, and who ends up paying for it?
- Why is "be a student of access pattern" a continuous practice rather than a one-time
  checklist item, unlike the other five axes as originally framed in this doc?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Six-axes framing (the default for any "which database would you use" question):** "I
  wouldn't name a technology first — I'd walk the access pattern, data size, latency
  budget, consistency needs, write shape, and failure modes this workload actually has, and
  let the technology fall out of those answers. Naming a database before that is picking by
  fashion, not engineering, and it's a pattern I actively try to avoid."
- **Compounding-cost framing (good for a storage-engine-choice deep-dive):** "Write
  amplification isn't one number — a B-tree's random page rewrites and an SSD's own erase-
  block garbage collection are two separate amplification sources that compound on a
  write-heavy, random-key workload. I'd check both before assuming 'the database handles
  it.'"
- **Failure-class framing (good for a durability/DR question):** "I'd separate 'durable'
  into the specific failure classes it needs to survive — process crash, disk failure,
  silent corruption, rack failure, region failure, human error — because each one has a
  genuinely different mechanism behind it, and a system can be airtight on five of them and
  still lose data on the sixth if nobody named it explicitly."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **fashion-driven selection** (n. phrase) — choosing a technology by familiarity or
  popularity rather than by the workload's actual requirements; the anti-pattern this whole
  doc is named against.
- **the six axes** (n. phrase) — access pattern, data size, latency budget, consistency
  model, write amplification, failure modes; the first-principles checklist that should
  precede any storage technology choice.
- **access pattern** (n. phrase) — the shape of how data is actually queried (point lookup,
  range scan, multi-predicate, analytical scan, graph traversal); the single most
  workload-defining axis.
- **compounding amplification** (n. phrase) — when a storage engine's own write
  amplification (e.g., a B-tree's page rewrites) stacks on top of the underlying medium's
  amplification (e.g., an SSD's WAF), rather than one substituting for the other.
- **failure class** (n. phrase) — one of the six genuinely distinct ways data can be lost or
  corrupted (crash, disk, silent corruption, rack, region, human error), each requiring its
  own named defense rather than one being assumed to cover all.
- **data independence** (n. phrase, Codd's term) — decoupling the logical data model (what
  you query) from physical storage (how it's laid out), the core contribution of the 1970
  relational model versus the pointer-navigation databases that preceded it.
- **normalization / 3NF** (n. phrase) — Codd and Boyce's design rules eliminating data
  redundancy; 3NF specifically means every non-key attribute depends on the key, the whole
  key, and nothing but the key — one stored copy per fact.
- **update / insert / delete anomaly** (n. phrases) — the three concrete failure modes
  normalization exists to prevent, all caused by the same root problem: the same fact stored
  in more than one place.
- **ACID's "C" vs. CAP's "C"** (n. phrase) — a deliberately named disambiguation: ACID
  Consistency means a transaction never violates the schema's own declared constraints; CAP
  Consistency means every replica returns the same (latest) value — unrelated guarantees
  that happen to share a letter.
- **MVCC (multi-version concurrency control)** (n. phrase) — Postgres's isolation mechanism:
  keep multiple versions of a row so readers never block writers and vice versa, instead of
  using locks.
- **join tax** (n. phrase) — the read-time cost of reconstructing a normalized entity by
  joining its decomposed tables back together; the price paid later for 3NF's
  store-once-now guarantee, and disproportionately worse across a distributed join.
- **impedance mismatch** (n. phrase) — the structural friction between an application's
  natural object/nested data model and the relational model's flat, tabular one, bridged
  (imperfectly) by an ORM; one of the direct historical arguments for document databases.
- **N+1 query problem** (n. phrase) — an ORM silently issuing one query per row instead of
  one query total, the classic visible symptom of impedance mismatch leaking through the
  abstraction.
- **schema-on-write / schema-on-read** (n. phrases) — whether structure is enforced by the
  engine once, at write time (SQL), or left implicit and re-derived by every reader,
  indefinitely (NoSQL document stores) — the precise mechanism behind why "schema-less" is a
  myth: the schema still exists, just unenforced and undocumented.
- **schema drift** (n. phrase) — documents in the same collection silently diverging in
  shape over time (different app versions, redesigns, partial migrations), the concrete cost
  schema-on-read defers onto every reader instead of catching once at write time.
- **implicit schema** (n. phrase) — the shape application code assumes data has, even when
  no engine enforces or documents it — the thing that proves "schema-less" is a misnomer,
  since code consuming data always has expectations about its structure.
- **Bigtable (2006)** / **Dynamo (2007)** (n., proper) — Google's OSDI paper and Amazon's
  SOSP paper, the two works marking the start of the NoSQL movement; Dynamo is also the
  origin of quorum reads/writes and consistent hashing as documented elsewhere in this repo.
- **embedding vs. referencing** (n. phrases, document DBs) — nesting related data inside a
  parent document (fast, no join, but reintroduces the update anomaly) versus storing just
  an ID and fetching separately (avoids duplication, but reintroduces the join as N
  sequential application-level round trips instead of one database-side join).
- **aggregate (DDD)** (n., from Domain-Driven Design) — an entity with one clear owner and
  everything naturally nested under it (an order and its line items); the exact shape a
  document store handles well, and the shape a social/relationship graph is not.
- **index-free adjacency** (n. phrase, Neo4j's term) — storing a direct physical pointer
  from each node to its adjacent nodes/relationships at the storage layer, instead of a
  foreign key re-resolved through an index at query time; the structural reason a graph
  traversal's cost scales with the touched subgraph, not the whole dataset.
- **recursive CTE (`WITH RECURSIVE`)** (n. phrase) — SQL's mechanism for variable-depth
  self-joins; correct but combinatorially expensive for multi-hop relationship queries,
  since intermediate result sets can explode per level with no bound known in advance.
- **variable-length path** (n. phrase, Cypher: `[:REL*1..4]`) — a graph query language's
  native syntax for "traverse this relationship type between 1 and 4 hops," the direct
  counterpart to a SQL recursive CTE, natively supported rather than simulated.
- **Golden Hammer fallacy / law of the instrument** (n. phrase, Maslow, 1966) — reaching for
  one familiar tool on every problem regardless of fit, because familiarity substituted for
  evaluation; the formal name for fashion-driven storage selection.
- **polyglot persistence** (n. phrase, Fowler & Sadalage, ~2011) — deliberately using
  multiple storage technologies within one system, each chosen by running the six axes
  against its specific sub-workload rather than forcing every workload through one engine.
- **NewSQL** (n. phrase, Matthew Aslett, 451 Group, ~2011) — the class of databases (Spanner,
  CockroachDB) attempting to keep SQL, ACID, and multi-row transactions *and* horizontal
  scale/region-failure survival, rather than giving up a piece of the relational dream the
  way each NoSQL child did.
- **Raft** (n., proper — Ongaro & Ousterhout, 2014) — a distributed consensus protocol
  (deliberately designed to be more understandable than Paxos) where a per-shard group of
  replicas elects a leader and requires a majority quorum to acknowledge a write before it
  commits; the mechanism underneath both Spanner-style and CockroachDB-style NewSQL systems.
- **range (CockroachDB)** (n.) — a contiguous shard of the key space, replicated (typically
  3x) and managed by its own independent Raft group; conceptually the same idea as a GFS
  chunk, applied to a relational engine.
- **TrueTime** (n., proper, Google Spanner) — a globally-synchronized clock API backed by
  GPS and atomic clocks, giving a tightly bounded time-uncertainty window that lets Spanner
  assign globally meaningful commit timestamps and guarantee external consistency
  (linearizability) across a planet-scale database.
- **Hybrid Logical Clock (HLC)** (n. phrase) — CockroachDB's substitute for TrueTime,
  approximating a similar ordering guarantee without requiring Google's specialized
  atomic-clock hardware — a real, documented architectural difference between the two
  systems, not an implementation detail.
- **consensus latency floor** (n. phrase) — the hard lower bound a cross-region Raft/Paxos
  write's commit latency cannot beat, set by the network round-trip time to a majority of
  replicas — a physical limit, not a tunable inefficiency.
- **embedding** (n.) — a dense numeric vector produced by a model from unstructured data
  (text, image, audio), engineered so semantic/perceptual similarity corresponds to
  geometric closeness in that vector space.
- **ANN (Approximate Nearest Neighbor)** (n. phrase) — the class of algorithms (HNSW, IVF)
  vector databases use instead of exact nearest-neighbor search, deliberately trading recall
  for speed, since exact search degrades toward linear scan at high dimensionality.
- **curse of dimensionality** (n. phrase) — the property that as dimensionality grows,
  distances between points concentrate and "nearest" vs. "farthest" stop being reliably
  distinguishable, which is why exact spatial indexes (k-d trees) that work in 2-3
  dimensions don't generalize to embedding-scale dimensionality.
- **HNSW (Hierarchical Navigable Small World graph)** (n. phrase) — the dominant modern ANN
  algorithm: a multi-layer graph of approximate nearest-neighbor connections, searched by
  greedily navigating from a sparse top layer down into denser layers near the query vector.
- **embedding-version drift** (n. phrase) — vectors produced by an old and a new version of
  an embedding model becoming silently incomparable in the same space; the vector-database
  analogue of schema drift, except the database has no mechanism to detect it at all.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…the technology name should be the last step, not the first"** — a compact way to
  argue for axis-first reasoning over familiarity-first reasoning in any storage-choice
  discussion.
- **"…every database embodies a trade-off"** — a reusable line for pushing back on "just
  tell me the best database," redirecting toward "best for which workload."
- **"…replication propagates mistakes exactly as faithfully as it propagates legitimate
  writes"** — a precise way to explain why backups and replication solve different
  problems, not overlapping ones.
- **"…integrity now, reconstruction cost later"** — a compact way to state exactly what
  normalization trades away in exchange for the store-once-per-fact guarantee.
- **"…fighting the workload's grain, the same way random I/O fights a disk's"** — a fluent
  way to connect a wrong storage-model choice back to Part 6's mechanical sympathy, framing
  it as a physical/structural mismatch rather than just "the wrong tool."
- **"…flexible doesn't mean the discipline went away, only where it lives"** — a reusable
  line for pushing back on "schema-less" or "no upfront design needed" claims, whether about
  a document store or a vector database's embedding versioning.
- **"…don't build apps, architect systems that can survive their own growth"** — the
  closing distinction between optimizing for today's feature and building the seams that let
  tomorrow's access pattern change be absorbed instead of forced.

## Final Synthesis: Don't Build Apps — Architect Systems That Survive Their Own Growth

Every technology in this doc's history — key-value, document, graph, NewSQL, vector — exists
because an *access pattern* changed and the previous default couldn't absorb the change
without either breaking or quietly becoming the wrong tool wearing the right tool's name.
That's the pattern worth carrying forward, not any single row of the taxonomy: **the six
axes are never answered once, permanently, at the moment a system is first built.** A
product that starts as pure point lookups by ID accumulates range queries, then an
analytics dashboard, then a recommendation feature needing similarity search — the same
system, the same team, a completely different set of honest answers to axis 1 eighteen
months later.

**This is the actual distinction between building an app and architecting a system.**
Building an app means making today's feature correct and shipped. Architecting a system
means building it so that when the access pattern *does* drift — and it will, because
product growth is precisely what changes how data gets queried — the system can absorb a
new storage technology at the point where the axes now demand one, instead of forcing every
future workload through whatever was chosen on day one out of necessity or familiarity. This
is polyglot persistence's deeper justification, not just "use multiple databases": it's
architecting with the expectation that the *set* of technologies a system needs will grow,
and building the seams (clean data-access boundaries, services that own their own storage
choice) that make adding one later a deliberate decision instead of a rewrite.

**"Be a student of access pattern"** is the closing discipline, and it's deliberately not
"be a student of databases." Databases are the last step of the decision, per this whole
doc — the axes, and access pattern most of all, are the thing actually worth studying
continuously, in production, against how a system is *actually* being queried, not how it
was designed to be queried on a whiteboard before a single real user touched it. The
engineer who reflexively reaches for what they know is fighting yesterday's access pattern
with today's decision. The one who keeps asking, as the system grows, "what is this actually
being asked to do now, and does my storage choice still fit that" — that's the discipline
this entire taxonomy exists to teach, and the only one of the six axes that's a continuous
practice rather than a checklist run once.

---

**Previous:** [Part 10: The Physics of Persistence (B-Trees vs. LSM-Trees)](10_physics_of_persistence.md)  |  **Next:** [Part 12: Sharding — The Illusion of Infinite Space, and the Vertical Wall](12_sharding_and_the_vertical_wall.md)

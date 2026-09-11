# Prerequisite Concepts, Part 20: Microservices Architecture Patterns — The Patterns a Distributed System Actually Needs

[Part 8 already named the cost](08_cost_of_communication.md#microservices-a-communication-tax-by-design-choice)
of splitting a monolith into services — every service boundary is a network boundary, paid
on every hop. This part assumes that cost is already accepted and asks the next question:
given that cost, what are the actual named patterns a real microservices architecture reaches
for? Four of them already have full first-principles treatments elsewhere in this series and
are only linked here, not repeated. The rest — how a service finds another service whose
address keeps changing, how a system migrates into this shape without a big-bang rewrite,
and how read and write access get structured once "the database" is no longer one shared
thing every service can just query — are new ground this part covers directly.

## In Plain English

Imagine a company that used to be one department where everyone sat in the same room and
just walked over to ask a coworker something directly. It splits into ten specialized teams
in ten different rooms. Immediately, new problems appear that never existed before: how does
someone find which room a given team is in *today*, given that teams move offices
constantly (**service discovery**)? How does the company reorganize into this shape without
shutting down for a year to do it all at once (**strangler fig**)? And once "the filing
cabinet" isn't one shared thing anymore, how does the company decide who's allowed to write
a new record versus who's just looking one up, and in what format each of them needs it
(**CQRS** and **event sourcing**)? None of these are exotic — they're the direct, structural
consequences of the split itself.

## The Problem, Precisely

A monolith's internal calls are function calls: resolved at compile time, always pointing at
a location that exists, with no discovery required and one shared database every part of the
code can query directly. Splitting into microservices removes all three of those guarantees
at once — a service's network address now changes constantly (deploys, autoscaling,
failures), the system has to get from "one monolith" to "many services" through some
sequence of intermediate, working states rather than a single cutover, and "the database"
fragments into several services' worth of independently-owned data with no single shared
schema left to query across.

## The Patterns Already Covered — Reused, Not Re-Derived

Four microservices patterns already have a full first-principles treatment elsewhere in this
series; naming them together here, as one family, is this part's only job for them:

| Pattern | Problem it solves | Where it's fully covered |
|---|---|---|
| **Circuit breaker / bulkhead** | Stop a failing dependency from being hammered, and stop one failing dependency from starving requests to healthy ones | [Part 3's Resilience Vocabulary](03_communication_and_resilience.md#resilience-vocabulary) |
| **Saga / 2PC** | Keep one logical operation atomic (or safely compensated) across multiple services' independent databases | [Part 01's Distributed Transactions](../../system_design_practice/01_distributed_systems_foundations/tutorial.md#distributed-transactions-2pc-vs-saga) |
| **Service mesh / sidecar** | Handle retries, mTLS, and observability as cross-cutting infrastructure instead of duplicated per-service code | [Part 01's Service Mesh](../../system_design_practice/01_distributed_systems_foundations/tutorial.md#service-mesh-cross-cutting-concerns-without-cross-cutting-code) |
| **API gateway** | A single, cheap-to-reject front door for auth, rate limiting, and protocol translation before a request reaches any service | [Part 9's "API Gateway as a Shield"](09_dns_bgp_and_the_edge.md#beyond-caching-the-security-and-routing-layer-at-the-edge) |

## Service Discovery: How a Service Finds Another Service Whose Address Keeps Changing

**The problem**: in a dynamic environment — containers restarting, instances autoscaling up
and down, a deploy replacing every instance's address at once — hardcoding a downstream
service's IP address stops working the moment that address is no longer stable. Something
has to track, in real time, which instances of a given service currently exist and where.

**The registry mechanism**: a **service registry** is the source of truth for "which
instances of service X are alive right now." Instances register themselves on startup
(**self-registration**) or get registered on their behalf by the platform watching their
lifecycle (**third-party registration** — Kubernetes' control plane doing this for every
pod is the most common real-world example). Staying registered isn't a one-time event: each
instance sends a periodic **heartbeat**, and the registry expires an entry whose heartbeat
goes silent past a TTL — the exact same active-health-check instinct [Part 19 already
covered for load balancer backends](19_load_balancing.md#health-checks-how-a-load-balancer-knows-a-server-is-actually-healthy),
applied one layer earlier, to registry membership rather than routing eligibility.

**Client-side vs. server-side discovery**: in **client-side discovery**, the calling service
queries the registry directly and picks a target instance itself — often using one of [Part
19's own load-balancing algorithms](19_load_balancing.md#algorithms-how-the-routing-decision-actually-gets-made)
client-side, the way gRPC's built-in client-side balancing works. In **server-side
discovery**, the caller just talks to a fixed, stable address (a load balancer or a DNS
name), and something else — the load balancer, or the platform — queries the registry and
routes on the caller's behalf; this is exactly what a Kubernetes `Service` does: a stable
virtual IP in front of pods whose real IPs are constantly changing underneath it.

**DNS-based discovery** is server-side discovery's simplest form — resolve a service name to
a current address the same way any DNS lookup works, which means it inherits [Part 9's own
DNS staleness
problem](09_dns_bgp_and_the_edge.md#ttl-a-hint-not-a-promise-and-why-that-breaks-failover)
directly: a cached DNS answer can point at an instance that's already gone, the identical
"TTL is a hint, not a promise" gap recurring one layer up from failover, here applied to
service-to-service calls instead of client-to-server ones.

## The Strangler Fig Pattern: Migrating Without a Big-Bang Rewrite

**The problem**: rewriting a working monolith into microservices all at once — freezing
feature work for months, shipping one enormous cutover — is one of the highest-risk moves
available to an engineering org: every bug is discovered at once, on a system nobody has
operated in production yet, with no working fallback if it goes badly.

**The mechanism**, named by Martin Fowler after the strangler fig vine, which grows around a
host tree and gradually replaces it rather than felling it outright: put a routing facade in
front of the monolith — mechanically the same [API gateway pattern already
named](09_dns_bgp_and_the_edge.md#beyond-caching-the-security-and-routing-layer-at-the-edge)
above, doing a new job — and migrate one route, one feature, or one bounded piece of
functionality at a time. The facade sends traffic for that one piece to a new microservice;
everything not yet migrated keeps flowing to the monolith unchanged. Each migrated piece
ships independently, gets validated against real production traffic on its own, and can be
rolled back on its own — the monolith is "strangled" incrementally instead of replaced in
one irreversible step.

**The two costs worth naming explicitly, not glossing over**: first, a **temporarily doubled
complexity** — during migration, both the old and new code paths exist, often needing data
kept in sync between the monolith's database and the new service's own store (a **dual-write**
problem, the same correctness burden [Part 15's cache invalidation](15_caching.md#cache-invalidation-the-genuinely-hard-part)
already named for a different pair of stores kept in sync). Second, the well-known failure
mode this pattern is named for avoiding, that still happens anyway in practice: **the
strangler that never finishes strangling** — migration work loses priority against new
feature work indefinitely, and the org ends up permanently operating both the monolith and a
partial set of microservices, paying the complexity cost of both architectures with the
benefit of neither.

## Event Sourcing: The Log as the Source of Truth, Applied to a Single Entity

**The problem**: a traditional CRUD table only stores an entity's *current* state — every
`UPDATE` overwrites what was there before, which means the system can't answer "what was
this order's state an hour ago," can't replay history to rebuild a view after discovering a
bug in how it was computed, and has no built-in audit trail beyond whatever's bolted on
separately.

**The mechanism**: instead of storing current state directly, store every state change as an
immutable, ordered, append-only sequence of events — `OrderPlaced`, `PaymentReceived`,
`OrderShipped` — and derive current state by replaying that sequence, rather than treating
current state as the thing that's actually saved. This is structurally the *same* mechanism
[Part 10's write-ahead log](10_physics_of_persistence.md#the-write-ahead-log-making-durability-affordable)
and [Part 18's partitioned commit
log](18_message_queues_and_event_driven_semantics.md#the-problem-precisely) already
established, just scoped down to a single entity's history instead of a whole storage
engine's durability or a whole topic's stream — the same "log as source of truth" idea [Part
10 already named as Kafka's own conceptual
origin](10_physics_of_persistence.md#wal-beyond-storage-engines-protecting-a-consensus-log-not-a-data-structure),
recurring a third time at the domain-modeling layer. Replaying the *entire* event history on
every read doesn't scale forever, which is why production event-sourced systems
periodically **snapshot** current state and replay only the events since the last
snapshot — the same checkpoint-then-replay-the-tail pattern [Part 10 already covered for
WAL replay after a crash](10_physics_of_persistence.md#checkpointing-why-the-wal-doesnt-grow-forever).

**The trade-off**: a genuine, complete audit trail and the ability to reconstruct any past
state or rebuild a derived view after fixing a bug, at the cost of real query complexity —
"what is this order's current status" is no longer a single-row lookup, it's either a
replay or a maintained projection, which is exactly the problem the next pattern exists to
solve.

## CQRS: Splitting the Write Model From the Read Model

**The problem**: the shape data needs to be *written* in (normalized, validated against
business rules, one authoritative record per entity) and the shape it needs to be *read* in
(denormalized, pre-joined, optimized for a specific screen or query) are frequently very
different — forcing both through one shared schema is a compromise that makes neither side
as good as it could be on its own.

**The mechanism**: **CQRS (Command Query Responsibility Segregation)** separates the write
path (**commands** — validated, business-rule-enforcing operations that change state) from
the read path (**queries** — served from one or more separate, purpose-built
**projections**, each denormalized for a specific read pattern, updated asynchronously as
writes happen). A projection is a materialized, precomputed view kept up to date as the
write side changes — the same **fan-out-on-write** trade [Part 3 already
named](03_communication_and_resilience.md#fan-out-push-applied-to-one-write-many-readers):
pay the cost of updating the view when data changes, so every read is cheap and doesn't
recompute anything. And because the projection updates asynchronously rather than inside the
same transaction as the write, a query can observe a value that's a few moments behind the
latest write — the identical **eventual consistency** trade-off [Part 2 already
established](02_data_and_consistency.md#eventual-consistency-fully-unpacked) for replicas,
recurring here between one service's own write model and its read-side projections instead
of between database replicas.

**Worth being precise about the relationship**: CQRS and event sourcing are independent
patterns commonly paired, not synonyms. CQRS is usable on its own, with commands writing
directly to a normalized store and projections rebuilt from it. But event sourcing pairs
with CQRS *unusually naturally*, because the event stream an event-sourced write model
already produces is exactly the input a projection needs to subscribe to and build itself
from — one pattern's natural output is the other's natural input, which is why the two are
so often described together even though neither requires the other.

## Real Tools, Modern Defaults

**Service discovery**: **Consul** and **etcd** — [etcd already named for consensus and
distributed locks in Part
01](../../system_design_practice/01_distributed_systems_foundations/tutorial.md#distributed-locks-zookeeper-etcd), reused here as a
registry backend — plus **Kubernetes' built-in discovery** (CoreDNS for name resolution,
`kube-proxy` with iptables/IPVS for routing to the resolved backend, [the same IPVS engine
Part 19 already named for L4 load
balancing](19_load_balancing.md#real-tools-modern-defaults)), and the **xDS protocol**
Envoy/Istio use to push live discovery data to every sidecar in a mesh. **Netflix Eureka**
is the classic, still-referenced historical example, largely superseded by Kubernetes-native
discovery in new systems. **Strangler fig**: any API gateway capable of route-level traffic
splitting (Envoy, Kong, NGINX, a cloud load balancer's path-based rules) serves as the
facade — this is a routing-configuration pattern, not a separate product. **Event
sourcing / CQRS**: **EventStoreDB** (purpose-built for this pattern), **Kafka** as the
event-log backbone with **Kafka Streams** or **ksqlDB** building projections from it, **Axon
Framework** (JVM, opinionated event-sourcing/CQRS framework), and — a common, pragmatic
middle ground rather than full event sourcing from scratch — **Debezium**-style **Change
Data Capture (CDC)**, which retrofits an event stream onto an existing CRUD database's
transaction log, so downstream projections can subscribe to change events without the
primary write model being rearchitected as event-sourced at all.

## Designing and Operating From First Principles

1. Have I named *which specific pattern* addresses a given microservices pain point in this
   design — or am I reaching for "a service mesh" or "event sourcing" as a general-purpose
   answer without tracing it back to the actual problem it solves here?
2. If services discover each other via DNS, have I accounted for [Part 9's TTL-is-a-hint
   gap](09_dns_bgp_and_the_edge.md#ttl-a-hint-not-a-promise-and-why-that-breaks-failover) —
   what happens when a caller holds a cached address for an instance that's already gone?
3. If this system is mid-migration via the strangler fig pattern, is there an explicit owner
   and timeline for finishing it, or is this a migration that's quietly at risk of never
   finishing?
4. If I'm introducing CQRS, have I named the actual staleness window between a write and its
   projection being updated — and is that window acceptable for every screen/query that
   reads from it, or does one of them actually need to read the write model directly?
5. Before reaching for full event sourcing, have I considered whether CDC on the existing
   database gets most of the same benefit (an event stream downstream systems can subscribe
   to) without the cost of rearchitecting the write model itself?

## Key Takeaways

- **Splitting into microservices trades a monolith's free guarantees for problems that now
  need explicit patterns** — service discovery, migration strategy, and read/write data
  structuring didn't exist as problems inside a monolith's function calls and shared
  database.
- **Four core resilience/consistency patterns are already fully covered elsewhere** —
  circuit breaker/bulkhead, saga/2PC, service mesh/sidecar, and API gateway — this part
  names them as one family rather than re-deriving any of them.
- **Service discovery is a registry plus a heartbeat**, with client-side and server-side
  variants differing only in *who* queries the registry and picks the target — and DNS-based
  discovery inherits the same TTL staleness gap Part 9 already named for ordinary DNS.
- **The strangler fig pattern trades a big-bang rewrite's risk for a smaller, real one** — a
  temporarily doubled system that must be actively finished, not left as a permanent
  half-migrated state.
- **Event sourcing is a domain-scoped append-only log** — the same mechanism as a WAL or a
  Kafka partition, one layer up — and **CQRS is the same eventual-consistency and
  fan-out-on-write trade-offs already established elsewhere**, applied to splitting a
  service's own read and write paths.

## Quick Self-Check

- Explain why client-side and server-side service discovery differ only in *where* the
  registry lookup happens, not in what problem either one solves.
- Walk through exactly why DNS-based service discovery inherits Part 9's TTL staleness
  problem — what specifically goes stale, and for how long, in the worst case?
- Name the two costs of the strangler fig pattern this part calls out explicitly, and explain
  why "the migration that never finishes" is a failure of prioritization, not of the pattern
  itself.
- Explain precisely how an event-sourced entity's event log is the same mechanism as a
  write-ahead log or a Kafka partition, just applied at a different scope.
- Why does introducing CQRS mean accepting an eventual-consistency window between a write and
  its projection — and what specifically would tell you that window is unacceptable for a
  given read?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Consequence-first framing (the default for 'what patterns would this microservices
  design need'):** "I'd start from what a monolith gave us for free that a split
  architecture now has to solve explicitly — finding a service at a changing address,
  migrating into this shape safely, and structuring reads and writes once there's no shared
  database — and name the specific pattern for each, rather than listing pattern names from
  memory."
- **Reuse framing (good for demonstrating you're not just naming buzzwords):** "Several of
  these patterns are mechanisms I'd already reach for elsewhere — a service registry's
  heartbeat is the same idea as a load balancer's active health check, and CQRS's projection
  lag is the same eventual-consistency trade-off as replica lag. I'd name that connection
  explicitly rather than treating each pattern as a standalone fact."
- **Migration-risk framing (good for a 'how would you evolve this system' follow-up):** "I'd
  reach for the strangler fig pattern specifically to avoid a big-bang rewrite's risk, but
  I'd also name its real cost upfront — a temporarily doubled system — and insist on an
  explicit owner and timeline, since an unfinished strangler migration is a common, expensive
  failure mode in practice."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **service registry** (n. phrase) — the source of truth for which service instances are
  currently alive and where; kept accurate via self- or third-party registration plus
  heartbeats.
- **client-side / server-side discovery** (n. phrases) — whether the calling service queries
  the registry directly, or a fixed intermediary does it on the caller's behalf.
- **strangler fig pattern** (n. phrase) — incrementally routing individual pieces of
  functionality from a monolith to new services via a facade, rather than rewriting
  everything at once.
- **dual-write** (n. phrase) — keeping two data stores in sync during a migration or across
  a cache/database boundary; a real, easy-to-drop correctness obligation.
- **event sourcing** (n. phrase) — storing every state change as an immutable, ordered event
  log and deriving current state by replay, rather than storing current state directly.
- **CQRS (Command Query Responsibility Segregation)** (n. phrase, initialism) — separating
  the write path (commands) from the read path (queries served from denormalized
  projections), independent of, but commonly paired with, event sourcing.
- **projection** (n.) — a denormalized, purpose-built read view kept up to date
  asynchronously from the write side; CQRS's version of a materialized view.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…what the monolith gave us for free"** — a fluent way to frame any microservices pattern
  discussion around the specific guarantee that was lost by splitting, rather than starting
  from the pattern's name.
- **"…strangled incrementally, not felled in one cut"** — a precise, memorable way to
  describe the strangler fig pattern's actual mechanism.
- **"…the write model's own exhaust, and the read side's fuel"** — a fluent way to describe
  why event sourcing and CQRS pair so naturally, without needing to explain either one from
  scratch first.

---

**Previous:** [Part 19: Load Balancing](19_load_balancing.md)  |  **Next:** [Part 21: The FR/NFR Framework and a Real-Tools Quick Reference](21_fr_nfr_framework_and_architecture_tools.md)

# Prerequisite Concepts, Part 21: The FR/NFR Framework and a Real-Tools Quick Reference — Turning Clarifying Questions Into a Spec You're Held To

[Part 20](20_microservices_architecture_patterns.md) closed out the pattern-level toolkit —
the named shapes a distributed system reaches for once it's already been split into
services. This part steps back one level earlier, to the step that decides *whether* any of
those patterns are even needed: turning a vague prompt ("design a URL shortener," "design a
notification system") into an explicit, written specification — a Functional/Non-Functional
Requirements split — and only then reaching for a technology. The [Interview
Framework](../01_ml_system_design/00_interview_framework.md) already lists the clarifying
questions to ask; this part is what happens to the answers *after* they're asked, and the
categorized inventory of real tools that gets consulted only once that spec exists.

## In Plain English

A contractor building a house needs two different kinds of answers before drawing a single
blueprint. The first kind is **what the house must do**: how many bedrooms, where the
kitchen goes, whether there's a garage. The second kind is **how well it must do it**: what
snow load the roof must survive, what the wiring's amperage needs to be, what the local fire
code requires for exit spacing. Skipping the first kind gets you a technically sound
structure nobody can actually live in. Skipping the second gets you a house that looks right
on move-in day and fails the first heavy winter. A system design interview asks for both,
and conflating them — or worse, skipping straight to "I'd use Postgres and Redis" — is the
architectural equivalent of picking paint colors before anyone has agreed how many rooms the
house has.

## The Problem, Precisely

The [Interview Framework's Step 1](../01_ml_system_design/00_interview_framework.md#step-1-clarify-requirements)
lists what to ask — scope, scale, latency, consistency, failure tolerance, constraints — and
that list is genuinely necessary. But a list of answered questions, left as answered
questions, isn't yet a specification: nothing forces each later design decision to trace back
to a specific, named requirement, which is exactly what turns "I asked good questions" into
"I have a spec I can be held to." The fix is mechanical and cheap: restate the clarified
answers as two explicit, numbered tables — **Functional Requirements (FR)**, what the system
must *do*, and **Non-Functional Requirements (NFR)**, how well it must do it, under what
constraints — before sketching a single box. [The URL Shortener
tutorial](../../system_design_practice/11_design_url_shortener/tutorial.md#requirements)
already does exactly this for one problem; this part generalizes the *procedure* so it's
ready before any problem, not derived fresh, under time pressure, every single time.

## Deriving Functional Requirements: What the System Must Do

Functional requirements answer *"what actions does this system support, for whom?"* — and
the fastest way to derive a complete list is to walk a fixed set of categories rather than
brainstorming freely, since freeform brainstorming is exactly where an obvious-but-easy-to-
forget action (revocation, an admin override, an expiry) quietly gets dropped:

1. **Core user actions** — the one or two verbs the system exists for (shorten a URL, send
   a message, place an order). These come out of Step 1's clarifying questions almost
   verbatim.
2. **Actors and roles** — is there more than one kind of user (an end user vs. an
   administrator vs. an abuse reviewer), and does each need different actions or visibility?
   A design that only names the end user's actions routinely under-specifies moderation,
   audit, or support tooling that a real production system can't ship without.
3. **The full CRUD surface, explicitly** — for the core entity, what's actually creatable,
   readable, updatable, and deletable — and is "delete" real deletion or a soft
   revoke/disable? Naming this explicitly is what catches a requirement like "links must be
   revocable" before it's discovered missing mid-design.
4. **Administrative and edge operations** — the actions that don't come up in the first
   thirty seconds of describing the system but are load-bearing once it's real: rate
   limiting, abuse review, expiry/TTL, audit export, bulk operations.
5. **Explicit non-goals** — stating what the system deliberately does *not* do is as valuable
   as stating what it does; it bounds scope creep mid-interview and signals the same
   judgment as a real system's design doc. [The URL Shortener tutorial's "Practice
   Variations" section](../../system_design_practice/11_design_url_shortener/tutorial.md#practice-variations)
   is effectively a list of *adjacent* systems this one deliberately isn't — pastebin,
   rules-based redirect, ID generator — worth naming the equivalent boundary for whatever
   system is actually being designed.

## Deriving Non-Functional Requirements: Nine Standard Categories

Where functional requirements vary entirely by problem, non-functional requirements draw
from the same fixed set of categories on almost every system design question — which is
exactly what makes them worth memorizing as a checklist rather than re-deriving from
scratch each time. Each row below names the category, the question that surfaces it, and
where the underlying mechanism is already covered in this repo.

| # | Category | The question to ask | Where the mechanism lives |
|---|---|---|---|
| NFR-Latency | Latency | What's the response-time budget (p50/p99), and *why* — a synchronous path on someone else's critical path, or a background job with minutes to spare? | [Part 6's physical hierarchy](06_mechanical_sympathy_and_physics_of_latency.md#hardware-reality-the-abstraction-hides-the-physics-not-the-cost); [Part 11's latency-budget axis](11_taxonomy_of_storage_choice.md#3-latency-budget-what-sla-does-each-request-actually-need) |
| NFR-Availability | Availability | What uptime target, and what does an outage actually cost — lost revenue every second, or a job that just runs later? | [Part 3's resilience vocabulary](03_communication_and_resilience.md#resilience-vocabulary) |
| NFR-Consistency | Consistency | If two replicas briefly disagree, what's the concrete cost — "someone loses money" or "a counter is off by one for a second"? | [Part 13's CAP/PACELC](13_cap_theorem_and_pacelc.md); [Part 11's consistency axis](11_taxonomy_of_storage_choice.md#4-consistency-model-what-does-correct-mean-for-this-data) |
| NFR-Durability | Durability | Which of the six named failure classes — crash, disk, silent corruption, rack, region, human error — does this data have to survive, specifically? | [Part 11's failure-modes axis](11_taxonomy_of_storage_choice.md#6-failure-modes-what-specifically-has-to-survive) |
| NFR-Scale | Scalability direction | What's the read:write ratio, and is growth expected in traffic, data volume, or geographic spread? | [Part 12's sharding/vertical wall](12_sharding_and_the_vertical_wall.md); the [URL Shortener's own ~100:1 read:write framing](../../system_design_practice/11_design_url_shortener/tutorial.md#clarify) as a worked example |
| NFR-Security | Security / access control | Does anything here expose an identifier or resource that must not be enumerable, guessable, or reachable without authorization? | The [URL Shortener's key-enumerability deep-dive](../../system_design_practice/11_design_url_shortener/tutorial.md#deep-dive-key-generation-an-access-control-decision-not-an-encoding-one) — the canonical worked example of an NFR hiding inside what looks like a formatting choice |
| NFR-Cost | Cost | Is this workload cost-sensitive enough that the "more correct" technical answer is actually the economically wrong one? | [Part 6's storage economics](06_mechanical_sympathy_and_physics_of_latency.md#the-economics-of-machine-cost-is-physics); [Part 11's data-size/tiering axis](11_taxonomy_of_storage_choice.md#2-data-size-does-it-fit-on-one-machine-and-where-in-the-storage-hierarchy) |
| NFR-Compliance | Compliance / data residency | Does any of this data carry a legal constraint — GDPR erasure, data residency, PII handling — that outlives the system's normal operating assumptions? | The [URL Shortener's "permanence obligation" deep-dive](../../system_design_practice/11_design_url_shortener/tutorial.md#deep-dive-the-permanence-obligation) as the worked example of a requirement that's organizational before it's technical |
| NFR-Observability | Observability | How will degradation be *known about* before a user reports it? | [Part 16: Observability](16_observability.md) |

## From Requirement to Decision: The "Drives" Column Habit

Listing NFRs and stopping there is only half the exercise a staff-level answer is graded
on — the other half is naming, for each one, *which specific design decision it forces*.
[The URL Shortener tutorial's NFR table](../../system_design_practice/11_design_url_shortener/tutorial.md#non-functional-requirements)
adds exactly this as an explicit **Drives** column next to every NFR (its revocation-latency
requirement drives an out-of-band revocation filter; its non-enumerability requirement drives
random key generation over a counter) — and that habit, reused generically, is the single
highest-leverage move available at the requirements stage:

1. **State the requirement as a number, not an adjective.** "Fast" isn't a requirement;
   "p99 under 50ms" is. A number can be checked against a design; an adjective can't.
2. **Name the specific decision the number forces**, out loud, the moment it's stated —
   this is what [the Interview Framework's Step 4](../01_ml_system_design/00_interview_framework.md#step-4-trade-offs-failure-modes)
   means by tracing every design choice back to a stated requirement, done at requirements
   time instead of retrofitted during the trade-off discussion.
3. **Actively look for two NFRs in tension before proposing a design**, not after an
   interviewer points it out. The URL Shortener's own sharpest moment is naming, unprompted,
   that its latency/caching NFR and its revocation-latency NFR directly conflict — and
   resolving that tension is what separates a senior answer from a staff one, per [that
   tutorial's own Staff Altitude section](../../system_design_practice/11_design_url_shortener/tutorial.md#staff-altitude).
   Scan every pair of stated NFRs for this before sketching a single box: availability vs.
   consistency (CAP), cost vs. durability, latency vs. security (an auth check on every
   request is not free), and freshness vs. cost are the four pairings that surface a design
   tension most often.

## A Real-Tools Quick Reference, By Category

The technology name is always the *last* step — a consequence of the FR/NFR answers above,
never the first, exactly as [Part 11's six-axes framework already
established](11_taxonomy_of_storage_choice.md#the-anti-pattern-named-explicitly-fashion-driven-selection)
for storage specifically. This table is a fast index into categories this repo already
covers in full depth — entries here are pointers and one-line differentiators, not a
restatement of the mechanism; follow the link for the actual trade-offs before defending a
choice in an interview.

| Category | Real tools | One line on choosing among them | Full depth |
|---|---|---|---|
| Load balancer (L4/L7) | AWS NLB (L4), Envoy/NGINX/AWS ALB (L7), HAProxy (either) | L4 for cheap, connection-blind volume in front; L7 only for content-based routing, sticky sessions, or connection draining | [Part 19](19_load_balancing.md) |
| Cache | Redis (feature-rich, TTL + pub/sub + counters), Memcached (simpler, pure cache), CDN edge (Cloudflare/Akamai/Fastly/CloudFront) | Redis when the cache also needs to do rate-limiting/leaderboards/pub-sub; Memcached when it genuinely only needs to cache | [Part 15](15_caching.md) |
| SQL / relational | Postgres, MySQL | Default when the workload is genuinely multi-predicate/relational and needs ACID — see axis 1 before reaching for this by habit | [Part 11 §Access Pattern](11_taxonomy_of_storage_choice.md#1-access-pattern-how-is-the-data-actually-queried) |
| NewSQL (relational + horizontal scale) | Google Spanner (TrueTime), CockroachDB (HLC) | Only when the workload needs *both* ACID/multi-row transactions *and* multi-region survival — a real, non-negotiable latency floor comes with that combination | [Part 11 §NewSQL](11_taxonomy_of_storage_choice.md#newsql-the-relational-dream-reclaimed-at-scale) |
| NoSQL — key-value | DynamoDB, Redis | Point lookup by a known key, no joins, no range scan needed | [Part 11 §Access Pattern](11_taxonomy_of_storage_choice.md#1-access-pattern-how-is-the-data-actually-queried) |
| NoSQL — document | MongoDB | The entity is a tree with one clear owner (an order + its line items) — not a graph of many-to-many relationships | [Part 11 §Document Stores](11_taxonomy_of_storage_choice.md#the-second-child-document-stores-born-from-impedance-mismatch) |
| NoSQL — wide-column | Cassandra | Very high, near-random-key write volume across regions that must always accept a write, even mid-partition | [Part 11 §~2005](11_taxonomy_of_storage_choice.md#2005-google-and-amazon-hit-the-wall-nosql-begins-with-key-value-stores) |
| Graph database | Neo4j | The query itself is about relationships — "friends of friends within N hops," fraud-ring detection — not about fetching one entity | [Part 11 §Graph Databases](11_taxonomy_of_storage_choice.md#the-third-child-graph-databases-built-specifically-for-relationships) |
| Vector database | Pinecone, Weaviate, Qdrant, pgvector (HNSW) | Similarity search over embeddings (RAG retrieval) — nearest-neighbor, not exact match | [Part 11 §Vector Databases](11_taxonomy_of_storage_choice.md#the-newest-arrival-vector-databases-similarity-search-in-high-dimensional-space) |
| Analytical / columnar | ClickHouse, Snowflake, Parquet-on-object-storage | Aggregation across millions of rows but only a handful of columns — a row store pays for every untouched column | [Part 11 §Access Pattern](11_taxonomy_of_storage_choice.md#1-access-pattern-how-is-the-data-actually-queried) |
| Message queue / broker | Amazon SQS, RabbitMQ | Simpler point-to-point work distribution; messages genuinely disappearing once handled is the right model | [Part 18](18_message_queues_and_event_driven_semantics.md) |
| Message log / stream | Apache Kafka, Pulsar | Multiple independent consumers need to read the same stream at their own pace, and replay matters | [Part 18](18_message_queues_and_event_driven_semantics.md) |
| Search index | Elasticsearch, OpenSearch | Multi-predicate, full-text access pattern neither a B-tree nor an LSM-tree serves well | [Part 11's Netflix example](11_taxonomy_of_storage_choice.md#the-golden-hammer-fallacy-and-its-antidote-polyglot-persistence) |
| Object / blob storage | S3, GCS, Azure Blob | Large, infrequently-accessed payloads (video, backups, data lake) where cold-tier economics dominate | [Part 6's storage economics](06_mechanical_sympathy_and_physics_of_latency.md#the-economics-of-machine-cost-is-physics) |
| Service mesh / sidecar | Istio, Linkerd, Envoy | Cross-cutting retries/mTLS/observability as infrastructure, not duplicated per-service code | [system_design_practice Part 01](../../system_design_practice/01_distributed_systems_foundations/tutorial.md#service-mesh-cross-cutting-concerns-without-cross-cutting-code) |
| Service discovery / coordination | Kubernetes-native (CoreDNS + kube-proxy), Consul, etcd | Kubernetes-native by default in a K8s-hosted system; etcd/Consul when discovery or distributed locking is needed outside that platform | [Part 20](20_microservices_architecture_patterns.md#service-discovery-how-a-service-finds-another-service-whose-address-keeps-changing) |

## Designing and Operating From First Principles

1. Have I written an explicit FR/NFR table before sketching any component — or am I holding
   the clarified answers only in my head, where nothing forces a later decision to trace
   back to one of them?
2. For every NFR I've stated, have I named the specific design decision it *drives* — or is
   it sitting there as an adjective ("fast," "secure") with no number and no consequence
   attached?
3. Have I scanned every pair of stated NFRs for a direct tension (availability vs.
   consistency, cost vs. durability, latency vs. security) *before* proposing a design, the
   way the URL Shortener's revocation-vs-caching conflict was named unprompted?
4. Am I choosing a technology because it satisfies the specific NFRs just stated — or because
   it's the tool I already know, the tool that's trending, or the tool the last system used?
5. Have I named at least one explicit non-goal, the same way naming what a system *doesn't*
   do bounds scope as effectively as naming what it does?

## Key Takeaways

- **Clarifying questions aren't yet a specification** — the [Interview
  Framework's](../01_ml_system_design/00_interview_framework.md) Step 1 questions have to be
  restated as an explicit, numbered FR/NFR table before any design decision can be said to
  trace back to a requirement.
- **Functional requirements are derived by walking fixed categories** — core actions,
  actors/roles, the full CRUD surface, administrative/edge operations, and explicit
  non-goals — rather than by open-ended brainstorming, which is exactly where an
  easy-to-forget action (revocation, an admin override) gets silently dropped.
- **Non-functional requirements draw from nine recurring categories** — latency,
  availability, consistency, durability, scalability direction, security, cost, compliance,
  observability — each mapping onto mechanism already established elsewhere in this repo.
- **The "Drives" column is the actual skill being tested**: stating a requirement as a
  number and naming the specific decision it forces, per [the URL Shortener tutorial's
  worked
  example](../../system_design_practice/11_design_url_shortener/tutorial.md#non-functional-requirements),
  is what separates "I asked good questions" from "I have a spec I can be held to."
- **Naming a tension between two NFRs unprompted, before proposing a design**, is one of the
  highest-signal moves available in any system design round — the URL Shortener's own
  revocation-vs-caching conflict is the canonical worked example.
- **The technology table is a last step, not a first one** — every entry above is a
  consequence of an FR/NFR answer, and the full trade-off reasoning behind each category
  lives in the linked part, not in this table.

## Quick Self-Check

- Explain why a list of answered clarifying questions is not the same thing as a
  specification — what specifically does writing an explicit FR/NFR table add?
- Walk through the four categories functional requirements should be derived from, and name
  a concrete example of a requirement each one would surface that open-ended brainstorming
  might miss.
- Pick any two NFR categories from the nine-row table and describe a realistic scenario
  where they'd be in direct tension for the same system.
- Explain, using the URL Shortener's key-generation example, how a non-functional
  requirement (non-enumerability) can hide inside what looks like a purely technical
  encoding choice.
- For a system with a sub-millisecond latency budget and a strong consistency requirement on
  the same piece of data, explain why those two NFRs are in tension and what it would cost
  to satisfy both simultaneously.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Spec-first framing (the default for 'how do you approach a design question'):** "Before
  I draw anything, I restate the clarifying answers as an explicit FR/NFR table — functional
  requirements from a fixed checklist of actors, actions, and edge operations, non-functional
  requirements from nine recurring categories like latency, consistency, and durability. That
  table is what I trace every later decision back to, rather than letting design choices float
  free of a stated reason."
- **Tension-first framing (good for demonstrating staff-level judgment):** "I actively scan
  the NFRs I've just stated for pairs that conflict — availability against consistency, cost
  against durability — and name that tension out loud before proposing a design, rather than
  waiting for the interviewer to surface it. Naming the conflict first is usually worth more
  than the design itself."
- **Tools-last framing (good for a 'why did you pick that database' follow-up):** "I never
  start from a technology name. I start from the access pattern, latency budget, and
  consistency requirement, and the technology falls out as the last step — which is also
  why I can defend the choice by pointing back at a specific requirement instead of a
  preference."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **FR / NFR** (n., initialisms) — Functional Requirements (what the system does) versus
  Non-Functional Requirements (how well, under what constraints); the standard split a spec
  is built from.
- **Drives** (v., used as a table-column label) — the specific design decision a stated
  requirement forces; the mechanism that turns a requirement from a fact into a constraint.
- **non-goal** (n.) — something explicitly stated as out of scope, as valuable to name as an
  in-scope requirement.
- **golden hammer fallacy** (n. phrase) — reaching for a familiar tool regardless of fit;
  the failure mode the "tools last" ordering exists to prevent.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…a spec I can be held to"** — the fluent way to describe the difference between having
  asked good clarifying questions and having actually written them down as requirements.
- **"…naming the tension before it's pointed out"** — a compact way to describe surfacing a
  conflict between two NFRs unprompted, one of the highest-signal moves in a design round.
- **"…the technology is the last step, not the first"** — a reusable line for defending any
  tool choice by pointing back at the requirement that produced it.

---

**Previous:** [Part 20: Microservices Architecture Patterns](20_microservices_architecture_patterns.md)  |  **Next:** [Part 22: Proxies — Forward, Reverse, and Why "Reverse Proxy vs. Load Balancer" Is a Trick Question](22_proxies_forward_and_reverse.md)

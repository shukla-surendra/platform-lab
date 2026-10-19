# Prerequisite Concepts, Part 3: Communication and Resilience

[Part 1](01_performance_and_scale.md) covered measurement and scaling; [Part 2](02_data_and_consistency.md)
covered data distribution. This part covers how machines actually talk to each other, and
the vocabulary for reasoning about what happens when a piece of that communication fails —
the last layer of shared assumptions every case study in this repo builds on.

## What Actually Happens When You Hit Enter

A classic warm-up question ("walk me through what happens when you type a URL and hit
enter") that's genuinely worth understanding, not just memorizing as an answer:

```mermaid
flowchart LR
    A["1. DNS lookup:\ndomain -> IP address"] --> B["2. TCP handshake:\nSYN / SYN-ACK / ACK"]
    B --> C["3. TLS handshake:\nnegotiate encryption"]
    C --> D["4. HTTP request sent"]
    D --> E["5. Server processes,\nsends HTTP response"]
    E --> F["6. Browser renders response"]
```

1. **DNS resolution**: the browser needs an IP address, not a domain name — it asks a DNS
   resolver, which (if not cached) walks a hierarchy of nameservers to find the IP address
   that domain currently points to.
2. **TCP handshake**: before any data flows, the client and server agree to a connection —
   the three-way handshake (`SYN` → `SYN-ACK` → `ACK`) establishes a reliable, ordered
   channel between them.
3. **TLS handshake** (for HTTPS): client and server negotiate encryption — exchange
   certificates, agree on a shared symmetric key — so everything sent afterward is
   encrypted in transit.
4. **HTTP request/response**: only now does the actual application-level request go out,
   and the server's response comes back over the already-established, already-encrypted
   connection.

**Why this matters beyond trivia**: every one of these steps adds latency *before any
actual application logic runs* — which is exactly why techniques like DNS caching, TLS
session resumption (skip re-negotiating on a reconnect), and HTTP keep-alive (reuse an
existing TCP connection for multiple requests instead of repeating the handshake every
time) exist. Understanding the stack tells you *where* a "why is this slow" investigation
should even look — a slow DNS resolver or an unnecessary TLS renegotiation can dominate a
latency budget that looks, from the application code's perspective, like a mystery.

## TCP vs. UDP

Two transport-layer protocols with a genuine, deliberate trade-off:

- **TCP**: connection-oriented, guarantees delivery, ordering, and error-checking — if a
  packet is lost, it's retransmitted; if packets arrive out of order, TCP reorders them
  before handing data to the application. The cost is overhead: the handshake, and the
  latency of waiting for retransmission when something is lost.
- **UDP**: connectionless, no delivery/ordering guarantees — packets are just sent, and if
  one is lost, nobody retransmits it automatically. The upside is speed and lower overhead:
  no handshake, no waiting on a lost packet before processing the next one.

**Why anyone chooses UDP given it's "less reliable"**: for some domains, a lost packet
that arrives late is *worse* than a lost packet that's simply skipped — video streaming and
real-time gaming are the canonical examples. A dropped video frame that arrives 500ms late
(after TCP retransmits it) is useless; you've already moved past that point in the
stream. Better to drop it and move on, which is exactly what UDP-based protocols do. TCP is
the correct default for almost everything else (HTTP, database connections, anything where
"the data must all arrive, correctly, in order" matters more than raw speed).

## Synchronous vs. Asynchronous Communication

- **Synchronous**: the caller sends a request and *blocks*, waiting for a response before
  doing anything else. Simple to reason about (linear, request-then-response), but the
  caller's own progress is now hostage to the callee's latency.
- **Asynchronous**: the caller sends a request and continues doing other work, handling the
  response later (via a callback, a promise/future, or a completely separate message when
  the work is done). More complex to reason about, but decouples the caller's throughput
  from the callee's latency.

**The direct link to the [message queue concept in
Fundamentals](../ml_system_design/00_interview_framework_fundamentals.md#message-queues)**: a queue is the
infrastructure pattern that makes asynchronous communication reliable at scale — the
producer doesn't wait for the consumer to process a message, it just enqueues it and moves
on, and the queue absorbs the timing mismatch between how fast producers produce and how
fast consumers can keep up.

## Push vs. Pull

A related but distinct axis: **who initiates** the transfer of new information.

- **Pull (polling)**: the consumer repeatedly asks "is there anything new?" — simple, but
  wastes work on empty checks and has a latency floor equal to the polling interval (ask
  every 30 seconds, and worst-case you learn about new data 30 seconds late).
- **Push**: the producer proactively sends data the moment it's available — lower latency
  (no polling delay), but the producer now needs to track *who* to push to, and what
  happens if a consumer is temporarily unreachable.
- **Webhooks**: a specific, common push pattern for server-to-server communication — the
  consumer registers a URL, and the producer POSTs to it when an event happens, inverting
  the usual client-initiates-requests model.
- **Streaming**: a persistent, held-open connection (as opposed to discrete push
  notifications) over which a continuous flow of updates arrives — the mechanism underneath
  the [chat system case study's](../../system_design_practice/03_design_chat_system/tutorial.md#deep-dive-connection-management-at-scale)
  entire connection-management design, and the reason that case study is a genuinely
  different problem from a typical request/response API.

### Fan-Out: Push Applied to "One Write, Many Readers"

**Fan-out** is push vs. pull applied to a specific, recurring shape: one write needs to
reach *many* readers (a social post reaching every follower, a notification reaching every
subscriber). The push-vs-pull choice here has two named variants, each paying a different
cost:

- **Fan-out-on-write (push)**: the instant something is posted, the system immediately
  writes a copy of it into every follower's own feed/inbox. Reads are then trivially fast —
  "give me my feed" is just "read my own pre-computed feed," one lookup, no fan-out work
  happens at read time at all. The cost is paid on the write side, and it's paid *once per
  follower* — posting to an account with 50 million followers means 50 million writes for
  that one post.
- **Fan-out-on-read (pull)**: nothing is pre-computed at write time; a feed is assembled on
  demand by pulling recent posts from everyone a user follows and merging them at read time.
  Writes stay cheap and constant-cost regardless of follower count, but every single feed
  read now does real work — fetching and merging from potentially thousands of followed
  accounts.

**Why this is exactly [Part 12's celebrity/hot-key
problem](12_sharding_and_the_vertical_wall.md#the-celebrity-problem-the-hot-key-consistent-hashing-cannot-fix),
recurring at the application layer**: fan-out-on-write turns one write from a
high-follower-count account into a write storm — the same shape as a hot key overwhelming
one shard, just spread across many downstream feed writes instead of one overloaded
partition. Production systems handle this the same way Part 12 already named the trade-off:
most accounts use fan-out-on-write (cheap reads, and follower counts are small enough that
the write fan-out is cheap too), while a small number of very-high-follower-count accounts
fall back to fan-out-on-read for just their own posts — a hybrid, not a single global
choice. This is the actual mechanism behind the [Twitter feed case
study's](../../system_design_practice/02_design_twitter_feed/tutorial.md) fan-out deep-dive.

## Caching and Load Balancing, Briefly

Both covered in full depth in [Fundamentals](../ml_system_design/00_interview_framework_fundamentals.md) — flagged
here only so the vocabulary is complete before you read further: **caching** trades
freshness for speed by storing frequently-accessed data closer to where it's needed (the
hard part is invalidation, not storage); **load balancing** distributes incoming requests
across multiple servers so no single one is overwhelmed (L4 balances on IP/port, L7 can
route on HTTP content like path or header).

## Resilience Vocabulary

The shared language for reasoning about what happens when a component fails — every case
study in this repo expects you to name these proactively, not just fix a failure once
asked "what if this breaks":

- **Single point of failure (SPOF)**: any component whose failure takes down the whole
  system, because nothing else can do its job. The first thing to look for when reviewing
  your own design — "what's the one box that, if it dies, everything stops?"
- **Redundancy**: having more than one of a component, so one failing doesn't remove the
  capability entirely — the general fix for a SPOF (multiple replicas, multiple availability
  zones, multiple regions).
- **Failover**: the *process* of switching from a failed component to a redundant one —
  redundancy is the "what" (having spares), failover is the "how" (actually cutting over to
  one when needed), and a failover process that's never been tested is a common,
  expensive-to-discover gap — see the [DR failover tricky
  scenario](../ml_system_design/12_tricky_scenarios_12_dr_failover_slow.md) for exactly this failure mode
  playing out.
- **Circuit breaker**: a pattern that stops calling a dependency once it's clearly failing,
  instead of retrying into a struggling system and making things worse. Three states worth
  knowing by name: **closed** (normal operation, calls flow through), **open** (failures
  crossed a threshold, calls are rejected immediately without even attempting the
  dependency), **half-open** (after a cooldown, let a small number of calls through to test
  if the dependency has recovered, before fully closing again). This is the concrete
  mechanism behind "fail fast instead of piling on a struggling dependency."
- **Bulkhead**: named after ship design — a ship's hull is divided into watertight
  compartments so *one* compartment flooding doesn't sink the whole ship. Applied to
  systems: isolate resources (thread pools, connection pools) *per dependency*, so one
  overwhelmed downstream service exhausting its allotted resources doesn't starve requests
  to every *other*, healthy dependency sharing the same pool.
- **Graceful degradation**: losing functionality in a controlled, prioritized way under
  stress, rather than failing outright — e.g., a product page that can't reach the
  recommendations service still renders the product, just without a "you might also like"
  section, instead of failing the whole page load.

**Why this vocabulary matters as a set, not individually**: a mature production system
layers several of these together — a circuit breaker prevents hammering a failing
dependency, a bulkhead prevents that dependency's failure from starving unrelated request
paths, and graceful degradation defines what the user actually sees while all of this is
happening. Naming which of these applies to a specific failure mode, together, is what
turns "this could fail" into an actual design decision.

## Rate Limiting

The worked algorithms (fixed window, sliding window, **token bucket**) are covered in full
in [Fundamentals](../ml_system_design/00_interview_framework_fundamentals.md#worked-example-design-a-rate-limiter)
and extended to global/multi-region scale in the [staff-level rate limiter case
study](../../system_design_practice/07_design_rate_limiter_at_scale/tutorial.md). The general
purpose: protecting a system's own availability by rejecting or throttling excess load
before it degrades service for everyone — one of the most common "design a small system"
warm-up questions precisely because it touches so much of this primer's vocabulary at once
(throughput, availability, the CAP-theorem trade-off of a distributed counter, and graceful
degradation under a fail-open-vs-fail-closed decision).

**One algorithm worth naming here that Fundamentals doesn't cover: the leaky bucket**, since
it's routinely confused with token bucket despite solving a genuinely different problem.

- **Token bucket** (already covered in Fundamentals): a bucket holds up to *N* tokens, refills
  at a steady rate, and a request consumes one token to proceed. Critically, **it allows
  bursts** — if the bucket has been sitting full (no recent requests), a client can fire off
  up to *N* requests instantly, back-to-back, and still be allowed through.
- **Leaky bucket**: requests are added to a queue (the "bucket"), and processed out of it at
  a **strictly constant rate**, regardless of how bursty the requests arriving into it are —
  like water leaking out of a bucket at a fixed rate no matter how fast it's poured in. If
  the bucket fills up (too many requests arrive before the queue drains), new requests are
  rejected. **It never allows a burst through** — the output rate is smoothed to exactly
  constant, which is the entire point of choosing it.

**The precise distinction, stated as a single sentence**: token bucket bounds the *average*
rate but permits bursts up to the bucket's capacity; leaky bucket bounds the
*instantaneous* rate to a constant, smoothing bursts out entirely rather than permitting
them. Choose token bucket when occasional bursts are fine as long as the average holds
(most API rate limits); choose leaky bucket when the downstream system genuinely cannot
tolerate a burst at all, even a brief one (e.g., protecting a fixed-capacity resource like a
serial hardware interface, or shaping traffic onto a network link with a hard bandwidth
ceiling).

## Quick Self-Check

You've now covered the vocabulary every tutorial in this repo assumes. Before starting
[0. The Interview Framework](../ml_system_design/00_interview_framework.md), you should be able to
answer:

- Why does understanding the DNS → TCP → TLS → HTTP sequence help you debug "why is this
  slow" beyond just profiling application code?
- Why is UDP a deliberate choice for some domains rather than simply "the worse protocol"?
- What's the difference between a circuit breaker and a bulkhead — what specific failure
  does each one prevent that the other doesn't?
- Why does fan-out-on-write turn a single celebrity post into the exact same shape of
  problem as Part 12's hot-key/celebrity problem — what's actually overloaded in both cases?
- Why do most production feed systems use a *hybrid* of fan-out-on-write and fan-out-on-read
  rather than picking one strategy globally for every account?
- Token bucket and leaky bucket are both "bucket" metaphors and both used for rate limiting.
  Explain precisely why they produce different behavior for a bursty client — what does
  each one actually bound?
- Why does a load balancer's L7 routing capability (from Fundamentals) depend on
  understanding that HTTP happens *after* the TCP/TLS handshake, not as part of it?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Where-to-look framing (the default for 'why is this slow' debugging questions):** "I'd
  use the DNS-to-TCP-to-TLS-to-HTTP sequence as a checklist before touching application
  code — a slow DNS resolver or an unnecessary TLS renegotiation can dominate a latency
  budget that looks, from inside the app, like an unexplainable mystery."
- **Deliberate-trade-off framing (good for TCP vs. UDP):** "I wouldn't call UDP 'the less
  reliable protocol' — for video or real-time gaming, a packet that arrives late after
  retransmission is actually worse than one that's simply dropped, so UDP is a deliberate
  choice for that domain, not a compromise."
- **Layered-defense framing (good for resilience-pattern questions):** "I'd name these
  together, not individually — a circuit breaker stops hammering a failing dependency, a
  bulkhead stops that failure from starving unrelated request paths, and graceful
  degradation defines what the user actually sees while both are happening."
- **Hybrid-fan-out framing (good for a feed/notification-system design question):** "I
  wouldn't pick fan-out-on-write or fan-out-on-read globally — I'd default to
  fan-out-on-write for the vast majority of accounts, since it keeps reads cheap and most
  accounts have few enough followers that the write fan-out is cheap too, then fall back to
  fan-out-on-read specifically for the small number of very-high-follower accounts, where
  fan-out-on-write would otherwise turn one post into a write storm — the same shape as a
  hot key overwhelming one shard, just at the application layer."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **circuit breaker** (n. phrase) — a pattern with closed/open/half-open states that stops
  calling a clearly-failing dependency instead of retrying into it.
- **bulkhead** (n., from ship design) — isolating resources per-dependency so one
  overwhelmed downstream service can't starve requests to unrelated, healthy dependencies.
- **single point of failure (SPOF)** (n. phrase) — any component whose failure takes down
  the whole system because nothing else can do its job.
- **keep-alive** (n. phrase) — reusing an already-established TCP connection for multiple
  requests instead of repeating the handshake every time.
- **fan-out-on-write / fan-out-on-read** (n. phrases) — pre-computing every follower's feed
  entry at post time (cheap reads, expensive writes for high-follower accounts) versus
  assembling a feed at read time by pulling from everyone followed (cheap, constant writes,
  expensive reads) — most production systems use a hybrid of both.
- **token bucket / leaky bucket** (n. phrases) — two rate-limiting algorithms that bound
  different things: token bucket bounds the *average* rate while permitting bursts up to a
  capacity; leaky bucket bounds the *instantaneous* rate to a constant, smoothing bursts out
  entirely.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…is the how; …is the what"** — a clean template for separating a mechanism from the
  property it provides. *"Redundancy is the what — having spares; failover is the how —
  actually cutting over to one."*
- **"…that's never been tested is a common, expensive-to-discover gap"** — a fluent way to
  flag an unvalidated assumption (an untested failover path) as a real risk, not a
  formality.
- **hostage** (used figuratively) — *"Synchronous communication makes the caller's
  progress hostage to the callee's latency."* A vivid way to argue for decoupling.

---

**Previous:** [Part 2: Data & Consistency](02_data_and_consistency.md)  |  **Next:** [Part 4: CPU vs. GPU](04_cpu_vs_gpu.md)

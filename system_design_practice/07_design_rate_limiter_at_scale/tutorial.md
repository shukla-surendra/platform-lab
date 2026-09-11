# Design a Rate Limiter at Global Scale

**Primarily tests**: distributed counting, clock synchronization, and the
approximate-vs-exact enforcement trade-off. Extends the
[single-node rate limiter in the ML track's fundamentals tutorial](../../system_design_foundation/ml_system_design/00_interview_framework_fundamentals.md#worked-example-design-a-rate-limiter)
(one Redis instance, one counting algorithm) to the genuinely harder problem: enforcing
one global limit per user/API-key when requests land on servers spread across multiple
regions.

**This tutorial assumes the algorithm landscape is already known** and focuses entirely on
the region-scale coordination problem. Three companion deep-dives fill in the rest of the
picture: **[algorithms_all_iterations.md](algorithms_all_iterations.md)** walks every
algorithm (fixed window through GCRA) as a chain of iterations, each motivated by a named
flaw in the last; **[kubernetes_native_implementations.md](kubernetes_native_implementations.md)**
maps every algorithm onto a concrete, deployable Kubernetes pattern — ingress annotations,
Envoy local/global rate limiting, Kong, Gateway API, and a DIY Redis-backed extension of
this repo's own [LLD rate limiter](../../lld/05_rate_limiter/problem.md) — and shows that
the "local counter + global aggregator" architecture below isn't just a diagram, it's what
Envoy's global rate-limit service deployed per-region actually is;
**[build_vs_buy_and_tooling_landscape.md](build_vs_buy_and_tooling_landscape.md)** answers
the question underneath all of it — do you actually write this code, or is there tooling
for it — with a different answer depending on whether you're in an LLD round, a system
design round, or shipping something real.

## Clarify

- Is the limit **per-region** (each region enforces its own independent quota — much
  simpler) or **truly global** (a user's total requests across all regions combined must
  stay under one limit)? Assume truly global — that's the version that's actually hard.
- Hard cutoff or throttling/backoff signal?
- How much overshoot is tolerable? (This single answer determines almost the entire
  design — see below.)

## High-Level Design

```mermaid
flowchart TB
    ClientUS["Client Request\n(US region)"] --> AppUS["App Server (US)"]
    ClientEU["Client Request\n(EU region)"] --> AppEU["App Server (EU)"]
    AppUS --> LocalCounterUS["Local Counter\n(fast, regional)"]
    AppEU --> LocalCounterEU["Local Counter\n(fast, regional)"]
    LocalCounterUS -->|"periodic async sync"| GlobalAggregator["Global Aggregator\n(eventually consistent count)"]
    LocalCounterEU -->|"periodic async sync"| GlobalAggregator
    GlobalAggregator -.->|"push updated global\nbudget/quota"| LocalCounterUS
    GlobalAggregator -.-> LocalCounterEU
```

The diagram above compresses "Client → App Server" into one hop for clarity — in a real
deployment a load balancer sits in that gap, and *where exactly* the rate-limit check
happens relative to it is a detail worth being precise about, not glossed over.

## Deep-Dive: Where the Rate Limiter Sits Relative to the Load Balancer

**Precise answer: the rate-limit check runs before the load-balancing decision, and in
most real stacks they're the same proxy process, not two separate hops.** Envoy, NGINX,
and Kong — the exact tools named in
[kubernetes_native_implementations.md](kubernetes_native_implementations.md) — each do
**both** jobs: an L7 load balancer's job is fundamentally "terminate the request, decide
what to do with it," and rate limiting is one of the decisions made before the other
decision (which backend to route to). In Envoy's own filter-chain model, this is literal:
the `ratelimit` HTTP filter runs *before* the `router` filter that performs load balancing
— a rejected request never reaches the code path that would have picked a backend pod at
all.

```mermaid
flowchart TB
    Client --> DNS["DNS / Global LB\n(anycast, region selection —\nsee [Part 19: DNS-Level and Global LB](../../system_design_foundation/00_prerequisite_concepts/19_load_balancing.md#dns-level-and-global-load-balancing))"]
    DNS --> L4["Regional L4 LB\n(TCP-level — AWS NLB.\nNo HTTP visibility, so it\ncannot see client_id/API-key)"]
    L4 --> L7["L7 LB / Gateway\n(Envoy, NGINX, Kong — HTTP-aware)"]
    L7 -->|"1. ratelimit filter runs FIRST"| RLCheck{"allow?"}
    RLCheck -->|"reject: 429"| Client
    RLCheck -->|"allow"| Router["2. router filter runs SECOND\n(the actual load-balancing decision:\nround-robin / least-conn / consistent hash)"]
    Router --> Pod1["Backend Pod 1"]
    Router --> Pod2["Backend Pod 2"]
    Router --> Pod3["Backend Pod 3"]
```

**Why this ordering, specifically, and not the reverse:**

- **Cost.** Load balancing does real work — picking a healthy backend, opening or reusing
  a connection, forwarding bytes. Rejecting a request *before* paying that cost is
  strictly cheaper than balancing it to a backend and rejecting it there — the same
  "fail fast, cheap" logic that motivates rejecting at the edge (CDN/WAF) before it even
  reaches this L7 hop at all, for the coarsest, cheapest checks (raw IP-based abuse).
- **Correctness — this is the load-bearing reason.** Rate limiting *after* the
  load-balancing decision means the check runs independently on whichever backend the
  request happened to land on. That's exactly
  [kubernetes_native_implementations.md's Iteration 1 failure](kubernetes_native_implementations.md#iteration-1-per-pod-in-memory-limiter-the-naive-answer):
  `replicas: 3` behind a load balancer fans one client's traffic across 3 independent
  enforcement points, each blind to the other two, producing an effective limit of
  `3 × configured_limit`. **Checking at or before the single load-balancing decision
  point — one hop, one shared view of state (Redis, or the local budget in this
  tutorial's design) — is what keeps the count meaningful; checking after it, once
  traffic has already been fanned out to N independent backends, is precisely what
  breaks it.**

**Why an L4 load balancer can't be "the rate limiter" on its own:** an L4 balancer
(AWS NLB, per
[Part 19's L4-vs-L7 mechanics](../../system_design_foundation/00_prerequisite_concepts/19_load_balancing.md#l4-vs-l7-the-mechanism-itself))
never parses the HTTP request — it has no visibility into a client ID, API key, or JWT
claim, only source IP and port. It can enforce coarse connection-level limits (max new
connections/sec from one IP — genuinely useful as a first line of defense against raw
connection floods), but it structurally cannot enforce the per-user/per-API-key limits
this whole tutorial is about. That requires HTTP-layer visibility, which is exactly why
every implementation in
[kubernetes_native_implementations.md](kubernetes_native_implementations.md) — and every
managed equivalent (AWS ALB needs **AWS WAF's rate-based rules** attached alongside it;
plain ALB has no native per-user rate limiting either) — is an L7 mechanism, not an L4
one. "The load balancer does rate limiting" is really shorthand for "the *L7* load
balancer, or something attached to it, does" — worth being precise about that distinction
unprompted.

**Mapping this back onto the diagram above:** `AppUS`'s box already implies a pool of app
servers behind a regional L7 load balancer, not a single machine — the `LocalCounterUS`
check happens in that L7 hop, on the *region's* single logical entry point, before the L7
balancer's own router filter fans the (now-admitted) request out across `AppUS`'s pool.
That's what keeps `LocalCounterUS` a single, coherent regional count instead of silently
fragmenting into one counter per app server — the same correctness argument above, just
restated at the regional-budget level this diagram operates at.

## Deep-Dive: Why "Just Use One Redis Instance Globally" Doesn't Work

The single-node answer (one Redis instance, atomic increment-and-check) is the correct
*starting* answer, and it's exactly where a senior-level response stops. The staff-level
question is: **what happens when app servers in the US and EU both need to check the same
global counter for every request?**

- **A single global counter store** means every request, regardless of region, makes a
  network round-trip to wherever that store lives — for a user in Asia checking against a
  US-hosted counter, this adds significant latency to *every single request*, defeating
  the purpose of having regional app servers at all.
- **This is a direct instance of the CAP-theorem trade-off** from the
  [ML track's fundamentals tutorial](../../system_design_foundation/ml_system_design/00_interview_framework_fundamentals.md#cap-theorem-consistency-models):
  a perfectly accurate global count requires either a single source of truth (a latency
  and availability bottleneck) or synchronous cross-region coordination on every request
  (a consensus-style cost, per the
  [foundations tutorial](../01_distributed_systems_foundations/tutorial.md#consensus-making-multiple-nodes-agree-on-one-truth)) —
  neither is acceptable at the latency budget a rate limiter needs to operate within
  (it must add negligible overhead to every request it protects).

## Deep-Dive: The Practical Answer — Local Enforcement + Async Global Reconciliation

- **Each region gets a local budget** — a fraction of the total global limit, allocated
  to that region (proportional to its typical traffic share, or dynamically rebalanced).
  Requests are checked against this **local** counter, at local latency — no cross-region
  call on the request's critical path at all.
- **Regions periodically report their local usage to a global aggregator** (every few
  seconds), which recomputes actual global usage and can push back adjusted local budgets
  — a region running hot gets a smaller allocation next cycle; an idle region's spare
  budget can be redistributed.
- **This is explicitly an approximate enforcement mechanism**: for the few seconds between
  reconciliation cycles, the true global count can drift above the nominal limit by a
  bounded amount (at most, roughly the sum of what each region could independently spend
  before the next sync). **State this bound explicitly as a design parameter** — "we
  tolerate up to N% overshoot, bounded by the reconciliation interval" — rather than
  presenting the design as if it enforces the limit exactly, which it does not and cannot
  at this latency budget.
- **When exact enforcement genuinely is required** (a hard business/legal limit, not just
  a soft throttle), the answer changes: accept the latency cost of a synchronous check
  against a single authoritative store for that specific limit, and scope that
  exact-enforcement requirement narrowly (e.g., only for the specific action that legally
  must not exceed the limit), rather than applying the expensive synchronous pattern to
  every rate-limited endpoint uniformly.

## Deep-Dive: Clock Synchronization

Any rate-limiting algorithm using time windows (fixed window, sliding window — see the
[fundamentals tutorial's algorithm table](../../system_design_foundation/ml_system_design/00_interview_framework_fundamentals.md#worked-example-design-a-rate-limiter))
depends on consistent notions of time across regions:

- **Clock drift between regions' servers** can cause a window boundary to be interpreted
  slightly differently in different places — usually a minor issue for approximate
  enforcement, but worth naming as a reason exact, tight time-window boundaries are
  another place this design is inherently approximate, not a precision instrument.
- **NTP-synchronized clocks** are the practical baseline expectation; for anything
  requiring tighter guarantees, logical/vector clocks (per the
  [foundations tutorial](../01_distributed_systems_foundations/tutorial.md#crdts-vector-clocks-resolving-conflicts-without-coordination))
  establish relative ordering without depending on wall-clock precision at all — worth
  mentioning as the "if we truly needed it" answer, while noting it's usually overkill for
  a rate limiter's actual accuracy requirements.

## Trade-offs

| Decision | Option A | Option B | When to pick which |
|---|---|---|---|
| Enforcement scope | Per-region independent limits (simple, no cross-region coordination) | Global limit with async reconciliation (complex, matches the actual business requirement) | Per-region if the business requirement can be restated as "per-region," which is worth explicitly asking about before building the harder version |
| Reconciliation frequency | Frequent (tighter global accuracy, more sync overhead) | Infrequent (looser accuracy, less overhead) | Tune based on the tolerable-overshoot bound established during clarification — this is a quantitative decision, not a guess |
| Overshoot handling | Hard rejection once local budget exhausted | Soft throttle/backoff signal, allow some overshoot | Soft throttling is more forgiving of the inherent approximation in this design; hard rejection is simpler but makes the overshoot bound feel more like a bug than a designed trade-off |
| Exact vs. approximate | Approximate (this design) | Exact via synchronous global check | Exact only for the narrow subset of limits with a genuine hard requirement — applying it universally reintroduces the latency/availability problem this whole design exists to avoid |

## Staff Altitude

A **senior** answer proposes a single global counter and, if pushed, acknowledges it adds
latency.

A **staff** answer additionally: (1) immediately identifies that a single global counter
is a CAP-theorem trade-off in disguise and proposes local-enforcement-plus-reconciliation
without needing to be pushed there; (2) makes the **overshoot bound a named, quantified
design parameter** rather than an unstated approximation — this is the single detail that
most distinguishes a staff answer here; and (3) explicitly asks whether the "global limit"
requirement is even real, or an unexamined assumption — often a business requirement
stated as "no user should exceed X globally" actually tolerates being restated as
"per-region, which sums to approximately X" once the actual motivation (protecting a
downstream dependency, say) is understood, which is dramatically simpler to build.

## Failure Modes to Raise Proactively

- **The global aggregator becoming a single point of failure** — if reconciliation can't
  reach it, regions should fail toward their **last-known-good local budget**, not fail
  open (unbounded) or fail closed (reject everything) by default — state which failure
  direction is appropriate for this specific limit's purpose.
- **A region's traffic share shifting suddenly** (a viral event in one region) — a static
  regional budget allocation would under-serve that region while others sit under-
  utilized; dynamic rebalancing based on recent usage, not a fixed split, handles this.
- **Reconciliation lag compounding under aggregator slowness** — if the aggregator itself
  falls behind, the overshoot bound silently grows past its designed value; this needs its
  own monitoring and alerting, not just monitoring of the rate limiter's primary function.

## Staff Follow-Ups

- "The business now needs a *hard* legal limit for one specific action, while everything
  else stays approximate — how do you evolve this design to support both without
  duplicating the whole system?"
- "How would you test that your overshoot bound actually holds under a real traffic
  spike, not just in theory?"
- "A new region needs to be added — walk through how its initial budget allocation is
  determined before there's any usage history to base it on."

## Practice Variations

- Design a global unique-ID generator (a related "needs global coordination but can't
  afford synchronous global calls" problem — see Twitter Snowflake-style approaches).
- Design a distributed quota system for a multi-tenant API platform, where tenants have
  wildly different traffic patterns.
- Extend this design to support a "burst allowance" (short bursts above the sustained
  limit are permitted) on top of the base global-limit design — this is exactly what
  token bucket / GCRA add over the simpler counting algorithms; see
  [algorithms_all_iterations.md](algorithms_all_iterations.md#iteration-4-token-bucket).
- Walk through deploying this design on an actual Kubernetes cluster instead of just
  diagramming it — [kubernetes_native_implementations.md](kubernetes_native_implementations.md)
  has the concrete manifests (Envoy global rate-limit service + Redis, per region) and a
  hands-on exercise using this repo's own `k8s/k8s_explorer/` and `lld/05_rate_limiter/`.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **CAP-in-disguise framing (the default for this topic):** "A single global counter is a
  CAP-theorem trade-off wearing a rate-limiter costume — I'd name that immediately rather
  than waiting to be pushed there, and propose local enforcement with async reconciliation
  as the direct consequence of that trade-off, not a separate idea."
- **Named-parameter framing (good for the overshoot discussion, the single strongest
  signal in this topic):** "I wouldn't present this design as if it enforces the limit
  exactly — it doesn't and can't at this latency budget. I'd state the overshoot bound as
  an explicit, quantified design parameter: we tolerate up to N%, bounded by the
  reconciliation interval."
- **Question-the-requirement framing (good for 'is global even real'):** "Before building
  the harder version, I'd ask whether 'no user exceeds X globally' is a real requirement or
  an unexamined assumption — often the actual motivation is protecting a downstream
  dependency, and 'per-region, summing to approximately X' satisfies that just as well,
  dramatically more simply."

### Vocabulary Builder

- **reconciliation** (n.) — periodically syncing distributed local state back to a shared
  view of the truth, accepting temporary drift between syncs in exchange for avoiding a
  synchronous cross-region call on every request.
- **fail toward last-known-good** (v. phrase) — when a dependency (the global aggregator)
  becomes unreachable, defaulting to the most recent value you trusted rather than either
  extreme (fail open or fail closed).
- **overshoot bound** (n. phrase) — the maximum amount a distributed, approximate system
  can exceed its nominal limit before the next reconciliation, stated as a number rather
  than left implicit.
- **"…is exactly where a senior-level response stops"** — a fluent way to explicitly mark
  the boundary between a correct-but-incomplete answer and the harder version the question
  is actually testing.
- **"…check before the load-balancing decision, not after"** — the precise, reusable
  phrase for why a rate limiter belongs at or ahead of the L7 load balancer's own routing
  step: checking after it means checking once per already-fanned-out backend instead of
  once per shared decision point, which is what actually causes the multi-replica
  undercounting bug.

---

**Previous:** [6. Design a Distributed Message Queue](../06_design_distributed_message_queue/tutorial.md)  |  **Next:** [8. Design a Video Streaming Service](../08_design_video_streaming/tutorial.md)

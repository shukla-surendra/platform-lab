# Prerequisite Concepts, Part 1: Measuring and Scaling a System

Every tutorial in this repo — ML-specific or general distributed systems — uses a shared
vocabulary of measurement and scaling without re-explaining it each time: "p99 latency,"
"the nines," "horizontal scaling," "back-of-the-envelope." If any of that feels like
jargon rather than something you could derive yourself, start here. The goal isn't to
memorize definitions — it's to understand *why* each concept exists, so the vocabulary
becomes something you reach for naturally instead of something you're recalling.

## Latency vs. Throughput

Two numbers that sound similar and get confused constantly, but measure different things:

- **Latency**: how long *one* request takes, start to finish. Measured in time (ms, s).
- **Throughput**: how many requests a system handles *per unit of time*. Measured in a
  rate (requests/sec, MB/sec).

**The highway analogy makes the difference concrete**: latency is how long it takes one
car to drive from A to B. Throughput is how many cars per hour pass a given point on the
highway. You can have low latency with low throughput (an empty highway, one fast car) or
high throughput with high latency (a packed highway where every car is crawling, but
thousands pass per hour). **They're not the same axis, and optimizing one can actively
hurt the other** — batching requests together to raise throughput (do more work per
round-trip) typically *increases* the latency any individual request experiences, since it
now waits for the batch to fill. This exact tension is why the [rate limiter case
study](../../system_design_practice/07_design_rate_limiter_at_scale/tutorial.md) and the [LLM
serving deep-dive](../ml_system_design/06_rag_llm_serving_at_scale.md#deep-dive-llm-serving-internals-vllm-on-triton)
both spend real time on batching trade-offs — it's never free.

**Why this matters for system design specifically**: "make it fast" is not a real
requirement until you've said whether you mean low latency (each user waits less) or high
throughput (the system serves more users overall) — a design that's excellent on one axis
can be mediocre on the other, and clarifying which one actually matters is exactly the kind
of question the [interview framework](../ml_system_design/00_interview_framework.md#step-1-clarify-requirements)
asks you to ask before designing anything.

## Percentiles: Why "Average" Lies to You

If you measure the response time of 100 requests and report the *average*, you've thrown
away the single most important piece of information: **how bad the worst ones were.**

Concretely: 99 requests take 10ms, one takes 5000ms. The average is `(99×10 + 5000)/100 =
59.9ms` — which describes almost none of your actual users. 99% of them had a 10ms
experience; the average makes it look like everyone had a mediocre one, and it completely
hides that *someone* waited five full seconds.

**Percentiles fix this by describing the distribution, not a single blended number:**

| Term | Means | Typical use |
|---|---|---|
| **p50** (median) | 50% of requests were this fast or faster | "Typical" experience |
| **p90** | 90% of requests were this fast or faster | Still fairly representative |
| **p95** | 95% of requests were this fast or faster | Common SLO target |
| **p99** | 99% of requests were this fast or faster | The "tail" — what your unluckiest 1-in-100 users feel |
| **p99.9** | 99.9% of requests were this fast or faster | The tail of the tail — matters enormously at high volume |

### Reading a Percentile Value: What "p99 Latency = 3 Seconds" Actually Means

This is worth walking through slowly once, because the two-sided reading (what's true
*below* the value, what's true *above* it) is where the confusion usually lives.

**The mechanics**: take every request in your measurement window, sort their latencies
from fastest to slowest, and walk 99% of the way down that sorted list. The value sitting
at that point is p99. Concretely, with exactly 100 sorted measurements (index 1 = fastest,
index 100 = slowest):

| Position in sorted list | What it is |
|---|---|
| 1 | The fastest single request |
| 50 | p50 (the median) |
| 90 | p90 |
| 99 | **p99 — this is the value we're calling "3 seconds"** |
| 100 | The single slowest request (not usually reported as its own percentile — see below) |

So if **p99 = 3 seconds**:

- **Below/at p99 (the 99% side, positions 1-99):** every one of those 99 requests
  completed in **3 seconds or less**. This is the group people mean when they say "the
  typical experience" — and note that p50, p90, and p95 are all necessarily ≤ 3 seconds
  too, since percentiles only increase as you move up the list (p50 ≤ p90 ≤ p95 ≤ p99,
  always, by construction — it's a sorted list, it can't go the other way).
- **Above p99 (the 1% side, position 100 in this example):** that remaining request took
  **more than 3 seconds** — and here's the detail that trips people up: **p99 = 3 seconds
  tells you nothing about *how much* more.** It could be 3.01 seconds. It could be 45
  seconds. It could be a timeout at 5 minutes. p99 only marks *where the boundary is*, not
  how bad things get past it — which is exactly why production systems track p99.9 or even
  max latency *alongside* p99: p99 alone can't distinguish "one request that was
  imperceptibly slower" from "one request that hung and someone gave up."

**Scaled up to a real system**: nobody measures 100 requests and stops — a real service
measures continuously over a rolling window (say, every 5 minutes) across potentially
millions of requests, but the mechanics are identical, just with the "1%" now
representing a much bigger absolute number of unhappy real users. At 1 million
requests/day with p99 = 3 seconds: 990,000 requests/day finished in ≤3s, and **10,000
requests/day (the 1%) took longer than 3 seconds** — some of them probably far longer.
That 10,000 is the number worth holding onto; "1%" sounds negligible until you multiply it
by real traffic.

**Common misreadings worth ruling out explicitly:**

- p99 is **not** "the 99th slowest request" — it's the boundary such that *everything
  below it* (the fast 99%) sits under that value.
- p99 is **not** an average of the slow 1% — it says nothing about how slow that 1%
  actually got, only that they crossed the line.
- p99 is **not** the maximum — the single slowest request in any window can be, and
  usually is, considerably worse than the p99 value.

**How this is actually computed at scale, briefly**: sorting every single raw latency
value to find an exact percentile becomes expensive at high volume, so production
monitoring systems (Prometheus histograms, HDRHistogram, t-digest) typically compute an
*approximate* percentile from bucketed data instead of an exact sort — worth knowing the
name of this trade-off exists, even if the mechanics of a specific approximation algorithm
aren't something you need to derive from scratch in an interview.

**Why engineers obsess over p99, not average, at scale**: at 1 million requests/day, p99
represents 10,000 requests/day having a bad experience — not a rounding error, a real
number of real people. And **SLAs are almost always written against a percentile, never
an average**, precisely because average lets a system look healthy while a meaningful
slice of users are having a bad time.

**The tail at scale (the insight that makes this genuinely non-obvious)**: if a single
user-facing request internally fans out to, say, 100 backend calls, and each individual
backend call has a p99 latency (i.e., each is slow only 1% of the time) — what's the
probability the *overall* request is slow? Roughly `1 - (0.99)^100 ≈ 63%`. **A component
that's "almost always fast" becomes "usually slow" once you're waiting on 100 of them
simultaneously.** This is why tail latency compounds ferociously in fan-out-heavy
architectures (search, ad-serving, microservices with deep call chains) — and it's why
"just optimize the average" is a genuinely wrong instinct once a system has real
fan-out, not just a stylistic preference for percentiles.

## Availability: The Nines

Availability is the percentage of time a system is capable of correctly serving requests.
Conventionally described by how many "9"s are in the percentage — and the difference
between consecutive nines is not small:

| Availability | Downtime / year | Downtime / month | Downtime / day |
|---|---|---|---|
| 99% ("two nines") | 3.65 days | 7.3 hours | 14.4 minutes |
| 99.9% ("three nines") | 8.76 hours | 43.8 minutes | 86.4 seconds |
| 99.99% ("four nines") | 52.6 minutes | 4.4 minutes | 8.6 seconds |
| 99.999% ("five nines") | 5.26 minutes | 26.3 seconds | 0.86 seconds |

**Each additional nine is roughly an order-of-magnitude harder engineering problem, not a
proportionally small improvement** — going from three nines to four nines means your
entire *annual* allowed downtime shrinks from "almost 9 hours" to "under an hour." This is
why teams explicitly negotiate which nine they're actually targeting rather than reaching
reflexively for "as available as possible" — five-nines infrastructure (active-active
multi-region, automated failover, extensive redundancy) costs dramatically more to build
and operate than three-nines infrastructure, and most products don't need it.

**Composite availability — the multiplication trap**: if a request depends on three
independent services, each individually 99.9% available, the *overall* availability of
that request path is `0.999 × 0.999 × 0.999 ≈ 99.7%` — worse than any individual
component. **Every additional dependency in a call chain drags overall availability down**,
which is a direct, first-principles argument for why deep microservice call chains are an
availability liability, and why redundancy/fallbacks on critical-path dependencies matter
more as a system decomposes into more services, not less.

## SLI, SLO, and SLA: The Practical Triangle

Three related but distinct terms, easy to conflate:

- **SLI (Service Level Indicator)**: the actual metric being measured — "p99 latency,"
  "error rate," "availability." A number, observed.
- **SLO (Service Level Objective)**: the internal target for that metric — "p99 latency
  under 200ms," "99.9% availability." A goal a team holds itself to.
- **SLA (Service Level Agreement)**: an SLO turned into an external, often contractual,
  commitment — usually with consequences (credits, penalties) if missed.

**The practical distinction that matters**: an SLO is usually set *stricter* than the SLA,
deliberately — if your SLA promises 99.9% to customers, you might run an internal SLO of
99.95%, so you have room to notice and fix degradation before it actually breaches the
external commitment. Stating this buffer explicitly is a mark of someone who's actually
operated a production SLA, not just read the definition.

## Vertical vs. Horizontal Scaling

Two fundamentally different answers to "this system needs to handle more load":

- **Vertical scaling (scale up)**: give the existing machine more resources — more CPU,
  more RAM, a faster disk. Simple (no architectural change), but hits a hard ceiling (the
  biggest machine money can buy) and creates a single point of failure — one machine, one
  outage away from everything going down.
- **Horizontal scaling (scale out)**: add more machines, and distribute load across them
  (via the load balancing covered in
  [Fundamentals](../ml_system_design/00_interview_framework_fundamentals.md#load-balancing)). No hard ceiling —
  theoretically add machines indefinitely — and naturally more fault-tolerant (one machine
  dying doesn't take down the whole system). The cost is real architectural complexity:
  the system now has to coordinate state across machines, which is where sharding,
  replication, and consistency trade-offs (Part 2 of this primer) all originate from.

**The first-principles reason horizontal scaling requires statelessness (or careful state
management)**: if a machine holds state in local memory (a user's session, an in-progress
computation) and a load balancer can route the *next* request from that same user to a
*different* machine, that state is invisible to the new machine. Horizontal scaling only
works cleanly when either (a) any machine can serve any request identically (stateless), or
(b) state is externalized to a shared store (a database, a distributed cache) all machines
can reach. This single fact is *why* "make the application servers stateless, push state
into Redis/a database" is such a recurring pattern across every tutorial in this repo — it's
not a style preference, it's what makes horizontal scaling possible at all.

## Concurrency vs. Parallelism

Another pair that sounds interchangeable and isn't:

- **Concurrency** is about *structure* — a system dealing with multiple things at once,
  making progress on several tasks by interleaving them, without necessarily executing any
  two at the exact same instant. A single CPU core running an event loop that juggles
  thousands of open connections (each one making a little progress, in turn) is concurrent.
- **Parallelism** is about *execution* — multiple things genuinely happening at the exact
  same instant, which requires multiple actual execution units (multiple CPU cores,
  multiple machines).

**A single-core async I/O server is concurrent but not parallel** — it never executes two
things simultaneously, but it structures work so that waiting on one slow I/O operation
(a database call, a network request) doesn't block progress on others. This is precisely
why a Node.js-style single-threaded event loop can still serve thousands of concurrent
connections efficiently: most of what a web server does is *wait* on I/O, not compute, and
concurrency (interleaving the waiting) captures nearly all the benefit without needing true
parallelism at all.

## Back-of-the-Envelope Capacity Estimation

A recurring first move in any real system design conversation: converting a vague
requirement ("millions of users") into concrete numbers that actually drive design
decisions (how many servers, how much storage, what database).

**The numbers worth memorizing** (approximate, but close enough for order-of-magnitude
reasoning):

| Quantity | Approx. value |
|---|---|
| Seconds in a day | ~86,400 (≈ 100,000 for quick mental math) |
| 1 KB | ~10³ bytes |
| 1 MB | ~10⁶ bytes |
| 1 GB | ~10⁹ bytes |
| 1 TB | ~10¹² bytes |

**A worked example**: "design a system for 10 million daily active users, each posting on
average 2 messages/day, each message averaging 200 bytes."

1. **Requests/day** → `10M users × 2 messages = 20M writes/day`.
2. **Writes/sec (average)** → `20M / 100,000 ≈ 200 writes/sec` (using the ~100K-seconds
   approximation for a day). This is the *average* — always state explicitly that real
   traffic isn't uniform across the day, and multiply by a peak factor (commonly 2-10x
   average, depending on how spiky the domain is) to get a *provisioning* number: "roughly
   200 writes/sec average, but I'd provision for something like 1,000-2,000/sec to survive
   a realistic peak, and confirm that factor with real traffic data rather than guessing
   once this ships."
3. **Storage/day** → `20M messages × 200 bytes ≈ 4 GB/day` of raw message data.
4. **Storage/year** → `4 GB × 365 ≈ 1.5 TB/year` — a number that immediately tells you
   whether this fits comfortably on a single database instance (it does, easily) or needs
   sharding from day one (it doesn't, at this scale).

**Why this habit matters more than the exact numbers**: the *precision* of the estimate is
almost never the point — being off by 2x rarely changes the architecture. What matters is
demonstrating that a design decision (do we need sharding? a CDN? a cache tier?) is
**grounded in an actual number**, not intuition or reflexive over-engineering. State your
assumptions explicitly as you go ("assuming average message size of 200 bytes...") — that
transparency is what lets an interviewer correct a bad assumption cheaply, early, instead
of 15 minutes into a design built on it.

## Quick Self-Check

Before moving to [Part 2: Data & Consistency](02_data_and_consistency.md), you should be
able to answer these without looking back:

- Why can a system have great average latency and still be failing a meaningful fraction
  of real users?
- Why does a request that fans out to 100 backend calls behave worse, tail-latency-wise,
  than any single one of those calls in isolation?
- Why does going from 99.9% to 99.99% availability represent a much bigger engineering
  investment than the numbers "99.9" and "99.99" make it look like?
- Why does horizontal scaling specifically push a system toward statelessness?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Distribution-not-average framing (the default whenever latency comes up at all):** "I
  wouldn't quote an average — I'd ask which percentile the requirement is actually about,
  because average latency can look perfectly healthy while a real slice of users are
  having a bad time. p99 is usually the number that actually matters."
- **Compounding-tail framing (good for demonstrating you understand *why*, not just the
  definition):** "In a fan-out architecture, tail latency compounds — if a request touches
  100 backend calls each slow 1% of the time, the overall request is slow more like 63% of
  the time. That's the reason 'just optimize the average' stops being good advice once a
  system has real fan-out."
- **Order-of-magnitude framing (good for availability/nines discussions):** "I'd treat each
  additional nine as roughly an order-of-magnitude harder engineering problem, not a small
  increment — going from three nines to four nines shrinks your entire annual downtime
  budget from almost nine hours to under one."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **tail latency** (n. phrase) — the latency experienced by the small slowest fraction of
  requests (e.g. the 1% that fall *beyond* the p99 threshold, or the 0.1% beyond p99.9),
  as opposed to the typical (median) experience. Note p99 itself is the *cutoff value* —
  "99% of requests were this fast or faster" — not the slow group; the tail is whatever's
  past that cutoff.
- **composite availability** (n. phrase) — the overall availability of a request path that
  depends on multiple independent services, found by multiplying their individual
  availabilities — always lower than any single component.
- **provisioning factor** (n. phrase) — the multiplier applied to average load to size
  capacity for realistic peaks, since average load is never what you need to survive.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…hides that someone waited five full seconds"** — a vivid, concrete way to argue
  against reporting only an average, by naming the specific harm it conceals.
- **"…is not a small improvement, it's an order of magnitude"** — useful whenever an
  interviewer's phrasing makes a jump (three nines to four nines) sound incremental when
  it isn't.
- **grounded in an actual number** — a fluent way to defend a design decision as
  quantitatively justified rather than reflexive over-engineering. *"I'd want this
  provisioning number grounded in an actual number, not intuition."*

---

**Previous:** [Overview](../README.md)  |  **Next:** [Part 2: Data & Consistency](02_data_and_consistency.md)

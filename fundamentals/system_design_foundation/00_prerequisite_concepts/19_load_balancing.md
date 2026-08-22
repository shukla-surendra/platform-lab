# Prerequisite Concepts, Part 19: Load Balancing — Choosing Which Server Answers, and Knowing When One Can't

[Part 3](03_communication_and_resilience.md#caching-and-load-balancing-briefly) named load
balancing in one paragraph and deferred it; the [Fundamentals
tutorial](../01_ml_system_design/00_interview_framework_fundamentals.md#load-balancing) it
pointed to lists the algorithms and the L4/L7 split in about ten lines. [Part 9's "L4 before
L7" section](09_dns_bgp_and_the_edge.md#beyond-caching-the-security-and-routing-layer-at-the-edge)
went one level deeper — *why* the two layers get ordered the way they do — but still assumed
the algorithms themselves as background. This part is where all of that finally gets
unpacked on its own: not just which algorithm picks a server, but how a load balancer
actually *knows* a server is still healthy enough to pick, and what breaks when that
knowledge is stale.

## In Plain English

Picture a restaurant host standing at the door with several servers working the floor. A
naive host seats parties in strict rotation — table to server A, next table to server B,
next to C, back to A — regardless of whether server A is still juggling a party of twelve
from ten minutes ago. A better host watches who's actually free right now and seats the next
party with whoever has the fewest open tickets. The best host also notices when a server
calls in sick and stops sending them parties at all — instead of a customer standing at an
empty station, indefinitely waiting for a server who already went home. A load balancer is
that host, making the same three decisions — who's up next, who's actually free, who's gone
missing — thousands of times a second.

## The Problem, Precisely

Multiple backend servers exist specifically so no single one is overwhelmed — but something
still has to decide, per incoming request, *which* one handles it, and that decision has to
keep being correct even as servers get slower, crash outright, or get added and removed
during a deploy. Get the algorithm wrong and load piles unevenly onto a subset of servers
regardless of how many you've provisioned; get the health detection wrong and the balancer
keeps confidently routing traffic to a server that's already dead.

## Algorithms: How the Routing Decision Actually Gets Made

**Round robin** — cycle through the server list in fixed order, one request each. Simple and
requires no state about server load, but it's blind to reality: a slow or already-busy
server gets the exact same share of new traffic as an idle one. **Weighted round robin**
fixes the one part of this that's knowable in advance — servers with more capacity get
proportionally more turns in the rotation — but it's still blind to *current* load, only
*provisioned* capacity.

**Least connections** — route each new request to whichever server currently has the fewest
active in-flight requests. This actually reacts to real-time load rather than a fixed
schedule, which is why it tends to beat round robin under uneven request costs (some
requests are cheap, some are expensive, and round robin has no way to know that). **Weighted
least connections** combines both signals — current load *and* known capacity — which is
usually the more production-accurate version of this idea.

**Power of two random choices** — pick two servers at random and route to whichever of the
two has fewer active connections, rather than tracking and comparing *every* server on every
request. This sounds like it should perform worse than true least-connections, but in
practice gets close to the same load distribution at a fraction of the coordination cost —
worth naming specifically because it's the algorithm several high-scale production systems
(including gRPC's own client-side load balancing) actually reach for once the server fleet
gets large enough that comparing all of it on every request becomes its own bottleneck.

**Consistent hashing** — route the same key to the same server, reusing the exact ring
mechanism [Part 12 already built in
full](12_sharding_and_the_vertical_wall.md#choosing-a-shard-key-attempt-3-consistent-hashing-the-ring)
and [Part 01's foundations doc named again for this
context](../../system_design_practice/01_distributed_systems_foundations/tutorial.md#consistent-hashing-advanced-sharding) — not
re-derived here, only reused. What's specific to load balancing is *why* you'd trade load
distribution for this: **session affinity** (the same user keeps hitting the same server
that holds their in-memory session state) and **cache locality** (the same cache key keeps
hitting the same server, so its local cache stays warm instead of every server holding a
partial, colder copy of the same data). The cost is the same one Part 12 already named for
sharding — an uneven key distribution can still produce a hot server — it's the identical
mechanism, just chosen for a different reason at this layer.

## Health Checks: How a Load Balancer Knows a Server Is Actually Healthy

Every algorithm above assumes the balancer already knows which servers are alive — that
knowledge isn't free, and it's genuinely easy to get stale.

**Active health checks** — the balancer proactively sends a probe (an HTTP `GET /health`, a
TCP connection attempt) to each server on a fixed interval, independent of real traffic.
Fast, controlled detection — a server can be pulled out of rotation before a single real
user request ever reaches it — at the cost of constant background probe traffic that scales
with fleet size and check frequency.

**Passive health checks** — instead of a separate probe, the balancer watches real request
outcomes (timeouts, connection resets, error responses) and ejects a server that's failing
enough of them. No extra probe traffic, but detection is inherently reactive: some number of
real user requests have to actually fail against a bad server before the balancer notices.
Envoy calls this **outlier detection** — the same idea, framed as statistically flagging a
server whose error rate diverges from its peers rather than checking it against a fixed
threshold alone.

**Flapping, and why detection alone isn't the whole mechanism**: a server hovering right at
the failure threshold can get ejected, recover, get re-admitted, fail again, and repeat —
churning in and out of rotation in a way that's worse than either staying in or staying out.
Production balancers guard against this with **hysteresis** (different thresholds for
ejecting vs. re-admitting, so a server has to clearly recover, not just barely cross back
over the same line) and **slow start** (a server that just rejoined rotation, whether newly
deployed or just recovered, gets ramped up to full traffic share gradually instead of
immediately — the same instinct behind a canary deploy, applied to routing weight instead of
version rollout).

## L4 vs. L7, the Mechanism Itself

[Part 9 already covers *why* these two layers get ordered in front of each
other](09_dns_bgp_and_the_edge.md#beyond-caching-the-security-and-routing-layer-at-the-edge)
— worth being precise here about what each one actually *is*, mechanically. An **L4**
(transport-layer) balancer operates purely on IP address and port; it never terminates or
parses the HTTP request inside the connection, which is exactly what makes it cheap enough
to sit at the front absorbing raw connection volume (AWS NLB, IPVS/LVS — the technology
behind many software load balancers' kernel-level packet forwarding). An **L7**
(application-layer) balancer terminates the TCP connection and actually parses the HTTP
request, which is what makes content-based routing possible at all (route `/v2/predict`
differently from `/v1/predict`, route by header, inspect a cookie for **sticky sessions** —
L7's own alternative to consistent hashing for keeping one user's requests on one server).
L7's parsing is also what makes **connection draining** possible during a deploy: stop
routing *new* requests to a server being taken out of rotation, while letting its
*already-in-flight* requests finish normally instead of killing them mid-response — an L4
balancer, blind to request boundaries, can't make this distinction at all.

## DNS-Level and Global Load Balancing

Everything above operates *within* one data center or region, choosing among servers that
are all roughly equidistant from the request. A genuinely global service adds a layer above
that: **DNS-based** or **anycast-based global load balancing (GSLB)**, routing an entire
request to the nearest *region* before any of the algorithms above ever run, reusing exactly
the [anycast mechanism Part 9 already
covered](09_dns_bgp_and_the_edge.md#anycast-one-ip-address-many-physical-locations) —
geo-routing by physical proximity, or latency-based routing by measured round-trip time to
each candidate region, rather than by server load at all. This is a different axis entirely
from everything above it, not a fancier version of the same algorithm: region selection
happens once, far upstream, and only after a request lands in a region do least-connections,
consistent hashing, or any of the other algorithms in this part ever get a chance to run.

## Real Tools, Modern Defaults

**L4**: AWS Network Load Balancer (NLB), IPVS/LVS (the Linux kernel-level engine underneath
many software load balancers, including what backs Kubernetes' own `Service` load
balancing), HAProxy (capable of running as either layer). **L7**: NGINX, Envoy, AWS
Application Load Balancer (ALB), Kong, Traefik — the same Envoy [already named as the
service-mesh sidecar in Part
01](../../system_design_practice/01_distributed_systems_foundations/tutorial.md#service-mesh-cross-cutting-concerns-without-cross-cutting-code),
doing L7 load balancing as one of that sidecar's jobs rather than a separate box. **Global**:
Google Cloud Load Balancing (a genuinely global anycast L7 balancer, one IP address in front
of every region), AWS Global Accelerator, Cloudflare Load Balancing. **Client-side load
balancing**: instead of a dedicated balancer box, the calling client itself picks a target
directly from a known server list — gRPC's built-in client-side balancing (using
power-of-two-choices among other strategies) and a service mesh's sidecar-per-caller model
both remove the balancer as a separate hop entirely, trading a simpler network path for
needing that logic embedded in every client instead of one central place.

**Where rate limiting fits into this stack, precisely:** an L4 balancer's blindness to the
HTTP request (no client ID, no API key visible) is exactly why per-user rate limiting has
to live at the L7 hop or later, and why it runs *before* that hop's own routing decision —
[the rate limiter case study's dedicated deep-dive](../../system_design_practice/07_design_rate_limiter_at_scale/tutorial.md#deep-dive-where-the-rate-limiter-sits-relative-to-the-load-balancer)
works through the ordering and the correctness argument for it in full.

## Designing and Operating From First Principles

1. Have I chosen an algorithm based on this workload's actual request-cost variance — is
   round robin genuinely fine here, or does uneven request cost mean least-connections (or
   power-of-two-choices, at scale) actually matters?
2. If I'm using consistent hashing for session affinity or cache locality, have I actually
   accepted the hot-key risk that comes with it, the same way Part 12 already named for
   sharding — or did I reach for it without weighing that cost?
3. Do I have active health checks, passive health checks, or both — and have I checked that
   my ejection and re-admission thresholds are different enough to avoid flapping a server
   that's hovering near the line?
4. During a deploy, does traffic actually drain from an outgoing server before it's
   terminated, or am I dropping in-flight requests because the balancer in front of it is
   L4-only and can't see request boundaries?
5. If this service runs in more than one region, is region selection actually happening at
   the DNS/anycast layer before any server-level algorithm runs — or is a single region's
   load balancer quietly handling cross-region traffic it was never designed for?

## Key Takeaways

- **Round robin is blind to real load; least-connections and power-of-two-choices react to
  it** — the practical choice is driven by how uneven this workload's actual request cost is,
  not by which algorithm sounds more sophisticated.
- **Consistent hashing at the load-balancing layer is the same ring mechanism as sharding**,
  reached for here specifically for session affinity or cache locality, with the identical
  hot-key cost Part 12 already named.
- **Health checking is a separate mechanism from routing, and it's where staleness actually
  bites** — active checks detect fast at the cost of probe traffic, passive checks are free
  but reactive, and flapping is a real failure mode neither one alone prevents without
  hysteresis and slow start.
- **L4 is cheap and connection-blind; L7 is more expensive and content-aware** — that's what
  makes L7-only features (path/header routing, sticky sessions, connection draining) possible,
  and it's why production systems layer both rather than picking one.
- **Global load balancing is a different axis, not a bigger version of the local one** —
  region selection via DNS/anycast happens once, upstream of every algorithm in this part.

## Quick Self-Check

- Explain precisely why power-of-two-choices can approach true least-connections' load
  distribution without comparing every server on every request.
- Walk through what specifically goes wrong if a balancer only uses active health checks
  with identical eject and re-admit thresholds — what failure pattern does that produce?
- Why can't an L4 load balancer perform connection draining during a deploy, but an L7
  balancer can?
- Explain why consistent hashing for session affinity carries the same hot-key risk Part 12
  named for sharding — what has to be true about the key distribution for that risk to show
  up here specifically?
- Why is global (DNS/anycast-based) load balancing a genuinely separate layer from
  local server-selection algorithms, rather than just a larger-scale version of the same
  problem?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Workload-first framing (the default for 'which load balancing algorithm would you
  use'):** "I'd pick based on how uneven this workload's actual request cost is — round
  robin if requests are roughly uniform, least-connections or power-of-two-choices if
  they're not — rather than defaulting to whichever algorithm is best known."
- **Health-is-separate framing (good for a 'what if a server dies' follow-up):** "Routing and
  health detection are two different mechanisms, not one — I'd want to know whether we're
  using active checks, passive checks, or both, and specifically whether the eject and
  re-admit thresholds differ, since a server flapping in and out of rotation is often a worse
  outcome than one that stays down."
- **Layered framing (good for demonstrating production experience with L4/L7):** "I wouldn't
  frame this as picking L4 or L7 — production systems layer both, L4 absorbing cheap,
  connection-blind volume in front, L7 doing the expensive content-aware routing only on
  traffic that's already survived that cheaper filter."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **round robin / weighted round robin** (n. phrases) — fixed-rotation routing, with or
  without accounting for known differences in server capacity.
- **least connections / power of two random choices** (n. phrases) — routing based on
  real-time active-connection count, either compared across every server or across a
  randomly sampled pair for lower coordination cost at scale.
- **active health check / passive health check** (n. phrases) — proactive probing on a fixed
  interval versus inferring health from real traffic outcomes; Envoy's passive version is
  called **outlier detection**.
- **flapping** (n.) — a server repeatedly ejected and re-admitted from rotation because its
  health sits right at the detection threshold; fixed with **hysteresis** and **slow start**.
- **connection draining** (n. phrase) — letting a server's in-flight requests finish normally
  while routing no new requests to it, an L7-only capability during a deploy.
- **GSLB (global server load balancing)** (n., initialism) — DNS- or anycast-based routing to
  the nearest region, a layer above and separate from any server-selection algorithm.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…blind to load, not blind to fairness"** — a precise way to describe round robin's exact
  limitation without implying it's simply a worse algorithm in every situation.
- **"…the same ring, borrowed for a different reason"** — a fluent way to connect
  load-balancing consistent hashing back to Part 12's sharding mechanism without re-deriving
  it.
- **"…detection and routing are two different jobs"** — a reusable line for redirecting a
  load-balancing discussion toward health checking specifically, when an answer stops at
  algorithm choice alone.

---

**Previous:** [Part 18: Message Queues & Event-Driven Semantics](18_message_queues_and_event_driven_semantics.md)  |  **Next:** [Part 20: Microservices Architecture Patterns](20_microservices_architecture_patterns.md)

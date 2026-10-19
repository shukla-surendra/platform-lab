# Prerequisite Concepts, Part 9: The Anatomy of a Request (DNS, BGP, and the Edge)

[Part 8](08_cost_of_communication.md) modeled a remote call as a stack of taxes — DNS,
TCP, TLS, kernel, serialization — but treated "DNS resolution" as a single line in a table
and started the physics discussion only once a packet already knew where it was going.
This part goes one layer earlier: **before any of Part 8's taxes can be paid, the client
has to answer two questions — what IP address am I even talking to, and what physical path
does a packet take to get there — and both answers are resolved by systems most engineers
never look at until they break.** [Part 3](03_communication_and_resilience.md) already
gave you the one-sentence version of DNS; this part unpacks the hierarchy underneath it,
introduces BGP (the protocol that makes "the internet" a coherent thing at all instead of
a pile of disconnected networks), and shows how CDNs use both together to make Part 6's
"shorten the distance" argument concrete at global scale.

## Recap: What Part 3 Already Owns, and What This Part Adds

Part 3's version: "the browser asks a DNS resolver, which finds the IP." True, and enough
for most interviews. What it deliberately left out — and what a staff-level "walk me
through what happens when you hit enter" answer is actually expected to go on to say:

| Question | Part 3's answer | This part's answer |
|---|---|---|
| Who does the resolver actually ask? | "A hierarchy of nameservers" | The exact hierarchy: root → TLD → authoritative, and why each layer exists |
| Why does a stale DNS entry linger after a fix? | Not covered | TTL is a *hint*, not a guarantee — caching resolvers can ignore it |
| How does a packet find the server once you have an IP? | Not covered | BGP — the routing protocol that stitches independently-owned networks into one internet |
| How does a CDN answer requests from wherever you are? | Not covered | Anycast + GeoDNS, and edge PoPs that terminate TLS close to the user |
| What does a request actually look like on the wire, before any of that? | Not covered | A byte tax paid per packet — MTU limits and header overhead |
| What happens to a request between the edge and your application code? | Not covered | WAF inspection, L4/L7 load-balancer ordering, and the API gateway |

## Before Any of This: Turning a String Into a Packet

[Part 8's kernel tax
section](08_cost_of_communication.md#the-kernel-tax-every-byte-crosses-a-privilege-boundary)
already covers *why* an application has to hand its bytes to the kernel via a syscall — a
userspace process has no permission to touch a NIC directly. What that section doesn't
cover is what the kernel actually does with those bytes before anything leaves the
machine — the first place a byte tax gets paid, before DNS, BGP, or TLS ever enter the
picture.

Every physical link enforces a **Maximum Transmission Unit (MTU)** — the largest single
frame it will carry. For the overwhelming majority of the internet, that ceiling is
**1,500 bytes**, a number that traces back to early Ethernet hardware limits and has
simply stuck. A payload larger than the MTU doesn't get shrunk — it gets split into
multiple packets before the first byte ever reaches the network, each independently routed
and reassembled only at the destination.

Each of those packets, in turn, isn't just payload — it carries a header at every layer it
passes through, and none of them are optional:

| Header | Approx. size | What it identifies |
|---|---|---|
| Ethernet frame | ~14 bytes | The next physical hop's hardware (MAC) address — typically your own router, not the destination server |
| IP | ~20 bytes | The source and destination IP address |
| TCP | ~20 bytes | Sequence number, flags, and which connection this packet belongs to |

Illustrative and approximate (exact sizes vary with options like IPv6 or TCP extensions) —
roughly **~54 bytes** spent on addressing and bookkeeping before a single byte of the
actual request has been carried. This is a small, *fixed* tax per packet, which is exactly
why it matters more, not less, as individual messages get smaller: 1,000 separate 10-byte
messages each pay that ~54-byte header cost — more overhead than payload — while [Part 8's
batching
argument](08_cost_of_communication.md#paying-less-tax-data-locality-batching-coarse-apis-and-caching)
amortizes that same fixed cost across one larger packet instead. The MTU and header tax
are the mechanical reason "send fewer, larger messages" is a real performance rule, not
just a rule of thumb.

### Inside the Headers: What Each Layer Actually Encodes

The three headers aren't opaque overhead — each one is answering a specific question the
next hop needs answered, and they nest inside one another rather than sitting side by side.
A REST request's JSON body ends up wrapped like this before it ever leaves the machine:

```
┌────────────────────────────────────────────────────────────────┐
│ Ethernet Frame  (dest MAC, src MAC, EtherType)                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ IP Packet  (dest IP, src IP, TTL, protocol)               │   │
│ │ ┌──────────────────────────────────────────────────────┐ │   │
│ │ │ TCP Segment  (dest port, src port, seq/ack, flags)    │ │   │
│ │ │ ┌────────────────────────────────────────────────┐   │ │   │
│ │ │ │ HTTP Payload — the actual request               │   │ │   │
│ │ │ │ POST /api/orders HTTP/1.1                        │   │ │   │
│ │ │ │ Host: api.example.com                            │   │ │   │
│ │ │ │ Content-Type: application/json                   │   │ │   │
│ │ │ │                                                   │   │ │   │
│ │ │ │ {"item":"widget","qty":3}                         │   │ │   │
│ │ │ └────────────────────────────────────────────────┘   │ │   │
│ │ └──────────────────────────────────────────────────────┘ │   │
│ └──────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

Each layer only ever reads its own header and hands the rest off unopened — a router
forwarding this packet never looks past the IP header; it has no idea an HTTP request, let
alone JSON, is inside. That's what "layers" means in practice: strict information hiding,
not just a diagram convention.

**Ethernet frame (~14-byte header)** — answers "which physical device is next":

| Field | Size | Purpose |
|---|---|---|
| Destination MAC | 6 bytes | The *next hop's* hardware address — your router, not the destination server, since this header gets rewritten at every hop |
| Source MAC | 6 bytes | The sending NIC's hardware address |
| EtherType | 2 bytes | Which protocol follows (`0x0800` = IPv4) |

**IP header (~20 bytes, IPv4, no options)** — answers "which host, and how do I survive fragmentation":

| Field | Size | Purpose |
|---|---|---|
| Total Length | 2 bytes | Full packet size, header included |
| Identification | 2 bytes | Groups fragments of one oversized packet back together |
| Flags / Fragment Offset | 2 bytes | Whether this piece was split, and where it belongs in the reassembly |
| TTL | 1 byte | A hop counter, decremented at every router and dropped at 0 — this is literally what `traceroute` abuses to map a path. **Same name, unrelated mechanism** to the DNS TTL earlier in this doc — one caps hops, the other caps cache lifetime; don't conflate them in an interview. |
| Protocol | 1 byte | What's nested inside (`6` = TCP, `17` = UDP) |
| Source / Destination IP | 4 bytes each | The two hosts's addresses — unlike the MAC pair, these stay unchanged for the packet's entire journey |

**TCP header (~20 bytes, no options)** — answers "which process, and is this reliable and in order":

| Field | Size | Purpose |
|---|---|---|
| Source / Destination Port | 2 bytes each | Which process on each host — destination `443` is how HTTPS traffic is even identified as HTTPS |
| Sequence Number | 4 bytes | This segment's position in the byte stream — how the receiver reassembles packets that arrive out of order |
| Acknowledgment Number | 4 bytes | The next byte the sender is expecting back — the mechanism behind retransmission when a packet is lost |
| Flags (`SYN`, `ACK`, `FIN`, …) | bits | Connection lifecycle state — `SYN` opens [Part 3](03_communication_and_resilience.md)'s handshake, `FIN` closes it |
| Window Size | 2 bytes | How many more bytes the receiver can buffer *right now* — this is what actually throttles [Part 8's sliding-window](08_cost_of_communication.md) "several packets in flight" behavior, not a fixed count |

**Why this matters beyond trivia:** the tuple `{source IP, source port, destination IP,
destination port, protocol}` is how the OS, NAT devices, and load balancers all identify
"these packets belong to the same connection" — it's the literal mechanism behind [Part
8's connection-pooling
discussion](08_cost_of_communication.md#concurrency-and-locality-how-many-handshakes-actually-happen):
a "connection" isn't a thing that exists on the wire, it's just every packet sharing this
same 5-tuple, tracked in a table on both ends.

## DNS, Fully Unpacked: The Hierarchy Behind One Bullet Point

DNS is a **distributed, hierarchical database** — no single server holds the whole
internet's name-to-IP mapping, because a single server that every lookup on Earth hit would
be both a latency disaster (everyone round-tripping to one place) and a single point of
failure, exactly the failure mode [Part 3's resilience
vocabulary](03_communication_and_resilience.md#resilience-vocabulary) warns against
generically. The hierarchy exists specifically to distribute both the *load* and the
*authority* for answering "what's the IP for this name":

```mermaid
flowchart TD
    A[Client / Stub Resolver] --> B[Recursive Resolver]
    B -->|"1. who handles .com?"| C[Root Server]
    C -->|referral| B
    B -->|"2. who is authoritative for example.com?"| D["TLD Server (.com)"]
    D -->|referral| B
    B -->|"3. what's the A record for www.example.com?"| E[Authoritative Nameserver]
    E -->|"IP + TTL"| B
    B -->|cached answer| A
```

1. **Recursive resolver** — the server your client actually talks to (your ISP's, or a
   public one like Google's `8.8.8.8` or Cloudflare's `1.1.1.1`). It does the walking on
   the client's behalf and **caches the result**, so most real-world lookups never touch
   steps 2-4 at all — this cache is why DNS "usually" feels instant.
2. **Root servers** — don't know the IP for `example.com`; they know which TLD server
   handles `.com` and hand back a referral, nothing more. There are 13 logical root server
   *addresses*, but each is served by hundreds of physical machines worldwide via
   **anycast** (covered below) — the same "one IP, many physical locations" trick a CDN
   uses, deployed here specifically so a foundational, globally-depended-on service isn't
   a single physical point of failure or a single distant round trip for every resolver on
   Earth.
3. **TLD servers** — `.com`, `.org`, `.io`, each typically run by a registry operator
   (e.g., Verisign for `.com`). They don't know `example.com`'s IP either; they know which
   **authoritative nameserver** is responsible for that specific domain and refer the
   resolver there.
4. **Authoritative nameserver** — the domain owner's own DNS (self-hosted, or a managed
   provider like Route 53 or Cloudflare DNS). This is the only layer that actually holds
   the real answer — the A/AAAA record — and it ships a **TTL** alongside it.

**Why the referral chain matters beyond trivia**: each of those four hops is, mechanically,
exactly the "remote call" [Part 8](08_cost_of_communication.md) describes — DNS mostly
rides on **UDP port 53** specifically because [Part 3's TCP-vs-UDP
trade-off](03_communication_and_resilience.md#tcp-vs-udp) favors it here: a lookup is a
single small request/response, and retrying a lost UDP query is cheaper than paying a full
TCP handshake for every name lookup on the internet (DNS falls back to TCP only for
responses too large for one UDP packet, or zone transfers).

### TTL: A Hint, Not a Promise — and Why That Breaks Failover

The authoritative nameserver's answer ships with a **Time To Live (TTL)** — "cache this for
N seconds." The TTL is the domain owner's *request* for how long to be trusted, not an
enforceable contract: a corporate proxy, an ISP resolver, or a misconfigured client can
(and in practice sometimes does) cache an answer well past its stated TTL. This single fact
is the direct mechanical reason behind a failure mode that shows up repeatedly elsewhere in
this repo — a **DNS-based failover** that a runbook promises will complete in "TTL seconds"
can instead take much longer, because some fraction of clients are holding a cached IP the
authoritative server has no way to actively revoke. This is precisely the gap the
[DR-failover-took-8x-longer
scenario](../ml_system_design/12_tricky_scenarios_12_dr_failover_slow.md#likely-root-causes-ranked) points
at when it flags "DNS/traffic-manager propagation delay," and exactly why
[Part 10's global traffic manager](../ml_system_design/10_cost_security_multiregion.md) is
described as **health-check-based failover**, not TTL-based — a health-check-driven system
can redirect traffic at the load-balancer layer without waiting on every cache on Earth to
expire naturally.

**The practical trade-off this creates for anyone operating DNS**: a short TTL (seconds to
low minutes) gives faster failover and faster propagation of legitimate changes, at the
cost of every resolver on Earth re-querying your authoritative server far more often; a
long TTL (hours) is cheap on query volume but means a bad record, once cached, lingers.
Neither number is "correct" in the abstract — it's a direct trade of **operational agility
against query load**, tuned per record based on how likely that specific record is to need
to change in an emergency.

### The Record Types Worth Knowing by Name

| Record | Answers | Example use |
|---|---|---|
| **A** | Name → IPv4 address | `example.com → 93.184.216.34` |
| **AAAA** | Name → IPv6 address | The IPv6 equivalent of an A record |
| **CNAME** | Name → another name (alias) | `www.example.com → example.com` |
| **NS** | Which nameservers are authoritative for this zone | The referral mechanism itself |
| **MX** | Which mail servers accept email for this domain | Routing inbound email, not web traffic |
| **TXT** | Arbitrary text | Domain-ownership verification, SPF/DKIM anti-spam records |

## BGP: The Protocol That Makes "The Internet" One Thing

Having an IP address answers *what* to talk to; it says nothing about *how a packet
physically gets there*. The internet is not one network — it's tens of thousands of
independently-owned networks (an ISP, a cloud provider, a university, a corporation), each
called an **Autonomous System (AS)**, identified by a globally unique number (an **ASN** —
e.g., a large cloud provider might operate as AS15169). **Border Gateway Protocol (BGP)**
is the protocol ASes use to tell each other what they can reach, and it is, without
exaggeration, the reason a request from a phone in Mumbai can reach a server in Virginia at
all — nothing about IP addressing alone guarantees a path exists between any two of them.

```mermaid
flowchart LR
    A[AS 1: Your ISP] -->|BGP advertisement| B[AS 2: Transit Provider]
    B -->|BGP advertisement| C[AS 3: Cloud Provider]
    C -->|BGP advertisement| D[AS 4: Origin Server's Network]
```

**The mechanism**: each AS **advertises** the IP prefixes it owns (or can reach) to its
directly-connected neighbor ASes, tagged with the **AS-path** — the ordered list of ASes a
packet would cross to get there. A neighbor receiving that advertisement can re-advertise
it onward to *its* neighbors, appending itself to the path — reachability information
propagates hop-by-hop across the entire AS graph this way, with no single party holding a
complete map of the whole internet at once. This makes BGP a **path-vector protocol**,
distinct from the shortest-path/link-state protocols (like OSPF) used for routing *inside*
a single AS — BGP's job is coordination *between* independently-administered networks, a
fundamentally different, much less trusting problem than routing within one.

**Why "shortest path" is the wrong mental model**: when a router has multiple advertised
routes to the same prefix, it picks one using a **policy**, not physics — AS-path length is
one input, but business relationships (a paid transit agreement vs. a settlement-free
peering arrangement) routinely override pure hop-count. A packet's route is decided by
**economics and contracts layered on top of the physical network**, not by "the shortest
cable" — the [physical, speed-of-light floor Part 6
derives](06_mechanical_sympathy_and_physics_of_latency.md#distance-of-data-one-physical-idea-two-different-scales)
still bounds every individual link, but which sequence of links your packet actually
traverses is a *human, contractual* decision layered on top of that physics, and can
absolutely be longer than the shortest physically possible path.

### BGP Hijacks and Leaks: When the Trust Model Breaks

BGP was designed assuming every AS honestly advertises only prefixes it legitimately owns —
there's no built-in cryptographic proof of that claim in the base protocol. When an AS
advertises a prefix it doesn't actually own — by misconfiguration (a **route leak**) or
deliberately (a **hijack**) — its neighbors have historically had no automatic way to
reject it, and that bad advertisement can propagate globally in minutes, silently pulling
traffic destined for the real owner toward the misconfigured or malicious AS instead. This
isn't hypothetical: in one of the most-cited real-world cases, a national ISP tried to
block a video-sharing site *on its own internal network* by null-routing its IP block, then
leaked that same route to an upstream provider — the leak propagated through BGP across the
global internet, and traffic bound for the video site was mis-routed worldwide for roughly
two hours, until the leak was traced and withdrawn. **The modern mitigation is RPKI
(Resource Public Key Infrastructure)** — a cryptographic system letting a prefix owner sign
a **Route Origin Authorization** stating which ASes are legitimately allowed to originate
that prefix, so a receiving router can validate an advertisement instead of trusting it
blindly.

**Why convergence time matters for everything else in this repo**: a BGP change doesn't
take effect everywhere simultaneously — it propagates hop-by-hop, and full internet-wide
convergence after a significant route change is measured in **tens of seconds to several
minutes**, not milliseconds. This is a second, independent reason (alongside DNS TTL
above) that DR/failover runbooks measured in "minutes" are describing a real, physical
floor of the routing system itself — not a conservative padding number someone made up —
directly relevant to any multi-region failover design, including the RTO discussion in
[Part 10](../ml_system_design/10_cost_security_multiregion.md).

## Anycast: One IP Address, Many Physical Locations

**The problem anycast solves**: a single physical server answering one IP address is both
a latency problem (every client on Earth pays the same physical distance to reach it,
however far that happens to be) and a resilience problem (that one server or datacenter is
a SPOF). **Anycast's answer**: announce the *same* IP address via BGP from many physically
separate locations simultaneously. Routers along the path don't know or care that the
prefix is multiply-announced — ordinary BGP path selection naturally routes each client's
packets to whichever announcing location is "closest" by the routing system's own metric
(AS-path length and policy, not literal geographic distance), and if one location
disappears, its BGP advertisement is simply withdrawn and traffic re-routes to the next
nearest one, with no explicit failover logic required at all.

This is exactly the mechanism root DNS servers use (the "13 root servers" are actually
hundreds of physical machines sharing those 13 IPs via anycast), and it's the same
mechanism most modern CDNs and DDoS-mitigation providers rely on: a large-scale volumetric
attack aimed at one anycast IP is naturally **absorbed and diluted across every location
simultaneously announcing it**, rather than concentrated on a single target.

**How this connects back to Part 6's core argument**: anycast is a *routing-layer* trick
for doing exactly what [Part 6](06_mechanical_sympathy_and_physics_of_latency.md) argues is
the only real lever on latency — **shortening the physical distance a signal has to
travel** — except the "shortening" happens automatically, at the BGP layer, instead of
being something an application explicitly chooses (like picking a nearby cache).

## The Edge: Where DNS, Anycast, and BGP Meet a CDN

A **CDN (Content Delivery Network)** is the productized combination of everything above,
built to answer one question: **how do I serve a request from the location physically
closest to whoever's asking, automatically, at global scale?**

```mermaid
flowchart TD
    U1[User: Tokyo] -->|anycast routes\nto nearest PoP| P1[Edge PoP: Tokyo]
    U2[User: London] -->|anycast routes\nto nearest PoP| P2[Edge PoP: London]
    P1 -->|cache miss| O[Origin Server]
    P2 -->|cache miss| O
```

- **PoPs (Points of Presence)** — physical facilities a CDN operates close to end users,
  often directly peered with local ISPs to minimize the number of AS-hops (and therefore
  BGP-negotiated distance) a request has to cross before hitting CDN infrastructure at all.
- **Getting the client to the *right* PoP** happens one of two ways: **anycast** (every
  PoP announces the same IP; BGP naturally routes each client to the topologically nearest
  one — Cloudflare's model) or **GeoDNS** (the authoritative nameserver itself returns a
  *different* IP depending on the resolver's apparent geographic/network location —
  functionally similar in outcome, decided at the DNS layer instead of the routing layer).
- **Cache hit vs. cache miss** — a hit is served entirely from the PoP, paying none of
  Part 8's cross-region taxes at all; a miss has to reach back to origin, which is exactly
  the [cache-population strategy the video-streaming case study's CDN
  deep-dive](../../system_design_practice/08_design_video_streaming/tutorial.md#deep-dive-cdn-architecture-and-cache-invalidation)
  covers — including **origin shield**, an intermediate layer that deduplicates concurrent
  misses across many edge nodes so a sudden spike in popularity doesn't send a thundering
  herd of identical requests at the origin simultaneously.
- **TLS termination at the edge** — the PoP, being physically close to the user, completes
  the [TLS handshake Part 3 and Part 8
  describe](03_communication_and_resilience.md#what-actually-happens-when-you-hit-enter)
  locally, instead of that handshake round-tripping all the way to a distant origin. This
  is a direct, separate application of "shorten the distance" specifically to *connection
  setup* — independent of whether the requested content is even cacheable, since even a
  cache-miss request still benefits from a nearby TLS handshake before the PoP forwards the
  (now-decrypted-once, re-encrypted) request onward to origin.
- **Edge compute** (Lambda@Edge, Cloudflare Workers, Fastly Compute) — the next step past
  caching *bytes* at the edge: running actual application logic at the PoP itself
  (authentication checks, A/B routing, request rewriting) so even *dynamic* logic pays the
  short, local round trip instead of a long one to origin.

### CDN vs. "The Edge": Not the Same Thing

The two terms get used interchangeably in casual conversation, but they name different
levels of the stack, and the distinction is worth stating precisely rather than
hand-waving:

| | **CDN** | **The edge** |
|---|---|---|
| What it is | A *product/service* — a network of PoPs specifically built to cache and deliver content | A general *architectural concept* — any infrastructure placed physically close to the user instead of centralized at one origin |
| Scope | Primarily caching static (and some dynamic) content | Broader — caching, but also TLS termination, WAF/security filtering, L4/L7 load balancing, and running arbitrary application logic |
| Relationship | A CDN **is one implementation of edge architecture** | "Edge" is the category; a CDN's PoPs are one specific instance of edge locations |

**Every CDN PoP is "at the edge," but not everything at the edge is a CDN.** The bullets
above already illustrate this: caching a static asset at a PoP is classic CDN behavior; a
PoP terminating TLS, running a WAF, or executing edge-compute logic (the bullet just above)
is edge infrastructure doing something a traditional "just serve cached bytes" CDN doesn't
do on its own. If someone says "we're using a CDN," they mean caching and delivery. If they
say "we're pushing logic to the edge," they mean running actual code physically near the
user — a move a CDN vendor's PoP network often makes *possible*, but that isn't what "CDN"
means by itself.

### Worked Example: A Static Asset, With and Without a CDN

Reusing [Part 8's SF↔London worked
example](08_cost_of_communication.md#physics-sets-the-floor-a-worked-rpc-example) — a user
in London requesting a static asset from an origin server in San Francisco, versus the same
request served from a CDN PoP in London itself (illustrative and approximate figures; the
relationship, not the exact numbers, is the point):

| Path | Round trips paid at ~85 ms/RTT (SF↔London floor) | Approx. total |
|---|---|---|
| Direct to SF origin (TCP + TLS + HTTP) | 3 RTTs | ≈255 ms + origin processing |
| CDN PoP in London (cache hit) | TCP + TLS handshake to a PoP a few ms away | **~5-10 ms** total |

The CDN doesn't just avoid re-fetching from origin — it collapses the physical round trip
that Part 6 and Part 8 both identify as the dominant cost from ~85 ms-per-hop down to
effectively local-network numbers, for every single request that hits cache, without the
application changing a single line of code.

## Beyond Caching: The Security and Routing Layer at the Edge

A CDN PoP in a production architecture usually does more than cache bytes and terminate
TLS — it's typically also where a request passes through a security and routing layer
before it ever reaches application code, and each piece of that layer has its own
first-principles cost worth naming explicitly.

**Web Application Firewalls (WAF) and the cost of looking inside the packet.** Everything
covered so far in this doc — DNS, BGP, anycast — operates on the envelope: an IP address, a
prefix, a destination, nothing more. A WAF is different: it performs **deep packet
inspection (DPI)**, reading the actual request payload and comparing it against a library
of attack signatures (SQL-injection patterns, script-injection payloads) before deciding
whether to let the request through at all. That comparison is real, non-free CPU work, run
against every byte of every request — which means a WAF's cost scales with *both* its rule
count and the size of the payload being scanned, and a large request body checked against
thousands of rules can add meaningfully more latency than the database query the request
was actually for. Security here is a per-rule, per-byte tax, not a free switch, and the
practical implication is to push that filtering as far upstream — as close to the edge — as
possible, so only traffic that's already passed inspection reaches the more expensive
layers behind it.

**L4 before L7: an ordering decision, not just an either/or choice.** [Part 1's
Fundamentals](../ml_system_design/00_interview_framework_fundamentals.md#load-balancing) already introduces L4 (IP/port
only) and L7 (HTTP-content-aware) load balancing as two distinct algorithms; the design
point worth adding here is that production systems don't usually pick one — they **layer**
both, in a specific order. An L4 balancer is blind to a request's content, which is exactly
why it's cheap enough to sit at the very front, absorbing raw connection volume and a
DDoS's worth of garbage traffic. An L7 balancer has to buffer and parse a request before it
can route on path or header, making it comparatively expensive to run — so it belongs
*behind* the L4 tier, spending its real cost only on traffic that's already survived the
cheap filter in front of it. Reversing that order means paying L7's parsing cost on every
hostile packet, not just the legitimate remainder.

**The API gateway as a shield, not just a router.** The last stop before application code
typically handles authentication (validating a token), rate limiting, and protocol
translation (REST/JSON at the edge, gRPC internally) — and the reason this belongs in a
dedicated gateway (Envoy, Kong) rather than inside application code isn't only separation
of concerns. A malformed or oversized request, or an invalid token, can be rejected by a
gateway built specifically to parse and discard it cheaply; the same bad input handed
straight to an application process means that process has to allocate memory and run real
code paths just to arrive at the same rejection. Moving the check earlier isn't only
cleaner — it keeps the most expensive, most stateful part of the system (the application
itself) from ever spending a cycle on input that was never going to be accepted.

## Putting the Full Anatomy Together

Combining this doc with Parts 3, 6, and 8 into the complete sequence a "hit enter" answer
is actually expected to walk through at a staff bar:

```mermaid
flowchart TD
    A["1. Packet framing\n(MTU + header tax, this doc)"] --> B["2. DNS resolution\n(recursive -> root -> TLD -> authoritative,\npossibly anycast/GeoDNS to nearest PoP)"]
    B --> C["3. BGP-determined path\n(the physical AS-hops to that IP)"]
    C --> D["4. TCP + TLS handshake\n(Part 3), possibly terminated at a nearby edge"]
    D --> E["5. WAF, L4/L7 load balancing,\nAPI gateway (this doc)"]
    E --> F["6. Application request\n(Part 8's tax stack: serialization, kernel, queueing)"]
    F --> G["7. Response, possibly served\nentirely from edge cache"]
```

Steps 1-3 and 5 are this doc's contribution: how a request is physically packaged, how it
finds an IP and a path to it, and what it passes through immediately before your code runs.
Step 4 is [Part 3](03_communication_and_resilience.md)'s territory. Step 6 is [Part
8](08_cost_of_communication.md)'s stack of taxes. A senior answer to "what happens when you
hit enter" usually starts around step 4; a staff-level answer names steps 1-3 and 5
explicitly, because that's frequently where a real "why is this slow" or "why did failover
take so long" investigation actually needs to look.

## Designing and Operating From First Principles

1. Do I need to run my own authoritative DNS, or does a managed provider's anycast network
   already solve the "one IP, globally close, resilient" problem better than I could?
2. Is each record's TTL deliberately tuned — short for anything that might need emergency
   failover, longer for anything stable — rather than left at a default?
3. Does my failover mechanism actually depend on DNS TTL expiring, or does it use
   health-check-based traffic management that doesn't wait on every client's cache?
4. Am I using anycast or a CDN to shorten physical distance for global users, not relying
   on caching (Part 8) alone?
5. Do I terminate TLS at the edge for geographically distant clients, or is every one of
   them paying a full cross-region handshake?
6. Have I planned for a cache-miss stampede at origin (an origin shield), not just assumed
   the CDN "handles it"?
7. Do I monitor and protect my own advertised prefixes against BGP route leaks/hijacks
   (RPKI), given how little of that trust model is enforced by default?
8. Does my DR/multi-region runbook's RTO account for BGP convergence and DNS-propagation
   floors measured in minutes, or does it assume failover is instantaneous?
9. Am I sending many small messages that each pay a fixed per-packet header tax, when
   batching them would amortize that cost instead?
10. Is expensive, content-aware filtering (a WAF, L7 routing) sitting behind a cheap,
    blind filter (L4, a CDN's cache), or is it exposed directly to raw, unfiltered traffic?
11. Is authentication, rate limiting, and input validation happening at a gateway before
    application code runs, or is a hostile request only rejected after my application has
    already spent memory and CPU parsing it?
12. When I'm debugging with `tcpdump`/Wireshark or reasoning about a NAT/load-balancer
    issue, am I thinking in terms of the actual 5-tuple (source/destination IP and port,
    protocol) that identifies a connection, or vaguely about "the connection" as if it were
    one thing on the wire rather than a shared label on many independent packets?

## Key Takeaways

- DNS is a distributed hierarchy (recursive resolver → root → TLD → authoritative), not a
  single lookup — most of that hierarchy is hidden behind the recursive resolver's cache.
- TTL is a *request* for how long to be cached, not an enforceable guarantee — this is why
  DNS-based failover is frequently slower in practice than "TTL seconds" implies.
- BGP is what makes the internet one coherent network instead of thousands of disconnected
  ones — it routes on policy and business relationships, not on literal shortest physical
  path.
- BGP's trust model has no built-in proof of ownership by default, which is why route
  hijacks/leaks are a real, historically-documented failure mode, and why RPKI exists.
- Anycast turns "one IP, many physical locations" into automatic, latency-aware,
  DDoS-resilient routing, with no explicit failover logic required.
- A CDN is DNS/GeoDNS, anycast, and edge PoPs combined into one system whose entire purpose
  is minimizing the physical distance between a user and the response.
- BGP convergence and DNS propagation both have real floors measured in minutes — a
  multi-region failover plan that assumes faster than that is assuming away physics and
  protocol behavior, not being conservative.
- Every packet pays a small, fixed header tax (~54 bytes) regardless of payload size,
  which is why many small messages are disproportionately more expensive than one batched
  one.
- A WAF's cost scales with rule count and payload size — deep packet inspection is real,
  non-free CPU work, not a security feature you get for free.
- L4 and L7 load balancing are usually layered, not chosen between — cheap, blind L4
  filtering belongs in front of expensive, content-aware L7 routing.
- An API gateway is a cost-saving shield as much as a routing convenience — rejecting bad
  input before it reaches application code is cheaper than letting the application do it.
- Ethernet, IP, and TCP headers **nest** rather than sit side by side — each layer reads
  only its own header and hands the rest off unopened, which is what "layering" means
  mechanically, not just as a diagram convention.
- A "connection" has no independent existence on the wire — it's just every packet sharing
  the same 5-tuple (source/destination IP, source/destination port, protocol), tracked in a
  table on both ends and at any NAT/load balancer in between.
- IP TTL (a hop counter, decremented per router) and DNS TTL (a cache-expiry hint) share a
  name but are unrelated mechanisms — conflating them is an easy, avoidable mistake.
- "CDN" and "the edge" aren't synonyms — a CDN is a product built for caching/delivery; the
  edge is the broader architectural layer that also hosts TLS termination, WAFs, load
  balancers, and edge compute at the same physical PoPs.

## Quick Self-Check

- Why does a recursive resolver's cache mean most real-world DNS lookups never actually
  touch a root or TLD server — and what would happen to root servers' load if that cache
  didn't exist?
- Why is TTL described as a "hint" rather than a guarantee, and what specific operational
  failure does that distinction explain?
- Why is "shortest AS-path" not the same thing as "physically shortest route," and what
  determines the actual path a packet takes between two ASes?
- How does anycast let a service survive a DDoS attack or a datacenter failure *without*
  any explicit failover mechanism being triggered?
- Walk through what changes, mechanically, between a cache-hit and a cache-miss request at
  a CDN edge PoP — which of Part 8's "taxes" does the cache-hit path skip entirely, and
  which does the cache-miss path still have to pay?
- If a PoP is running a WAF check and executing edge-compute auth logic, is that PoP still
  accurately described as "a CDN," or is that the wrong word for what's happening there?
- Why does the ~54-byte header tax matter more for a stream of tiny messages than for one
  large one, and how does batching change that math?
- Why does putting an L7 load balancer in front of an L4 one (instead of behind it) make a
  DDoS attack more expensive to absorb, not less?
- Why is rejecting a malformed request at an API gateway cheaper than rejecting the same
  request inside application code?
- What does it mean, mechanically, for a router forwarding a packet to "never look past the
  IP header" — and why does that matter for what a router can and can't ever inspect or
  filter on?
- What five fields make up the tuple that identifies a single TCP connection, and why is
  that the right answer to "what actually is a connection" rather than something more
  physical?
- Why do IP TTL and DNS TTL sound like the same concept but actually protect against two
  completely different failure modes?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Layering framing (the default for "what happens when you hit enter," staff-level
  depth):** "I'd separate this into two questions most people collapse into one: first,
  what IP am I even talking to — that's DNS's hierarchy, root to TLD to authoritative —
  and second, what physical path gets a packet there — that's BGP, stitching independently
  owned networks into one internet. Only after both are answered does the TCP/TLS/HTTP
  stack from earlier in this primer even start, and even that stack is itself nested
  headers — Ethernet inside IP inside TCP inside your actual HTTP request — where every
  layer only ever reads its own header and hands the rest off unopened."
- **Failure-mode framing (good for incident/DR-style questions):** "DNS TTLs and BGP
  convergence both have real floors measured in minutes, not milliseconds — so when a
  failover runbook promises a five-minute RTO, I'd ask whether that number was tested
  against how DNS caching actually behaves in the wild, not just what the TTL field says."
- **Cost-ordering framing (good for CDN/global-service and edge-security design
  questions):** "A CDN PoP is the same anycast trick root DNS servers use — one IP,
  announced everywhere, so ordinary routing sends each user to the nearest copy — but once
  a PoP already sits on the path, it's also the cheapest place to order defense: blind L4
  filtering absorbs raw volume first, expensive L7 parsing only runs on what survives that,
  and a WAF's deep packet inspection — the priciest, most content-aware check of all — only
  ever touches what's already earned its way through both. Even before any of that, every
  packet on the wire already paid a fixed ~54-byte tax just to exist, which is the
  mechanical throughline connecting 'shorten the distance' all the way down to 'don't pay
  more per packet than you have to.'"

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **Autonomous System (AS)** (n. phrase) — an independently-administered network with its
  own globally unique ASN; the internet is a graph of these, not one network.
- **path-vector protocol** (n. phrase) — BGP's category: propagates reachability plus the
  AS-path taken, as opposed to a link-state protocol that computes shortest paths directly.
- **anycast** (n.) — announcing the same IP address from multiple physical locations so
  ordinary routing sends each client to the nearest one automatically.
- **RPKI (Resource Public Key Infrastructure)** (n. phrase) — a cryptographic system for
  proving which ASes are legitimately allowed to originate a given IP prefix, mitigating
  BGP hijacks/leaks.
- **origin shield** (n. phrase) — a CDN's intermediate caching layer that deduplicates
  concurrent cache-misses across edge nodes so a popularity spike doesn't stampede origin.
- **GeoDNS** (n.) — returning a different IP from the same DNS name based on the
  resolver's apparent location, an alternative to anycast for routing clients to a nearby
  PoP.
- **MTU (Maximum Transmission Unit)** (n. phrase) — the largest single frame a physical
  link will carry (~1,500 bytes for most of the internet); larger payloads are split into
  multiple packets before they ever leave the sending machine.
- **deep packet inspection (DPI)** (n. phrase) — reading and pattern-matching a request's
  actual payload (as a WAF does), as opposed to routing decisions (BGP, L4 load balancing)
  that only ever look at the envelope.
- **encapsulation** (n.) — wrapping one layer's whole unit (a TCP segment) as the payload
  of the layer below it (an IP packet), each header nested inside the last rather than
  concatenated beside it — the mechanical basis for "layers" in networking.
- **5-tuple** (n. phrase) — {source IP, source port, destination IP, destination port,
  protocol}; the set of fields an OS, NAT device, or load balancer actually uses to decide
  which packets belong to the same connection.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…a hint, not a guarantee"** — a precise, reusable way to describe TTL (or any
  best-effort cache-control signal) without overstating what it actually enforces.
- **"…routes on policy, not physics"** — a compact way to explain why BGP's chosen path
  isn't necessarily the physically shortest one available.
- **"…no explicit failover logic required"** — a fluent way to credit anycast's resilience
  property without implying someone had to hand-write a failover mechanism for it.
- **"…a per-rule, per-byte tax, not a free switch"** — a fluent way to push back on
  treating a security layer (a WAF, extra validation) as costless just because it's
  correct to have.
- **"…earn the right to reach the next layer"** — a fluent way to describe defense-in-depth
  ordering (L4 before L7, a cache before origin) without reciting a bullet-pointed list of
  every layer involved.
- **"…reads its own header and hands the rest off unopened"** — a precise way to describe
  what "layering" actually enforces mechanically (strict information hiding between
  Ethernet/IP/TCP/HTTP), not just a convenient diagram convention.

---

**Previous:** [Part 8: The Cost of Communication](08_cost_of_communication.md)  |  **Next:** [Part 10: The Physics of Persistence (B-Trees vs. LSM-Trees)](10_physics_of_persistence.md)

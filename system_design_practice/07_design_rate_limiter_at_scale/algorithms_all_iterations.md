# The Full Rate-Limiting Algorithm Landscape: Every Iteration

Companion deep-dive for **[tutorial.md](tutorial.md)**, which assumes algorithm basics
and focuses entirely on the harder multi-region problem. This doc is the other half: every
algorithm you could reach for, presented as a chain of iterations where each one exists to
fix a specific, nameable flaw in the one before it — not a flat list to memorize. For
runnable code of the first three (Fixed Window, Sliding Window Log, Token Bucket) as a
single-process class-level design, see
**[LLD: Rate Limiter](../../lld/05_rate_limiter/problem.md)**. For where each of these
algorithms actually shows up inside real Kubernetes infrastructure, see
**[kubernetes_native_implementations.md](kubernetes_native_implementations.md)**.

## Why "Iterations," Not Just "Options"

Reciting six algorithms off a list signals memorization. Explaining *why* the sixth one
exists — what specific failure in the fifth one it closes — signals understanding. Every
section below follows the same shape: **what breaks in the previous iteration, the
mechanism that fixes it, and what new cost that fix introduces.** Nothing here is a free
lunch; each iteration trades one weakness for a different one, never eliminates trade-offs
outright.

## Iteration 0: No Limiter

The baseline this whole conversation exists to prevent: unbounded concurrent load on a
shared resource, a single misbehaving or compromised client able to consume the entire
capacity budget, and no mechanism to convert "this backend is overloaded" into a fast,
cheap rejection instead of a slow, expensive failure (timeouts, cascading retries, an
actual outage). Every algorithm below is a different answer to the same question: *how do
I convert "too many requests" into "reject early, cheaply, and predictably" instead?*

## Iteration 1: Fixed Window Counter

**Mechanism:** partition time into fixed-size windows aligned to clock boundaries (e.g.
`:00`–`:59` of each minute). Key the counter as `{client_id}:{window_start}`. On each
request: `INCR` the counter for the current window; if the result exceeds the limit,
reject. The counter naturally expires — set a TTL equal to the window size and the key
disappears on its own once the window closes.

```
def allow(client_id, now, limit, window_seconds):
    window_start = now - (now % window_seconds)
    key = f"{client_id}:{window_start}"
    count = incr(key)
    if count == 1:
        expire(key, window_seconds)
    return count <= limit
```

**Complexity:** O(1) memory per client (one integer), O(1) time per check.

**The flaw, with numbers:** limit = 100 requests/minute. 100 requests land at `0:59.9`
(the tail end of window 1) — all allowed, window 1 hits exactly its limit. 100 more land
at `1:00.1` (the very start of window 2) — window 2's counter is fresh, so all 100 are
allowed too. **200 requests passed in a 200ms span**, and every individual window
"complied" with the 100/minute limit. This is the *boundary burst*: up to `2×` the
intended rate is achievable right at a window edge, and it requires no special client
behavior to trigger — it's a structural property of the algorithm, not an edge case.

```
Window 1 [0:00 ────────────────────────── 1:00) Window 2 [1:00 ────────────────────── 2:00)
                                        │      │
                                  100 req│      │100 req
                                  at 0:59.9      at 1:00.1
                                        └──200 req in 200ms──┘
Each window individually shows "100/100 — compliant." Neither counter ever saw
the other side of the boundary.
```

## Iteration 2: Sliding Window Log

**Motivated by:** eliminate the boundary burst entirely by tracking *exact* request times
instead of coarse, clock-aligned windows.

**Mechanism:** store a timestamp per request per client (a sorted set keyed by
`client_id`, scored by request time, works well in Redis). On each request: evict entries
older than `now - window`, then check whether the remaining count is below the limit;
if so, add the new timestamp.

```
def allow(client_id, now, limit, window_seconds):
    key = f"log:{client_id}"
    zremrangebyscore(key, 0, now - window_seconds)   # evict stale
    count = zcard(key)
    if count < limit:
        zadd(key, now, now)                          # record this one
        return True
    return False
```

In Redis specifically, the evict-count-add sequence must run as a single Lua script (or
`MULTI`/`EXEC` transaction) — otherwise two concurrent requests from the same client can
both read `count < limit` before either writes, letting both through (the classic
check-then-act race, the same class of bug a naive `SELECT` + `UPDATE` has in SQL without
a transaction).

**Complexity:** O(N) memory per client, where N is the number of requests allowed within
one window — for a generous limit (10,000/hour), that's 10,000 timestamps held per active
client. O(log N) time per operation (sorted-set insert/range-delete).

**The trade-off:** perfectly exact — no boundary burst is possible, because the window is
truly continuous, not aligned to clock ticks. The cost is memory that scales with traffic
volume rather than staying constant, and per-request eviction work that grows with how
many stale entries have accumulated. A single very active client (a legitimate high-volume
API partner, not necessarily an attacker) can make this the most expensive per-key
structure in the whole rate-limiting layer.

## Iteration 3: Sliding Window Counter (Weighted)

**Motivated by:** keep the O(1) memory of the fixed window while getting most of the
accuracy of the sliding log — trading a *small, quantifiable* approximation error for a
large reduction in memory and per-request cost.

**Mechanism:** keep exactly two fixed-window counters per client — the current window's
count and the *previous* window's count. Estimate the true count in the trailing
`window_seconds` as a weighted blend:

```
estimated_count = current_window_count
                 + previous_window_count * overlap_fraction
```

where `overlap_fraction` is how much of the previous window still falls inside the
trailing look-back — e.g., if we're 25% of the way into the current window, 75% of the
previous window is still "inside" the sliding look-back, so `overlap_fraction = 0.75`.

**Worked example:** limit = 100. Previous window's final count was 80. We're 25% into the
current window, current count so far is 20. `estimated_count = 20 + 80 × 0.75 = 80 ≤ 100`
→ allow. Compare to what a true sliding log would compute — it depends on exactly *when*
within the previous window those 80 requests landed, which this algorithm doesn't track.
**This is the explicit approximation**: the formula assumes requests are distributed
*uniformly* across the previous window. If all 80 of the previous window's requests
actually landed in its final 10%, the true trailing count is much closer to 100 than the
estimated 80 — the algorithm can under-count in adversarial or bursty-within-window
traffic patterns. State this bound as a named property, not a hidden gap: "approximately
accurate under roughly uniform traffic, with a bounded error that grows with how bursty
traffic is *within* a single window."

**Complexity:** O(1) memory (two integers), O(1) time — this is the production sweet
spot for straightforward HTTP-request-level limiting, and what a large share of API
gateways and CDN edge limiters (Cloudflare's public rate-limiting docs describe exactly
this algorithm) actually run, precisely because it matches fixed window's cost while
closing most of its accuracy gap.

## Iteration 4: Token Bucket

**Motivated by:** iterations 1–3 all share one property — they *smooth* traffic toward
the sustained rate and treat any burst as something to suppress. None of them let you say
"allow a controlled burst up to X, but cap the long-run sustained rate at Y" as two
independently tunable numbers. Token bucket introduces that second degree of freedom,
which matches how real clients actually behave far better (a batch job that's idle for
nine seconds then sends ten requests in the tenth is not "abusive" — a limiter that treats
burst and sustained rate as one number can't distinguish it from an attacker sending a
steady stream at the same average rate).

**Mechanism:** each client has a bucket holding up to `capacity` tokens, refilling
continuously at `rate` tokens/second. A request costs one token (or more, for
weighted-cost operations — see below). Reject if the bucket is empty. Refill is computed
*lazily*, at check-time, from elapsed time — no background timer or scheduled job needed
per key:

```
def allow(client_id, now, capacity, rate):
    tokens, last_ts = load(client_id, default=(capacity, now))
    elapsed = now - last_ts
    tokens = min(capacity, tokens + elapsed * rate)   # lazy refill
    if tokens >= 1:
        tokens -= 1
        save(client_id, (tokens, now))
        return True
    save(client_id, (tokens, now))
    return False
```

**Complexity:** O(1) memory (two numbers: `tokens`, `last_refill_ts`), O(1) time.

**Why this is "the one most production systems actually use":** AWS API Gateway,
Stripe's public API, and GitHub's REST API all document token-bucket-family limiters. The
burst/sustained-rate split directly matches real traffic shape, and it composes cleanly
with **weighted costs** — an expensive endpoint (a full-text search, a bulk export) can
cost 5 or 10 tokens instead of 1, letting one limiter express both "requests per second"
and "expensive-operation budget" with the same mechanism. This is exactly the extension
this repo's [LLD rate limiter](../../lld/05_rate_limiter/problem.md) names as a natural
follow-up (per-tier limits) — weighted cost is the same idea applied per-endpoint instead
of per-client-tier.

## Iteration 5: Leaky Bucket — Shaping, Not Just Policing

**Motivated by:** token bucket is a **policer** — it makes an instant admit/reject
decision, and once admitted, a request reaches the backend immediately. A burst up to
`capacity` still arrives at the backend *as a burst* (a bounded one, but a burst). Leaky
bucket is a **shaper**: it doesn't just gate requests, it queues them and releases them at
a strictly constant output rate, so the *backend* never sees anything but a smooth,
constant-rate stream, no matter how bursty the input was.

**Mechanism:** implemented as a bounded FIFO queue (the "bucket"). Incoming requests are
enqueued; if the queue is full, reject immediately (the bucket "overflows"). A separate
process drains ("leaks") one request at fixed intervals of `1/rate` seconds, regardless of
how many are currently queued.

```
def enqueue(client_id, request, queue_capacity):
    q = queue_for(client_id)
    if len(q) >= queue_capacity:
        return False   # bucket overflow, reject
    q.append(request)
    return True

# runs on a fixed-interval timer, independent of enqueue():
def leak(client_id, rate):
    q = queue_for(client_id)
    if q:
        process(q.popleft())
    # scheduled again after 1/rate seconds
```

**The token-bucket-vs-leaky-bucket distinction is a favorite interview "gotcha"** — the
two are frequently described as opposites, but the precise distinction is **policing vs.
shaping**: token bucket makes an instant decision and lets admitted bursts pass through
unmodified; leaky bucket absorbs bursts into a queue and converts them into added
*latency* instead of a burst reaching the backend at all. Being able to state that
distinction precisely, unprompted, is a stronger signal than knowing both names exist.

**Complexity:** O(min(capacity, current queue depth)) memory — genuinely heavier than
token bucket, since you're holding actual requests (or request handles), not just a
counter.

**When to pick this over token bucket:** when the protected resource has *zero* burst
tolerance — a downstream system that degrades badly under any burst, regardless of how
bounded — added latency from queueing is the better failure mode than letting even a
capped burst reach it. Token bucket is the right default when the protected resource (or
the caller) tolerates some burst and instant reject is preferable to added latency; leaky
bucket is the right choice when it doesn't and isn't.

## Iteration 6: GCRA — Token Bucket's O(1)-Storage Twin

**Motivated by:** token bucket needs two stored numbers per key (`tokens`,
`last_refill_ts`) and a small recomputation on every check. The Generic Cell Rate
Algorithm (GCRA, originally from ATM network traffic control) is **mathematically
equivalent to token bucket** — same admit/reject decisions, same burst-capacity and
sustained-rate semantics — but stores a single value per key: the **Theoretical Arrival
Time (TAT)**, the time at which the next fully-conforming request is expected. One value
per key is a natural fit for a single atomic Redis operation (`GET` + compare + `SET`, or
one Lua script), with less state to reason about than a two-field token-bucket record.

**Mechanism:**

```
emission_interval = 1 / rate           # time "cost" of one request
burst_tolerance   = capacity * emission_interval

def allow(client_id, now):
    tat = load(client_id, default=now)
    if now >= tat - burst_tolerance:
        new_tat = max(tat, now) + emission_interval
        save(client_id, new_tat)
        return True
    return False
```

**Real production usage — the direct bridge to Kubernetes:** Stripe's public engineering
write-up on their rate limiter describes exactly this algorithm. `lua-resty-limit-traffic`
(the OpenResty library nginx-based ingress controllers build on for advanced rate
limiting) implements a GCRA-family algorithm under the name `limit_req` — and nginx's own
native `limit_req_zone` module, which `ingress-nginx`'s Kubernetes annotations compile
down to, is leaky-bucket/GCRA-flavored by design (its `burst=` parameter is the queue
depth, `nodelay` switches it toward token-bucket-like instant accept/reject within the
burst allowance). This is not a coincidence worth glossing over — see
[kubernetes_native_implementations.md](kubernetes_native_implementations.md) for exactly
where this shows up as running infrastructure.

**Complexity:** O(1) memory (one timestamp), O(1) time, one round trip to the backing
store — marginally cheaper to reason about atomically than token bucket's two-field
record, which is why high-throughput, Redis-backed limiters often reach for GCRA over
"plain" token bucket even though the two make identical decisions.

## Bridging to the Distributed / Multi-Region Problem

Every iteration above answers "what arithmetic decides admit vs. reject." None of them
answer "where does that arithmetic run, and how is state kept consistent when multiple
processes need to check the same limit" — that's a completely separate axis, covered in
full in [tutorial.md](tutorial.md)'s deep-dives on local-enforcement-plus-reconciliation
and clock synchronization. The short version: a single Redis instance running any
algorithm above, checked synchronously by every server, is the correct *single-region*
answer (this is literally what the
[ML track's fundamentals tutorial](../../system_design_foundation/01_ml_system_design/00_interview_framework_fundamentals.md#worked-example-design-a-rate-limiter)
assumes as the starting point) — it only breaks down once servers are spread across
regions far enough apart that a synchronous round-trip on every request becomes
unacceptable, at which point tutorial.md's local-budget-plus-async-reconciliation pattern
takes over.

## Master Comparison Table

| Algorithm | Memory/key | Exact or approximate | Allows controlled burst? | Smooths sustained rate? | Real-world production examples |
|---|---|---|---|---|---|
| Fixed Window | O(1) | Approximate (2× boundary burst) | No (unbounded burst at edges) | No | Simplest API gateways, quick internal tools |
| Sliding Window Log | O(N), N = requests/window | Exact | No | Yes | Anywhere exactness matters more than memory (billing-adjacent limits) |
| Sliding Window Counter | O(1) | Approximate (bounded, uniform-traffic assumption) | No | Yes | Cloudflare edge limiting, most general-purpose API gateways |
| Token Bucket | O(1) | Exact for its own semantics | Yes (capacity param) | Yes (rate param) | AWS API Gateway, Stripe, GitHub API |
| Leaky Bucket | O(queue depth) | Exact for its own semantics | No — shapes into constant output | Yes, strictly | Traffic shaping in front of burst-intolerant downstreams |
| GCRA | O(1) | Exact, equivalent to token bucket | Yes (burst_tolerance param) | Yes | Stripe (public write-up), nginx `limit_req`, OpenResty `lua-resty-limit-traffic` |

## Picking One: A Decision Framework

If asked cold "which one would you actually use," the answer that signals depth: *"Token
bucket, or its GCRA twin, by default — the burst/sustained-rate split matches how real
clients behave. I'd reach for sliding window counter instead only when I want the
simplicity of two fixed-window integers and can tolerate its bounded approximation error,
and leaky bucket specifically when I need to shape traffic hitting a genuinely
burst-intolerant downstream, not just police an API surface."* Naming the *reason* for
each choice, not just the name of the algorithm, is what separates this from a
memorized list.

## Practice Questions

- Implement GCRA from scratch and verify — against a randomized request trace — that it
  produces identical admit/reject decisions to a token bucket configured with the same
  capacity and rate.
- Given a downstream with genuinely zero burst tolerance, justify choosing leaky bucket
  over a token bucket configured with `capacity = 1` (which also disallows bursts) — what's
  actually different between the two in that specific configuration?
- Extend the sliding window counter's worked example: construct a traffic pattern where
  the estimated count and the true sliding-log count diverge by the largest possible
  margin, and state that margin as a function of the limit.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Iteration-chain framing (the default opening move):** "I'd walk through these as a
  chain, not a list — fixed window's boundary burst motivates sliding window log, sliding
  log's memory cost motivates the weighted counter approximation, and none of the first
  three separate burst from sustained rate, which is what token bucket adds. Presenting it
  causally, not as six memorized names, is the point."
- **Policing-vs-shaping framing (good for the token-bucket-vs-leaky-bucket question
  specifically):** "The two are often called opposites, but the precise distinction is
  policing versus shaping — token bucket makes an instant decision and lets admitted
  bursts through unmodified, leaky bucket queues and releases at a constant rate,
  converting bursts into latency instead of letting them reach the backend at all."
- **Equivalence framing (good for GCRA, and for signaling depth beyond the obvious
  four):** "GCRA and token bucket make identical admit/reject decisions — the difference
  is purely storage shape, one timestamp versus a token-count-plus-last-refill pair —
  which is exactly why high-throughput Redis-backed limiters often reach for GCRA even
  though token bucket is the more commonly taught name."

### Vocabulary Builder

- **boundary burst** (n. phrase) — the up-to-2× overshoot fixed-window counting allows
  right at a window edge, purely from the algorithm's structure, not client misbehavior.
- **policing vs. shaping** (n. phrase pair) — instant admit/reject that lets bursts
  through unmodified (policing, token bucket) vs. queueing and releasing at a constant
  rate to smooth bursts into latency instead (shaping, leaky bucket).
- **Theoretical Arrival Time (TAT)** (n. phrase) — GCRA's single stored value per key: the
  time the next fully-conforming request is expected, from which admit/reject and the next
  TAT are both computed in one step.
- **"…is mathematically equivalent to token bucket, just a different storage shape"** — a
  fluent way to show depth on GCRA without implying it's a fundamentally different
  algorithm from the one already covered.

---

Companion deep-dive for **[tutorial.md](tutorial.md)** — the algorithm landscape its
Deep-Dive sections assume is already known. See
**[kubernetes_native_implementations.md](kubernetes_native_implementations.md)** next for
where each of these actually runs inside real cluster infrastructure, or
**[build_vs_buy_and_tooling_landscape.md](build_vs_buy_and_tooling_landscape.md)** for
whether you'd ever actually write this code outside an interview.

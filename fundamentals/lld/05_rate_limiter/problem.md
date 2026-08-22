# 5. Rate Limiter (Class-Level, Pluggable Algorithms)

**Difficulty:** Medium
**Topic:** Low-Level Design
**Pattern:** Strategy (interchangeable limiting algorithms) + Interface Segregation

## Requirements — and how this differs from the distributed version

This is the **class-level** rate limiter question: design a `RateLimiter` you'd import
into a single process to gate calls per client. It's asked as an LLD question, not a DSA
one, because the real ask is usually *"implement more than one algorithm, and make them
swappable"* — the evaluation is on the interface design and the trade-offs between
algorithms, not on any single implementation being clever.

This is **not** the same question as *"design a rate limiter service in front of a fleet
of API servers"* — that's a distributed-systems question about shared state (Redis,
consistency across nodes, clock skew) and lives in
[System Design Practice: Design a Rate Limiter at Global Scale](../../system_design_practice/07_design_rate_limiter_at_scale/tutorial.md).
Interviewers sometimes start with this class-level version and escalate to the distributed
one as a follow-up — noticing that pivot and re-framing your answer (shared state instead
of an in-memory dict) is itself a signal worth naming out loud.

The three algorithms below are the ones worth *implementing* by hand in an LLD round; for
the full landscape (including Leaky Bucket and GCRA, which most LLD rounds don't ask you
to code but which are worth being able to name and compare) see
[algorithms_all_iterations.md](../../system_design_practice/07_design_rate_limiter_at_scale/algorithms_all_iterations.md)
in that same section — and for what it takes to make *this exact code* correct behind a
Kubernetes Service with multiple replicas (swap the dict for Redis), see
[kubernetes_native_implementations.md](../../system_design_practice/07_design_rate_limiter_at_scale/kubernetes_native_implementations.md#iteration-7-diy-redis-backed-middleware-closing-the-loop-with-lld).

Requirements: given a `client_id`, decide whether to allow or reject a request right now,
supporting at least two different limiting algorithms behind the same interface so a
caller can swap algorithms without changing calling code.

## Core entities

- **`RateLimiter`** (interface) — one method, `allow_request(client_id, now) -> bool`.
  Kept intentionally minimal (Interface Segregation) — callers depend on exactly one
  capability.
- **`FixedWindowRateLimiter`** — counts requests in a fixed time bucket (e.g. per 10-second
  window), resets to zero at each new window. Cheapest to implement and reason about, but
  allows a burst of up to `2 × max_requests` right at a window boundary (max requests at
  the end of one window, plus max requests at the start of the next, with almost no time
  between them).
- **`SlidingWindowLogRateLimiter`** — stores actual request timestamps per client in a
  deque, discards any older than the window on each check. Exact — no boundary burst — at
  the cost of O(max_requests) memory per client instead of O(1).
- **`TokenBucketRateLimiter`** — each client has a bucket that refills continuously at a
  fixed rate up to a capacity; a request costs one token. Allows controlled bursts (spend
  a full bucket at once) while still capping the *sustained* rate to the refill rate —
  the algorithm most production systems (AWS, Stripe) actually use, because it's the only
  one of the three that treats "burst" and "sustained rate" as two independently tunable
  parameters.

## Relationships

All three implementations satisfy the same `RateLimiter` interface (Strategy pattern) —
any caller holding a `RateLimiter` reference is agnostic to which algorithm backs it. Each
implementation independently owns its **per-client state** (a dict keyed by `client_id`),
which is what makes this a single-process design — see the concurrency note below for why
that assumption breaks down at scale.

## Algorithm trade-off table

| Algorithm | Memory/client | Boundary burst? | Smooths sustained rate? |
|---|---|---|---|
| Fixed Window | O(1) | Yes, up to 2x | No |
| Sliding Window Log | O(max_requests) | No | Yes |
| Token Bucket | O(1) | Controlled (bucket size) | Yes |

Being able to produce this table from memory — not just implement one algorithm — is what
this problem is actually testing.

## Why class-level state doesn't survive a second process

Every implementation here keeps counters in an in-memory dict, which is correct for one
process but silently wrong the moment there are two: two API server instances behind a
load balancer would each allow `max_requests`, giving an effective limit of
`2 × max_requests` with no coordination between them. This is exactly the gap the
distributed version closes with shared state (Redis) — naming this limitation
unprompted, rather than waiting for the interviewer to ask "what if this runs on multiple
machines," is a strong senior+ signal.

## Extension follow-up

*"Now support different limits per client tier (free vs. paid), and let a client see how
many requests they have left."* With this design: pass a `(max_requests, window_seconds)`
— or `(capacity, refill_rate)` for token bucket — per client instead of one global config
at construction time (a small refactor to accept a lookup keyed by tier); add a
`remaining(client_id) -> int` method to the `RateLimiter` interface. Because the algorithm
choice is already isolated behind the interface, this extension touches all three
implementations identically and doesn't touch any calling code.

## Solution

### Python
Runnable, with sample test cases at the bottom (`python3 lld/05_rate_limiter/solution.py`):

```python
--8<-- "05_rate_limiter/solution.py"
```

### Rust
Same design, translated directly — no self-referential mutation issue here (each
algorithm only reads/writes its own internal map), so a plain `trait RateLimiter` with
three implementing structs works exactly like solution.py's ABC. Runnable via
`cd lld/05_rate_limiter/rate_limiter_rusty && cargo test`:

```rust
--8<-- "05_rate_limiter/rate_limiter_rusty/src/main.rs"
```

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Algorithm-comparison framing (the default opening move):** "I'd name the trade-off
  table before implementing anything — fixed window is cheap but allows boundary bursts,
  sliding window log is exact but costs memory per request, token bucket is what most
  production systems actually use because it separates burst allowance from sustained
  rate. Naming all three and their trade-offs up front, before picking one to implement
  first, shows I know the space rather than one algorithm."
- **Scope-boundary framing (good for distinguishing this from the distributed
  version):** "I'd flag explicitly that this class-level design keeps state in an
  in-memory dict, which is correct for one process but breaks the moment there are two —
  each instance would independently allow the full quota. I'd say that's exactly the gap
  the distributed version closes with shared state, rather than waiting to be asked."
- **Interface-design framing (good for justifying the Strategy choice):** "The interface
  is deliberately one method wide — `allow_request` — because that's the only thing a
  caller actually needs to depend on; keeping the three algorithms interchangeable behind
  it is what lets a follow-up question ('now use token bucket instead') be a
  one-line swap at the call site instead of a rewrite."

### Vocabulary Builder

- **boundary burst** (n. phrase) — the flaw in fixed-window limiting where up to double
  the intended rate can pass through right at a window edge; the standard critique that
  motivates sliding-window or token-bucket alternatives.
- **sustained rate vs. burst allowance** (n. phrase) — two independently tunable
  properties of a rate limiter (the long-run average rate vs. how much can be spent at
  once); token bucket is the only algorithm here that separates them cleanly.
- **per-client state** (n. phrase) — data keyed by client identity rather than global;
  the detail that makes this design fall over across multiple processes without shared
  storage.
- **"…is exactly the gap the distributed version closes"** — a reusable phrase for
  naming a design's known limitation and pointing at what fixes it, rather than letting
  the interviewer discover the gap and ask.

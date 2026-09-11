# Do You Write This, or Is There Tooling? Build vs. Buy for Rate Limiting

Companion deep-dive for **[tutorial.md](tutorial.md)**. The other two companion docs
answer "which algorithm" ([algorithms_all_iterations.md](algorithms_all_iterations.md))
and "which Kubernetes pattern implements it"
([kubernetes_native_implementations.md](kubernetes_native_implementations.md)). This one
answers a question those two intentionally sidestep: **do you actually sit down and write
token-bucket arithmetic, or does something already exist for this?** The honest answer —
almost always, tooling already exists, and the skill being tested is knowing *which layer*
handles it and when the narrow exception applies — depends entirely on which of three
contexts you're in, and conflating them is itself the mistake to avoid.

## The Three Contexts, and Why the Answer Changes Between Them

| Context | Do you write the algorithm? | What's actually being evaluated |
|---|---|---|
| LLD / coding interview | **Yes** | Interface design, algorithm trade-offs, correctness — see [`lld/05_rate_limiter`](../../lld/05_rate_limiter/problem.md) |
| System design interview | **No — name real tools** | Architecture, knowing what exists and its trade-offs, not code |
| Actual production system | **Almost never, until you do** | Judgment about which of the three tiers below the problem actually falls into |

Answering "you write it" in a system design round, or "you'd just use a library" in an
LLD round where the interviewer explicitly wants you to implement `allow_request`, both
read as missing the point of the question being asked — not as being wrong about
tooling in general.

## Context A: The LLD/Coding Round — Yes, Write It

This repo's own [`lld/05_rate_limiter/problem.md`](../../lld/05_rate_limiter/problem.md)
says it directly: *"the real ask is usually implement more than one algorithm, and make
them swappable — the evaluation is on the interface design and the trade-offs between
algorithms, not on any single implementation being clever."* When an interviewer hands you
this question in an LLD context, producing a `RateLimiter` trait/interface with two or
three algorithms behind it **is** the exercise. Reaching for "in real life I'd just use a
library" here isn't a wrong fact, it's a non-answer to the question that was actually
asked.

## Context B: The System Design Round — No, Name Real Tools

[`tutorial.md`](tutorial.md) and
[`kubernetes_native_implementations.md`](kubernetes_native_implementations.md) never ask
you to produce code — they ask you to draw an architecture and defend trade-offs. The
signal here is knowing that "Envoy's global rate-limit service, backed by Redis" is a real,
namable thing (not a hand-wave like "some service checks a counter"), and being able to
say what it costs (a synchronous gRPC hop per request) and why that cost is acceptable
in-region but not cross-region. Producing pseudocode unprompted in a system design round
usually reads as *not knowing* the answer is "an existing piece of infrastructure," not as
extra rigor.

## Context C: Actual Production — Three Tiers, in Order of Preference

This is the part worth having a real opinion on, because it's also frequently the
follow-up question after the LLD or system-design answer: *"okay, you've shown me you can
implement this — would you, on the job?"*

### Tier 1: Zero Application Code — Configure Existing Infrastructure

If a gateway, proxy, CDN, or API management layer already sits in the request's path,
rate limiting is a **configuration change**, not a code change:

- **Kubernetes-native**: everything in
  [kubernetes_native_implementations.md](kubernetes_native_implementations.md)'s
  Iterations 2–6 — ingress-nginx annotations, Envoy local/global rate limiting, Kong's
  plugin, Gateway API policy attachment. Zero lines of application code.
- **Cloud-managed API gateways** (non-K8s, or in front of a K8s cluster): AWS API Gateway
  usage plans + throttling (per-API-key, built in), Azure API Management rate-limit
  policies, GCP Apigee/Cloud Endpoints quotas — all configuration on a managed control
  plane, no servers to run at all.
- **Edge/CDN**: Cloudflare rate limiting rules, Fastly, AWS WAF rate-based rules — enforced
  before traffic even reaches your infrastructure, the cheapest possible place to reject
  abusive traffic since it never costs you compute.

**This is "buy," in the fullest sense** — no server to run, no library to patch, no
algorithm to get subtly wrong. It's also the correct default answer to "would you write
this on the job" for the overwhelming majority of real rate-limiting needs (protecting an
API surface from abuse, basic per-key quotas).

### Tier 2: A Library — You Call It, You Don't Reimplement It

When rate limiting needs to live *inside* application code (per-user business logic,
limits that depend on data the gateway layer can't see — subscription tier, feature
flags), reach for a maintained library before writing the algorithm:

| Language | Library | What it gives you |
|---|---|---|
| Python | `slowapi` (FastAPI/Starlette), `django-ratelimit`, `Flask-Limiter` | Decorator/middleware-level limiting, pluggable storage (in-memory, Redis) |
| Go | `golang.org/x/time/rate`, `uber-go/ratelimit` | Token-bucket primitives as a standard-library-adjacent import |
| Java | `Resilience4j` `RateLimiter`, `Bucket4j` | Token-bucket implementations with Spring integration, distributed backends |
| Node.js | `express-rate-limit`, `rate-limiter-flexible` | Middleware with pluggable Redis/Memcached backends for multi-instance correctness |
| Rust | `governor` crate | GCRA implementation (see [algorithms_all_iterations.md](algorithms_all_iterations.md#iteration-6-gcra-token-buckets-o1-storage-twin)) as a well-tested dependency |

**The honest relationship to this repo's own LLD code:** `lld/05_rate_limiter`'s
`solution.py`/`rate_limiter_rusty` implement, by hand, exactly what `Bucket4j` or
`governor` already ship as tested, maintained packages. Writing it yourself in an
interview is the point; writing it yourself in a real codebase, when a library already
does it and is already a dependency your team can support, is usually **reinventing a
solved problem** — the LLD exercise is valuable *because* it makes you understand what
these libraries do internally, not because you'd normally hand-roll one from scratch.

### Tier 3: Hand-Rolled — When the Pseudocode in `algorithms_all_iterations.md` Is the Real Answer

Reach for
[algorithms_all_iterations.md](algorithms_all_iterations.md)'s actual pseudocode, for
real, when:

- **The business logic is genuinely custom** and doesn't fit any off-the-shelf tool or
  library cleanly — e.g., weighted costs that vary per endpoint *and* per customer tier
  *and* need to feed into the specific overshoot/reconciliation policy from
  [tutorial.md](tutorial.md#deep-dive-the-practical-answer--local-enforcement--async-global-reconciliation),
  where no vendor's config schema expresses that combination.
- **No mature library exists** for the specific runtime/constraint (an embedded system, a
  language without a maintained rate-limiting package, a performance-critical hot path
  where a general-purpose library's overhead is unacceptable).
- **You're building the shared rate-limiting *service* itself** that other teams' code or
  gateways call into — at which point, say the quiet part out loud before writing it:
  *you are now building the same thing Lyft's open-source
  [`ratelimit`](https://github.com/envoyproxy/ratelimit) service already is.* Ask
  explicitly whether running that instead is viable before committing to build one from
  scratch — this is the build-vs-buy question from
  [`00_staff_level_signal/tutorial.md`](../00_staff_level_signal/tutorial.md#build-vs-buy-as-organizational-strategy-not-just-a-technical-choice),
  applied directly to this exact scenario.

## The Decision Framework — Three Questions, in Order

Before writing a single line of algorithm code, staff-level judgment asks, in this order:

1. **Does a gateway, proxy, or edge layer already sit in this request's path?** If yes,
   configure Tier 1 there. Zero code beats any code.
2. **Is there a mature, maintained library for this language that supports the algorithm
   and the storage scope (single-process vs. Redis-backed) I need?** If yes, use it. A
   dependency you don't maintain the internals of beats code you do.
3. **Is the remaining requirement genuinely not expressible in either of the above** —
   custom weighted business logic, no library exists, or you're building shared
   infrastructure other teams will depend on? Only here does
   [algorithms_all_iterations.md](algorithms_all_iterations.md)'s pseudocode become the
   real answer, not an interview exercise.

## Applying the Staff-Level Build-vs-Buy Axis, Specifically to Rate Limiting

Directly instantiating the three questions
[`00_staff_level_signal/tutorial.md`](../00_staff_level_signal/tutorial.md#build-vs-buy-as-organizational-strategy-not-just-a-technical-choice)
asks for build-vs-buy in general:

- **Undifferentiated heavy lifting, or a real differentiator?** For nearly every company,
  *how* rate limiting works is not the product — it's infrastructure. Building a bespoke
  distributed rate limiter when Envoy's `ratelimit` service (or a cloud API gateway)
  solves it is spending engineering effort on something that earns the business nothing
  strategic. The exception: a company *whose product is* API infrastructure (an API
  gateway vendor, a CDN) may have rate limiting as genuinely differentiated IP.
- **Total cost of ownership, not just build cost.** A hand-rolled Redis-backed limiter
  looks cheap to build (a few hundred lines) but comes with an on-call burden the moment
  it misbehaves under real traffic — clock skew, Lua script bugs, Redis failover behavior
  — that a maintained library or managed gateway has already paid down for thousands of
  other users.
- **Exit cost if the choice is wrong.** A library import is trivially swappable; a
  bespoke shared rate-limiting *service* that a dozen other teams now call into is not —
  naming that asymmetry before choosing Tier 3 for shared infrastructure, not after it's
  load-bearing, is the staff-level move.

## Why Interviewers Still Make You Implement It

The meta-question worth being able to answer if asked: *if almost nobody hand-rolls this
in production, why does every LLD interview ask you to?* Because the exercise isn't
testing "will you write this at your job" — it's testing whether you understand the
trade-offs **deeply enough to evaluate, configure, and debug the tooling** that Tier 1 and
Tier 2 actually are. Someone who's implemented sliding-window-log by hand once
understands *why* `ingress-nginx`'s `limit_req_zone` has a `zone=mylimit:10m` size
parameter and what happens when it fills up; someone who's only ever set the annotation
doesn't. The hand-rolled exercise builds the mental model that makes the "just configure
the tool" answer a genuinely informed one, not a guess.

## Comparison Table: The Three Tiers

| Tier | Example tools | Code you write | Reach for it when |
|---|---|---|---|
| 1. Infra config | ingress-nginx, Envoy, Kong, Gateway API, AWS API Gateway, Cloudflare | None | A gateway/proxy/edge layer already sits in the request path — the default first answer |
| 2. Library | `slowapi`, `Bucket4j`, `governor`, `express-rate-limit`, `golang.org/x/time/rate` | Glue code calling the library, not the algorithm | Rate limiting needs application-level context (tiers, feature flags) the gateway can't see |
| 3. Hand-rolled | This repo's [`lld/05_rate_limiter`](../../lld/05_rate_limiter/) code, or the pseudocode in [algorithms_all_iterations.md](algorithms_all_iterations.md) | The actual algorithm | Genuinely custom business logic, no mature library for the runtime, or building the shared service other teams will call |

## Practice Questions

- A team wants per-customer-tier limits (free/pro/enterprise) with different burst
  allowances, enforced at the API gateway. Is this Tier 1, 2, or 3 — and does the answer
  change if the tier lookup requires a database call the gateway can't make?
- You've been asked to build an internal rate-limiting service that a dozen other
  microservices will call into. Before writing any code, what's the specific build-vs-buy
  question to ask, and who should you ask it to?
- Justify, out loud, why implementing sliding window log by hand in an LLD round is still
  valuable even though you'd never ship that exact code to production.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Context-first framing (the default opening move, especially if the question is
  ambiguous about which round you're in):** "The answer to 'do I write this or use
  tooling' depends entirely on context — an LLD round wants me to implement it, a system
  design round wants me to name real tools and their trade-offs, and in production I'd
  default to configuring existing infrastructure first. I'd clarify which one is actually
  being asked before answering."
- **Tiered-preference framing (good for the 'would you actually build this' follow-up):**
  "I'd reach for infrastructure config first, a maintained library second, and only
  hand-roll the algorithm when the business logic is genuinely custom or I'm building
  shared infrastructure — and even then, I'd ask whether an existing service like Lyft's
  `ratelimit` solves it before committing to build one."
- **Meta-framing (good for 'why does the interview ask you to implement this if nobody
  does in production'):** "The exercise isn't testing whether I'd ship hand-rolled
  token-bucket code — it's testing whether I understand the trade-offs deeply enough to
  configure and debug the tooling that actually runs in production, which is a different
  and more foundational skill than memorizing a config schema."

### Vocabulary Builder

- **undifferentiated heavy lifting** (n. phrase) — infrastructure work that costs
  engineering effort but earns the business no competitive advantage; the standard
  argument for buying instead of building it.
- **total cost of ownership (TCO)** (n. phrase) — the full cost of a technical choice
  including maintenance, on-call burden, and institutional knowledge, not just the
  upfront build/license cost.
- **exit cost** (n. phrase) — how expensive it is to reverse a build-vs-buy decision later;
  a swappable library import has low exit cost, a shared internal service other teams
  depend on has high exit cost.
- **"…is reinventing a solved problem"** — a fluent, non-dismissive way to flag that a
  proposed hand-rolled solution duplicates an existing, maintained tool, prompting the
  build-vs-buy question before committing effort.

---

Companion deep-dive for **[tutorial.md](tutorial.md)**. See
**[algorithms_all_iterations.md](algorithms_all_iterations.md)** for the algorithms this
doc's Tier 2/3 code would actually implement, and
**[kubernetes_native_implementations.md](kubernetes_native_implementations.md)** for the
Tier 1 tooling landscape in Kubernetes specifically.

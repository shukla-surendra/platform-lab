# Prerequisite Concepts, Part 16: Observability — Metrics, Logs, and Traces

Every part in this series has assumed a distributed system exists; none of them have
covered how you actually find out what one is doing right now, or why one specific request
just failed. Once a request can touch a dozen services across a dozen machines — exactly
what [Part 13's distributed-systems
catalog](13_cap_theorem_and_pacelc.md#what-is-a-distributed-system-precisely) describes —
"attach a debugger and step through it" stops being an option. Observability is the
discipline that replaces it.

## In Plain English

A car's dashboard has a fixed set of gauges: speed, fuel, engine temperature. It tells you
about problems someone already anticipated you'd need to watch for — that's **monitoring**.
A flight data recorder is different: it captures enough raw detail about *everything* that
happened that investigators can later ask a question nobody thought to ask in advance —
"what was the left engine doing three minutes before the incident" — and actually get an
answer, without having pre-built a gauge for that exact question. That's **observability**:
not a dashboard of things you predicted, but the capability to ask a *new* question about
your system's internals after the fact, using only what it already recorded.

## Monitoring vs. Observability, Precisely

**Monitoring** is watching a predefined set of metrics and dashboards for known failure
modes — useful, necessary, and not enough on its own, because it can only tell you about a
problem you already thought to build a gauge for. **Observability** is the broader *system
property* of being able to answer arbitrary new questions about internal state from
external outputs, without shipping new code to add instrumentation after the fact. The
industry's shift toward observability over pure monitoring is a direct response to
[Part 13's own point](13_cap_theorem_and_pacelc.md#what-is-a-distributed-system-precisely):
distributed-system failures are frequently novel combinations nobody predicted, and a fixed
dashboard can't cover a failure mode its author never imagined.

## The Three Pillars

- **Metrics** — numeric measurements over time (request rate, error rate, latency
  percentiles, CPU usage). Cheap to store and aggregate, excellent for dashboards and
  alerting on trends, but they tell you *that* something is wrong (error rate spiked at
  14:32) without telling you *which* request or *why* — they're an aggregate, by design,
  which is exactly what makes them cheap.
- **Logs** — discrete, timestamped records of individual events, free-text or structured
  (JSON). Rich detail per event, but expensive to store and search at real volume, and
  correlating log lines scattered across many services for a single request is genuinely
  hard without help.
- **Traces** — following *one specific request's* journey across every service it touches,
  showing the timing and dependency tree of every hop. This is [Part 6/9's distance-and-
  latency argument](06_mechanical_sympathy_and_physics_of_latency.md#distance-of-data-one-physical-idea-two-different-scales),
  made visible: a trace is literally a picture of exactly where a request's latency budget
  was spent, service by service. It requires a **trace ID** (or correlation ID) generated at
  the start of a request and propagated through every downstream call — a header passed
  along each hop — so all the individually-collected pieces can be stitched back into one
  timeline afterward.

**A fourth idea worth naming, since it's where the industry is actually heading**: some
modern tooling (Honeycomb popularized this framing) collapses metrics, logs, and traces
toward **wide structured events** — one high-cardinality record per request capturing
everything at once — plus **continuous profiling** (always-on CPU/memory profiling in
production, not just point-in-time debugging). Both are real, current extensions of the
three-pillar model, not a replacement for it.

## SLI, SLO, SLA, and the Error Budget

[Part 1 already used "the nines" language](01_performance_and_scale.md) for availability
targets without naming the full vocabulary around it — worth doing precisely here:

- **SLI (Service Level Indicator)** — the actual measured metric: "p99 latency," "% of
  requests returning a non-error status."
- **SLO (Service Level Objective)** — the internal target for that indicator: "p99 latency
  under 200ms, 99.9% of the time." This is the number an engineering team actually holds
  itself to.
- **SLA (Service Level Agreement)** — the externally-facing, often contractual promise,
  usually set deliberately *looser* than the internal SLO — the margin exists so the team
  catches and fixes a problem internally before it ever breaches the customer-facing
  contract.
- **Error budget** — 100% minus the SLO threshold, i.e., the amount of unreliability
  explicitly "allowed to spend" before the SLO itself is breached. A modern SRE concept
  (originating from Google's SRE practice) used to balance reliability work against feature
  velocity: an error budget that's nowhere near exhausted is a legitimate signal to ship
  faster and take more risk; one that's nearly spent is a legitimate signal to slow down and
  prioritize reliability work instead — turning "how careful should we be right now" into a
  measured number instead of a gut feeling.

## The Cardinality Problem

A genuinely easy-to-miss, concrete design mistake: attaching a **high-cardinality** label
(a user ID, a request ID) to a metric. Most metrics systems (Prometheus among them) store
each *unique combination* of label values as its own separate time series — tagging a
counter by user ID doesn't just add a dimension, it multiplies the number of stored time
series by the number of distinct users, which can explode storage and query cost by orders
of magnitude. **The rule this implies**: high-cardinality data belongs in logs or traces,
which are built to hold per-event detail; metrics are for genuinely low-cardinality
dimensions (service name, status code, region) that stay small and bounded regardless of
traffic volume.

## Sampling: Making Tracing Affordable at Scale

Capturing 100% of traces at real production volume is often prohibitively expensive. Two
sampling strategies, with a real difference in what they guarantee:

- **Head-based sampling** — the decision to keep or discard a trace is made *before* the
  request finishes (e.g., "sample 1% of requests, randomly, up front"). Cheap and simple, but
  purely random — an error or an unusually slow request has no better chance of being kept
  than a completely normal one.
- **Tail-based sampling** — the decision is made *after* seeing the full trace, specifically
  so all error traces and all unusually slow traces can be kept deliberately, even while the
  overall sample rate for "boring, successful, fast" traces stays low. This is the modern,
  smarter default precisely because it guarantees the *interesting* traces — the ones
  someone will actually need during an incident — are never randomly missed the way
  head-based sampling can miss them.

## Real Tools, Modern Defaults

**Prometheus + Grafana** — the near-universal open-source metrics-and-dashboards pairing
(Prometheus scrapes/stores time-series metrics, Grafana visualizes them); already documented
hands-on in this repo's own [`mlops_aiops/docs`](../../../mlops_aiops/docs/) and
`k8n_explorer` observability work. **The ELK/EFK stack** (Elasticsearch, Logstash or
Fluentd, Kibana) — the long-standing default for centralized log aggregation and search,
also already covered in this repo's own docs. **OpenTelemetry** — the current, vendor-neutral
industry standard for *instrumenting* an application to emit metrics, logs, and traces in one
unified way, so the collection layer isn't locked to one specific backend; genuinely the
biggest recent shift in this space and worth treating as the modern default to reach for.
**Jaeger, Zipkin** — dedicated distributed-tracing backends. **Datadog, New Relic,
Honeycomb** — commercial full-stack observability platforms, with Honeycomb specifically the
origin of the wide-structured-events framing named above. **CloudWatch** — AWS's native
offering, already covered in this repo's `cloud-practice` material.

## Designing and Operating From First Principles

1. Have I actually distinguished monitoring (dashboards for problems I already anticipated)
   from observability (the ability to ask a question I haven't thought of yet) — or am I
   assuming a good dashboard is the same thing as being observable?
2. For any given piece of telemetry, have I deliberately chosen metrics vs. logs vs. traces
   based on whether it's aggregate, per-event, or per-request-journey data — or is
   everything going into whichever system was easiest to wire up first?
3. Have I checked any metric I'm about to add for high-cardinality labels (user ID, request
   ID) before it ships — or will I only discover the cost explosion after it's already in
   production?
4. Do I know my system's actual SLI/SLO numbers, or only a vague sense of "it's usually
   pretty fast" — and is the SLA (if one exists) deliberately looser than the internal SLO,
   or accidentally the same number?
5. If I'm sampling traces, am I using tail-based sampling specifically to guarantee errors
   and slow requests are kept — or head-based sampling that could randomly miss the exact
   traces an incident investigation would need?

## Key Takeaways

- **Monitoring watches for problems you already anticipated; observability is the broader
  capability to answer new questions after the fact** — the industry's shift toward it is a
  direct response to distributed systems failing in ways nobody predicted in advance.
- **The three pillars measure genuinely different things**: metrics are cheap aggregates
  (good for "that something's wrong"), logs are rich per-event detail (expensive at scale),
  traces are one request's cross-service journey (require a propagated trace ID to stitch
  together).
- **SLI is the measurement, SLO is the internal target, SLA is the external promise** — the
  SLA is deliberately looser than the SLO so a team catches problems before a customer-facing
  contract is breached; the error budget turns "how careful should we be" into a number.
- **High-cardinality labels on metrics are a real, concrete cost mistake** — a user ID or
  request ID as a metric label can multiply stored time series by orders of magnitude; that
  detail belongs in logs/traces instead.
- **Tail-based sampling is the modern default over head-based** specifically because it
  guarantees error and slow traces are kept, rather than randomly, possibly missing exactly
  the traces an incident investigation needs.
- **OpenTelemetry is the current instrumentation standard** unifying metrics/logs/traces
  collection across whatever backend a team actually uses — the real "stay current" answer
  in this space right now.

## Quick Self-Check

- Why is a well-built dashboard not the same thing as "being observable" — what question can
  observability answer that a fixed dashboard structurally cannot?
- Name the three pillars and, for each, state one thing it's good at and one thing it
  structurally cannot tell you on its own.
- Why does a trace require a propagated trace ID specifically — what would break about
  stitching a request's cross-service journey back together without one?
- Explain precisely why an SLA is usually set looser than the internal SLO — what would go
  wrong if a team set them to the exact same number?
- Why does tagging a Prometheus metric with a user ID cause a cost problem that tagging it
  with a status code doesn't — what's the actual mechanism, not just "it's more data"?
- Why does tail-based sampling guarantee capturing error traces in a way head-based sampling
  cannot, even at the identical overall sample rate?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Dashboard-vs-black-box framing (the default for 'how would you monitor this' questions):**
  "I'd separate monitoring — dashboards for failure modes I already anticipated — from
  observability, the ability to answer a question about my system I haven't thought of yet.
  Distributed systems fail in combinations nobody predicts in advance, so I'd design for the
  second property, not just build more dashboards for the first."
- **Three-pillars-are-different-tools framing (good for an instrumentation design question):**
  "I wouldn't just 'add logging' — I'd ask whether this specific piece of telemetry is
  aggregate (metrics), per-event (logs), or cross-service-journey (traces) data, since each
  one has a genuinely different cost profile and answers a different question."
- **Error-budget framing (good for a reliability-vs-velocity trade-off question):** "I'd use
  the error budget to make that trade-off a number instead of a gut call — if the budget's
  nowhere near spent, that's a legitimate signal to ship faster; if it's nearly gone, that's
  a legitimate signal to slow down, without anyone having to argue about it qualitatively."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **the three pillars** (n. phrase) — metrics, logs, and traces; the standard framing for
  what observability data actually consists of.
- **trace ID / correlation ID** (n. phrases) — an identifier generated at the start of a
  request and propagated through every downstream call, letting a distributed trace be
  stitched back together afterward from independently-collected pieces.
- **SLI / SLO / SLA** (n., initialisms) — the measured indicator, the internal target for it,
  and the external (often contractual) promise, deliberately in increasing looseness.
- **error budget** (n. phrase) — 100% minus the SLO threshold; the amount of unreliability
  explicitly allowed before breaching the objective, used to balance reliability work
  against feature velocity as a number rather than a judgment call.
- **cardinality (metrics)** (n.) — the number of unique label-value combinations a metric
  produces; high-cardinality labels (user ID, request ID) multiply stored time series and
  belong in logs/traces instead.
- **head-based / tail-based sampling** (n. phrases) — deciding to keep a trace before vs.
  after seeing its outcome; tail-based specifically guarantees errors/slow traces are kept.
- **OpenTelemetry** (n., proper) — the current vendor-neutral standard for instrumenting an
  application to emit metrics, logs, and traces in one unified way.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…a dashboard versus a flight recorder"** — a compact, plain-language way to state the
  monitoring-vs-observability distinction without reciting definitions.
- **"…a question nobody thought to ask in advance"** — a fluent way to argue for
  observability's value over a fixed set of dashboards.
- **"…turns a gut call into a number"** — a reusable line for describing what the error
  budget actually buys a team in a reliability-vs-velocity discussion.

---

**Previous:** [Part 15: Caching — Trading Freshness for Speed](15_caching.md)  |  **Next:** [Part 17: Isolation Levels & Concurrency Control](17_isolation_and_concurrency_control.md)

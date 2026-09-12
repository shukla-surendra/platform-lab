# Microservices: Operational Pitfalls, Anti-Patterns, and When Not To

Part of [`README.md`](README.md)'s microservices section — see its top note on scope and
sourcing. That file covered what breaks *technically*: network unreliability, cascading
failure, and distributed data consistency. This file covers what changes *operationally*
once a system is many independently-deployed services instead of one — API evolution,
observability, deployment safety, security boundaries, testing — plus the organizational
reality and concrete anti-patterns that show up in almost every real microservices
migration, and a direct answer to the question every principal engineer should be asking
before proposing this architecture at all: whether it's actually the right trade-off here.

## API contracts and versioning: the cost of independent deployability

The entire point of splitting a system into services is that each one can be built,
tested, and deployed independently. That independence has a direct cost: **a service can no
longer assume every caller is running its latest code**, because callers deploy on their own
schedule, not in lockstep with the service they call. A field renamed, a field removed, an
enum value added, a required field newly added to a request — any of these, shipped without
care, breaks every caller still running the previous version, and in a system with many
independent consumers, "every caller has upgraded" is never simultaneously true.

- **Backward-compatible changes** — adding a new optional field, adding a new enum value a
  caller can safely ignore, adding a new endpoint — are safe to deploy without coordinating
  with consumers.
- **Breaking changes** — removing or renaming a field, changing a field's type, making an
  optional field required — need an explicit compatibility strategy: version the API
  (`/v2/orders`) and run both versions in parallel until every known consumer has migrated
  off the old one, or evolve the schema additively (deprecate a field, stop reading it
  internally, but keep emitting it for some transition window) rather than removing it in
  one atomic step.
- **Contract testing** (Pact and similar tools implement this directly) is the practical
  discipline for catching a breaking change *before* it reaches production: the consumer of
  an API records the exact shape of requests/responses it actually depends on (a
  "contract"), and the provider's CI pipeline runs that contract against its own code on
  every change — catching "I broke a field a real consumer depends on" at build time,
  without needing a live end-to-end integration environment running every service
  simultaneously just to notice the same thing.

The underlying discipline this all serves is simple to state and easy to violate under
deadline pressure: **a deployed API is a promise to callers you may not control and can't
force to upgrade on your schedule** — every breaking change has to be treated as a
migration, not a same-day edit.

## Observability across a boundary that used to be a stack trace

In a monolith, "why is this request slow" is answerable with a profiler and a single stack
trace — the whole call path lives in one process. Once that same request crosses five
service boundaries, **no single service has visibility into the full path** — each one only
sees its own piece, and correlating "the checkout request was slow" with "which one of the
five services it touched was actually the slow one" requires deliberate instrumentation that
doesn't exist by default.

- **Correlation IDs** — a unique ID generated at the system's entry point (the API gateway,
  typically) and propagated through every downstream call (as a header) for the lifetime of
  that request. Every log line, in every service, includes it — the direct, low-tech
  mechanism that makes it possible to grep every service's logs for one ID and reconstruct
  what actually happened for one specific request, across service boundaries that otherwise
  have no shared context at all.
- **Distributed tracing** (OpenTelemetry as the current standard instrumentation API;
  Jaeger and Tempo as common backends — all three already covered hands-on elsewhere in
  this repo: [`../opentelemetry/`](../opentelemetry/), [`../jaeger/`](../jaeger/),
  [`../tempo/`](../tempo/)) builds on the same correlation-ID idea but captures the full
  call graph and per-hop timing as a structured trace, not just a shared ID to grep for —
  the direct answer to "which one of these five services actually accounted for the 4
  seconds of latency," visualized as a waterfall rather than reconstructed by hand from
  scattered logs.
- **Centralized log aggregation** (the [`../elasticsearch/`](../elasticsearch/) /
  [`../loki/`](../loki/) family already in this repo) exists for the same underlying reason:
  once "the system" is many separate processes, each with its own local log file, "check the
  logs" stops being a single `ssh` and `tail` — logs have to be shipped somewhere centrally
  searchable, or the correlation ID above has nothing to actually be grepped against in
  practice.

Without all three, the honest failure mode isn't "debugging is harder" — it's that some
classes of production incident become **effectively undebuggable after the fact**: a
transient error that touched four services and self-resolved before anyone looked leaves no
reconstructable trail at all if it was never captured as a correlated, centrally-searchable
record in the first place.

## Deployment and rollout safety

A monolith deploy is one binary, one moment, one rollback target. A microservices
architecture multiplies both the number of independent deploys *and* the number of ways
those deploys can interact badly with each other — two services mid-rollout, briefly running
different versions simultaneously, is not an edge case, it's the normal state of any system
deploying continuously.

- **Canary and blue-green deployments** exist directly because of the API-versioning
  reality above: routing a small fraction of real traffic to a new version before cutting
  everything over (canary) or keeping the previous version fully live and ready as an
  instant rollback target (blue-green) both assume — and require — that the new version
  can coexist with the old one handling live traffic side by side, which is only true if
  breaking changes were actually avoided as described above.
- **Feature flags decoupling deploy from release** — deploying new code with a feature
  disabled by default, then enabling it separately (often gradually, per-cohort) is what
  lets a risky change be *reverted instantly* (flip the flag) without a full redeploy/
  rollback cycle — a meaningfully faster recovery path during an incident than "revert the
  commit, rebuild, redeploy."
- **Schema migrations across services need their own explicit ordering**, for the same
  backward-compatibility reason as the API contracts above: if Service A's database schema
  change and Service B's code that depends on the new shape deploy in the wrong order (or
  simply at slightly different times, which is the default in independent deploy pipelines),
  there's a real window where the system is broken — not by an application bug, but purely
  by deploy sequencing. [`../postgresql/production-and-scaling.md`](../postgresql/production-and-scaling.md#zero-downtime-ddl-more-generally)'s
  zero-downtime DDL patterns (`NOT VALID` + `VALIDATE CONSTRAINT`, additive-then-cleanup
  schema changes) are the direct database-level tool for making a schema change safe to
  deploy *before* the code that depends on it, specifically so migration order stops being
  a source of production incidents.

## Security boundaries multiply along with the services

A monolith has one process boundary and, typically, one point where a request is
authenticated. A microservices architecture has as many internal network boundaries as it
has services calling each other — every one of those is a place a request could,
technically, be forged, replayed, or intercepted if it isn't itself explicitly secured.

- **Service-to-service authentication** — a request arriving at an internal service needs
  to be verifiable as genuinely coming from another legitimate internal service, not just
  "arrived on the internal network," since "internal network" is a much weaker security
  boundary than it sounds once a system has dozens of services and any compromised one could
  otherwise impersonate any other. **mTLS** (mutual TLS — both sides of a connection present
  and verify a certificate, not just the client verifying the server the way ordinary HTTPS
  works) is the standard mechanism for service-to-service identity at the network layer;
  short-lived, scoped JWTs passed between services are the common application-layer
  alternative or complement.
- **Secret sprawl** — each service typically needs its own database credentials, API keys
  for third-party services, and internal service-to-service credentials. Multiplied across
  dozens of services, "where do secrets live and how do they rotate" stops being a
  per-service concern and becomes a real platform requirement — a dedicated secrets manager
  (Vault, AWS Secrets Manager) with short-lived, automatically-rotated credentials, rather
  than long-lived secrets hand-copied into each service's environment variables and quietly
  never rotated again.
- **Expanded attack surface** — every internal service-to-service call is, in principle, an
  additional place an attacker who's compromised one service could pivot from — a genuinely
  different threat model than a monolith, where compromising the single process is required
  to compromise anything at all. This is a real argument for **not** blindly trusting
  "internal" traffic and applying least-privilege network policy (which services are even
  allowed to reach which other services at the network layer, not just at the application
  authorization layer) between services, not just at the system's external edge.

## Testing complexity: the integration-testing problem

Unit-testing a single service in isolation is unchanged from monolith testing. What's
genuinely new and harder: verifying that a *change* to one service doesn't break another
service that depends on it, without needing a full environment running every service
simultaneously for every test run (slow, flaky, and expensive to maintain at any real scale).

- **Contract testing** (already covered above under API versioning) is the primary answer —
  it turns "does my change break a consumer" into a fast, isolated, per-service test rather
  than a live, multi-service integration environment.
- **Consumer-driven contracts** specifically (the Pact model) flip the direction from
  "provider defines the contract" to "consumers define what they actually depend on, and the
  provider's tests are run against the union of all real consumers' actual usage" — this
  matters because it catches breaking a field *nobody said they needed* but someone was
  actually depending on, which a provider-authored contract (written from the provider's own
  assumptions about what matters) can miss entirely.
- **Testing in production** (feature flags, canary releases, synthetic monitoring/shadow
  traffic mirrored to a new version without affecting real users) is a deliberate,
  increasingly standard complement, not a replacement — some classes of integration bug
  (real-world data shape, real third-party service behavior, real cross-service timing)
  are genuinely hard to reproduce faithfully in any pre-production environment, however
  well-built.

## The organizational reality: Conway's Law is not optional

**Conway's Law** — a system's architecture ends up mirroring the communication structure of
the organization that builds it — is not a cute observation, it's a direct operational
constraint on microservices specifically, because a microservices architecture's entire
value proposition (independent deployability, independent scaling, independent ownership) is
only real if service boundaries roughly match **team** boundaries. A service boundary that
splits work two teams have to constantly coordinate on recreates exactly the same
coordination overhead a monolith has — just with strictly worse tooling for it (network
calls, version skew, and the entire technical cost catalog in
[`README.md`](README.md) added on top, in exchange for organizational independence that was
never actually achieved). Deliberately designing service boundaries *around* team boundaries
(sometimes called the "inverse Conway maneuver" — organizing teams first, around the
boundaries you actually want, and letting the architecture follow) is a real, standard
technique specifically because the reverse — architecting services first and hoping team
structure adapts to match — reliably fails to deliver the independence microservices are
supposed to buy.

### The distributed monolith: the worst of both worlds

The single most common real-world microservices failure mode, and worth naming precisely
because it's easy to arrive at gradually without anyone deciding to build it: a system that's
been split into many separately-deployed services, but which still has to be deployed
together, in a specific order, because they're too tightly coupled to actually release
independently — synchronous call chains three or four services deep for a single user
request, shared databases between services (below), or APIs so unstable that every consumer
has to redeploy in lockstep with every provider change. **This configuration pays every real
cost of microservices (network latency, partial failure, operational complexity,
distributed debugging) while getting none of the actual benefit (independent deployability,
independent scaling, fault isolation)** — genuinely worse than either a well-built monolith
or a well-built microservices architecture, and the most common outcome of adopting the
pattern without addressing the organizational and API-boundary discipline it actually
requires.

## A catalog of concrete anti-patterns

- **The shared database** — multiple services reading and writing the same database/tables
  directly, instead of each service owning its own data and exposing it through an API. This
  quietly destroys the entire premise of service independence: a schema change in "your"
  table can silently break another team's service that happens to also query it, with no
  API contract, no version, and no warning — the database itself becomes an undocumented,
  unversioned shared API, which is strictly worse than an actual API precisely because
  nobody thinks to treat it with the same care. [`../postgresql/security-and-access-control.md`](../postgresql/security-and-access-control.md#least-privilege-is-a-design-decision-not-a-default)'s
  least-privilege framing applies here almost directly: a service's database credentials
  should be scoped to *that service's own tables*, which is itself a forcing function against
  this anti-pattern, not just a security posture.
- **Chatty services** — a single user-facing request that fans out into a long, often
  serial, chain of internal calls (Service A calls B, which calls C, which calls D, just to
  assemble one response) multiplies the latency cost from the trade-off table in
  [`README.md`](README.md) by every hop in the chain, and multiplies the number of places a
  partial failure can occur along the way. The direct fixes are service boundaries drawn
  around what's actually needed together in one response (avoiding needing five calls to
  answer one question in the first place), parallelizing independent calls instead of
  chaining them serially, and — for read-heavy fan-out specifically — a
  dedicated aggregation/BFF (Backend-for-Frontend) layer that assembles the response, so the
  chattiness is contained in one place rather than repeated by every client that needs the
  same composite data.
- **Config drift** — environment-specific configuration (feature flags, connection strings,
  resource limits) diverging silently across services and environments over time, especially
  once dozens of services each maintain their own config independently, with no single place
  to see what's actually deployed where. Centralized configuration management, and treating
  config changes with the same review/audit discipline as code changes, is the standard
  countermeasure — "just SSH in and change the env var for this one service" is exactly how
  drift accumulates unnoticed until it causes an incident that's confusing specifically
  because the code is identical everywhere and only the configuration silently isn't.

## When not to reach for microservices

None of the patterns in this section make microservices free — every one of them is a real,
ongoing engineering cost paid specifically in exchange for independent deployability and
independent scaling. That trade is worth making when a system genuinely needs one or both of
those properties: teams large enough that shared deploys are a real bottleneck, or components
with genuinely different, divergent scaling needs (an image-processing pipeline and a
user-authentication service have nothing in common in their resource profile, and forcing
them to scale together as one monolith wastes real capacity). It is **not** automatically the
better architecture, and a principal engineer's job includes being able to argue for *not*
adopting it just as readily as for adopting it:

- **A small team (roughly, a team that can still fit around one table) rarely benefits** —
  the coordination overhead microservices are meant to *remove* barely exists yet at that
  size, so splitting the system mainly adds the technical costs from this section without
  removing a real organizational cost that isn't there to remove.
- **A system with no genuinely divergent scaling needs** gains little from independent
  scaling — if every component's load grows roughly together, splitting them apart doesn't
  save real resources, it just adds network hops between them.
- **A modular monolith** — a single deployable process, but internally organized into
  clearly-separated modules with disciplined, enforced boundaries between them (no reaching
  into another module's internals, clean interfaces between modules) — captures much of the
  *organizational* clarity benefit of microservices (clear ownership, clear boundaries) while
  keeping the trade-off table at the top of [`README.md`](README.md) firmly in the "function
  call" column: fast, atomic, no network unreliability to design around. It's frequently the
  right starting architecture, with a credible, well-trodden migration path — the strangler
  fig pattern covered in
  [`20_microservices_architecture_patterns.md`](../../../../fundamentals/system_design_foundation/00_prerequisite_concepts/20_microservices_architecture_patterns.md#the-strangler-fig-pattern-migrating-without-a-big-bang-rewrite) —
  to actually extract services later, specifically once a real, concrete organizational or
  scaling need for one emerges, rather than splitting a system upfront on the speculative
  belief that it will need to scale like a much bigger company's system eventually.

The question worth asking before proposing this architecture, stated plainly: **what
specific organizational or scaling problem does splitting this system solve, that a
well-organized monolith genuinely can't** — and if the honest answer is "none yet," that's a
complete, sufficient reason to not pay the costs cataloged across this section until it
changes.

# Microservices: What Actually Breaks in Production

**Category:** distributed systems architecture (not a single tool — a pattern spanning many)

## What this section is

Not a survey of microservices as an idea, and not a duplicate of
[`fundamentals/system_design_foundation/00_prerequisite_concepts/20_microservices_architecture_patterns.md`](../../../../fundamentals/system_design_foundation/00_prerequisite_concepts/20_microservices_architecture_patterns.md)
(service discovery, the strangler fig migration pattern, event sourcing, CQRS — read that
first if the architectural vocabulary itself is new). This section starts from the opposite
direction: **given that you've already split a system into services, what actually goes
wrong once it's carrying real production traffic, and why** — the edge cases and failure
modes a principal engineer is expected to have internalized, not from a checklist, but from
the same handful of physical facts every problem below traces back to.

Two files:

- **This README** — the core trade-off every microservices problem is downstream of, plus
  network unreliability (timeouts, retries, idempotency, retry storms), partial and
  cascading failure (circuit breakers, bulkheads, backpressure, load shedding), and
  distributed data consistency (no more cross-service transactions — sagas, the outbox
  pattern, the dual-write problem).
- [`production-pitfalls-and-operations.md`](production-pitfalls-and-operations.md) — what
  changes about API evolution, observability, deployment, security, and testing once a
  system is many independently-deployed services instead of one; the organizational reality
  (Conway's Law, the distributed monolith anti-pattern); a catalog of concrete anti-patterns
  (chatty services, the shared database, config drift); and a principal-engineer checklist
  for when *not* to reach for microservices at all.

This content is conceptual/architectural, like
[`../kafka-vs-rabbitmq.md`](../kafka-vs-rabbitmq.md) and
[`../airflow-vs-alternatives.md`](../airflow-vs-alternatives.md) elsewhere in this repo —
grounded in well-established, real production experience across the industry, not re-derived
against a live multi-service deployment in this lab. Where a pattern has a concrete, runnable
counterpart elsewhere in this repo (Kafka for event-driven decoupling, Redis for distributed
locks/caching, PostgreSQL for the "shared database" anti-pattern this section warns against),
it's linked directly rather than re-explained.

## The one trade-off everything else is downstream of

A monolith calls a function. A microservices architecture calls a function **over a
network**. Stated that plainly, it sounds like a minor implementation detail — it is not.
Every property a function call gets for free, a network call has to fight for, explicitly,
or lose silently:

| | In-process function call | Network call between services |
|---|---|---|
| Latency | Nanoseconds, effectively free | Milliseconds to seconds — routinely 10,000x+ slower |
| Failure | Can't fail independently of the caller — if it runs, it runs in the same process, same moment | Can fail in ways the caller has no way to distinguish: the request never arrived, it arrived but the response was lost, the callee crashed mid-processing, the network partitioned |
| Atomicity | Trivial — one call stack, one outcome | None, by default — two services can each "succeed" from their own point of view while the overall operation is left half-done |
| Ordering | Guaranteed by the call stack | Not guaranteed at all — two calls issued in order can arrive, retry, or be processed out of order |

This table is the entire reason microservices are hard, and everything below is one of its
rows worked out to its real, concrete production consequence. It's also the honest reason to
be skeptical of any team adopting microservices purely for "clean architecture" reasons
without a real organizational or scaling need driving it — see
[`production-pitfalls-and-operations.md`](production-pitfalls-and-operations.md#when-not-to-reach-for-microservices)
for that trade-off stated directly. You are not getting a cleaner system for free; you are
trading in-process guarantees for independent deployability and scaling, and paying for that
trade in exactly the ways below.

## The network is not reliable

The starting assumption a monolith's author never has to make explicit — "if my code called
this function, it ran" — is false the instant that function call becomes a network call. A
request can fail before reaching the other service, the other service can fail while
processing it, or the *response* can fail on the way back — and from the caller's side,
**a timeout looks identical in all three cases.** This single ambiguity is the root of most
of what follows.

### Timeouts: a design decision, not a default to leave alone

Every network call needs an explicit timeout — without one, a single unresponsive downstream
service can hold a caller's thread/connection open indefinitely, and that exhaustion
propagates: the caller's own callers now wait on *it*, and so on up the call chain. A
timeout that's too short causes false failures on requests that would have succeeded a
moment later (adding retry load to an already-struggling downstream service — see retry
storms, below); a timeout that's too long delays failure detection and holds resources open
needlessly. The number itself should come from the downstream service's actual measured
latency distribution (its p99, not its average — see
[`07_saturation_amdahls_law_and_hedged_requests.md`](../../../../fundamentals/system_design_foundation/00_prerequisite_concepts/07_saturation_amdahls_law_and_hedged_requests.md)
for why tail latency, not average latency, is what actually determines a good timeout), not
a round number picked without data.

### Retries without idempotency corrupt data, not just waste effort

The ambiguity above — "did that request actually succeed?" — makes retrying a failed call
the obvious response. It's also where a specific, concrete production bug lives: **retrying
a request that actually succeeded, but whose success response was lost on the way back, means
the operation runs twice.** A "charge this customer $50" request that times out waiting for a
response, when the charge itself actually went through, and gets naively retried, charges the
customer $100.

The fix is **idempotency**, not "retry less" — designing the operation itself so that
running it more than once with the same input produces the same result as running it once.
The standard mechanism is an **idempotency key**: the caller generates a unique ID for the
logical operation (not the HTTP request — the *business* operation, "charge this order"),
sends it with every attempt including retries, and the receiving service checks whether it's
already processed that exact key before doing any real work:

```
POST /charges
Idempotency-Key: order-8842-charge-attempt

{ "amount": 5000, "currency": "usd" }
```

The receiving service stores completed idempotency keys (alongside the response that was
returned) for some retention window, and on a repeat key, returns the *stored* response
instead of re-executing the charge. This has to be built deliberately into every operation
that mutates state and might be retried — it is not a property that emerges automatically
from "just adding retries," and an API that accepts retries without an idempotency mechanism
is one where retrying is actively unsafe, whether or not that's obvious from its interface.

### Retry storms: the failure mode retries themselves cause

A downstream service that's genuinely struggling (overloaded, partially degraded) starts
failing or slowing down. Every caller, following a naive "retry on failure" policy, retries
— which adds *more* load to the exact service that's already struggling, pushing it further
into failure, which triggers more retries. This is a real, self-reinforcing feedback loop,
not a hypothetical: it's one of the more common causes of an outage that starts small and
becomes total.

Three mechanisms combine to prevent it, none optional in a real production retry policy:

- **Exponential backoff** — each successive retry waits longer than the last (typically
  doubling), so retry pressure on a struggling service decays over time instead of staying
  constant.
- **Jitter** — randomizing the backoff delay (rather than every caller retrying at exactly
  `2s, 4s, 8s, ...` in lockstep) spreads retries out instead of having every client hammer
  the recovering service at the same synchronized instant — the same "thundering herd"
  problem [`../postgresql/production-and-scaling.md`](../postgresql/production-and-scaling.md#adjacent-failure-mode-concepts-worth-knowing)
  covers for cache stampedes, same underlying mechanism, different trigger.
- **A retry budget / max attempts** — an explicit cap on total retries (per-request and,
  ideally, system-wide as a circuit breaker — below), so a struggling service eventually
  gets a chance to shed load and recover rather than facing indefinite retry pressure from
  every caller simultaneously.

## Partial failure and cascading failure

In a monolith, "the system is down" is close to a binary state. In a microservices
architecture, **partial failure is the normal condition, not the exception** — at any given
moment in a system of dozens of services, some non-zero number of them are degraded, slow,
or briefly unreachable, simply as a matter of probability across that many independent
moving parts. The problem isn't preventing partial failure (impossible) — it's preventing
one service's partial failure from **cascading** into every service that depends on it,
directly or transitively.

### How a cascade actually happens

Service A calls Service B, which is slow (not down — slow, which is often worse). Each of
A's threads/connections calling B now sits waiting instead of completing quickly. If A has a
fixed pool of worker threads or connections, and B stays slow long enough, **every one of
A's workers eventually ends up blocked waiting on B** — at which point A can't serve *any*
request, including the ones that have nothing to do with B. A, now fully blocked, becomes
slow from *its* callers' point of view, and the same failure propagates one level further up
the call graph. A single slow, non-critical downstream dependency can take down services that
never directly depend on the thing that actually broke — this is the real mechanism behind
an incident where the "cause" and the "symptom" appear to be in completely unrelated parts of
the system.

### Circuit breakers: stop calling a service that's already failing

A circuit breaker wraps a call to a dependency and tracks its recent failure rate. Modeled
directly on the electrical analogy it's named for:

- **Closed** (normal state) — calls pass through to the real dependency; failures are
  counted.
- **Open** — once failures cross a threshold within a time window, the breaker "trips": for
  a cooldown period, calls **fail immediately without even attempting the network call**,
  instead of adding more load to an already-struggling dependency and waiting out a full
  timeout on every single request.
- **Half-open** — after the cooldown, the breaker lets a small number of trial requests
  through. If they succeed, it closes again (resume normal calls); if they fail, it re-opens
  and waits another cooldown period.

The concrete production value: a caller that would otherwise burn every worker thread
waiting on full timeouts against a dead dependency instead fails those calls **instantly**
while the breaker is open, freeing its own capacity to keep serving requests that don't
depend on the broken service — directly preventing the cascade described above. It's also
the mechanism that lets a struggling downstream service actually recover: without it, a
fully-saturated caller keeps hammering it with new attempts even while it's trying to come
back up.

### Bulkheads: failure in one dependency shouldn't exhaust resources needed by another

Named after a ship's watertight compartments — a hull breach in one compartment floods that
compartment, not the whole ship. Applied to a service: if *every* outbound call (to five
different dependencies, say) draws from one shared connection/thread pool, one slow
dependency can exhaust that shared pool and starve calls to the other four, completely
healthy dependencies. **Isolating pools per-dependency** (a fixed, separate connection/thread
budget for each downstream service a caller talks to) means one dependency failing can only
ever exhaust *its own* allocation — calls to everything else keep flowing normally. This is
the direct fix for the specific "one slow dependency takes down unrelated functionality"
failure mode described above, and it's a deliberate resource-allocation decision, not
something that happens automatically just by having a circuit breaker in place.

### Backpressure and load shedding: when you can't do the work, say so immediately

Once a service is genuinely at capacity, it has two choices: keep accepting work it can't
keep up with (queues grow unboundedly, latency climbs for everyone, and the service
eventually falls over completely) or **explicitly refuse new work** once it's past
capacity, returning a fast, honest failure (a `503`, typically) rather than a slow, eventual
one. This is **load shedding**, and it's a deliberate design choice, not a fallback — a
service that has no explicit capacity limit doesn't avoid overload, it just fails less
predictably and less gracefully once overload happens anyway. **Backpressure** is the
related, upstream-facing version of the same idea: a service under load signals its callers
to slow down (via an explicit signal, or simply by its queue/connection pool filling up and
naturally blocking new work) rather than silently accepting more than it can process. Both
exist for the same reason: a system that degrades gracefully under overload (some requests
fail fast, most succeed normally) is recoverable; a system that accepts unlimited load until
it collapses entirely usually isn't, and takes far longer to recover once it does.

## Distributed data consistency: there is no `BEGIN`/`COMMIT` across services

A monolith talking to one database gets transactions for free — a multi-step operation
either fully commits or fully rolls back, guaranteed by the database. The moment "place an
order" means writing to an `Orders` service's database *and* calling a `Payments` service
*and* calling an `Inventory` service, **there is no single transaction spanning all three** —
each service has its own database, and a distributed transaction protocol across them (Two-
Phase Commit) is generally avoided in practice specifically because it requires locking
resources across the network for the duration and introduces a coordinator as a single point
of failure — see
[`../postgresql/production-and-scaling.md`](../postgresql/production-and-scaling.md#distributed-transactions-across-services)
for that mechanism stated in full. The practical consequence: **a multi-service operation
that appears atomic from the outside has to be built out of independently-committing local
transactions, engineered so a partial failure is either impossible to observe or explicitly
reversible.**

### The dual-write problem

A deceptively common, genuinely broken pattern: a service updates its own database, then
separately publishes an event about that update to a message broker (Kafka, say), as two
separate operations:

```
UPDATE orders SET status = 'confirmed' WHERE id = 123;   -- write 1: the database
publish("order.confirmed", {"order_id": 123});           -- write 2: the broker
```

These are **two independent writes to two independent systems, with no atomicity between
them.** If the process crashes between them, or the broker publish fails after the database
commit succeeds, the database says the order is confirmed but nothing downstream — anything
that reacts to that event (sending a confirmation email, updating a search index, notifying
a shipping service) — ever finds out. The failure is silent: no error is thrown, no
constraint is violated, the data is just quietly wrong from that point forward, often not
discovered until a customer complains.

**The outbox pattern is the standard fix.** Instead of publishing directly, the service
writes the event into an `outbox` table in the *same database, same transaction* as the
actual business data change — meaning the two writes now share the atomicity guarantee of a
single local database transaction, which the database already gives for free:

```sql
BEGIN;
UPDATE orders SET status = 'confirmed' WHERE id = 123;
INSERT INTO outbox (event_type, payload, published) VALUES ('order.confirmed', '{"order_id": 123}', false);
COMMIT;
```

A separate process (a poller, or — more robustly — a change-data-capture process reading the
database's write-ahead log directly, via a tool like Debezium) then reads unpublished outbox
rows and actually publishes them to the broker, marking them published once the broker
confirms receipt. If that publishing step fails or crashes partway, it simply retries later
— the event is durably recorded in the database and can't be lost the way an unrecorded
in-memory publish attempt can. This turns "two independent writes with no atomicity between
them" into "one atomic local write, plus a separately-retriable publish step that can safely
fail and recover" — the asymmetry between the two pieces is deliberate: the local database
transaction is the only place true atomicity is available, so that's exactly where the
event's existence gets guaranteed.

### Sagas: an eventually-consistent transaction, built from steps and compensations

For a multi-service operation with no single database to anchor an outbox to at all (place
an order → charge a payment → reserve inventory, three separate services, three separate
databases), the **Saga pattern** is the standard structure: each step executes its own local
transaction and, on success, triggers the next step. If a later step fails, instead of
attempting an impossible distributed rollback, earlier steps are undone explicitly via
**compensating transactions** — a new, separate operation that semantically reverses the
original one (not a database `ROLLBACK`, since that step's transaction already committed):

```
1. Order Service:    create order (status = pending)         [commits]
2. Payment Service:  charge card                             [commits]
3. Inventory Service: reserve stock                           -- fails, out of stock

Compensating actions, run in reverse:
2'. Payment Service:  refund the charge
1'. Order Service:    mark order cancelled
```

This is a genuinely different consistency model than the transaction a monolith gets for
free — the system passes through a real, observable intermediate state (briefly, an order
exists and a card has been charged before the compensation reverses it), which is why this
is called **eventual consistency**, not atomicity: correctness is guaranteed *eventually*,
after every compensating action completes, not at every single instant along the way. Two
implementation styles exist: **choreography** (each service listens for the previous step's
event and reacts independently — no central coordinator, but the overall flow is implicit,
spread across every service's event handlers, and harder to see as a whole from any one
place) and **orchestration** (a dedicated coordinator service explicitly calls each step in
order and explicitly triggers compensations on failure — the flow is visible in one place,
at the cost of that coordinator becoming a new, single piece every saga now depends on).
Neither is universally correct; the choice is a real trade-off between implicit
decentralized flow and an explicit but more centralized one, made per-system based on how
many sagas exist and how important a single, auditable view of the flow actually is.

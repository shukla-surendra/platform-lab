# Phrase Library: Comparisons, Trade-offs, and Architecture Description

## 1. Comparing Two Systems or Options

- "The key difference between X and Y is..."
- "X and Y solve similar problems, but diverge on..."
- "Where X shines is..., whereas Y is better suited for..."
- "It's less about which is 'better' and more about which fits our constraints — specifically..."
- "X wins on [dimension], Y wins on [dimension] — for us, [dimension] mattered more because..."
- "On paper they look similar; the practical difference shows up when..."
- "We evaluated both against three criteria: ..."
- "X is the safer default; Y is the better fit if you specifically need..."
- "The crossover point is [scale/condition] — below that, X is fine; above it, Y pulls ahead."
- "They're not actually substitutes — X solves [problem A], Y solves [problem B]."
- "If I were starting from scratch today, I'd still pick X, because..."
- "In hindsight, Y would have been the better call for [specific reason] — X was the right call given what we knew then."

## 2. Describing Architecture (Verbally, No Diagram)

- "At a high level, requests flow from A through B into C..."
- "Picture three layers: ingestion, processing, and serving..."
- "The system has two main paths — the hot path for real-time requests, and the batch path for..."
- "Everything sits behind a load balancer that fans out to..."
- "The data flows one direction: source → transform → sink, no cycles."
- "Think of it as a pipeline with three stages..."
- "There's a control plane and a data plane — the control plane handles [X], the data plane handles [Y]."
- "It's event-driven — nothing polls, everything reacts to a message on the queue."
- "The core abstraction is a [job/task/record] that moves through a fixed set of states: ..."
- "Ownership boundaries roughly map to team boundaries — team A owns ingestion, team B owns serving."
- "There's a synchronous path for [use case] and an asynchronous path for [use case] — most traffic goes through the async path."
- "The system is intentionally stateless at the compute layer — all state lives in [store]."

## 3. Presenting Trade-offs

- "We're trading [X] for [Y] here — specifically..."
- "This optimizes for [read-heavy / low-latency / cost / simplicity] at the expense of [the other thing]."
- "There's no free option here — every path costs us something. This one costs us [X], which we judged acceptable because..."
- "The trade-off is explicit: we get [benefit], and in exchange we accept [cost]."
- "This is the right trade-off at our current scale; it may not be at 10x scale, and here's the signal we'd watch for..."
- "We chose to over-invest in [X] and under-invest in [Y], deliberately, because [Y] is cheap to fix later and [X] is not."
- "It's a reversible decision, which is why we didn't spend more time deliberating — if it's wrong, the cost of reversing is low."
- "This is a one-way door, so we spent more time here than the decision size might suggest."
- "We optimized for time-to-market over long-term maintainability on this one, with the explicit plan to revisit in [timeframe]."

## 4. Giving a Recommendation

- "My recommendation is X, with medium/high confidence."
- "If forced to choose today, I'd go with X — but I'd flag [condition] as something that could change that."
- "I'd recommend X for now, and revisit once we have [missing data point]."
- "Weighing the options, X comes out ahead on the dimensions that matter most to us."
- "I don't think this is a close call — X is clearly the better fit, for [reason]."
- "This one is genuinely close — I have a slight preference for X, but Y is defensible too."
- "I'd push back on Y specifically because [concrete reason], not just as a general preference."
- "My default would be X unless someone has context I'm missing."

## 5. Explaining Scalability

- "This scales horizontally — adding nodes adds capacity roughly linearly, up to [bottleneck]."
- "The current bottleneck is [component]; everything else has headroom."
- "It's designed to scale to [N], and we've load-tested to [N] with [safety margin]."
- "Vertical scaling buys us time, but the real fix at scale is [architectural change]."
- "We hit a wall at [scale] because [specific reason — e.g., a shared lock, a single-writer constraint]."
- "The scaling story is different for reads vs. writes — reads scale easily via replicas, writes are still bound by [constraint]."
- "This wasn't built for [current scale] originally — it was built for [10x smaller], and it's held up better than expected because..."

## 6. Explaining Reliability

- "We target [X] nines for this service, measured over [window]."
- "The failure domain is isolated to [component] — a failure there doesn't cascade to [other component] because..."
- "We've engineered for graceful degradation — if [dependency] is down, we fall back to [degraded mode] instead of failing outright."
- "Redundancy is at the [AZ/region] level — we can lose a full AZ without customer-visible impact."
- "The single point of failure that remains is [X] — it's a known, accepted risk because [reason], tracked as [ticket/decision]."
- "We test failure modes deliberately via [chaos engineering / game days / fault injection]."

## 7. Explaining Security Posture

- "Access follows least-privilege — each service has its own IAM role scoped to exactly what it touches."
- "Data is encrypted at rest via [mechanism] and in transit via [TLS/mTLS]."
- "We treat the network boundary as untrusted — auth happens at the service level, not just the perimeter."
- "Secrets are never in code or environment variables directly — they're pulled from [Vault/Secrets Manager] at runtime."
- "The threat model we designed against is [specific threat], not a generic 'best practices' checklist."
- "This was reviewed by security before rollout, and the main finding was [X], which we addressed by [Y]."

## 8. Explaining Cost Optimization

- "The biggest cost driver was [component] — it accounted for roughly [%] of spend."
- "We right-sized based on actual utilization data, not initial provisioning guesses."
- "This moved us from a fixed cost model to a usage-based one, which cuts cost at low traffic and scales predictably at high traffic."
- "The savings came from [specific mechanism — e.g., spot instances, reserved capacity, autoscaling to zero], not from cutting corners on reliability."
- "We quantified the trade-off explicitly: [$X] saved per month against [Yms] of added latency — an easy call given our SLA headroom."
- "Cost and reliability were in tension here, and we chose to hold reliability constant and optimize cost within that constraint, not the reverse."

## 9. Cloud Migration Language

- "We're doing this as a phased migration, not a big-bang cutover — [phase 1], then [phase 2]."
- "The strangler-fig pattern applies well here — new traffic routes to the new system, old traffic drains off the legacy one gradually."
- "We're migrating data first, with dual-writes during the transition window, then cutting over reads once parity is confirmed."
- "The rollback plan is [X] — we can revert within [timeframe] if [trigger condition] happens."
- "Migration risk is front-loaded deliberately — we moved the riskiest, highest-uncertainty piece first, while we still have the most time buffer."

## 10. Describing Distributed Systems Concepts Precisely

- "This is eventually consistent, not strongly consistent — writes propagate within [typical window], and here's why that's acceptable for this use case: ..."
- "We chose availability over consistency here, per CAP — during a partition, we serve stale reads rather than fail the request."
- "Idempotency is enforced via [mechanism], so retries are safe even under at-least-once delivery."
- "The ordering guarantee is per-key, not global — messages for the same key are ordered, across keys they're not, and that's sufficient because..."
- "We use optimistic concurrency here — conflicts are rare enough that pessimistic locking would cost more than it saves."

**Next:** [`03_recommendations_disagreement_feedback.md`](./03_recommendations_disagreement_feedback.md) — phrases for disagreeing professionally, handling objections, and giving feedback.

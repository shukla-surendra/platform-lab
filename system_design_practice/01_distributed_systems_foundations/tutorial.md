# Distributed Systems Foundations at Staff Depth

The mechanics every case study in this section draws on. The
[fundamentals covered in the ML track](../../system_design_foundation/01_ml_system_design/00_interview_framework_fundamentals.md)
(load balancing, caching, basic sharding, CAP theorem) are assumed background — this
tutorial goes one level deeper into the machinery staff-level rounds expect you to
actually understand, not just name.

## Consensus: Making Multiple Nodes Agree on One Truth

**The problem**: in a distributed system, multiple nodes need to agree on a single value
(who's the leader, what's the next log entry) even when nodes can crash and messages can
be delayed — this is provably impossible to solve perfectly in an asynchronous network
(the FLP impossibility result), which is *why* consensus algorithms make specific,
nameable trade-offs rather than solving the problem outright.

- **Raft** (the one to know cold, since it was explicitly designed to be
  understandable/explainable, unlike Paxos): nodes are Leader, Follower, or Candidate.
  Leader election uses randomized timeouts (preventing repeated split votes). The leader
  replicates a log to followers; an entry is **committed** once a majority of nodes have
  it. If the leader fails, a new election happens; the node with the most up-to-date log
  among the majority wins, guaranteeing no committed entry is ever lost.
- **Paxos**: solves the same problem, proven first, but with a reputation for being hard
  to reason about and implement correctly — worth naming as "the original," with Raft as
  "the practical one," rather than needing to explain Paxos's proposer/acceptor/learner
  roles in depth.
- **Where this actually shows up**: leader election in a database cluster (etcd/Zookeeper
  use Raft/Paxos-family algorithms internally), distributed lock services, and any
  "exactly one node should do X" coordination problem.
- **The staff-level framing**: consensus is *expensive* (every write needs majority
  acknowledgment, adding latency) — the staff-level judgment call is recognizing **when you
  need it at all**. Most of a distributed system doesn't need strong consensus; it needs
  consensus *only* for a small, critical coordination point (leader election, a
  distributed lock), with everything else built on cheaper eventual-consistency
  mechanisms. Reaching for consensus everywhere is a common over-engineering signal.

## Distributed Transactions: 2PC vs. Saga

**The problem**: a single logical operation needs to atomically update state across
multiple independent services/databases (e.g. "reserve inventory" + "charge payment" must
both succeed or both fail) — but there's no single database transaction spanning both.

- **Two-Phase Commit (2PC)**: a coordinator asks all participants to "prepare" (lock
  resources, confirm they *can* commit), and only after every participant confirms does it
  send "commit" to all. Guarantees atomicity, but the coordinator is a single point of
  failure/blocking — if it crashes between phases, participants can be left holding locks
  indefinitely. This is why 2PC is rarely used across service boundaries at scale, despite
  being the "textbook correct" answer.
- **Saga pattern**: break the operation into a sequence of local transactions, each with a
  defined **compensating action** to undo it. "Reserve inventory" → "charge payment" → if
  payment fails, run "release inventory" (the compensating action for the first step).
  No global lock, much better availability — the cost is that the system passes through
  genuinely inconsistent intermediate states (inventory reserved but payment not yet
  confirmed) that every downstream reader must be designed to tolerate.
- **Orchestration vs. choreography Sagas**: orchestration has a central coordinator
  explicitly calling each step and its compensations (easier to reason about, one more
  component to build); choreography has each service reacting to events from the previous
  one with no central coordinator (more decoupled, harder to trace/debug a failure across
  services).
- **The staff-level framing**: the choice between 2PC and Saga is really a choice between
  **consistency and availability during a partial failure**, restated at the application
  level — and it's usually resolved by asking "can this operation tolerate a visible,
  temporary inconsistent state, if it's provably eventually resolved?" Most business
  operations can (a "payment processing" status is a perfectly normal user-facing state);
  a small few genuinely can't (double-spending a unique inventory unit), which is where
  2PC or a stricter design is actually justified.

## CRDTs & Vector Clocks: Resolving Conflicts Without Coordination

**The problem**: in a multi-leader or offline-capable system, the same piece of data can
be modified concurrently on different nodes with no coordination — when they reconcile,
what happens?

- **Vector clocks**: each node keeps a counter per node it's seen writes from
  (`{node_a: 3, node_b: 1}`). Comparing two vector clocks tells you if one **causally
  precedes** the other (safe to just take the newer one) or if they're **concurrent**
  (a genuine conflict requiring resolution — either "last write wins" by a
  secondary rule, or application-level merge logic). This is *how* a system detects a
  conflict exists, not how it resolves one.
- **CRDTs (Conflict-free Replicated Data Types)**: data structures specifically designed
  so concurrent updates **always merge deterministically without conflict**, by
  construction. A simple example: a grow-only counter that only supports increment — merge
  is just "take the max count seen from each node and sum," which is commutative and
  associative regardless of what order updates arrive in. More complex CRDTs exist for
  sets, maps, and even collaborative text editing (the algorithm behind Google Docs-style
  concurrent editing).
- **The staff-level framing**: CRDTs trade expressiveness for conflict-free merging — not
  every operation can be modeled as a CRDT (e.g., "transfer money between two accounts"
  fundamentally can't be, since it's not commutative/mergeable in the required sense).
  Recognizing *which part* of a system's data model is CRDT-representable (counters,
  presence/last-seen indicators, collaborative document edits) versus which part needs
  genuine coordination (financial transfers) is the actual skill being tested.

## Consistent Hashing & Advanced Sharding

Beyond the [basic sharding covered in the ML fundamentals tutorial](../../system_design_foundation/01_ml_system_design/00_interview_framework_fundamentals.md#sharding-partitioning):

- **The problem with naive `hash(key) % N` sharding**: adding or removing a node changes
  `N`, which reshuffles the mapping for *almost every key* — a massive, unnecessary data
  migration for what should be a small capacity change.
- **Consistent hashing**: map both nodes and keys onto a conceptual ring (via hashing);
  each key belongs to the next node clockwise on the ring. Adding/removing a node only
  remaps the keys between it and its neighbor — a small, bounded fraction of keys, not
  everything.
- **Virtual nodes**: assign each physical node multiple positions on the ring (not just
  one) — this smooths out load distribution (avoiding one physical node getting an unlucky
  large arc of the ring) and makes rebalancing after a node change more evenly
  distributed across the *remaining* nodes rather than dumping everything onto one
  neighbor.
- **The staff-level framing**: this is the mechanism underneath *every* "distributed
  cache" or "distributed database" case study's horizontal scaling story — being able to
  explain consistent hashing precisely (not just name it) is what makes the deep-dive in
  the [distributed cache case study](../05_design_distributed_cache/tutorial.md)
  land as staff-level rather than a name-drop.

## Service Mesh: Cross-Cutting Concerns Without Cross-Cutting Code

**The problem**: every service in a large microservices architecture independently needs
retries, timeouts, mTLS, load balancing, and observability for its outbound calls —
implementing this in every service's application code duplicates effort and drifts
inconsistently over time.

- **The sidecar pattern**: a proxy (Envoy is the common one) runs alongside every service
  instance, intercepting all network traffic in/out. Cross-cutting concerns (retries,
  circuit breaking, mTLS, tracing) are configured and enforced at the proxy layer,
  uniformly, without any application code change.
- **Control plane vs. data plane**: the sidecars (data plane) do the actual traffic
  handling; a control plane (Istio, Linkerd) centrally configures and observes all
  sidecars — "route 10% of traffic to v2" becomes a control-plane config change, not a
  redeploy of every service.
- **The staff-level framing**: a service mesh is a genuine **organizational** answer to a
  technical problem — it's the mechanism that lets a platform team enforce consistent
  reliability/security policy across dozens of independently-deployed services owned by
  different teams, without requiring every team to individually implement retry logic
  correctly. Naming it as an organizational-scaling tool, not just a technical one, is
  exactly the staff-altitude framing from the
  [staff-level signal tutorial](../00_staff_level_signal/tutorial.md).

## Multi-Region Active-Active

Extends the [active-passive DR discussion in the ML track](../../system_design_foundation/01_ml_system_design/10_cost_security_multiregion.md#multi-region-disaster-recovery)
to the harder, fuller case: multiple regions **simultaneously serving live writes**, not
just one active region with a standby.

- **The core problem**: if region A and region B can both accept writes to the same
  logical data, you need a strategy for reconciling concurrent writes to the same record
  from different regions — this is exactly where CRDTs, vector clocks, or an explicit
  conflict-resolution policy (e.g. "last write wins by timestamp, with clock-skew
  tolerance") become load-bearing, not optional.
- **Data partitioning by region ("cell-based architecture")** sidesteps the conflict
  problem for data that's naturally region-scoped (a user's data lives primarily in their
  home region) — cross-region conflict only needs solving for genuinely global,
  concurrently-written data (a global inventory count, a global leaderboard), which is
  usually a much smaller surface area than "everything."
- **The staff-level framing**: active-active is dramatically more operationally complex
  than active-passive, and the staff-level judgment call is recognizing that **most
  systems don't need full active-active** — cell-based partitioning (regional data
  locality) solves the availability problem for the 90% of data that's naturally
  region-scoped, reserving true multi-region-write complexity for the genuinely global
  subset.

## Distributed Locks (Zookeeper / etcd)

- Built on top of the consensus mechanisms above — a distributed lock service uses Raft
  (etcd) or a Paxos-derived protocol (Zookeeper, via ZAB) internally to guarantee only one
  client holds a given lock at a time, even as nodes fail.
- **The failure mode worth naming explicitly**: a lock with a lease/TTL can expire while
  the client that holds it is still "working" (a long GC pause, a network partition) —
  the client may not realize its lock has expired and continue acting as if it still holds
  exclusive access. Mitigation: a **fencing token** — a monotonically increasing number
  issued with each lock acquisition, which downstream resources check and reject any
  request bearing an older token than one already seen. This closes the gap that a naive
  "check if you still hold the lock" client-side check cannot.

## Practice Questions

- Design a distributed lock service from scratch — walk through your consensus choice and
  justify it.
- Design a system where regions need to serve local writes with low latency but eventually
  reconcile a shared global counter — what's your conflict-resolution strategy?
- A payment operation spans three services. Walk through designing it as a Saga, including
  every compensating action.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **When-not-if framing (the default for consensus/coordination questions):** "Consensus is
  expensive — every write needs majority acknowledgment. The staff-level judgment call
  isn't knowing Raft, it's recognizing that most of a system doesn't need it at all; you
  want consensus at one small, critical coordination point, not everywhere."
- **Restated-trade-off framing (good for 2PC vs. Saga):** "I'd frame the 2PC-versus-Saga
  choice as consistency versus availability during partial failure, restated at the
  application level — resolved by asking whether the operation can tolerate a visible,
  temporary inconsistent state if it's provably going to resolve."
- **Representability framing (good for CRDTs specifically):** "The actual skill isn't
  knowing what a CRDT is, it's recognizing which part of a data model is CRDT-representable
  — counters, presence indicators — versus which part fundamentally needs coordination,
  like a money transfer that isn't commutative."

### Vocabulary Builder

- **causally precedes** (v. phrase) — one event happened strictly before another in a way
  every observer would agree on, as opposed to two concurrent events with no inherent
  order.
- **compensating action** (n. phrase) — the explicit undo step for one stage of a Saga,
  used when a later stage fails.
- **commutative** (adj.) — an operation whose result doesn't depend on order; the
  mathematical property that makes a CRDT's merge conflict-free.
- **fencing token** (n. phrase) — a monotonically increasing number issued with a lock,
  letting downstream resources reject stale requests from a client that no longer actually
  holds the lock.
- **"…is a genuine organizational answer to a technical problem"** — a fluent template for
  arguing a piece of infrastructure (a service mesh) solves a people/process problem, not
  just a technical one.

---

**Previous:** [The Staff-Level Signal](../00_staff_level_signal/tutorial.md)  |  **Next:** [Design Twitter/X Feed (Distributed Systems Design track)](../02_design_twitter_feed/tutorial.md)

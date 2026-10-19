# Personal Concept Notes — Verified Study Log

Raw handwritten/verbal notes, transcribed as-is and checked against the canonical
[Prerequisite Concepts](00_prerequisite_concepts/) primer for the same topic. Kept in my own
phrasing on purpose — the point of this file is a fast personal-recall check before a mock
interview, not another polished explanation (that's what the linked Part already is). Each
entry: the note verbatim, a verdict, what it nails, and what the canonical doc covers that
the note doesn't yet.

## CAP Theorem

**My note, verbatim:**

> CAP: (These are not features. They are promises your system makes under stress)
> 1. Consistency: linearizability, every read sees most recent write. "one brain one truth"
> 2. Availability (A): every request gets a non-error response (it can't say timeout, I'm
>    busy, system never says no to user) — measured in 9s
> 3. Partition tolerance (P): fancy word for network failure. System continues to operate
>    despite arbitrary number of messages being delayed or dropped. "Network will fail." CA
>    is a lie. Networks are bound to fail. So CAP theorem says when network fails (partition
>    happens) do you choose CP or AP? Means you must choose: 1. stop answering (CP), 2.
>    answer with old data (AP). That's the whole theorem. Truth over uptime, or uptime over
>    stale/old data.

**Verdict: accurate — no corrections needed on what's here.**

**What it nails:**
- C = linearizability, "every read sees most recent write" — exactly right, and matches the
  precise (not the sloppy) definition [Part 13](00_prerequisite_concepts/13_cap_theorem_and_pacelc.md#cap-theorem-precisely)
  uses.
- A = every request gets a non-error response, measured in nines — exactly right.
- P = arbitrary message loss/delay, not "handles it gracefully" — right, and "network will
  fail" is the correct instinct.
- **"CA is a lie" is the sharpest line in the note, and it's not just a phrase — it's the
  same argument [Part 13 cites from Daniel Abadi](00_prerequisite_concepts/13_cap_theorem_and_pacelc.md#why-partition-tolerance-is-a-genuinely-confusing-name):
  P isn't a free variable traded against C and A like "pick 2 of 3" implies — it's a
  precondition, because partitions are a physical inevitability, not a preference. The real
  choice CAP forces is CP vs. AP, made specifically *during* a partition — which is exactly
  what the note says.

**What's not in the note yet — the actual gap to close:**
- **PACELC**, [Part 13's second half](00_prerequisite_concepts/13_cap_theorem_and_pacelc.md#pacelc-naming-the-trade-off-cap-leaves-out).
  CAP only describes the rare moment — *during* a partition. PACELC names the trade-off that
  applies the rest of the time, with a perfectly healthy network: does a read/write wait for
  replica confirmation (safer, slower — pays for consistency in latency) or return
  immediately (faster, riskier)? This is paid on *every single request*, not just during a
  rare partition — which is why Part 13 argues a system's PACELC classification says more
  about its actual daily behavior than its CAP classification does.
- Worth memorizing cold before a mock interview: **PA/EL** (Dynamo, Cassandra — availability
  during a partition, latency the rest of the time) and **PC/EC** (BigTable, MongoDB
  default, Spanner, CockroachDB — consistency both times) are the two combinations that show
  up in practice.

## Why Partition Tolerance Is Physically Inevitable

**My note, verbatim:**

> Partitions are inevitable. Why? You can not outrun speed of light. 1. Signal flow: node
> communication. Say for example Java GC got triggered, network is full, packet got
> delayed. Say node A sends a message and waited for 500ms — what happened? Network cut?
> Node B dead/crashed? Node B slow (GC pause, busy CPU). Node A can't know! From perspective
> of A, slow == dead. This is unavoidable!

**Verdict: accurate, and this is a real, formally named result — not just a good intuition.**
This is a direct, correct rediscovery of what distributed-systems theory calls the
**FLP impossibility result** (Fischer, Lynch, Paterson, 1985) and, more practically, the
**unreliable failure detector** problem (Chandra & Toueg): in an asynchronous network — one
with no upper bound on message delay — no algorithm can reliably distinguish a crashed node
from one that is merely slow. This isn't covered as its own named concept anywhere else in
this repo yet (Part 6 covers the speed-of-light latency floor itself; Part 13 covers CAP's
consequence of it), so this note fills a real gap rather than duplicating something already
written elsewhere.

**Rephrased, since parts of the original are terse shorthand:** A message from Node A to
Node B takes *at least* the speed-of-light travel time to arrive — a hard physical floor,
not a tuning problem ([Part 6](00_prerequisite_concepts/06_mechanical_sympathy_and_physics_of_latency.md#hardware-reality-the-abstraction-hides-the-physics-not-the-cost)).
On top of that floor, real delay is added by things that have nothing to do with the network
itself — a Java GC pause on Node B, Node B's CPU being saturated by an unrelated process, a
switch queueing packets under load. When Node A sends a request and sets a timeout, and that
timeout fires, **all Node A actually knows is "no response arrived by T=500ms."** It has no
way to distinguish between three completely different underlying causes, because all three
produce the exact same observable symptom — silence:

```
Node A                                          Node B
  |----- request, t = 0ms ------------------->     |  (unreachable? crashed? just slow?)
  |                                                  |
  |            ... 500ms of silence ...              |
  |                                                  |
  |----- timeout fires, t = 500ms                    |

Node A's only observation: "no response by 500ms."
Three physically different causes, one identical symptom:
  1. Network partition   — the request or the ack was lost/delayed in transit
  2. Node B crashed       — the process is dead and will never respond
  3. Node B is just slow  — GC pause / CPU starvation / disk stall; it WILL
                             respond, just late

From Node A's side, these three are indistinguishable. slow == dead == partitioned.
```

**Why this matters, concretely, one level deeper than the note already goes:** this is the
actual mechanism *underneath* [Part 13's claim that P isn't optional](00_prerequisite_concepts/13_cap_theorem_and_pacelc.md#cap-theorem-precisely) —
partition tolerance isn't a design choice a system opts into, because *the system has no way
to even detect, with certainty, that a partition (rather than a slow node) is what's
happening in the first place*. Every timeout-based failure detector (the mechanism behind
health checks in [Part 19](00_prerequisite_concepts/19_load_balancing.md#health-checks-how-a-load-balancer-knows-a-server-is-actually-healthy),
heartbeats in [Part 20's service discovery](00_prerequisite_concepts/20_microservices_architecture_patterns.md#service-discovery-how-a-service-finds-another-service-whose-address-keeps-changing),
and quorum timeouts in Raft/Paxos) is a **heuristic, not a guarantee** — it trades accuracy
for liveness by picking a timeout value and accepting that it will occasionally misclassify
a slow node as dead (a false positive) or wait too long on a truly dead one (a false
negative). Tightening the timeout doesn't remove the ambiguity, it just moves where the
system chooses to err.

**Worth being able to say out loud in an interview:** "A timeout doesn't detect a failure —
it detects an absence of response, and then the system *decides* to treat that absence as a
failure. Making that decision is unavoidable because there is no way, from one side of an
asynchronous network, to distinguish 'the other side is dead' from 'the other side is just
slow' — that's the FLP result, and it's the actual reason partition tolerance can't be
opted out of."

## CP in the Real World — Who Actually Chooses It

**My note, verbatim:**

> CAP is law not suggestion. Consistency and partition tolerance — who chooses this? Banks,
> stock markets, inventory sync.

**Verdict: two out of three are right; the third is actually the textbook AP example, not
CP — worth correcting now, because the mistake reveals the wrong decision rule
("money-related = CP") instead of the right one.**

- **"CAP is law not suggestion"** — correct, and it's the same point [Part 13
  already establishes](00_prerequisite_concepts/13_cap_theorem_and_pacelc.md#cap-theorem-precisely):
  P isn't optional, so during an actual partition a system is *forced* into CP or AP whether
  it planned to be or not. Nobody "chooses" CAP itself; they choose which failure mode they'd
  rather have when the law kicks in.
- **Banks** — correct, a clean CP example. A financial ledger cannot serve a balance that
  might be wrong; the [worked table in Part
  11](00_prerequisite_concepts/11_taxonomy_of_storage_choice.md) names this exact case: "a
  financial ledger cannot tolerate a partially-applied transfer — it needs strong
  consistency and ACID, full stop." Refusing to answer (CP) is cheaper than answering wrong.
- **Stock markets** — correct, but with a real nuance worth being able to state: the *trade
  ledger / matching engine* (who owns what, what price a trade executed at) is CP — an
  exchange will **halt trading entirely** (a circuit breaker, literal unavailability) rather
  than risk two people believing they bought the same share. But *market data distribution*
  (streaming quotes/prices to viewers) is usually AP — a slightly stale quote shown to a
  viewer is a UI problem, not a correctness violation, so that side optimizes for
  availability and low latency instead. One system, two different CAP choices for two
  different pieces of data — worth naming both halves rather than treating "stock market" as
  one monolithic answer.
- **Inventory sync — this is actually the classic textbook *AP* example, not CP.** [Part
  13's own AP example is literally
  this](00_prerequisite_concepts/13_cap_theorem_and_pacelc.md#cap-theorem-precisely): "Dynamo
  and Cassandra choose A during a partition... a shopping cart has to accept a write even
  mid-partition." Amazon's own motivation for building Dynamo in the first place was that
  **refusing to let someone add an item to their cart (or complete a purchase) because of a
  network blip costs a guaranteed lost sale — a worse outcome than occasionally overselling
  a unit of inventory and fixing it afterward** (cancel, refund, backorder, apologize).
  Most real e-commerce inventory systems accept this trade deliberately.

**The actual decision rule your note is reaching for, stated precisely** (this is the
generalizable takeaway, not "money = CP"): **ask which failure is more expensive — refusing
the request, or being wrong and fixing it later.** A wrong bank balance can't be un-said
gracefully → CP. A missed sale is gone forever the moment you say "no" → AP, reconcile after.
The one place this flips back to CP even in a retail/inventory context is a **provably
scarce, non-fungible resource** — this repo's own [Ticket / Event Booking
case study](../system_design_practice/15_design_ticket_booking_system/tutorial.md) is exactly
that: you cannot "reconcile" two people who both believe they own the same physical seat the
way you can reconcile an oversold generic SKU, so that system deliberately reaches for strong
isolation and reservation TTLs instead of Dynamo-style AP.

## How CP Is Actually Built — Locking, Consensus, and What Else

**My note, verbatim:**

> To build CP we usually use distributed locking, consensus algorithm like Raft, and
> mention another.

**Verdict: both correct, but they're not two independent items on a list — locking is built
*on top of* consensus, not a separate mechanism next to it. Naming that relationship is
worth more than naming a third technique alone.**

- **Consensus (Raft/Paxos)** — correct, and it's the actual foundation. [The Distributed
  Systems Foundations
  tutorial](../system_design_practice/01_distributed_systems_foundations/tutorial.md#consensus-making-multiple-nodes-agree-on-one-truth)
  frames it precisely: multiple nodes agree on one value (who's leader, what's the next log
  entry) even with crashes and delayed messages — which, worth connecting back to the
  previous note, is provably impossible to solve *perfectly* in an asynchronous network
  (the same FLP result already in this file). Consensus algorithms don't defeat FLP, they
  make a specific, nameable trade-off around it (Raft: majority-quorum commit + randomized-
  timeout leader election).
- **Distributed locking — correct, but it's an *application* of consensus, not a second,
  independent technique.** [The same
  tutorial](../system_design_practice/01_distributed_systems_foundations/tutorial.md#distributed-locks-zookeeper--etcd)
  is explicit about this: a lock service (ZooKeeper, etcd) uses Raft or a Paxos-derived
  protocol (ZAB) *internally* to guarantee only one client holds a lock at a time. So the
  real mental model isn't "locking and consensus," it's **consensus is the primitive; a
  distributed lock is one specific thing you build with it** (others: leader election,
  config that must be agreed on cluster-wide).
- **The gotcha worth knowing cold, because it's exactly the kind of thing a naive answer
  misses:** a lock with a lease/TTL can expire while its holder is still "working" — a long
  GC pause or a partition (the same slow-vs-dead ambiguity from the earlier note) means the
  client may not even know its lock already expired, and keeps acting as if it still has
  exclusive access. The fix is a **fencing token** — a monotonically increasing number
  issued with each lock grant, checked by the downstream resource, which rejects any request
  carrying an older token than one it's already seen. Without this, "we use a distributed
  lock" is not actually a correctness guarantee by itself.

**Two more real answers for "mention another," since the note asked for one and there are
a couple of genuinely distinct options:**

1. **Two-Phase Commit (2PC)** — for when the thing that needs to stay consistent isn't "who
   holds a lock" but "did this multi-step operation across several services commit
   atomically." [Same
   tutorial](../system_design_practice/01_distributed_systems_foundations/tutorial.md#distributed-transactions-2pc-vs-saga):
   a coordinator asks every participant to prepare, and only commits once *all* confirm —
   correct, but the coordinator is a blocking single point of failure, which is exactly why
   it's a CP mechanism (it will hang/block — sacrifice availability — rather than risk a
   partial commit).
2. **Synchronous quorum replication** — a write isn't acknowledged to the client until a
   majority of replicas confirm it, the same majority-overlap guarantee consensus uses,
   applied directly to data replication instead of to agreeing on a leader/log. This is the
   mechanism underneath why Spanner/CockroachDB pay a real latency floor even when nothing
   is failing (already flagged in this file's PACELC gap, above) — a write physically cannot
   commit faster than the round trip to a quorum of replicas.

**The one-line version worth having ready:** *"CP systems are built from one real primitive
— consensus — used three ways: directly for leader election/coordination, wrapped as a
distributed lock service with fencing tokens to stay safe under partition, or applied to
data replication itself as a synchronous quorum write."*

## AP in the Real World — Social Media

**My note, verbatim:**

> AP side: usually social media.

**Verdict: correct, and it's the cleanest possible application of the decision rule from
the earlier CP note — worth stating *why*, not just filing it as a fact.**

- **Rephrased using the same rule already established above** ("which failure is more
  expensive — refusing the request, or being wrong and fixing it later"): a like count that's
  off by a few, a feed that shows a post to one user a second before another, a follower
  count that briefly lags — none of that is user-visible harm. Refusing to load the feed, or
  refusing to let someone post, *because* one datacenter can't currently reach another, is a
  far worse outcome for a product whose entire value is "always there, always scrolling."
  This is the exact same reasoning [Part 11 already gives for a like-counter
  specifically](00_prerequisite_concepts/11_taxonomy_of_storage_choice.md#4-consistency-model--what-does-correct-mean-for-this-data):
  "a social media like-counter can be wrong for a few seconds with zero user-visible harm —
  eventual consistency isn't a compromise there, it's the objectively correct choice."
- **Same shape as the Dynamo/Cassandra AP example already in this file's CAP entry**: huge
  write volume, near-random keys (every user posting/liking independently), must always
  accept a write even mid-partition — the identical profile Part 13 gives for why
  Dynamo/Cassandra choose PA/EL.

**The nuance worth adding, same pattern as the stock-market split earlier — "social media" is
not one monolithic CAP answer either:**

| Slice of the same platform | CAP choice | Why |
|---|---|---|
| Likes, views, feed ranking, follower counts | AP | Wrong-for-a-moment is invisible; unavailable is not |
| Auth (login, session tokens, password reset) | CP | A stale "you're logged in" or a race on password reset is a real security bug, not a UX nit |
| Payments / ad billing / creator payouts | CP | Same reasoning as the bank note — a partially-applied charge can't be un-said |
| Direct messages (per-conversation ordering) | Somewhere between | Doesn't need full linearizability, but two messages in one conversation showing up out of order is a real, noticeable bug — this is what [Part 18's partition-key ordering guarantee](00_prerequisite_concepts/18_message_queues_and_event_driven_semantics.md#ordering-what-a-partition-actually-buys-you) exists for: order *within* a conversation, not globally |

**The one-line version worth having ready:** *"I wouldn't call the whole platform AP — I'd
say the engagement surface (likes, feeds, counters) is AP because staleness is invisible and
downtime isn't, while auth and billing on the same platform are CP for the same reason a
bank is, and messaging sits in between because it needs ordering without needing full
consistency."*

## CP vs. AP — Short Reference

| | **CP** | **AP** |
|---|---|---|
| During a partition | Stops answering (on the minority/unreachable side) | Keeps answering, possibly with stale data |
| Guarantees | Linearizability — every read is the latest write | Only that you get *a* response, not the latest one |
| Fails toward | Correctness over uptime | Uptime over freshness |
| Built with | Consensus (Raft/Paxos), locks + fencing tokens, 2PC, sync quorum writes | Gossip, async replication, vector clocks / last-write-wins, tunable quorum |
| Real examples | Bank ledgers, trade matching engines, auth/billing, ticket/seat reservations | Social feeds/likes, shopping carts, DNS, most CDNs |
| Reference systems | ZooKeeper, etcd, Spanner, CockroachDB | Dynamo, Cassandra |
| PACELC "else" (no partition) | Usually still pays latency for consistency (EC) | Usually optimizes for speed (EL) |
| Pick when | Being wrong can't be undone (money, a seat, a lock) | Being unavailable is the worse failure (a lost sale, a stale like count) |

## PACELC Decision Tree + The Consistency Spectrum

**Verdict: accurate throughout — no corrections needed on mechanics or examples. One real
find: "monotonic reads" wasn't in the canonical spectrum table, so I added it there
directly** ([Part 2](00_prerequisite_concepts/02_data_and_consistency.md#the-consistency-spectrum-its-not-just-strong-vs-eventual)) —
that's a genuine gap you caught, not just a personal-notes addition.

### PACELC, condensed

- CAP only covers the rare case (partition). PACELC covers the rest: **P**artition → A vs C.
  **E**lse (normal operation, network healthy) → L vs C. [Part
  13](00_prerequisite_concepts/13_cap_theorem_and_pacelc.md#pacelc-naming-the-trade-off-cap-leaves-out).
- The "else" choice is made on *every* request, not just during rare partitions — this is
  why PACELC classification matters more than CAP classification for daily behavior.

| | Mechanism | Cost |
|---|---|---|
| **Sync (C > L)** | Primary waits for replica(s) to confirm before telling the client "success" | Slower, but a replica always has what the client was told was saved |
| **Async (L > C)** | Primary saves locally, tells client "success" immediately, replicates in background | Fast, but data written between "success" and replication is lost if the primary dies |

- **Dynamo / Cassandra** → PA/EL (available during partition, fast normally).
- **Spanner, CockroachDB, MongoDB (default)** → PC/EC (consistent both times, pays latency
  for it always).
- **PostgreSQL with synchronous replication specifically** → PC/EC, same reasoning — but
  worth the precision: a single, non-replicated Postgres instance isn't a distributed system
  at all ([Part 13's own scoping point](00_prerequisite_concepts/13_cap_theorem_and_pacelc.md#cap-theorem-precisely):
  CAP/PACELC only apply once a second node holding the same data exists), and Postgres with
  the *default async* replication would actually be PA/EL-shaped instead — the classification
  depends on the replication mode configured, not on "Postgres" as a name.

### The Consistency Spectrum, condensed

Strongest → weakest, cost decreasing left to right:

**Strong (linearizability)** → **Causal** (effect never seen before its cause) → **Monotonic
reads** (never see an older value after a newer one — no "time travel") + **Read-your-writes**
(you always see your own latest write) → **Eventual** (converges given enough time, no
ordering promise in between).

Full definitions + examples: [Part 2's spectrum
table](00_prerequisite_concepts/02_data_and_consistency.md#the-consistency-spectrum-its-not-just-strong-vs-eventual) —
not re-deriving it here since your examples for each (Twitter bio for read-your-writes, the
question-before-answer example for causal, the score-going-backward example for monotonic
reads) all matched the canonical ones almost exactly.

### The engineering wisdom line — this is the actual takeaway to keep

**Find the weakest consistency model your business can tolerate, and stop there.** Weaker =
higher performance, lower cost, better scalability. Every level of consistency stronger than
what a specific piece of data actually needs is a cost paid for nothing — the same "don't pay
for consistency you don't need" framing as [Part 11's consistency
axis](00_prerequisite_concepts/11_taxonomy_of_storage_choice.md#4-consistency-model--what-does-correct-mean-for-this-data)
and this file's own social-media entry above, generalized into one rule.

---

*Add new entries above this line, most recent first or last — whichever stays easiest to
scan. Each entry: raw note verbatim, verdict, what it nails, what the canonical Part covers
that the note doesn't yet.*

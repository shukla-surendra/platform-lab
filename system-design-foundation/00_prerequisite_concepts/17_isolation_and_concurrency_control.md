# Prerequisite Concepts, Part 17: Isolation Levels & Concurrency Control — What Actually Happens When Two Transactions Run at Once

[Part 11's "ACID, Fully Unpacked"](11_taxonomy_of_storage_choice.md#acid-fully-unpacked)
named Isolation as "concurrent transactions behave as if run one at a time, even while
physically interleaved, enforced via locking (two-phase locking) or MVCC" and moved on —
that one sentence is doing a lot of work. This part unpacks it: what specifically goes
wrong when transactions interleave, the precise ladder of guarantees a database can offer
about it, and the two families of mechanism (locking and MVCC) that actually deliver each
guarantee. This is a different problem from [Part 13's CAP
theorem](13_cap_theorem_and_pacelc.md), which is about replicas agreeing across a network —
everything here can happen on a single machine, with a single copy of the data, the moment
more than one transaction touches it at the same time. It's also different from [Part
01's 2PC vs. Saga](../../system_design_practice/01_distributed_systems_foundations/tutorial.md#distributed-transactions-2pc-vs-saga),
which is about one logical operation spanning *multiple* databases — this part is about
what "one database, several transactions, same instant" actually requires.

## In Plain English

Imagine two roommates splitting a shared grocery fund tracked in a notes app. Roommate A
opens the app, sees $100, and starts typing "spent $20 on milk → $80 left." At the exact
same moment, Roommate B opens the same app, also sees $100 (A hasn't saved yet), and types
"spent $30 on eggs → $70 left." Whoever saves last wins — and the fund now shows $70 or
$80, silently losing whichever spend happened first. Nobody made a mistake; the problem is
that both roommates read the *same* starting number and neither knew the other was mid-edit.
A database has this exact problem, constantly, at a scale of thousands of "roommates" a
second — isolation is the set of rules for exactly how much of that interleaving a database
will let you see, and concurrency control is the actual machinery that enforces those rules.

## The Problem, Precisely

A **transaction** is a unit of work meant to appear atomic to everything outside it. But
underneath, a database runs many transactions concurrently for throughput — true one-at-a-
time execution would waste every CPU core and disk queue depth [Part
7](07_saturation_amdahls_law_and_hedged_requests.md) already established matters. The
question isolation answers is: when transaction A and transaction B are physically
interleaved on the same data, what is A allowed to see of B's in-progress, not-yet-committed
work — and what happens if they touch the same row at the same time? Get the answer too
loose and you get silent data corruption (the lost grocery update above); get it too strict
and every transaction effectively waits behind every other one, destroying the concurrency
you built the system for in the first place. Isolation levels are where a database lets you
choose a specific point on that spectrum, deliberately, instead of getting stuck with
whichever end the engine happened to default to.

## The Anomalies: What Isolation Levels Are Actually Named After

Each isolation level is defined by which of these race conditions it rules out. Naming them
precisely first is what makes the isolation-level table below legible instead of a list of
memorized words.

- **Dirty read** — transaction A reads a row that transaction B has modified but not yet
  committed. If B then rolls back, A has now acted on data that officially never existed.
- **Non-repeatable read** — transaction A reads the same row twice within one transaction
  and gets two different values, because transaction B committed a change to that row in
  between A's two reads. A's own transaction is no longer internally consistent with itself.
- **Phantom read** — transaction A runs the same *query* (not the same row) twice, and the
  second run returns rows that weren't there the first time, because transaction B inserted
  a new row matching A's filter in between. Subtly different from a non-repeatable
  read — it's about a changing *result set*, not a changing single row.
- **Lost update** — the roommate scenario above, formalized: A and B both read the same
  row, both compute a new value from what they read, and whichever writes last silently
  overwrites the other's change instead of both being applied.
- **Write skew** — the subtle one: A and B read *different* rows that share an invariant
  (e.g., "at least one doctor must be on call," backed by two separate doctor rows), each
  independently makes a change that's individually valid, and the *combination* violates
  the invariant (both doctors go off call) even though neither transaction wrote a row the
  other one touched. This one survives even snapshot isolation, which is precisely why it's
  the anomaly that separates "strong-sounding" from genuinely serializable.

## The Isolation Levels, Precisely

The SQL standard defines four levels as a ladder — each one rules out strictly more
anomalies than the one below it, at the cost of more coordination (locking, blocking, or
abort-and-retry) between concurrent transactions:

| Isolation Level | Dirty Read | Non-Repeatable Read | Phantom Read | Write Skew |
|---|---|---|---|---|
| Read Uncommitted | Possible | Possible | Possible | Possible |
| Read Committed | Prevented | Possible | Possible | Possible |
| Repeatable Read | Prevented | Prevented | Possible (standard) / Prevented (Postgres) | Possible |
| Serializable | Prevented | Prevented | Prevented | Prevented |

**Read Uncommitted** is rare in production — it means literally reading another
transaction's in-flight, possibly-about-to-be-rolled-back writes; a few analytics engines
allow it deliberately for "approximate is fine, don't block writers" dashboards.
**Read Committed** is the practical default (Postgres, Oracle, SQL Server all default here)
— you never see another transaction's uncommitted work, but you can see different committed
values across two reads in the same transaction. **Repeatable Read** locks in a consistent
view for the duration of the transaction; the SQL standard still technically permits
phantoms at this level, but Postgres's implementation (via MVCC snapshotting, below) happens
to prevent them too — a detail worth knowing precisely, because "Repeatable Read" doesn't
mean the same guarantee on every database. **Serializable** is the only level that
guarantees the result is *equivalent* to some one-at-a-time ordering of all transactions,
full stop — including ruling out write skew, which is why it's the only level a genuinely
safety-critical invariant (double-booking, double-spending) should be built on.

## How Isolation Is Actually Implemented: Two Families of Mechanism

### Pessimistic: Two-Phase Locking (2PL)

**The idea**: assume conflicts are likely, so prevent them upfront. A transaction acquires a
**shared lock** before reading a row (multiple readers can hold a shared lock at once) and
an **exclusive lock** before writing one (only one transaction can hold it, and it blocks
readers too). "Two-phase" names the discipline: a *growing phase* where the transaction only
acquires locks, followed by a *shrinking phase* where it only releases them — never
interleaving acquire and release — which is the specific rule that makes the resulting
schedule provably serializable. In practice, production databases use **strict 2PL**: hold
every lock until commit or rollback, rather than releasing early, which avoids a subtler
anomaly (cascading rollbacks) the plain version allows.

**Deadlocks are the direct cost of pessimistic locking**: transaction A holds a lock B
wants, and B holds a lock A wants — both wait forever unless something intervenes. Databases
handle this one of two ways: **detection** (periodically build a wait-for graph of who's
blocked on whom; a cycle means deadlock, and the engine kills one transaction — the
"victim" — to break it) or **prevention** (a convention like "always acquire locks in a
fixed global order," e.g. always lock the lower account ID first in a transfer, which makes
a cycle structurally impossible). Detection is what most databases actually ship with;
prevention is a discipline applications sometimes adopt on top for hot, well-known
contention paths.

### Optimistic: Optimistic Concurrency Control (OCC)

**The idea**: assume conflicts are rare, so don't pay locking's cost upfront — read and
compute freely, then check for a conflict only at commit time. Concretely: read a row along
with its version number (or a timestamp), do the work, and on commit, check whether that
version number has changed since the read. If it hasn't, commit succeeds and the version
increments. If it has — someone else committed a conflicting write in the meantime — the
transaction aborts and retries from scratch.

OCC trades locking overhead for retry overhead, which makes it a genuinely different tool
for a genuinely different workload shape: it wins decisively under **low contention** (few
transactions actually fight over the same row, so retries are rare and you've avoided
locking cost on every single one), and loses badly under **high contention** (many
transactions collide on the same hot row, and they spend more time re-doing aborted work
than 2PL would have spent just making them wait their turn). This is the same shape of
trade-off as [Part 7's hedged
requests](07_saturation_amdahls_law_and_hedged_requests.md#hedged-requests-buying-a-100x-tail-latency-reduction-with-5-more-traffic) — a strategy
that's free-to-cheap when the bad case is rare, and actively harmful once the bad case
becomes common.

### MVCC: What Postgres and MySQL Actually Do

**Multi-Version Concurrency Control** is the mechanism behind Part 11's one-line mention,
and it's the default in both Postgres and MySQL/InnoDB, precisely because it sidesteps a
cost both locking families share: readers and writers blocking each other at all.

**The mechanism**: instead of one copy of a row, the engine keeps *multiple versions* of it,
each tagged with the transaction ID (or timestamp) that created it. When a transaction
starts, it gets a **snapshot** — a definition of "which versions of every row count as
visible to me," fixed at that instant. A reader never blocks a writer and a writer never
blocks a reader, because a write simply creates a new version rather than modifying the one
a concurrent reader is looking at; the reader keeps seeing its own consistent snapshot
throughout. Write-write conflicts (two transactions both trying to create the next version
of the *same* row) still need resolution — Postgres aborts the second committer with a
serialization failure it must retry, which is OCC's abort-and-retry logic, reappearing here
as the write-path half of MVCC.

Old row versions aren't free — they accumulate until nothing could possibly still need them,
which is exactly what Postgres's **VACUUM** process reclaims (and what MySQL's InnoDB
purge thread does): a maintenance cost that is the direct, physical price of readers never
blocking, the same "nothing is free, it's moved somewhere else" pattern [Part 6's storage
hierarchy](06_mechanical_sympathy_and_physics_of_latency.md#the-economics-of-machine-cost-is-physics)
already established for speed-vs-cost trade-offs generally.

**Why plain MVCC still allows write skew**: snapshot isolation, on its own, only checks
whether the exact row a transaction *wrote* changed underneath it — it never validates the
rows a transaction only *read* to decide whether to write. The doctors-on-call example
above passes a plain MVCC check cleanly, because neither transaction's write conflicts with
the other's write. Fixing this requires **Serializable Snapshot Isolation (SSI)** — Postgres's
actual `SERIALIZABLE` level — which additionally tracks read-write dependencies between
concurrent transactions (a form of predicate locking) and aborts one of them if committing
both would produce a result no serial ordering could have produced.

## Real Tools, Modern Defaults

**PostgreSQL**: MVCC by default; `READ COMMITTED` is the engine default, `REPEATABLE READ`
and `SERIALIZABLE` (true SSI, write-skew-safe) are opt-in per transaction. **MySQL/InnoDB**:
MVCC plus **next-key locking** (a range lock combining a row lock with a gap lock) at its
default `REPEATABLE READ`, specifically to close the phantom-read gap the SQL standard
otherwise allows at that level. **CockroachDB and Google Spanner**: serializable by
*default*, not opt-in — built on MVCC plus a global ordering source (Spanner's TrueTime
atomic clocks; CockroachDB's hybrid logical clocks) so serializability holds even across a
geographically distributed cluster, not just one machine. **DynamoDB transactions**: OCC-based
— a conditional-write / version-check primitive under the hood, the same mechanism this part
just unpacked, exposed as an API rather than a SQL isolation-level knob. **SQLite**: single-
writer, MVCC-backed since WAL mode, sidesteps most of this by simply serializing all writes
through one connection at a time.

## Designing and Operating From First Principles

1. Have I picked an isolation level deliberately for this specific transaction's actual
   correctness requirement, or am I just running at whatever the database's default happens
   to be?
2. If this workload has genuinely high contention on a hot row, have I reached for
   pessimistic locking (2PL) instead of OCC's default-friendly retry loop — or am I paying
   OCC's worst case without realizing it?
3. Does this transaction read rows only to decide whether to write a *different* row (the
   write-skew shape)? If so, is `REPEATABLE READ` actually enough, or do I need true
   `SERIALIZABLE`/SSI?
4. Have I named, explicitly, what happens on a deadlock or a serialization-failure abort in
   this code path — is there an actual retry loop, or does the transaction just fail silently
   the first time it collides with another one?
5. Am I aware of what MVCC's version accumulation costs operationally here — has this table's
   vacuum/purge cadence actually been tuned, or is it running on whatever the default
   schedule ships with under this write volume?

## Key Takeaways

- **Isolation is a spectrum of named anomalies, not a single on/off guarantee** — dirty
  read, non-repeatable read, phantom read, lost update, and write skew are each a distinct
  failure mode, and each isolation level is defined by exactly which subset it rules out.
- **Write skew is the anomaly that separates "sounds strong" from actually serializable** —
  it survives plain snapshot isolation (MVCC alone) because it involves each transaction
  writing a *different* row while violating a shared invariant; only true `SERIALIZABLE`/SSI
  catches it.
- **Two families of mechanism deliver isolation**: pessimistic locking (2PL — prevent
  conflicts upfront, pay in blocking and deadlocks) and optimistic concurrency control
  (OCC — allow conflicts, detect and retry at commit, wins under low contention and loses
  under high contention).
- **MVCC is why readers and writers don't block each other** in Postgres/MySQL — multiple
  row versions plus a per-transaction snapshot, at the ongoing operational cost of vacuuming
  old versions.
- **"Repeatable Read" isn't one guarantee across databases** — the SQL standard permits
  phantoms at that level, but Postgres's MVCC-based implementation happens to prevent them
  and MySQL's next-key locking closes the gap a different way; the name alone doesn't tell
  you which anomalies are actually ruled out.

## Quick Self-Check

- Walk through the grocery-fund roommate example as a lost update, then explain precisely
  what isolation level and mechanism would have prevented it.
- Explain why write skew survives snapshot isolation (plain MVCC) but not Serializable
  Snapshot Isolation — what does SSI track that plain MVCC doesn't?
- Given a workload description, argue whether pessimistic locking or OCC is the better fit
  — what specifically about contention level drives that answer?
- Why does MVCC mean a reader never blocks a writer — what is a "snapshot" actually holding
  onto that makes this true, and what does that cost operationally over time?
- Explain the difference between deadlock detection and deadlock prevention, and why most
  production databases ship with detection rather than prevention.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Anomaly-first framing (the default for 'what isolation level would you use' questions):**
  "I'd start from which anomaly actually threatens this specific invariant — a lost update,
  a phantom, or write skew — rather than naming an isolation level from memory, since the
  right level is just whichever one rules out the anomaly that's actually possible here."
- **Contention framing (good for a 'locking vs. optimistic' follow-up):** "I'd pick based on
  contention, not preference — pessimistic locking when many transactions genuinely fight
  over the same row, optimistic concurrency control when conflicts are rare and I'd rather
  pay an occasional retry than block every transaction upfront."
- **MVCC framing (good for demonstrating you know the actual mechanism, not just the term):**
  "Postgres doesn't block a reader against a writer at all — it keeps multiple row versions
  and hands each transaction a consistent snapshot, so the real cost isn't blocking, it's the
  vacuum work to reclaim old versions later. That's worth naming explicitly instead of just
  saying 'MVCC' and moving on."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **dirty read / non-repeatable read / phantom read** (n. phrases) — three distinct
  anomalies from reading another transaction's uncommitted work, an already-committed
  change, or a newly-inserted row respectively.
- **write skew** (n. phrase) — two transactions each write a different row, individually
  valid, whose combination violates a shared invariant neither transaction's write directly
  touched; survives snapshot isolation, caught only by true serializability.
- **two-phase locking (2PL)** (n. phrase) — a growing phase that only acquires locks
  followed by a shrinking phase that only releases them; the discipline that makes locked
  execution provably serializable.
- **optimistic concurrency control (OCC)** (n. phrase) — read and compute without locking,
  validate against a version/timestamp at commit, abort and retry on conflict.
- **MVCC (multi-version concurrency control)** (n., initialism) — keeping multiple versions
  of a row so readers see a consistent snapshot without ever blocking a writer.
- **serializable snapshot isolation (SSI)** (n. phrase) — MVCC plus read-write dependency
  tracking, Postgres's actual `SERIALIZABLE` level; the mechanism that closes the write-skew
  gap plain MVCC leaves open.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…the same starting number, and neither one knew"** — a plain-language way to describe a
  lost update without needing to define isolation levels first.
- **"…sounds strong, but write skew still gets through"** — a fluent way to push back on an
  answer that stops at "we use snapshot isolation" as if that alone were sufficient.
- **"…paid in blocking, or paid in retries"** — a compact way to frame the 2PL-vs-OCC choice
  as a cost trade-off rather than one being categorically better.

---

**Previous:** [Part 16: Observability — Metrics, Logs, and Traces](16_observability.md)  |  **Next:** [Part 18: Message Queues & Event-Driven Semantics](18_message_queues_and_event_driven_semantics.md)

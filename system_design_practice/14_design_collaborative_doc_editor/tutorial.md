# Design a Collaborative Document Editor (Google Docs)

**Primarily tests**: real-time conflict-free merging under true concurrent editing — the one
case study in this track that puts [Part 01's
CRDTs](../01_distributed_systems_foundations/tutorial.md#crdts-vector-clocks-resolving-conflicts-without-coordination)
to direct use, contrasted against the historically dominant alternative (Operational
Transformation) this track hasn't covered elsewhere — plus event sourcing applied to a
document's own edit history.

## Clarify

- Rich text (formatting, embedded images) or plain text? Rich text has a much larger
  operation space to merge correctly.
- Is offline editing with later reconnection required, or is this always-connected,
  real-time-only?
- Typical concurrent-editor count for one document — a handful of people, or hundreds of
  simultaneous viewers with occasional edits?

## High-Level Design

Presence/cursor updates and edits both need the server to push to clients unprompted — see
[Part 23's WebSockets
treatment](../../system_design_foundation/00_prerequisite_concepts/23_realtime_communication_long_polling_websockets_sse.md)
for why a persistent connection is required here rather than ordinary request/response.

```mermaid
flowchart TB
    ClientA["Client A\n(local edit buffer)"] <-->|WebSocket| DocServer["Document Server\n(owns this doc's live session)"]
    ClientB["Client B\n(local edit buffer)"] <-->|WebSocket| DocServer
    DocServer -->|append| EventLog[("Edit Event Log")]
    EventLog -->|periodic| Snapshot[("Document Snapshot")]
    DocServer -.->|presence/cursors\n(ephemeral)| ClientA
    DocServer -.->|presence/cursors\n(ephemeral)| ClientB
```

## Deep-Dive: Two Real Approaches to Merging Concurrent Edits

**Operational Transformation (OT)** — the historically dominant approach (Google Docs'
original mechanism): every edit is expressed as an operation ("insert 'x' at position 12"),
and when two operations arrive concurrently, the server **transforms** the second one against
the first before applying it (if someone inserted 3 characters before position 12 first, the
second operation's position shifts by 3). This requires a **central sequencing authority** —
one server that decides the order operations get applied in — which makes the algorithm
easier to reason about but means the document genuinely has one owner at a time, and offline
editing (transforming against operations you haven't seen yet) is hard to get right.

**CRDTs (Conflict-free Replicated Data Types)** — [the mechanism Part 01 already
covers](../01_distributed_systems_foundations/tutorial.md#crdts-vector-clocks-resolving-conflicts-without-coordination),
applied here directly: structure the document's own data (e.g., each character or block gets
a stable, globally unique position identifier) so that merging two divergent copies is
**commutative and associative by construction** — applying edits in any order, or merging
after an arbitrary offline period, always converges to the same result, with **no central
sequencing authority required at all**. This is what makes true offline editing and
peer-to-peer sync (no round-trip to a server before an edit is visible locally) practical —
Figma's real-time multiplayer canvas is the same mechanism applied to a design document
instead of text.

**The real trade-off, stated precisely**: OT is conceptually simpler and has decades of
production hardening, but couples correctness to a single sequencing server and struggles
with true offline support. CRDTs decouple from any central authority and merge cleanly
offline, at the cost of **metadata overhead that can outlive the content itself** — a CRDT
structure typically keeps a **tombstone** (a marker for deleted content, needed so a
concurrent edit near that deletion still merges correctly) for every deletion, which grows
the document's underlying data structure over time unless it's periodically compacted — a
direct structural cousin of [Part 17's MVCC version
accumulation](../../system_design_foundation/00_prerequisite_concepts/17_isolation_and_concurrency_control.md#mvcc-what-postgres-and-mysql-actually-do)
needing its own vacuum pass, here applied to a document's edit history instead of a
database row's versions.

## Deep-Dive: Presence Is a Different Consistency Class Than Content

Cursor positions and "who's currently viewing this doc" (**presence**) look like part of the
same real-time stream as actual content edits, but they have genuinely different correctness
requirements: losing a cursor-position update, or momentarily showing a slightly stale
collaborator list, is invisible and harmless; losing a content edit is not. Treating presence
as **ephemeral, best-effort state** — never durably persisted, never part of the CRDT/OT
merge logic, simply the latest value broadcast to connected clients — rather than routing it
through the same strict, durable path as document content is a deliberate, staff-level
distinction: not all state flowing through the same system needs the same guarantees.

## Deep-Dive: Persistence Is Event Sourcing, Applied to One Document

A document's edit history *is* [Part 20's event sourcing
pattern](../../system_design_foundation/00_prerequisite_concepts/20_microservices_architecture_patterns.md#event-sourcing-the-log-as-the-source-of-truth-applied-to-a-single-entity),
concretely: every edit is appended to an immutable event log, and the document's current
content is derived by replaying that log — which is exactly why version history and "restore
to an earlier point" are natural, close-to-free features of this design rather than a bolted-
on afterthought. Replaying the entire history on every document open doesn't scale past a
short document, so production systems **snapshot** periodically and replay only the edits
since the last snapshot on load — the identical checkpoint-then-replay-the-tail pattern
[Part 10 already established for WAL
recovery](../../system_design_foundation/00_prerequisite_concepts/10_physics_of_persistence.md#checkpointing-why-the-wal-doesnt-grow-forever),
recurring a third time at this layer.

## Trade-offs

| Decision | Option A | Option B | When to pick which |
|---|---|---|---|
| Merge mechanism | Operational Transformation | CRDT | CRDT when true offline editing or peer-to-peer sync matters; OT when a single always-connected sequencing server is an acceptable constraint and the simpler mental model is worth it |
| Presence delivery | Route through the same durable, ordered path as content | Separate, ephemeral, best-effort broadcast | Always separate — presence's looser correctness needs don't justify paying content's stricter guarantees |
| Document load | Replay the full edit history every time | Snapshot + replay only the tail | Snapshot for any document with meaningful edit history — full replay only works for short-lived or lightly-edited documents |

## Staff Altitude

A **senior** answer says "use operational transformation" or "use CRDTs" because one of them
is the more familiar name, without naming the actual trade-off between them.

A **staff** answer additionally: (1) names the *structural* difference — central sequencing
authority (OT) versus no authority required (CRDT) — and ties that directly to whether
offline editing is an actual requirement, rather than picking based on familiarity; (2)
explicitly separates presence from content as two different consistency classes instead of
routing both through one mechanism; and (3) names tombstone/metadata growth as a real,
ongoing operational cost of the CRDT choice, not a one-time implementation detail.

## Failure Modes to Raise Proactively

- **A client disconnects and reconnects** — it needs to catch up on every edit it missed,
  the same **replay-from-a-known-point** problem [Part 18's consumer offset
  model](../../system_design_foundation/00_prerequisite_concepts/18_message_queues_and_event_driven_semantics.md#consumer-groups-and-rebalancing)
  already solves for a message queue, applied here to one document's own edit stream.
- **The document server crashes with edits in its in-memory buffer not yet flushed to the
  event log** — exactly the durability gap [Part 10's write-ahead
  log](../../system_design_foundation/00_prerequisite_concepts/10_physics_of_persistence.md#the-write-ahead-log-making-durability-affordable)
  exists to close; an edit isn't safely acknowledged to the user until it's durably logged,
  not merely applied in memory.
- **Two document servers both believe they own the live session for the same document**
  (a split-brain during a deploy or network partition) — needs a single-owner mechanism per
  document, the same problem [Part 01's distributed
  locks](../01_distributed_systems_foundations/tutorial.md#distributed-locks-zookeeper-etcd)
  already names.

## Staff Follow-Ups

- "Scale this to 500 simultaneous connections on one document, most of them viewers with only
  a handful actually editing — does your design change?"
- "A user edits offline for two days, then reconnects — walk through exactly how their local
  changes merge with everything that happened on the server in the meantime."
- "Add comments and suggested edits as a feature — are they part of the same CRDT/OT merge
  stream as content, or a genuinely separate concern?"

## Practice Variations

- Design Figma's real-time multiplayer canvas specifically (the same CRDT mechanism applied
  to shapes/layers instead of text).
- Design a shared spreadsheet (cell-level conflicts are a different shape than character-level
  text conflicts — what changes?).
- Extend this design to support granular permissions (comment-only, view-only) enforced live,
  mid-session, without disconnecting the user.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Authority-first framing (the default for 'OT or CRDT'):** "The real question isn't which
  algorithm is better in the abstract — it's whether this product needs true offline editing.
  OT assumes a central sequencing server; CRDTs don't need one, which is what actually makes
  offline and peer-to-peer sync practical."
- **Consistency-class framing (good for a presence/cursor follow-up):** "I'd treat presence
  as a genuinely different consistency class from content — ephemeral, best-effort, never
  durably persisted — rather than routing cursor positions through the same strict merge
  pipeline as the document's actual text."
- **Operational-cost framing (good for demonstrating you know CRDTs aren't free):** "CRDTs
  solve the merge problem structurally, but they don't do it for free — I'd name tombstone
  accumulation as an ongoing cost that needs its own compaction pass, the same way an MVCC
  database needs vacuuming."

### Vocabulary Builder

- **Operational Transformation (OT)** (n. phrase) — merging concurrent edits by transforming
  one operation against another at a central sequencing server.
- **CRDT (Conflict-free Replicated Data Type)** (n. phrase, initialism) — a data structure
  designed so merges are commutative and associative by construction, requiring no central
  authority to converge correctly.
- **tombstone** (n.) — a retained marker for deleted content in a CRDT, needed so concurrent
  edits near that deletion still merge correctly; a real, growing storage cost.
- **presence** (n.) — ephemeral, best-effort collaborative state (cursors, who's viewing) with
  deliberately looser correctness requirements than document content.
- **"…no central authority required to converge"** — a precise, fluent way to state CRDTs'
  core structural advantage without needing to explain the underlying math first.

---

**Previous:** [13. Distributed File Storage](../13_design_distributed_file_storage/tutorial.md)  |  **Next:** [15. Ticket / Event Booking](../15_design_ticket_booking_system/tutorial.md)

# Prerequisite Concepts

First-principles system design primer, Parts 1-14. The goal of every doc here is to take a
reader from **complete beginner to principal-engineer depth on that one topic**, in a single
continuous doc — not a beginner doc and a separate advanced doc.

## Explanation shape: layman → principal, every time

Every concept must be introduced in **plain, jargon-free language first** — the kind of
explanation you'd give a smart friend with no engineering background — before any technical
term, formula, or mechanism appears. Only after that plain-English grounding is in place
does the doc build upward through the formal mechanism, the trade-offs, the real-world
systems that made this choice, and finally the principal-level nuance (what breaks it, what
it costs, when a senior engineer would reach for it versus when they wouldn't).

Concretely, that means:

- Open with the **problem** in relatable terms before naming the **mechanism** that solves
  it, before explaining **why it matters** at staff/principal depth — problem → mechanism →
  why it matters, never definition-first.
- Don't assume the reader already has the vocabulary a term requires. Define it in plain
  language the first time it's used in a doc, even if a prior part already defined it —
  point back to that part for depth, but don't require having read it to follow along here.
- An analogy (a group chat, a library with branches, a round table, a post office) earns its
  place whenever it makes an abstract mechanism concrete — see the "In Plain English"
  subsections already used in `02_data_and_consistency.md` (eventual consistency) as the
  worked example of this pattern.
- The doc should still end at genuine principal-engineer depth: precise definitions, the
  actual academic/industry source when one exists (Brewer, Gilbert & Lynch, Abadi, Dynamo,
  GFS, etc.), real production trade-offs, and the "Articulate It" interview-framing section
  every part already ends with.

## Analogies, real tools, and current trends — required, not decorative

Every mechanism gets a concrete analogy — not an occasional nice-to-have, an expected part
of introducing it. If a doc can't yet state the relatable, everyday version of a concept
(the DNS/branch-library/consistent-hashing-ring analogies already in this series are the
bar), that's a sign the explanation hasn't actually been thought through from first
principles yet, not a sign the concept is "too technical for an analogy."

Every mechanism also gets named, real, currently-relevant tooling — never left as pure
abstract theory. State *which actual systems* use a pattern (Cassandra, CockroachDB,
Kafka, etcd, Redis, Kubernetes, PostgreSQL/Citus, Pinecone, and so on, exactly as Parts 1-14
already do throughout) so the reader leaves knowing not just the idea but where they'd
actually encounter or reach for it.

**Stay current, not textbook-frozen**: favor what a principal engineer would actually
reach for or discuss in 2025-2026-era system design — vector databases and RAG-serving
infrastructure, NewSQL (Spanner/CockroachDB/TiDB), modern cloud-managed services (DynamoDB,
Cosmos DB, managed Kafka/Kinesis), current consensus/coordination tooling (etcd over raw
Paxos papers) — alongside the foundational papers and classics (GFS, Dynamo, Bigtable) that
still explain *why* those modern systems are built the way they are. The classics earn their
place because they're the origin of the mechanism; the modern examples earn their place
because they're what the reader will actually be asked about, built on, or expected to
already know in a real conversation happening now. Revisit and refresh named examples as the
industry's actual default tooling shifts — a doc that only cites what was current five years
ago is falling out of the "modern system" bar this whole folder is held to.

## Plain English is the entry ramp, never a substitute for precision

Simplifying the *on-ramp* into a concept must never mean cutting the exact technical
vocabulary a reader needs later. These docs exist to prepare someone for real
architect-to-architect conversations, where the precise term — linearizability, quorum,
Byzantine fault tolerance, write amplification, PACELC, consistent hashing, whatever the
concept actually calls itself in the industry — *is* the fast, unambiguous way two staff+
engineers communicate. Dropping a term because it "sounds too advanced" produces a reader
who can follow the analogy but can't hold their own in the room it's actually preparing them
for, which defeats the doc's purpose.

The rule this implies: **every advanced term the concept actually has must still appear,
correctly and precisely defined** — the plain-English pass is what earns the reader the
right to encounter that term without getting lost, not a reason to leave the term out. A
doc that stays at "layman terms" throughout and never lands on the real vocabulary is just
as incomplete, in the other direction, as one that opens with jargon and never explains it.
Every existing part's own `### Vocabulary Builder` subsection is exactly this contract kept:
plain-English explanation earlier in the doc, full precise term list at the end, nothing
traded away either direction.

## First principles, not memorized facts

Every explanation must be derivable from **why**, not just stated as **what**. Before
naming a technology or pattern, name the physical or structural constraint that makes it
necessary — the six-axes framework (`11_taxonomy_of_storage_choice.md`), the vertical-wall
economics (`12_sharding_and_the_vertical_wall.md`), and the "problem, precisely" framing
used throughout Parts 1-14 are the house style. If a doc introduces a term or a technology
without first establishing the problem it exists to solve, that's a gap to fix, not an
acceptable shortcut.

## Practical implications for new/edited content

- New parts follow the numbered `NN_topic_name.md` convention, get wired into this folder's
  own navigation (`Previous`/`Next` footer links) and the parent
  `system_design_foundation/README.md` part count, and end with `Designing and Operating
  From First Principles`, `Key Takeaways`, `Quick Self-Check`, and `Articulate It` sections
  matching every existing part.
- Cross-reference liberally instead of re-deriving mechanism a prior part already covered —
  link back to it, then build on it, rather than repeating it.
- This folder still follows the repo-wide `## Articulate It: Interview Framing & Vocabulary`
  convention from `../CLAUDE.md` — this file adds the layman-to-principal shape on top of
  that, it doesn't replace it.

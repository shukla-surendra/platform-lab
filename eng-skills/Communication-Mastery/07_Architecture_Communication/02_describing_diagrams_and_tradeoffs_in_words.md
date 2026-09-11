# Describing Diagrams and Trade-offs in Words

A specific, learnable skill: converting a visual architecture into a verbal description that a listener can actually follow with no image in front of them — critical for phone screens, audio-only calls, and any moment where you're explaining a system you can picture perfectly but the listener cannot.

## Why This Is Harder Than It Sounds

A diagram lets the eye jump around non-linearly — you can look at the database, then trace back to what writes to it, then glance at the cache layer, in any order, re-checking freely. Speech is strictly linear and has no "re-glance." This means a verbal description has to do work a diagram never has to: it has to **choose a traversal order that builds correctly in the listener's head, one piece at a time, with nothing assumed and nothing requiring a look-back.**

This is the same working-memory constraint from `01_Foundations/02` applied to spatial/structural information specifically — the listener is building a mental diagram from your words, one edge and node at a time, and if you jump around, their partial mental diagram gets corrupted or dropped.

## The Traversal Order Rule

**Always describe left-to-right or top-to-bottom, following the actual flow of data or requests — never jump around, and announce direction changes explicitly if you must.**

```
GOOD TRAVERSAL (follows request flow, one direction):
"A request comes in through the load balancer, hits one of our
API servers, which reads from a cache first — and only on a
cache miss does it query the primary database. Writes go through
a separate path: they hit the API server, write directly to the
primary database, and a background job invalidates the relevant
cache keys afterward."

BAD TRAVERSAL (jumps around, hard to build mentally):
"So there's a database, and also a cache, and requests come in
through a load balancer, and actually I should mention the cache
gets invalidated by a background job, and the load balancer sends
to API servers which — going back to the database — reads and
writes happen differently there..."
```

The good version has an invisible narrator's finger tracing one continuous path. The bad version requires the listener to hold disconnected facts and stitch them together themselves — which, per the working-memory limits in `01_Foundations/02`, they usually can't do reliably past 3-4 disconnected facts.

## The Three-Pass Technique

For anything more complex than a simple pipeline, describe it in three deliberate passes, each adding detail, rather than trying to say everything at once:

```
PASS 1 — SHAPE ONLY       "There are three layers: ingestion,
                            processing, and serving."
                            (3 chunks — see 01_Foundations/02 —
                            gives the listener a skeleton to hang
                            detail on)

PASS 2 — MAIN FLOW         "Data comes in through ingestion, gets
                            transformed in the processing layer,
                            and lands in a store the serving layer
                            reads from."
                            (fills the skeleton with the primary path)

PASS 3 — DETAIL ON REQUEST  "Want me to go deeper on any of those
                             three? The processing layer is
                             probably the most interesting — that's
                             where the actual complexity lives."
                             (offers depth rather than dumping it
                             uninvited — respects the listener's
                             actual interest and working-memory budget)
```

This mirrors the altitude-control concept from `01_Foundations/03`, applied specifically to verbal-diagram description: start at the highest altitude (shape), descend one level (flow), then let the listener pull you deeper rather than pushing all detail at once.

## Describing Specific Diagram Types

### A Layered/Tiered Architecture (e.g., web app: LB → app servers → DB)

> "Think of it as three tiers, stacked: a load balancer on top distributing to a fleet of app servers in the middle, which all talk to one database on the bottom."

### A Pipeline (e.g., Spark ETL, CI/CD)

> "It's linear — five stages in sequence: extract, validate, transform, load, and a final verification step. Each stage only depends on the one before it, nothing branches or loops back."

### A Fan-out / Fan-in Pattern (e.g., a scatter-gather microservice call)

> "One request fans out to three downstream services in parallel — pricing, inventory, and recommendations — and we wait for all three (or timeout) before fanning back in to build the final response."

### An Event-Driven / Pub-Sub System

> "There's no direct caller-callee relationship here — producers publish events to a topic without knowing who's listening, and any number of consumers can subscribe independently. Today we have two consumers: an analytics pipeline and a notification service, and adding a third doesn't require touching the producer at all."

### A Distributed/Replicated System (e.g., multi-region database)

> "Picture the same database running in three regions. Writes go to a primary region and replicate asynchronously to the other two — so reads in those two regions can be slightly stale, typically by under a second, and that's an accepted trade-off for the availability we get in return."

## Verbalizing Trade-offs Inside a Diagram Description

Weave the trade-off into the traversal, right at the point it's relevant, rather than as a separate bolted-on section at the end — this keeps the trade-off attached to the specific component it applies to, which is easier for the listener to retain.

> "...and only on a cache miss does it query the primary database — that cache adds a small consistency risk, since a write can take up to 30 seconds to propagate to the cache, which we've decided is fine for this use case since the data isn't safety-critical..."

Compare to bolting it on at the end (*"...oh, and one thing — the cache can be up to 30 seconds stale"*) — technically the same information, but disconnected from its context by the time it arrives, forcing the listener to mentally re-attach it to the right component.

## Handling "Can You Draw That?" When You Can't

On an audio-only call or in a spoken interview, you sometimes need to build a diagram with words alone, in real time. Use explicit spatial/sequential language to substitute for the visual:

- "Picture three boxes left to right: ..."
- "There's a top layer and a bottom layer — top layer does X, bottom layer does Y..."
- "If you're sketching this, draw an arrow from A to B, then another from B to C..."
- "Two parallel paths that merge back together at the end — like a diamond shape..."
- "It's a tree, not a line — one root, three branches, each branch independent of the others..."

## Self-Check Before Describing Any System Verbally

- [ ] Have I picked ONE traversal order (data flow, request flow, or top-to-bottom) and committed to it, or will I jump around?
- [ ] Did I give the shape (3-5 components) before the detail, so the listener has a skeleton first?
- [ ] Are trade-offs attached to the specific component they apply to, not bolted on at the end?
- [ ] Did I offer to go deeper rather than dumping full detail uninvited?

## Glossary — Vocabulary Used in This Chapter

| Term / Phrase | Meaning |
|---|---|
| **Re-glance** | The ability to look back and re-check something already seen (available with a diagram, unavailable in speech). |
| **Stitch together** | To piece disparate, disconnected facts into one coherent whole. |
| **Bolted on** | Attached afterward, disconnected from the thing it modifies, rather than integrated from the start. |
| **Weave (into)** | To integrate something smoothly into surrounding material, rather than adding it separately. |
| **Skeleton (to hang detail on)** | A basic structural outline established first, onto which further detail is attached afterward. |

**Next:** [`../08_Interview_Communication/01_behavioral_and_system_design_frameworks.md`](../08_Interview_Communication/01_behavioral_and_system_design_frameworks.md) — applying everything so far to the highest-pressure communication context: interviews.

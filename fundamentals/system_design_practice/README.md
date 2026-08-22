# System Design Practice

General distributed-systems design at staff-engineer depth — independent of the
[ML System Design track](../system_design_foundation/README.md). Where that track is scoped to ML/LLM
infrastructure (feature stores, model serving, RAG), this one covers the classic
large-scale distributed systems ground staff+ loops actually probe: consensus, distributed
transactions, and a set of fully worked "design X" case studies spanning social/feed
systems, real-time messaging, infra building blocks, and content/search systems.

## Why This Is Separate from the ML Track

Not every staff-level system design round is ML-specific — plenty of loops (and plenty of
rounds even at ML-focused companies) test general distributed-systems depth: can you
design a system that handles a celebrity's tweet fanning out to 100M followers, or a
payment-processing-grade distributed queue, regardless of whether ML ever enters the
picture. This track exists so that ground gets the same depth of treatment.

## Read This First

If terms like **p99 latency**, **the nines**, **sharding vs. replication**, **CAP
theorem**, or **idempotency** aren't things you could explain from first principles yet,
start with the [ML track's Prerequisite Concepts
primer](../system_design_foundation/00_prerequisite_concepts/01_performance_and_scale.md) (three
short parts covering measurement/scaling, data/consistency, and communication/resilience)
— it's the shared vocabulary this track assumes too, even though the case studies below
are ML-independent. Also worth reading before the first case study: [Part 21, The FR/NFR
Framework and a Real-Tools Quick
Reference](../system_design_foundation/00_prerequisite_concepts/21_fr_nfr_framework_and_architecture_tools.md)
— the generic requirements-derivation checklist and technology cheat sheet every case study
below assumes, applied fresh in each one's own `Requirements` section.

**[0. The Staff-Level Signal](00_staff_level_signal/tutorial.md)** — what actually
separates a staff-level answer from a senior one in these rounds. It's not "bigger
numbers" — it's organizational scope, ambiguity handling, and trade-off framing at a
different altitude. Read this before any case study; it's the lens the rest of this
section is evaluated through.

**[1. Distributed Systems Foundations](01_distributed_systems_foundations/tutorial.md)** —
the underlying mechanics every case study below draws on: consensus (Raft/Paxos),
distributed transactions (2PC vs. Saga), CRDTs and vector clocks, consistent hashing,
service mesh, and multi-region active-active replication. Read this second.

## The Case Studies

| # | System | What It Primarily Tests |
|---|---|---|
| 2 | [Twitter/X Feed](02_design_twitter_feed/tutorial.md) | Fan-out strategies, the celebrity/hot-key problem, feed ranking |
| 3 | [Chat System (WhatsApp)](03_design_chat_system/tutorial.md) | Persistent connection management at scale, message ordering, delivery guarantees |
| 4 | [Ride-Hailing Dispatch (Uber)](04_design_ride_hailing_dispatch/tutorial.md) | Geospatial indexing, real-time matching, consistency under contention |
| 5 | [Distributed Cache (Redis Cluster)](05_design_distributed_cache/tutorial.md) | Consistent hashing, replication, hot keys, cache stampede |
| 6 | [Distributed Message Queue (Kafka)](06_design_distributed_message_queue/tutorial.md) | Log-structured storage, partitioning/replication, exactly-once semantics |
| 7 | [Rate Limiter at Global Scale](07_design_rate_limiter_at_scale/tutorial.md) | Distributed counting, clock synchronization, approximate vs. exact enforcement — plus companion deep-dives on the [full algorithm landscape](07_design_rate_limiter_at_scale/algorithms_all_iterations.md), [Kubernetes-native implementations](07_design_rate_limiter_at_scale/kubernetes_native_implementations.md), and [build-vs-buy/tooling](07_design_rate_limiter_at_scale/build_vs_buy_and_tooling_landscape.md) |
| 8 | [Video Streaming (YouTube/Netflix)](08_design_video_streaming/tutorial.md) | Transcoding pipelines, adaptive bitrate, CDN architecture |
| 9 | [Web Crawler](09_design_web_crawler/tutorial.md) | URL frontier design, politeness, dedup at scale |
| 10 | [Search Autocomplete](10_design_search_autocomplete/tutorial.md) | Distributed trie structures, ranking, real-time trending updates |
| 11 | [URL Shortener](11_design_url_shortener/tutorial.md) | Key generation as access control, revocation vs. edge caching, conflict-free multi-region writes |
| 12 | [Payment / Order Processing](12_design_payment_order_processing/tutorial.md) | Saga across a third-party payment gateway, idempotency, CQRS for order status |
| 13 | [Distributed File Storage (Dropbox)](13_design_distributed_file_storage/tutorial.md) | Content-addressed chunking/dedup, replication vs. erasure coding, metadata/blob separation |
| 14 | [Collaborative Doc Editor (Google Docs)](14_design_collaborative_doc_editor/tutorial.md) | CRDTs vs. Operational Transformation, presence as ephemeral state, event-sourced edit history |
| 15 | [Ticket / Event Booking (Ticketmaster)](15_design_ticket_booking_system/tutorial.md) | Isolation levels/concurrency control under extreme contention, reservation TTLs, virtual waiting rooms |
| 16 | [Notification System](16_design_notification_system/tutorial.md) | Priority-isolated fan-out, idempotent delivery, provider failover |
| 17 | [Ad Click Aggregation](17_design_ad_click_aggregation/tutorial.md) | Exactly-once stream aggregation, watermarks, approximate counting at scale |

Each case study follows the same four-step structure from the staff-signal tutorial:
clarify → high-level design → deep-dive → trade-offs, with an explicit staff-altitude
framing note in each — what a *senior* answer stops at, and what a *staff* answer adds on
top.

## How to Practice This

- **Out loud, with a whiteboard or Excalidraw**, same as the ML track — these are verbal
  reasoning exercises, not take-home documents.
- **Time-box the high-level design deliberately** (10-15 minutes) so you have real time
  left for the deep-dive and trade-off discussion — staff rounds weight those far more
  heavily than the box diagram.
- **Push yourself past the first working design.** Every case study includes a "Staff
  Follow-Ups" section — the questions an interviewer asks *after* your design works, to
  see how far your thinking actually goes.

# 1. Regional Feature Staleness

**Primary topic:** [Feature Store & Model Promotion](03_feature_store_model_promotion.md)

## The Situation

A fraud-detection model's precision has quietly dropped over the past week — but only for
traffic served out of one region (`eu-west-1`). The on-call feature-store dashboard shows
"healthy" (green) for materialization jobs in every region. Support tickets mention
"seemingly obvious fraud getting approved," but only intermittently — maybe 1 in 10
transactions in that region.

## First Questions to Ask

- Is "healthy" on the dashboard based on **job completion** or **data freshness**? (These
  are different things — a materialization job can complete successfully while writing
  stale or partial data.)
- Is the online feature store **regionally replicated**, or is `eu-west-1` reading from a
  cross-region replica of a primary store elsewhere?
- Does the 1-in-10 pattern correlate with anything — a specific feature, a specific
  partition/shard, a specific time window?
- When did this start, and does it correlate with any recent deploy, config change, or
  infra event in that region?

## Likely Root Causes (ranked)

1. **Partial materialization failure that still reports "success."** If the
   materialization job writes to multiple shards/partitions and only logs job-level
   status (not per-partition), a job that fails to write one shard but succeeds on the
   rest can report green while serving stale data for exactly the requests that hash to
   that shard — explaining both the regionality and the ~10% intermittency (proportional
   to shard count).
2. **Cross-region replication lag exceeding the feature's freshness SLA.** If
   `eu-west-1`'s online store is a read replica of a primary in another region, and
   replication lag spikes (network issue, replica under load), reads there would serve
   stale values while the dashboard — which likely checks the *primary's* materialization
   job — shows healthy.
3. **A regional config drift** — e.g. `eu-west-1` running an older version of the
   materialization job that hasn't picked up a recent feature-definition change.

## Diagnostic Path

1. Check materialization **freshness metrics per shard/partition**, not just per-job
   status — if the dashboard doesn't have this granularity, that's itself a finding worth
   raising (a monitoring gap, not just a bug).
2. Directly query the `eu-west-1` online store for a known entity and compare its
   timestamp against the offline store's latest value for the same entity — a direct
   freshness check bypasses any dashboard blind spot.
3. Check replication lag metrics between the primary store and the `eu-west-1` replica
   specifically, if that architecture applies.
4. Correlate the 10%-of-requests pattern against shard/partition assignment — if it lines
   up with a specific shard, that strongly points to root cause #1.

## The Fix

- **Immediate mitigation**: if a specific shard/replica is confirmed stale, force a
  re-materialization of that shard, and add a temporary fallback (serve a slightly more
  conservative default, or route affected traffic to the offline-computed value) until
  freshness is restored.
- **Long-term fix**: add per-partition/per-region freshness metrics to the materialization
  job's health check — "job completed" and "data is fresh" must be reported as separate
  signals, since this incident exists specifically because they were conflated into one
  "healthy" status.

## Prevention

This is fundamentally a **monitoring granularity** gap, not a data-pipeline bug — the
underlying materialization failure would have been caught immediately if freshness were
monitored at the same granularity data is actually partitioned and served. The general
lesson: any "healthy" status on a distributed system should be asked "healthy *at what
granularity*?" — job-level health can hide partition-level, shard-level, or region-level
failure. See the freshness-SLA discussion in the
[feature store tutorial](03_feature_store_model_promotion.md#failure-modes-to-raise-proactively).

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Question-the-signal framing (the default for a debugging round):** "Before I chase root
  cause, I'd interrogate the dashboard itself — 'healthy' here means job completion, not
  data freshness, and those are different claims. A lot of debugging time gets wasted
  trusting a status that was never actually measuring the thing you assumed."
- **Granularity framing (good for explaining why nothing alerted):** "The gap here isn't
  the pipeline, it's monitoring granularity — job-level health can hide shard-level or
  region-level failure. I'd generalize that as a question I ask about any 'healthy' status
  going forward: healthy at what granularity?"
- **Narrative-first (good for 'walk me through how you'd debug this live'):** "I'd bypass
  the dashboard entirely first — query the region's online store directly for a known
  entity and diff its timestamp against the offline store. A direct freshness check rules
  out an entire dashboard blind spot in one query."

### Vocabulary Builder

- **partial failure** (n. phrase) — a component fails for a subset of its work while
  reporting overall success, the specific shape of bug this scenario walks through.
- **conflate** (v.) — to treat two distinct signals as one. *"'Job completed' and 'data is
  fresh' were conflated into a single healthy status."*
- **"…is itself a finding worth raising"** — a phrase for treating a monitoring gap you
  discover mid-investigation as a deliverable, not a distraction from the main fix.

---

**Previous:** [Overview](12_tricky_scenarios_readme.md)  |  **Next:** [2. Canary Passed, P1 Two Days Later](12_tricky_scenarios_02_canary_passed_p1_later.md)

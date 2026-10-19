# 6. Silently Duplicated Training Data

**Primary topic:** [High-Throughput Ingestion Pipelines](02_ingestion_pipeline.md)

## The Situation

A newly trained model performs suspiciously well offline — noticeably better than the
previous version, more than the feature/data changes would seem to justify. Before
promoting it, a data scientist notices the training dataset has grown 15% since last
month, but the business didn't grow anywhere near that fast.

## First Questions to Ask

- Is the row-count growth consistent with actual new-data volume from source systems, or
  disproportionate?
- Has the ingestion pipeline had any retries, replays, or backfills in that window?
- Is there a unique/idempotency key on the training data table, and is it actually
  enforced (a unique constraint), or just a convention nobody verified?
- Did the "suspiciously good" performance improvement show up specifically on metrics
  computed via train/test split from the *same* dataset (which duplicated rows would
  directly inflate via train-test leakage), or also on a genuinely held-out, independently
  sourced evaluation set?

## Likely Root Causes (ranked)

1. **Retry-induced duplication without effective deduplication.** If the ingestion
   pipeline's idempotency key (per the
   [ingestion tutorial](02_ingestion_pipeline.md#idempotency)) is generated at
   write time rather than deterministically from content, or if upserts were implemented
   as inserts somewhere in the pipeline, retries (from transient failures, Lambda
   timeouts, a Step Functions re-run) would silently re-insert the same logical records as
   new rows.
2. **Train-test leakage from duplicated rows landing on both sides of the split.** If
   rows are duplicated *before* the train/test split is taken, a random split will place
   copies of the same logical record on both sides — the model then partially "memorizes"
   test answers it saw duplicated in training, inflating offline metrics without any real
   generalization improvement. This is the direct mechanism connecting duplication to
   "suspiciously good" performance.
3. **A backfill or replay job double-processing an already-ingested date range** — e.g. a
   well-intentioned reprocessing job re-ran over a window that had already succeeded,
   without checking what was already ingested first.

## Diagnostic Path

1. **Directly query for exact or near-exact duplicate rows** (by content hash, not just
   row ID) in the training dataset — this is the fastest way to confirm or rule out
   duplication as the root cause before investigating *why*.
2. **Check the idempotency key generation logic** in the ingestion code — confirm whether
   it's deterministic (hash of content) or non-deterministic (a UUID or timestamp
   generated per attempt), since the latter defeats retry-safety entirely regardless of
   good intentions elsewhere in the pipeline.
3. **Check for unique constraints at the storage layer** — if the idempotency key isn't
   enforced as a database-level unique constraint (only assumed/conventional), duplicate
   writes wouldn't be rejected even if the key itself were correct.
4. **Re-evaluate the model on a genuinely independent, deduplicated evaluation set** and
   compare against the suspiciously-good number — a large gap between the two confirms
   the leakage hypothesis directly.
5. **Audit recent pipeline run history** (Step Functions execution history, retry counts,
   any manual backfill/replay jobs) for the specific date range showing anomalous growth.

## The Fix

- **Immediate mitigation**: deduplicate the existing training dataset (by content hash),
  retrain or re-evaluate on the cleaned data, and do not promote the currently-flagged
  model version until re-validated on clean data.
- **Long-term fix**: make the idempotency key deterministic (content-based hash, not
  attempt-based) and enforce it as a genuine unique/upsert constraint at the storage
  layer — not just a convention documented somewhere and hoped-for.

## Prevention

The systemic lesson: **"suspiciously good" offline results deserve exactly as much
scrutiny as suspiciously bad ones** — a large, unexplained jump in either direction should
trigger a data-integrity check before anyone even discusses promotion. See the
idempotency and retry-safety design in the
[ingestion pipeline tutorial](02_ingestion_pipeline.md#idempotency), and the
point-in-time-join / leakage discussion in the
[feature store tutorial](03_feature_store_model_promotion.md#deep-dive-point-in-time-joins-the-trickiest-part-to-get-right)
for the closely related failure mode of label leakage.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Suspicion-symmetry framing (the default for this scenario):** "A suspiciously good
  result deserves exactly the same scrutiny as a suspiciously bad one — I wouldn't accept
  an unexplained improvement without a data-integrity check first, before anyone even
  discusses promoting it."
- **Mechanism-first (good for explaining why duplication inflates metrics):** "The
  mechanism matters, not just the symptom: duplicated rows land on both sides of a random
  train/test split, so the model partially memorizes answers it already saw — that's
  leakage, and it's a different bug from 'the data grew.'"
- **Root-vs-symptom framing (good for the fix discussion):** "Deduplicating the dataset
  fixes the symptom for this model version. The actual fix is making the idempotency key
  deterministic and enforcing it as a real constraint — otherwise the next retry
  reintroduces the same class of bug."

### Vocabulary Builder

- **train-test leakage** (n. phrase) — information from the test set inadvertently present
  in training, here via duplicate rows landing on both sides of a split, inflating offline
  metrics without real generalization.
- **deterministic** (adj.) — always producing the same output given the same input; the
  property an idempotency key needs to survive retries safely.
- **"…deserves exactly as much scrutiny as…"** — a fluent way to argue symmetric skepticism
  is applied to both surprising-good and surprising-bad results, not just the latter.

---

**Previous:** [5. Retrieval Looks Right, Answers Are Wrong](12_tricky_scenarios_05_rag_retrieval_correct_answers_wrong.md)  |  **Next:** [7. Multi-GPU Training Plateau](12_tricky_scenarios_07_distributed_training_plateau.md)

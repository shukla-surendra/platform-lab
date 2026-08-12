# Storage for GPU Clusters: Why "Just Use S3" Breaks at This Scale

Part of [Phase 6 — Production Operations](../README.md#phase-6-production-operations).
Builds directly on
[`aws-production-architecture.md`'s storage section](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/aws-production-architecture.md#storage-getting-1tb-of-weights-onto-gpus-quickly),
which already introduced the S3 → FSx for Lustre → GPU pattern for inference weight
loading. This chapter generalizes that pattern to the other two storage-heavy GPU
workloads that doc didn't cover — training checkpointing and dataset I/O — and names the
general storage-tier taxonomy underneath all three.

## Clarify

"Storage for AI infrastructure" isn't one problem — it's at least three, with genuinely
different I/O patterns: **loading model weights** (already covered, read-heavy, happens
at cold-start/scale-out), **training checkpoint I/O** (write-heavy, recurring, latency-
sensitive because the whole training job stalls during a checkpoint write), and
**training dataset I/O** (read-heavy, continuous, throughput-sensitive across potentially
thousands of concurrent readers). Each has a different bottleneck, and "just use S3 for
everything" fails each one for a different, specific reason — this chapter is those
reasons, not a generic storage-options list.

## Core Concepts

### The storage tier hierarchy, by speed and by what each tier is actually for

```
Local NVMe (on the GPU node itself)
  Fastest tier available, but LOCAL — data doesn't survive a node
  replacement or exist anywhere else. Right for: checkpoint staging
  (write here first, fast, then async-copy to durable storage) and
  hot local caches, never as the sole copy of anything durable.

Parallel filesystem (FSx for Lustre / Ceph / on-prem equivalents)
  Shared across many nodes simultaneously, built specifically for many
  concurrent readers/writers hitting large files at once — the exact
  shape of both "load 1TB of weights onto 16 GPUs at once"
  (aws-production-architecture.md's pattern) and "1000 training nodes
  all reading the same dataset shards concurrently." NOT the durable
  source of truth — a fast staging/working layer in front of one.

Object storage (S3 / equivalent)
  Durable, versioned, cheap at scale — the actual source of truth for
  model artifacts and datasets. NOT fast enough, per-request, for
  thousands of GPUs hitting it directly and simultaneously at
  training/inference time — this is precisely why the parallel-
  filesystem tier exists as an intermediary, not a redundant layer.
```

**The organizing rule that resolves "why not just use S3 directly everywhere"**: object
storage is optimized for durability and cost at rest, not for the specific access pattern
of many compute nodes reading (or writing) large files *concurrently* and *quickly* — the
parallel filesystem tier exists specifically to bridge that gap, not because object
storage is bad, but because it's solving a different problem than the one GPU compute
actually has at runtime.

### Checkpoint I/O — the write-heavy, latency-sensitive case `aws-production-architecture.md` didn't cover

Recall from [`21_fsdp_deepspeed_zero.md`](../phase7_advanced_training_infra/21_fsdp_deepspeed_zero.md)
and [`16_reliability_and_failure_management.md`](16_reliability_and_failure_management.md):
training relies on periodic checkpointing both as routine practice and as the actual
recovery mechanism after a hardware fault or spot reclamation
(per [`18_capacity_planning_and_finops.md`](18_capacity_planning_and_finops.md)'s spot
discussion). The storage implication this creates:

```
A large model's checkpoint (weights + optimizer states — recall
14_model_memory_estimation.md's finding that optimizer states alone
can be 4x the weight size) can be hundreds of GB to multiple TB. During
a synchronous checkpoint write, training typically PAUSES — every GPU
sits idle until the write completes. This makes checkpoint write
THROUGHPUT a direct, measurable cost: slow checkpoint I/O means more
idle GPU-hours (an immediate FinOps cost, per 18_capacity_planning_and_finops.md)
every single time a checkpoint is taken.
```

The practical mitigation pattern, connecting local NVMe's role from the tier hierarchy
above: write the checkpoint to fast local NVMe first (minimizing the GPU-idle window),
then asynchronously copy from local NVMe to durable object storage in the background
while training resumes — trading a small window of "the latest checkpoint only exists
locally, not yet durably" for a much shorter GPU-idle stall. This is a genuinely
different pattern than the read-heavy weight-loading case
`aws-production-architecture.md` covers, using the same tier hierarchy for the opposite
reason (write latency, not read throughput).

### Dataset I/O — the sustained, many-reader throughput case

Training dataset access differs from both weight-loading (a one-time or infrequent burst)
and checkpointing (periodic writes): it's **continuous read throughput, sustained for the
entire training run, from potentially thousands of concurrent GPU-hosting nodes** each
pulling their own data shards. This is the workload the parallel-filesystem tier's design
point (many concurrent readers, large files, high aggregate throughput) most directly
targets — an FSx for Lustre (or Ceph, on-prem) filesystem sized for this workload
specifically needs aggregate throughput scaled to the GPU count and per-GPU data
consumption rate, not just "big enough to hold the dataset," which is a capacity question,
not the actual throughput question that determines whether GPUs sit idle waiting on data.

**The direct connection to a failure mode named earlier in this track**: a data-loading
pipeline that can't keep up with GPU consumption rate produces exactly the "GPU sitting
idle, unrelated to any GPU-level fault" symptom —
[`17_observability_for_gpu_fleets.md`](17_observability_for_gpu_fleets.md)'s metric
catalog (SM utilization low, no XID errors, no thermal issue) would show a *healthy* GPU
that's simply starved of data, a diagnostic conclusion only reachable by also checking the
storage layer's throughput, not the GPU metrics alone — a concrete instance of "the
bottleneck isn't always where the symptom appears."

## Deep-Dive: why this generalizes `aws-production-architecture.md`'s pattern rather than repeating it

All three storage workloads in this chapter — weight loading, checkpoint writes, dataset
reads — use the *same* tier structure (local NVMe for speed, parallel filesystem for
concurrent multi-node access, object storage for durability) but for different reasons:

| Workload | Direction | Why the parallel filesystem tier matters here |
|---|---|---|
| Weight loading (aws-production-architecture.md) | Read, one-time/infrequent burst | Many GPUs need the same large file set FAST, at cold-start |
| Checkpoint writes (this chapter) | Write, periodic, recurring | Training is PAUSED during the write — write throughput directly costs GPU-idle time |
| Dataset reads (this chapter) | Read, continuous, sustained | Many nodes need DIFFERENT data shards continuously, for the entire training run's duration |

Recognizing that these three workloads share one underlying storage-tier solution, for
three distinct reasons, is a stronger interview answer than listing "FSx for Lustre" as a
name-drop for each independently.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| Async checkpoint write (local NVMe first, background copy to S3) | Minimizes GPU-idle time during checkpointing | Brief window where the latest checkpoint isn't yet durably stored — a real risk if the node fails before the async copy completes |
| Synchronous checkpoint write direct to durable storage | No durability gap | Longer GPU-idle window per checkpoint — a direct, recurring cost |
| Sizing the parallel filesystem for dataset throughput, not just capacity | Prevents GPU starvation from slow data loading | Requires accurately estimating aggregate per-GPU consumption rate × GPU count, a real planning exercise, not a default assumption |

## Failure Modes to Raise Proactively

- **Treating storage sizing as a capacity question ("does it fit") rather than a
  throughput question ("can it keep up with GPU consumption rate")** — the dataset-I/O
  failure mode above is exactly this mistake, and it produces a GPU-utilization symptom
  that looks like a compute problem until the storage layer is checked.
  the storage layer specifically is checked.
- **Using synchronous, direct-to-S3 checkpoint writes for a very large model without the
  local-NVMe staging pattern** — directly costs GPU-idle time on every single checkpoint,
  compounding over a long training run into meaningful wasted spend.
- **Assuming the same storage architecture serves weight-loading, checkpointing, and
  dataset I/O equally well without checking each workload's actual read/write direction
  and frequency** — as the deep-dive table shows, the tier structure is shared but the
  sizing/tuning reasoning is not interchangeable across the three.

## Make It Yours

- If `aws-production-architecture.md`'s S3 → FSx → GPU pattern is already familiar from
  earlier in this session's work, explicitly extend it to the checkpoint-write case: name
  what changes (direction: write not read; trigger: periodic, not cold-start; cost
  driver: GPU-idle time during the pause, not cold-start latency).

## Practice Questions

1. Why is "does the dataset fit in the parallel filesystem" the wrong sizing question,
   and what's the right one?
2. A training job's GPU utilization metrics look healthy (no XID errors, no thermal
   issues, but SM utilization is unexpectedly low) — what storage-layer cause should be
   checked before assuming a GPU-level problem?
3. Why does the async local-NVMe-first checkpoint pattern trade a durability risk for a
   throughput benefit, and under what condition does that risk actually materialize?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "GPU cluster storage has three genuinely different I/O
patterns sharing one tier structure: local NVMe for speed, a parallel filesystem like FSx
for Lustre for many-node concurrent access, and object storage like S3 as the durable
source of truth. Weight loading is a read burst at cold-start, checkpoint writes are
periodic and pause training while they happen — so write throughput directly costs
GPU-idle time — and dataset reads are continuous, sustained throughput across potentially
thousands of concurrent readers. Sizing storage for capacity alone, without checking
whether it can sustain the actual read/write throughput each workload needs, is how a
storage bottleneck shows up disguised as a GPU utilization problem."

**The follow-up-proof version**: be ready to name which of the three storage workloads a
given symptom (slow cold-start, training pausing longer than expected during checkpoints,
low GPU utilization with no hardware fault) actually points to, rather than treating
"storage" as one undifferentiated concern.

**Vocabulary builder**: *parallel filesystem* (a filesystem built for many concurrent
readers/writers hitting large files simultaneously, distinct from both local disk and
object storage), *staging* (writing to a fast local tier first, then asynchronously
copying to durable storage), *data starvation* (GPUs sitting idle because the storage/data
pipeline can't keep up with consumption rate, not because of a GPU-level fault).

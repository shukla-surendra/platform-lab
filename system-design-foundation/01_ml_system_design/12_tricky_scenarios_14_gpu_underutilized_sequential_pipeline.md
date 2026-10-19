# 14. GPU Sitting Idle 75% of the Time in a Sequential Fraud-Detection Pipeline

**Primary topic:** [High-Throughput Ingestion Pipelines](02_ingestion_pipeline.md) ·
[Prerequisite Concepts, Part 4: CPU vs. GPU](../00_prerequisite_concepts/04_cpu_vs_gpu.md)

## The Situation

A receipt-fraud detection pipeline runs as a sequence of steps inside each pod: PDF → image
conversion, deduplication, orientation detection, rotate the image if needed, run
`fake_receipt_prediction` (a GPU model), then further downstream tasks. Each pod is
provisioned on a GPU-attached instance (e.g. `g6.2xlarge`) so the model step has a GPU
available. GPU utilization metrics show the GPU is actually busy **less than 25% of the
pod's runtime.** The team is considering whether to add more GPU instances to handle
growing volume.

## First Questions to Ask

- Of the six pipeline steps, how many actually touch the GPU? (Just one —
  `fake_receipt_prediction` — versus five CPU-only steps is the detail that reframes the
  whole question.)
- Do the steps run strictly sequentially within one process/pod, or is there any overlap
  between stages?
- Is `fake_receipt_prediction` called once per receipt, or are receipts ever batched
  before being sent to the model?
- What's the actual wall-clock time split between the CPU-only steps (PDF rasterization,
  dedup hashing, orientation detection, rotation) and the GPU step, per receipt?
- Is the current plan to add more GPU instances driven by an actual GPU-bound bottleneck,
  or by rising overall pod count/volume without isolating which resource is actually
  saturated?

## Likely Root Causes (ranked)

1. **A GPU-bound step is embedded inside an otherwise CPU-bound sequential pipeline, on a
   GPU-attached instance for the pipeline's entire duration.** This is the dominant cause,
   and it doesn't require anything to be "wrong" with the model or the GPU itself — five
   of six steps are CPU work (PDF rasterization, hashing, a small orientation classifier
   or heuristic, image rotation, and downstream tasks), and the GPU sits idle for all of
   them because the whole pod, GPU included, is held for the pipeline's full runtime
   regardless of which resource each step actually needs. See the [workload-shape
   framing in the serverless-vs-EKS receipt
   deep-dive](02_ingestion_pipeline_serverless_vs_eks_receipt_processing.md#the-workload-shape-that-actually-decides-this)
   — this is the same "what does this workload actually need" question, just landing on
   a different answer for a different step.
2. **Receipts are scored one at a time, not batched, through the GPU model.** Even during
   the fraction of time the GPU *is* in use, a single-image inference call fills only a
   tiny sliver of a GPU's parallel capacity — see the [batching discussion in the GPU
   primer](../00_prerequisite_concepts/04_cpu_vs_gpu.md#putting-it-together-why-batching-matters-so-much-on-a-gpu).
   This compounds root cause #1 rather than replacing it: even the ~25% "busy" time may
   itself be running at low actual utilization within that window.
3. **Adding more GPU instances would scale the wrong resource.** If the real bottleneck
   is CPU-bound preprocessing steps queuing up ahead of an underused GPU, adding GPU
   capacity doesn't relieve that bottleneck at all — it just creates more GPU instances
   sitting idle for the same 75% of their runtime, multiplying cost without addressing
   throughput.

## Diagnostic Path

1. **Instrument per-step wall-clock time**, not just aggregate GPU utilization — get an
   actual breakdown of how many milliseconds each of the six steps takes per receipt.
   This single measurement either confirms or reframes everything else: if PDF
   rasterization and dedup dominate the time budget, the fix is entirely on the CPU side
   of the pipeline, independent of anything GPU-related.
2. **Check whether `fake_receipt_prediction` is called per-image or per-batch** — if
   per-image, that's an immediate, cheap-to-fix contributor before touching
   infrastructure at all.
3. **Check whether pipeline stages run strictly sequentially in one process** — confirm
   there's no overlap where CPU work for the next receipt could already be happening
   while the GPU scores the current one.
4. **Before adding GPU capacity, verify GPU queue depth/backlog is actually the
   constraint** — if GPU instances are idle 75% of the time, by definition GPU capacity
   is not currently the bottleneck; check what *is* queuing (likely a CPU-bound stage, or
   simply pods spending most of their time on non-GPU work) before spending on more GPUs.

## The Fix

- **Immediate mitigation**: if `fake_receipt_prediction` is being called one image at a
  time, add a small batching buffer (accumulate up to N images or wait up to a bounded
  timeout, whichever comes first) before invoking the model — a low-effort change that
  directly improves GPU efficiency during the time it's already in use, without any
  infrastructure changes.
- **Long-term fix**: decouple the pipeline into two independently-scaled tiers connected
  by a queue — a CPU-only tier for PDF→image, dedup, orientation detection, and rotation
  (running on cheap CPU instances, scaled on CPU load), and a GPU-only tier for
  `fake_receipt_prediction` (running on GPU instances, scaled on GPU queue depth, per the
  [custom-metric autoscaling pattern in the model-serving
  tutorial](04_model_serving_deployment.md#autoscaling-for-model-serving)).
  This is the [message-queue decoupling pattern from
  Fundamentals](00_interview_framework_fundamentals.md#message-queues) applied directly: the CPU
  stages stop holding a GPU hostage for work that never touches it, and the GPU tier can
  batch, scale, and be sized independently of everything upstream of it.
- **Further optimization once decoupled**: evaluate whether multiple pipeline instances
  can share one GPU (via a proper serving layer, or hardware-level sharing like NVIDIA
  MPS/MIG) given the model likely uses a small fraction of an L4's 24GB VRAM — fewer,
  well-utilized GPUs beats many idle dedicated ones on cost, almost always.

## Prevention

The systemic lesson: **low GPU utilization is very rarely a GPU efficiency problem — it's
almost always a pipeline architecture problem**, specifically a GPU-bound step embedded
inside a synchronous, mostly-CPU pipeline sized and billed as a single unit. "Add more
GPUs" is the instinctive fix and the wrong one here: it scales a resource that isn't
actually the bottleneck, and multiplies the same underutilization across more instances
instead of resolving it. The durable fix is architectural — decouple by resource shape
(CPU-bound steps on CPU instances, GPU-bound steps on GPU instances, connected by a queue)
and batch the GPU-bound step once it's decoupled — the same "what does this workload
actually need" discipline the [receipt-processing cost
deep-dive](02_ingestion_pipeline_serverless_vs_eks_receipt_processing.md) already
argues for, just applied one layer further into the pipeline.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Wrong-resource framing (the default for this scenario):** "The instinct is to add more
  GPUs, but if a GPU is idle 75% of the time, GPU capacity isn't the bottleneck by
  definition — I'd refuse to scale a resource I haven't confirmed is actually saturated."
- **Resource-shape framing (good for explaining the root cause):** "Five of six steps here
  are CPU work with one GPU step embedded in the middle — holding a GPU-attached instance
  for the whole pipeline's duration means paying for expensive, specialized compute during
  work that structurally can't use it."
- **Decouple-then-batch framing (good for the fix):** "I'd sequence the fix in two moves,
  not one — decouple by resource shape first (CPU tier and GPU tier, connected by a
  queue), then batch the GPU step once it's decoupled. Batching alone doesn't fix a
  pipeline that's mostly CPU work; decoupling alone leaves single-image GPU calls
  underutilized. You need both."

### Vocabulary Builder

- **resource-shape mismatch** (n. phrase) — provisioning one compute type (GPU) for a
  workload whose actual resource needs vary sharply step to step, most of which don't use
  that compute type at all.
- **hold a GPU hostage** (v. phrase, figurative) — tying up a scarce, expensive resource
  for work that never touches it, simply because it shares a pod/instance with the step
  that does.
- **"…scales the wrong resource"** — a precise, reusable way to reject an instinctive fix
  (add more GPUs) by naming which resource is actually saturated versus which one isn't.
- **"…almost never a GPU efficiency problem — it's a pipeline architecture problem"** — a
  strong, quotable reframe for redirecting a hardware-sounding question toward the actual
  systemic cause.

---

**Previous:** [13. Eval Passed, Guardrail Bypassed in Production](12_tricky_scenarios_13_eval_passed_guardrail_bypassed.md)  |  **Next:** [Back to System Design Overview](../README.md)

# 7. Multi-GPU Training Plateau

**Primary topic:** [Distributed Training & Ray/Ray Serve](07_distributed_training_serving.md)

## The Situation

A team doubled their training cluster from 4 to 8 GPUs expecting roughly 2x throughput.
Actual throughput improved by about 15%. They've asked you to figure out why scaling is so
poor before they spend more on GPUs.

## First Questions to Ask

- Are all 8 GPUs on the same physical node (NVLink-connected), or spread across multiple
  nodes over standard networking?
- What's the per-GPU batch size, and did total/global batch size change when scaling from
  4 to 8 GPUs, or stay the same (halving per-GPU batch size)?
- What's actual GPU compute utilization (not just "GPU allocated") during training on both
  configurations?
- Is the data-loading pipeline (I/O, preprocessing) the same across both configurations,
  or does it also need to scale?

## Likely Root Causes (ranked)

1. **Cross-node network bandwidth bottlenecking all-reduce.** If the original 4 GPUs were
   on a single node (fast NVLink interconnect) and the additional 4 are on a second node
   (standard networking), gradient synchronization now crosses a dramatically
   slower link for a large fraction of communication — the
   [distributed training tutorial](07_distributed_training_serving.md#deep-dive-diagnosing-poor-scaling-efficiency)
   calls this out directly as the most common real-world cause of exactly this pattern.
2. **Data loading can't feed 8 GPUs fast enough.** If the data pipeline (disk I/O,
   preprocessing, augmentation) was sized for 4 GPUs' consumption rate, doubling compute
   capacity without scaling the data pipeline leaves GPUs idle waiting for batches —
   this shows up as GPU utilization dropping (not staying high while throughput
   stagnates), which is the key diagnostic signal distinguishing this from root cause #1.
3. **Per-GPU batch size halved, hurting compute efficiency per step.** If global batch
   size was held constant while scaling to 8 GPUs, each GPU now processes a smaller batch
   — smaller batches use GPU compute less efficiently (more overhead relative to useful
   work per kernel launch), which can measurably hurt scaling even before communication
   overhead is considered.
4. **A straggler GPU/node** — inconsistent hardware, thermal throttling, or noisy-neighbor
   resource contention on one of the 8 GPUs capping the whole synchronous training step at
   its speed.

## Diagnostic Path

1. **Check GPU compute utilization directly** (not allocation) on both configurations
   during a training run — high utilization with poor scaling points to communication
   overhead (#1); low/dropping utilization points to data starvation (#2).
2. **Check the physical topology** — confirm whether the additional 4 GPUs are same-node
   or cross-node, and if cross-node, what interconnect is actually being used for
   inter-node communication.
3. **Profile the all-reduce step specifically** (most distributed training frameworks
   expose per-step communication time) and compare its share of total step time between
   the 4-GPU and 8-GPU runs — a growing communication share directly confirms root cause
   #1.
4. **Check per-worker step-time variance** — a single consistently-slower worker among the
   8 points to a straggler rather than a systemic communication or data issue.
5. **Confirm batch-size configuration** — verify whether global batch size was kept
   constant (halving per-GPU batch) or scaled proportionally (keeping per-GPU batch size
   constant) when moving to 8 GPUs.

## The Fix

- **Immediate mitigation**: if cross-node communication is the bottleneck and a
  faster interconnect isn't readily available, keeping the additional GPUs on the same
  node (if physically possible) or accepting sub-linear scaling as expected given the
  hardware topology — set expectations accordingly rather than continuing to add
  cross-node GPUs expecting linear returns.
- **Long-term fix**: if scaling further is a genuine requirement, invest in
  high-bandwidth interconnect (or a managed cluster offering that guarantees it) *before*
  adding more nodes, and scale the data-loading pipeline in tandem with compute capacity,
  not as an afterthought.

## Prevention

The systemic lesson: **"more GPUs" only pays off linearly for as long as compute stays
the bottleneck** — communication overhead, data loading, and stragglers all become
binding constraints at different scale points, and diagnosing *which one* is binding
(via utilization and communication-time profiling) is the actual skill, not just
"add more hardware." See the full scaling-efficiency diagnostic order in the
[distributed training tutorial](07_distributed_training_serving.md#deep-dive-diagnosing-poor-scaling-efficiency).

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Diagnosis-as-skill framing (the default for this scenario):** "'More GPUs' only pays
  off linearly while compute is the actual bottleneck — communication, data loading, and
  stragglers all become binding constraints at different scale points. Figuring out *which
  one* is binding, not just reaching for more hardware, is the actual skill being tested
  here."
- **Utilization-as-signal framing (good for explaining the diagnostic order):** "GPU
  utilization is the fork in the diagnosis: high utilization with poor scaling points to
  communication overhead; low or dropping utilization points to data starvation. I'd check
  that number before touching anything else."
- **Expectation-setting framing (good for the fix discussion):** "Sometimes the right fix
  isn't a technical change at all — it's telling the team sub-linear scaling is expected
  given the current topology, and setting expectations accordingly instead of buying more
  GPUs that won't help."

### Vocabulary Builder

- **topology** (n.) — the physical arrangement of hardware (same-node vs. cross-node GPUs)
  that determines communication cost; often the real variable behind a scaling result.
- **binding constraint** (n. phrase) — whichever bottleneck currently caps performance,
  useful for framing why fixing a non-binding constraint won't help.
- **"…is the actual skill, not just 'add more hardware'"** — a fluent way to reframe a
  scaling question from a purchasing decision into a diagnostic one.

---

**Previous:** [6. Silently Duplicated Training Data](12_tricky_scenarios_06_duplicate_training_data.md)  |  **Next:** [8. Stale Checkpoint After Preemption](12_tricky_scenarios_08_stale_checkpoint_resume.md)

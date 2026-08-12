# Capacity Planning & FinOps: Turning Utilization Data Into Cost Decisions

Part of [Phase 6 — Production Operations](../README.md#phase-6-production-operations).
Builds on [`15_gpu_fleet_lifecycle.md`](15_gpu_fleet_lifecycle.md)'s OPTIMIZE stage and
[`17_observability_for_gpu_fleets.md`](17_observability_for_gpu_fleets.md)'s metrics —
this chapter is where utilization data actually becomes a cost/capacity decision, closing
the loop the lifecycle chapter left open.

## Clarify

"FinOps" for ordinary cloud infrastructure (compute, storage, network) is likely already
familiar territory given your existing cloud/AWS background. GPU FinOps is genuinely
different in ways worth naming precisely: GPUs are far more expensive per unit than
ordinary compute, idle GPU capacity wastes money at a much higher rate than idle CPU
capacity, and — the detail most generic FinOps knowledge misses — **spot instances,
a standard cost lever for ordinary compute, are actively dangerous for a large chunk of
GPU workloads**, per the stateful-multi-node-serving constraint
`aws-production-architecture.md` already named. This chapter is the GPU-specific version
of capacity/cost reasoning, not a repeat of general cloud FinOps.

## Core Concepts

### The two core unit-economics metrics, and when each applies

```
$/GPU-hour
  The raw cost of GPU capacity itself, independent of what's running
  on it. The right metric for: comparing instance types/commitment
  options, capacity planning, and any conversation about
  infrastructure cost BEFORE workload efficiency is accounted for.

$/million tokens (or $/inference, $/training-run for other workload
shapes)
  The cost of actually accomplishing the work, folding in utilization,
  batching efficiency, and quantization choices. The right metric for:
  comparing whether a SERVING deployment is actually cost-efficient,
  and for cost conversations with stakeholders who care about business
  outcomes, not raw infrastructure spend.

  $/million tokens = ($/GPU-hour × GPU-hours consumed) / (tokens
                      generated in that time)

  This is why two deployments with IDENTICAL $/GPU-hour costs can have
  wildly different $/million-tokens costs — one might be running at
  90% GPU utilization with continuous batching
  (12_llm_performance_engineering.md) and FP8 quantization
  (13_quantization.md), the other at 30% utilization with static
  batching at FP16. The infrastructure cost is the same; the ACTUAL
  cost of doing the work is not.
```

**The direct, checkable connection worth naming in an interview answer**: every
performance-engineering lever from
[`12_llm_performance_engineering.md`](../phase5_llm_serving/12_llm_performance_engineering.md)
(continuous batching, chunked prefill) and every precision lever from
[`13_quantization.md`](../phase5_llm_serving/13_quantization.md) is *also*, mechanically,
a FinOps lever — better throughput per GPU-hour directly lowers $/million-tokens without
changing $/GPU-hour at all. Performance engineering and cost optimization aren't two
separate disciplines here; for GPU serving specifically, they're the same work viewed
through two different metrics.

### Commitment models, and why spot is the wrong default for GPU serving

| Model | What it is | Right fit |
|---|---|---|
| On-demand | Pay full price, no commitment | Bursty, unpredictable, or short-lived workloads; early-stage capacity planning before commitment sizing is known |
| Reserved / Savings Plans | Commit to sustained usage for a discount | Steady-state production serving — predictable baseline load, per `aws-production-architecture.md`'s cost management section |
| Spot | Deep discount, but can be reclaimed by the cloud provider with short notice | **Training**, specifically checkpointable, restartable training jobs — NOT stateful multi-node serving |

**Why spot is actively wrong for the multi-node serving deployments this track has
covered**: recall
[`aws-production-architecture.md`'s cost management section](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/aws-production-architecture.md#cost-management) —
"an interrupted node breaks the whole TP group it belongs to, not just itself." A spot
reclamation isn't a graceful, drainable event the way REPAIR-stage draining is (per
[`16_reliability_and_failure_management.md`](16_reliability_and_failure_management.md))
— it's a short-notice, involuntary removal, and for a tensor-parallel serving group, that
single reclaimed GPU takes the entire group's serving capacity down with it. Training, by
contrast, tolerates this well *if* checkpointing is frequent enough (per
[`21_fsdp_deepspeed_zero.md`](../phase7_advanced_training_infra/21_fsdp_deepspeed_zero.md)'s
training context) — a reclaimed spot node just means resuming from the last checkpoint,
not a cascading failure across a live-serving TP group.

### Right-sizing — the OPTIMIZE-stage decision this chapter feeds

Utilization data from
[`17_observability_for_gpu_fleets.md`](17_observability_for_gpu_fleets.md) directly
answers the right-sizing question, and the answer routes to different levers depending on
what's actually under-utilized:

```
Consistently low GPU compute utilization, memory headroom available:
  → MIG or time-slicing candidate (10_gpu_scheduling_mig_sharing.md)
    — this workload doesn't need a whole GPU

Consistently low utilization, but memory-bound (high DRAM_ACTIVE
relative to compute):
  → Quantization candidate (13_quantization.md) — reduces the actual
    bottleneck resource, not just "use less GPU"

Consistently HIGH utilization, queue depth growing:
  → Scale-up candidate — add node-group capacity
    (aws-production-architecture.md's autoscaling-by-node-group), NOT
    a cost-optimization target — this is a capacity shortfall, not
    waste

Bursty, predictable-schedule load (e.g. business-hours-only traffic):
  → Scheduled scale-to-zero candidate, per
    aws-production-architecture.md's cost management section
```

**Why this table matters as an interview-answer structure**: "right-size the fleet" is a
vague instruction until it's routed through *which specific signal* justifies *which
specific lever* — the same diagnostic-tree discipline
`12_llm_performance_engineering.md` and `17_observability_for_gpu_fleets.md` already
established, now applied to cost rather than latency.

## Deep-Dive: chargeback and showback — making cost visible to the teams causing it

At organizational scale, a real FinOps practice needs a way to attribute GPU cost back to
the teams/workloads actually consuming it — otherwise cost-optimization incentives are
diffuse (nobody's budget is directly affected by their own inefficiency):

- **Showback** — reporting each team's actual GPU consumption/cost, without directly
  billing their budget for it. Lower friction to implement, but weaker incentive — visible
  cost without a direct consequence often doesn't change behavior on its own.
- **Chargeback** — actually billing each team's budget for their GPU consumption. Stronger
  incentive, but requires accurate, trusted attribution (namespace/label-based cost
  allocation in Kubernetes, or account/tag-based allocation in AWS) — a real
  implementation cost, and a political one if the attribution methodology is disputed.

Both depend on the same underlying data: accurate per-workload GPU-hour attribution,
which in turn depends on the observability chapter's metrics actually being
labeled/tagged by team or workload, not just by node — a concrete requirement this
chapter places back onto how `17_observability_for_gpu_fleets.md`'s metric catalog should
actually be deployed in practice.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| Reserved/Savings Plans for steady-state serving | Meaningful discount over on-demand, predictable budget | Commitment risk if actual usage falls below the reserved level |
| Spot for training | Deep discount, tolerable given checkpointing | Requires frequent, reliable checkpointing infrastructure to actually be safe — not free to implement |
| Chargeback over showback | Real behavioral incentive for teams to optimize their own usage | Implementation and political cost of building trusted, granular attribution |

## Failure Modes to Raise Proactively

- **Using spot instances for stateful multi-node serving to save cost** — the specific,
  named mistake this chapter (and `aws-production-architecture.md`) warns against
  explicitly; a reclaimed node doesn't gracefully drain, it breaks the whole TP group.
- **Optimizing $/GPU-hour without checking $/million-tokens** — a cheaper GPU-hour rate
  achieved by, say, switching to a less capable instance type can *increase*
  $/million-tokens if throughput drops more than the hourly cost fell; the two metrics can
  move in opposite directions and only the second one reflects actual cost-effectiveness.
- **Treating high utilization as a cost-optimization signal** — as the right-sizing table
  shows, high utilization with growing queue depth is a capacity shortfall requiring more
  spend, the opposite of what a cost-cutting instinct would suggest.

## Make It Yours

- For any GPU workload you have utilization data for (even informally observed), compute
  a rough $/million-tokens (or equivalent unit-cost) estimate and compare it against the
  raw $/GPU-hour rate — practice explaining, out loud, why the two numbers can diverge
  even when nothing about the infrastructure spend changed.

## Practice Questions

1. Why can two deployments with identical $/GPU-hour costs have very different
   $/million-tokens costs, and what specific technical levers explain the difference?
2. Why is spot capacity a reasonable choice for training but a dangerous one for
   multi-node serving, in terms of what actually happens when capacity is reclaimed?
3. A fleet shows high GPU utilization and growing queue depth — is this a cost-
   optimization opportunity or a capacity problem, and what's the risk of misreading it
   as the other?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "GPU FinOps needs two separate metrics — $/GPU-hour for raw
infrastructure cost, and $/million-tokens (or the workload-appropriate equivalent) for
actual cost-effectiveness, because utilization, batching, and quantization choices mean
the same infrastructure spend can produce very different amounts of useful work. Spot
instances are a real lever for training, which tolerates interruption via checkpointing,
but actively dangerous for stateful multi-node serving, where losing one GPU breaks an
entire tensor-parallel group's capacity, not just that GPU's share."

**The follow-up-proof version**: be ready to route a specific utilization pattern (low
compute, high memory-bandwidth; high utilization with growing queue depth) to the correct
lever — MIG/time-slicing, quantization, or scale-up — rather than giving a generic
"right-size the fleet" answer.

**Vocabulary builder**: *unit economics* ($/GPU-hour vs. $/million-tokens as the
infrastructure-cost vs. actual-cost-effectiveness distinction), *chargeback/showback*
(billing vs. reporting GPU cost back to consuming teams), *commitment risk* (the exposure
from reserving capacity that ends up under-utilized).

# Mixture-of-Experts & Expert Parallelism: A Fourth Axis, Not a Bigger Dense Model

Part of [Phase 7 — Advanced Distributed Training Infra](../README.md#phase-7-advanced-distributed-training-infra).
Closes out Phase 7. Builds on
[`21_fsdp_deepspeed_zero.md`](21_fsdp_deepspeed_zero.md) (data-parallel sharding) and
directly grounds a fact
[`tutorial.md`](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/tutorial.md)
already introduced without deriving: DeepSeek-V3 has 671B *total* parameters but only 37B
*active* per token — this chapter is the mechanism that makes that distinction real.

## Clarify

Every parallelism strategy covered so far — TP, PP, DP/FSDP — assumes a **dense** model:
every parameter participates in computing every token. Mixture-of-Experts (MoE)
architectures break that assumption deliberately: most parameters are organized into
"experts," and **only a subset of experts actually run for any given token**. This isn't
a training or serving *infrastructure* technique the way TP/PP/FSDP are — it's a
**model architecture** choice that then *requires* its own dedicated parallelism strategy
(expert parallelism) to serve or train efficiently. Understanding MoE means understanding
both halves: why the architecture exists, and what infrastructure problem it creates.

## Core Concepts

### The sparse-activation idea, precisely

```
Dense model (e.g. a standard 70B model):
  Every token → passes through ALL 70B parameters' worth of computation
  Total params = active params (always)

MoE model (e.g. DeepSeek-V3: 671B total, 37B active per token):
  Every token → a ROUTER selects a small subset of "experts" (typically
  a handful out of many, e.g. 8 of 256) → only those selected experts'
  parameters actually compute for that token
  Total params (671B) >> active params (37B) — most of the model's
  capacity exists, but any single token only touches a small slice of it
```

**Why this is a genuinely different lever than anything else in this track**: TP, PP, and
FSDP all answer "how do we spread a fixed amount of *necessary* computation and memory
across GPUs." MoE changes the numerator itself — it lets a model have far more total
capacity (parameters, and therefore more "knowledge"/specialization) without a
proportional increase in the compute cost of processing each token, because most of that
capacity sits idle for any given token. This is *why* DeepSeek-V3 can be a ~1.3TB model
(per
[`tutorial.md`'s framing](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/tutorial.md))
while having a compute cost per token closer to a much smaller dense model.

### The router — the component that makes MoE work, and the one that creates the infrastructure problem

Each MoE layer has a small **router (gating) network** that looks at each token and
decides which experts should process it — typically the top-K highest-scoring experts out
of the full expert pool, per token, per MoE layer. This routing decision is **learned**
during training (not a fixed, hand-coded assignment) and, critically, **varies token by
token** — two tokens in the same batch, even adjacent tokens in the same sequence, can be
routed to completely different experts.

**This is exactly where the infrastructure problem originates**: with a dense model, every
GPU in a TP group does the same, predictable amount of work every forward pass. With MoE,
which specific experts (and therefore which specific GPUs, if experts are distributed
across GPUs) get used depends on the *data*, discovered only at runtime — a fundamentally
harder scheduling and communication problem than anything TP/PP/FSDP have to solve, since
those are all static, known-in-advance communication patterns.

### Expert parallelism — spreading experts across GPUs, and the all-to-all it requires

**Expert parallelism (EP)** places different experts on different GPUs (rather than
replicating every expert on every GPU, which would defeat the memory-saving point of
having many experts at all). This introduces a genuinely new communication pattern beyond
anything named in
[`06_nccl_and_collective_communication.md`](../phase3_gpu_networking/06_nccl_and_collective_communication.md#the-collective-operations-precisely-defined):

```
Expert-parallel forward pass, one MoE layer:

1. Router on each GPU decides, for each of its local tokens, which
   expert(s) (potentially on OTHER GPUs) should process them

2. ALL-TO-ALL communication: every GPU sends each token to the GPU
   hosting its selected expert, and simultaneously receives tokens
   FROM other GPUs that were routed to experts it hosts — this is a
   genuinely different collective shape than all-reduce/all-gather/
   reduce-scatter (06_nccl_and_collective_communication.md's four
   primitives didn't include this one, because dense-model parallelism
   never needs it) — every GPU potentially exchanges DIFFERENT data
   with every other GPU, not the same reduction/broadcast pattern

3. Each GPU runs its local expert(s) on the tokens it received

4. A second ALL-TO-ALL sends results back to each token's originating
   GPU, so the rest of the model (which expects tokens to stay in their
   original GPU-local order) can continue
```

**Why this makes MoE models harder to serve efficiently than their active-parameter count
alone would suggest**: the all-to-all's cost depends on how evenly tokens happen to route
across experts in a given batch — if routing is imbalanced (some experts get many more
tokens than others in a given batch), the GPUs hosting popular experts become a
bottleneck while GPUs hosting unpopular experts sit idle, a load-imbalance problem dense
models structurally don't have (every GPU in a dense TP group always does equal work).

### Load balancing — the practical answer to routing imbalance

Real MoE training adds an explicit **load-balancing loss** term during training — an
auxiliary objective that penalizes the router for sending too many tokens to too few
experts, encouraging roughly even utilization across the expert pool over the course of
training. This doesn't guarantee perfect balance on any single batch (routing is still
data-dependent, token by token), but it prevents the pathological case where the model
learns to rely on only a handful of experts and effectively wastes the rest of its
parameter budget — directly protecting the sparse-activation benefit this section opened
with.

## Deep-Dive: how expert parallelism composes with everything else in this track

A real large-scale MoE deployment (DeepSeek-V3-class) doesn't use expert parallelism
alone — it composes with the parallelism dimensions already covered:

- **TP** still applies within each expert's own computation (an individual expert is
  itself a set of dense layers, per-expert, and can be tensor-parallel-sharded the same
  way any dense layer would be, per
  [`03_gpu_architecture.md`](../phase2_gpu_fundamentals/03_gpu_architecture.md#deep-dive-why-tensor-parallelism-stays-intra-node)).
- **PP** can still split the overall layer stack across node groups, MoE layers included.
- **EP** adds a new axis: *which GPUs host which experts*, with the all-to-all pattern
  above layered on top of whatever TP/PP structure is already in place.
- The all-to-all's frequency and volume make **network fabric quality (Phase 3) even more
  load-bearing than in a dense-only setup** — since EP's communication pattern is both
  more frequent-shaped (every MoE layer) and less predictable (data-dependent routing)
  than TP's or PP's, a degraded NVLink/RDMA path (the exact failure modes named
  repeatedly across Phases 2-3) has a correspondingly larger, harder-to-predict impact on
  an MoE model's actual serving throughput.

This is the concrete reason MoE serving infrastructure (vLLM, SGLang, and others'
MoE-specific serving paths) is a genuinely harder engineering problem than dense-model
serving, not just "the same infrastructure with a bigger model."

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| MoE architecture over an equivalently-capable dense model | Much lower active-compute cost per token for the same total capacity | Requires expert parallelism and its all-to-all communication — genuinely new infrastructure complexity, not free |
| More experts, smaller top-K per token | More total capacity/specialization | Routing imbalance risk grows; load-balancing becomes a harder training-time problem |
| Replicating all experts on every GPU (skip EP) | Simplest to implement, no all-to-all needed | Defeats MoE's memory advantage entirely — every GPU pays for every expert's memory regardless of whether it ever uses them |

## Failure Modes to Raise Proactively

- **Treating "671B parameters" as the number that determines serving cost** — as this
  chapter establishes, active parameters (37B for DeepSeek-V3), not total parameters, is
  what determines per-token compute cost; quoting total parameter count alone
  misrepresents the actual serving-infrastructure requirement.
- **Assuming expert parallelism's communication cost is predictable/uniform like TP's or
  PP's** — routing is data-dependent; a load-imbalanced batch can create a real,
  hard-to-anticipate bottleneck that a static communication-cost estimate (appropriate
  for TP/PP) would miss entirely.
- **Ignoring network fabric quality for an MoE deployment because "the active parameter
  count is small"** — the all-to-all pattern's sensitivity to network degradation is, if
  anything, *higher* than a dense model's, precisely because of its unpredictable,
  data-dependent shape — a subtle point worth raising proactively since it cuts against
  the intuitive "smaller active model = simpler infra" assumption.

## Make It Yours

- Revisit [`tutorial.md`'s DeepSeek-V3 reference](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/tutorial.md)
  with this chapter's mechanism in hand — explain out loud, using the router/all-to-all
  trace above, exactly why 671B total / 37B active is possible, rather than treating it
  as a given fact from the earlier doc.
- Compare the all-to-all communication pattern against all-reduce/reduce-scatter/
  all-gather from `06_nccl_and_collective_communication.md` — name specifically what
  makes it a different shape (every GPU potentially exchanges different data with every
  other GPU, vs. a uniform reduction/broadcast pattern).

## Practice Questions

1. Why does routing imbalance create a bottleneck in expert-parallel serving that has no
   real equivalent in tensor-parallel serving of a dense model?
2. What does the load-balancing loss term during training actually protect against, and
   why would a model without it risk wasting most of its own parameter budget?
3. A team estimates an MoE model's inference cost using only its active-parameter count
   and is surprised by network-related throughput problems in production — what
   architecture-specific communication pattern did that estimate likely fail to account
   for?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "MoE models route each token through only a small subset of
experts, via a learned router, so total parameter count and active (per-token) compute
cost decouple — DeepSeek-V3's 671B total / 37B active split is exactly this. That
decoupling requires expert parallelism, which spreads experts across GPUs and needs an
all-to-all communication pattern — a genuinely different, data-dependent shape than
all-reduce or reduce-scatter, and one that makes routing imbalance a real, harder-to-
predict bottleneck that dense-model parallelism never has to deal with."

**The follow-up-proof version**: be ready to explain why all-to-all is a different
collective shape than the four operations in `06_nccl_and_collective_communication.md` —
every GPU exchanges potentially different data with every other GPU based on runtime
routing decisions, rather than a fixed reduction or broadcast pattern known in advance.

**Vocabulary builder**: *router / gating network* (the learned component deciding which
experts process each token), *active vs. total parameters* (the core MoE distinction
driving both capacity and compute-cost claims), *all-to-all* (the communication pattern
expert parallelism requires, distinct from all-reduce/all-gather/reduce-scatter),
*load-balancing loss* (the auxiliary training objective preventing router collapse onto a
small expert subset).

# GPU Scheduling: MIG, Time-Slicing, and the Gang-Scheduling Problem

Part of [Phase 4 — Kubernetes GPU Infrastructure](../README.md#phase-4-kubernetes-gpu-infrastructure).
Builds on
[`09_gpu_operator_and_device_plugin.md`](09_gpu_operator_and_device_plugin.md), which
named — but didn't solve — the default device plugin's whole-GPU-only allocation. This
chapter covers the two real problems that default leaves open: wasted capacity for
small workloads, and coordinating GPUs across multiple pods for one distributed job.

## Clarify

Two genuinely separate scheduling problems get casually lumped together as "GPU
scheduling," and conflating them is a real source of confused answers:

1. **Sub-GPU allocation** — a workload needs less than one whole GPU (a small inference
   endpoint, a notebook, a dev/test job) but the default device plugin only grants whole
   units — MIG and time-slicing are the two real answers.
2. **Multi-GPU/multi-pod coordination** — a distributed training or multi-node inference
   job needs *several* pods (each requesting GPUs) scheduled **together, atomically**,
   because a partial launch is useless — this is the **gang scheduling** problem, and
   Kueue/Volcano exist specifically for it. It has nothing to do with sub-GPU allocation;
   a job needing gang scheduling might be requesting whole GPUs, many of them.

## Core Concepts

### MIG (Multi-Instance GPU) — real hardware partitioning

MIG, available on A100/H100-class GPUs, partitions **a single physical GPU into multiple
fully isolated hardware instances** — each with its own dedicated slice of SMs, its own
dedicated slice of HBM, and its own memory bandwidth, enforced by the hardware itself, not
software scheduling:

```
One A100 80GB, MIG-partitioned into 2 instances (example: 3g.40gb profile):
  ┌─────────────────────┐  ┌─────────────────────┐
  │ MIG Instance 1        │  │ MIG Instance 2        │
  │ 3/7 of SMs             │  │ 3/7 of SMs             │
  │ 40GB HBM (dedicated)   │  │ 40GB HBM (dedicated)   │
  │ own memory bandwidth   │  │ own memory bandwidth   │
  └─────────────────────┘  └─────────────────────┘
  Each instance appears to Kubernetes as its own
  nvidia.com/gpu (or a MIG-specific resource name) —
  two pods can each get one instance, with HARD
  isolation between them.
```

**The property that matters most**: because the partitioning is done in hardware, one
tenant's workload on one MIG instance cannot degrade another tenant's performance on a
different instance on the same physical GPU — no noisy-neighbor risk, which is why MIG is
the answer of choice for genuinely **multi-tenant** GPU sharing (this is the direct
mechanism behind the "multi-tenant GPU isolation" domain in
[`00_mental_model_and_roadmap.md`'s Phase 6 table](../00_mental_model_and_roadmap.md),
not an abstract security concern). The cost: partition sizes are fixed, coarse-grained
profiles chosen at configuration time (not arbitrary fractions), and re-partitioning
requires draining and reconfiguring the GPU — not a live, dynamic operation.

### Time-slicing — software scheduling, no hardware isolation

The alternative, for GPUs without MIG support or when finer-grained/more-flexible sharing
is worth the trade-off: multiple pods are scheduled onto the **same physical GPU**, with
the GPU's own driver-level context-switching handling multiple processes' kernels
time-sliced onto the same SMs/HBM — the same GPU, shared in time, not partitioned in
space.

| | MIG | Time-slicing |
|---|---|---|
| Isolation | Hardware — no cross-tenant interference | None — one tenant's burst of work can slow another's |
| Granularity | Fixed profiles (e.g. 1g.10gb, 3g.40gb) | Arbitrary — any number of pods can share |
| Reconfiguration | Requires draining/reconfiguring the GPU | Purely a scheduler-side config change |
| Right for | Multi-tenant, latency-sensitive, "hard neighbor" concerns | Trusted internal workloads, bursty/low-average-utilization jobs, dev/test |

**A concrete connection worth naming explicitly**: `12_tricky_scenarios_14_gpu_underutilized_sequential_pipeline.md`
(already in `system_design_foundation/`) is exactly the class of problem MIG/time-slicing
solves at the infrastructure level — a GPU sitting mostly idle because a workload doesn't
need the whole device is a scheduling-granularity problem, and this chapter is the
mechanism-level answer that scenario's write-up doesn't itself provide.

### The gang-scheduling problem — a completely different concern

Recall from
[`aws-production-architecture.md`'s autoscaling section](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/aws-production-architecture.md#autoscaling-by-node-group-not-by-pod):
a tensor-parallel group is useless with only some of its GPUs running. Translated into
Kubernetes terms: if a distributed job submits 8 pods (one per GPU, spanning a TP=8
group) and the default scheduler places 5 of them before running out of available
capacity, those 5 pods sit there — consuming GPU allocation, doing no useful work,
**blocking other jobs from using that capacity** — while waiting indefinitely for the
other 3 to schedule. Worse, if two such partial jobs deadlock each other's remaining
capacity, neither ever completes. This is the **gang scheduling problem**: a group of
pods needs to be scheduled **all-or-nothing**, atomically, or not scheduled at all.

The default Kubernetes scheduler has no concept of "these N pods are one unit" — it
schedules pods independently. **Kueue** and **Volcano** are the two real answers:

- **Kueue** — a Kubernetes-native job-queueing layer (a CNCF project) that holds a
  distributed job's pods in a pending queue until *all* the resources the job needs are
  simultaneously available, then admits the whole group at once. Adds fair-sharing and
  quota management across teams/namespaces on top — the piece that answers "who gets the
  next available GPU capacity when multiple teams are competing for it."
- **Volcano** — a batch-scheduling system built specifically for HPC/AI workloads
  (a Kubernetes-native alternative closer in spirit to HPC schedulers like Slurm — see
  [`11_slurm_vs_kubernetes.md`](11_slurm_vs_kubernetes.md)), with gang scheduling as a
  first-class primitive plus bin-packing-aware placement (actively trying to consolidate
  jobs onto fewer nodes to leave larger contiguous blocks of capacity free for future
  large jobs, rather than fragmenting availability).

**Why this can't be solved by just requesting more replicas in a Deployment**: a
Kubernetes Deployment's rolling/incremental pod creation model is exactly the mechanism
that produces the partial-launch problem above — Deployments were never designed for
"all N or none," and retrofitting that guarantee is what Kueue/Volcano's job-level
abstraction (distinct from a Deployment) actually provides.

## Deep-Dive: MIG and gang scheduling are orthogonal, and can combine

A common confusion worth resolving directly: MIG answers "how much of a GPU does one pod
get," gang scheduling answers "do all the pods in this job start together." A large
serving deployment with many small MIG-sliced inference replicas doesn't need gang
scheduling (each replica is independent — a partial rollout is fine, even expected during
a rolling update). A large distributed training job needs gang scheduling regardless of
whether it's requesting whole GPUs or MIG slices. The two mechanisms solve different
axes of the same broader "GPU scheduling" space and are chosen independently based on the
workload's actual shape — not a single "GPU scheduling" decision made once for a cluster.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| MIG | Hard isolation, safe multi-tenancy | Coarse, fixed partition sizes; reconfiguration isn't live |
| Time-slicing | Flexible, works on any GPU generation | No isolation — real noisy-neighbor risk under contention |
| Kueue | Kubernetes-native, good fair-share/quota story | Younger ecosystem than Slurm for the deepest HPC-specific features |
| Volcano | Purpose-built for gang scheduling + bin packing | Another scheduler to operate alongside (or in place of) the default one |

## Failure Modes to Raise Proactively

- **Using time-slicing for genuinely multi-tenant, SLA-bound workloads** — the missing
  hardware isolation means one tenant's burst can silently degrade another's latency
  SLOs, with no error, the same "looks fine until you check" pattern this track keeps
  surfacing at every layer.
- **Submitting a distributed job as an ordinary Deployment/set of independent pods
  without a gang-scheduling layer** — the partial-launch/resource-holding failure
  described above, a real, expensive way to waste cluster capacity silently.
- **Assuming MIG solves the gang-scheduling problem or vice versa** — as the deep-dive
  shows, they're orthogonal; picking one doesn't address the other.

## Make It Yours

- Next time a workload's actual GPU utilization is checked (via DCGM, from
  `09_gpu_operator_and_device_plugin.md`) and it's consistently low, ask explicitly:
  is this a sub-GPU-allocation problem (MIG/time-slicing territory) or a placement/gang-
  scheduling problem — the diagnostic split this chapter's Clarify section opens with.

## Practice Questions

1. Why can't a noisy-neighbor problem occur between two workloads on separate MIG
   instances of the same physical GPU, even though they share the same silicon?
2. A distributed training job's pods are stuck half-scheduled, holding GPU capacity but
   making no progress — what's missing from the cluster's scheduling setup, and what
   would fix it?
3. Why would a large serving deployment made of many small independent inference
   replicas specifically NOT need a gang-scheduling layer, while a training job using the
   same total GPU count would?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "GPU scheduling in Kubernetes splits into two separate
problems. Sub-GPU allocation — letting more than one workload use a single GPU — is
solved by MIG (hardware-partitioned, isolated) or time-slicing (software, no isolation).
Gang scheduling — getting all the pods of one distributed job to start together, or not
at all — is solved by Kueue or Volcano, because the default Kubernetes scheduler treats
pods independently and will happily leave a job half-launched, silently wasting capacity."

**The follow-up-proof version**: be ready to explain why MIG's isolation is a hardware
property, not a scheduler policy — that's what makes it safe for genuinely
untrusted/multi-tenant workloads in a way time-slicing structurally cannot be, no matter
how the scheduler is configured.

**Vocabulary builder**: *gang scheduling* (all-or-nothing atomic scheduling for a group of
pods), *noisy neighbor* (one workload degrading another's performance by sharing an
under-isolated resource), *bin packing* (actively consolidating placements to keep large
contiguous capacity blocks free, as opposed to spreading jobs to minimize per-node load).

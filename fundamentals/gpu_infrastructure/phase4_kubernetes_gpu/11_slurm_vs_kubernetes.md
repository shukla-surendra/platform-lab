# Slurm vs. Kubernetes for GPU Clusters: Why HPC Never Fully Moved to K8s

Part of [Phase 4 — Kubernetes GPU Infrastructure](../README.md#phase-4-kubernetes-gpu-infrastructure).
Closes out Phase 4. Builds on
[`10_gpu_scheduling_mig_sharing.md`](10_gpu_scheduling_mig_sharing.md)'s gang-scheduling
problem — Slurm is worth understanding specifically because it solved that exact problem
natively, decades before Kubernetes needed Kueue/Volcano bolted on to approximate it.

## Clarify

A reasonable-sounding assumption, worth confronting directly: "Kubernetes is the modern
standard, so any serious GPU cluster runs on Kubernetes." This is false for a large,
specific slice of the industry — most of the world's largest AI training clusters (many
frontier-model training runs, most academic/national-lab HPC clusters) run **Slurm**, not
Kubernetes, and this isn't legacy inertia — Slurm solves the training-cluster problem in
ways that are still, today, more native than Kubernetes's approach. Given your existing
Kubernetes/EKS strength, the useful target here isn't "learn Slurm as deeply as
Kubernetes" — it's knowing precisely *why* the split exists, so a "why not just use K8s
for everything" interview follow-up has a real, mechanism-grounded answer.

## Core Concepts

### What Slurm actually is

**Slurm (Simple Linux Utility for Resource Management)** is a batch-job scheduler and
resource manager purpose-built for HPC clusters — it predates Kubernetes by over a
decade and was designed from the start around exactly the workload shape a large training
run has: a fixed-size, all-or-nothing batch job that runs to completion (or checkpoint)
and exits, not a long-running service that needs rolling updates, ingress, or service
discovery.

```
Slurm's core primitives:

  Partition   — a named pool of nodes (e.g. "gpu-h100", "gpu-a100"), the
                rough Slurm analog of a Kubernetes node pool/group, but
                first-class and central to how jobs are submitted.

  QoS         — Quality of Service tiers governing priority, preemption
                rules, and resource limits per user/group — Slurm's
                native answer to the fair-share/priority question Kueue
                (10_gpu_scheduling_mig_sharing.md) was built to bring to
                Kubernetes.

  GRES        — Generic RESource — Slurm's extensible mechanism for
                scheduling non-CPU resources, GPUs included. This is
                Slurm's direct analog to Kubernetes's extended resource
                mechanism from 09_gpu_operator_and_device_plugin.md —
                same underlying problem (schedule a specialized
                resource), independently solved in each system.

  srun/sbatch — submit a job (a fixed node/GPU count, a script to run).
                Slurm's scheduler holds the job until the FULL requested
                allocation is simultaneously available, then launches
                every process together — gang scheduling is Slurm's
                default, native behavior, not an add-on.
```

**The core structural difference from Kubernetes, stated precisely**: Kubernetes's
scheduling unit is the individual pod, with jobs/gang-scheduling as something layered on
top (Kueue, Volcano); Slurm's scheduling unit *is* the multi-node job — atomic,
all-or-nothing allocation was never a retrofit, it's the primitive the whole system was
designed around from day one.

### Why HPC clusters still choose Slurm, as real trade-offs not just tradition

| Dimension | Slurm's native strength | Kubernetes's position |
|---|---|---|
| Gang scheduling | Native, default behavior | Requires Kueue/Volcano — real, workable, but bolted on |
| Tight MPI/NCCL integration | Decades of HPC-specific tuning (`srun` launches MPI ranks directly, topology-aware placement built in) | Works, but the integration is comparatively newer and less battle-tested at extreme scale |
| Fair-share scheduling across many users/groups | Deep, mature priority/preemption/QoS system, purpose-built for shared research clusters | Kueue provides this, competitively, but is a younger, still-maturing subsystem in this specific role |
| Long-running services, rolling updates, service discovery | Not really Slurm's model at all — jobs run and exit | Kubernetes's actual home turf — this is what it was built for |
| Ecosystem breadth (ingress, service mesh, operators, secrets management, GitOps) | Minimal — Slurm doesn't attempt to be a general platform | Kubernetes's other major strength, largely irrelevant to a pure training job but essential for serving |

**The honest framing, since this is a real trade-off and not a "Kubernetes just isn't
there yet" story**: Slurm is better *at the one thing it does* — batch HPC job scheduling
— precisely because it does only that thing and has been refined at that single job for
decades. Kubernetes is better as a general platform because generality was always the
design goal. Choosing between them is choosing which of those two properties the cluster's
actual workload mix needs more.

### The real-world pattern: training on Slurm, serving on Kubernetes

The pattern this split most often produces in practice, and the direct connection back to
this track's earlier chapters: **training clusters skew Slurm, serving/inference
infrastructure skews Kubernetes** — because training is exactly the fixed-size,
all-or-nothing batch job Slurm was built for, while serving is exactly the long-running,
rolling-updated, autoscaled service Kubernetes was built for. This is precisely the shape
of [`aws-production-architecture.md`'s orchestration section](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/aws-production-architecture.md#orchestration-the-actual-deployment-shape)'s
EKS+KubeRay choice — that doc is describing the *serving* side of this exact split, where
Kubernetes is the natural fit, without needing to name Slurm as the training-side
counterpart that a real end-to-end platform typically also operates.

AWS's own product lineup reflects this same split: **SageMaker HyperPod** offers both a
Slurm-orchestrated mode and an EKS-orchestrated mode for large training clusters
specifically because both are genuinely live options in production, not because one has
superseded the other.

## Deep-Dive: what "topology-aware placement" means concretely in each system

Both systems claim to place jobs with network topology in mind, but the maturity differs
in a way worth being specific about: Slurm's scheduler has long had built-in awareness of
fabric topology (which nodes are closer together on the InfiniBand fabric from
[`07_rdma_roce_infiniband.md`](../phase3_gpu_networking/07_rdma_roce_infiniband.md)) and
can preferentially pack a job's nodes to minimize hop count directly as a scheduling
input. Kubernetes's answer to the same problem is comparatively coarser and newer —
cluster placement groups (the AWS-level mechanism from
`07_rdma_roce_infiniband.md`) plus node affinity/anti-affinity rules a job author sets
explicitly — Kubernetes itself doesn't natively reason about fabric topology as a
first-class scheduling signal the way Slurm's scheduler traditionally has, which is a
concrete instance of "gang scheduling and topology-awareness were retrofitted, not
native."

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| Slurm for the training cluster | Native gang scheduling, deep HPC/MPI tuning, mature fair-share | A separate system to operate alongside any Kubernetes-based serving infrastructure |
| Kubernetes (with Kueue/Volcano) for everything | One platform, one operational model, reuses existing EKS/Kubernetes expertise | Retrofitted gang-scheduling/topology-awareness is real but younger than Slurm's decades of refinement at exactly this job |
| SageMaker HyperPod (either mode) | AWS-managed, reduces the operational burden of either choice | Less control than self-managed, and still requires choosing Slurm-mode vs. EKS-mode based on the same trade-offs above |

## Failure Modes to Raise Proactively

- **Assuming Kubernetes is a strict, drop-in upgrade over Slurm for training workloads**
  — as shown above, Slurm's gang scheduling and topology-awareness are native and mature
  where Kubernetes's are retrofitted and younger; a real regression is possible if this
  trade-off isn't evaluated honestly for a training-heavy workload.
- **Assuming Slurm could replace Kubernetes for a serving deployment** — the reverse
  mistake; Slurm has no native answer to rolling updates, service discovery, or
  autoscaling a long-running endpoint, because it was never designed for that workload
  shape.
- **Not naming the training-vs-serving split explicitly in a system-design answer** — a
  candidate who names only Kubernetes for an end-to-end "how would you build this AI
  platform" question is missing half the real picture that most production shops
  actually operate.

## Make It Yours

- Next time a system-design conversation touches "how do you run training at scale,"
  explicitly name the Slurm option alongside Kubernetes+Kueue/Volcano, and state which
  one you'd pick for a given cluster's actual mix of training vs. serving workloads —
  rather than defaulting to Kubernetes because it's the tool already familiar from
  `k8n_explorer/`.

## Practice Questions

1. Why was gang scheduling never something Slurm needed to "add" the way Kubernetes
   needed Kueue/Volcano — what's different about Slurm's original design assumption?
2. A company runs both large training jobs and production LLM serving — what's the
   likely reasoning behind operating Slurm for one and Kubernetes for the other, rather
   than standardizing on a single scheduler for both?
3. What does "topology-aware placement" mean concretely, and why is it a more native,
   longstanding capability in Slurm than in Kubernetes?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "Slurm is a batch scheduler purpose-built for HPC decades
before Kubernetes existed, with gang scheduling and topology-aware placement as native,
default behavior rather than something layered on. Kubernetes's scheduling unit is the
individual pod, with tools like Kueue and Volcano retrofitting gang scheduling on top.
In practice, this produces a real split: training clusters — fixed-size, all-or-nothing
batch jobs — skew Slurm, while serving infrastructure — long-running, rolling-updated,
autoscaled — skews Kubernetes, and a lot of real production AI platforms operate both."

**The follow-up-proof version**: be ready to name the concrete mechanism difference —
Slurm's job (not pod) as the atomic scheduling unit — rather than a vague "Slurm is more
mature for HPC" claim, and be ready to name SageMaker HyperPod's dual-mode design as
direct evidence this is a live, current trade-off, not a solved-in-Kubernetes's-favor
question.

**Vocabulary builder**: *partition* (Slurm's named node pool, the rough analog of a
Kubernetes node group), *QoS/fair-share* (priority and resource-limit policy across
users/groups, native in Slurm, added via Kueue in Kubernetes), *GRES* (Generic RESource
— Slurm's extensible non-CPU resource scheduling mechanism, the direct analog of
Kubernetes's extended resources).

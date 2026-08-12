# Multi-Cloud GPU Landscape: What's Actually Different Across AWS, Azure, GCP, and OCI

Part of [Phase 6 — Production Operations](../README.md#phase-6-production-operations).
Builds directly on
[`aws-production-architecture.md`](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/aws-production-architecture.md),
this track's existing deep-dive into AWS's GPU infrastructure. This chapter doesn't
repeat that depth for every cloud — it names the equivalent building blocks on Azure,
GCP, and OCI, and, more importantly, states which parts of the AWS-specific reasoning
generalize unchanged and which parts are genuinely cloud-specific.

## Clarify

A common, avoidable interview mistake: presenting deep AWS-specific knowledge (EFA,
FSx for Lustre, SageMaker LMI) as if it's universal GPU-infrastructure knowledge, then
being unable to answer "what would this look like on GCP" at all. The underlying
mechanisms this entire track has covered — NVLink/NVSwitch topology, RDMA, gang
scheduling, quantization, fleet lifecycle — are **vendor-neutral**; what's genuinely
cloud-specific is narrow: the instance/VM naming, the specific network-fabric product,
and the managed-orchestration product layered on top. This chapter is that narrow,
cloud-specific delta, named explicitly so it's not confused with the vendor-neutral
mechanism underneath it.

## Core Concepts

### The instance/VM lineup, compared directly against the AWS reference already covered

```
AWS (already covered in aws-production-architecture.md)
  p5.48xlarge      8× H100 80GB, NVSwitch, EFA (~3200 Gbps)
  trn2/inf2        AWS custom silicon (Trainium2/Inferentia2)

Azure
  ND H100 v5       8× H100 80GB, NVSwitch, InfiniBand (NDR, ~3200 Gbps
                     class) — structurally the closest analog to
                     p5.48xlarge: same GPU generation, same NVSwitch
                     topology claim (05_nvlink_nvswitch_topology.md's
                     reasoning applies identically), InfiniBand instead
                     of EFA as the cross-node fabric
                     (07_rdma_roce_infiniband.md's point that EFA/
                     InfiniBand/RoCE are three implementations of the
                     same RDMA idea is exactly the fact that makes this
                     substitution a naming difference, not a mechanism
                     difference)
  NC-series         Smaller-scale, often A100/older-generation GPUs —
                     the Azure analog of a mid-tier, non-flagship
                     instance family

GCP
  A3 (H100)         8× H100, NVSwitch, GPUDirect-TCPX or newer GPUDirect-
                     RDMA-over-network-fabric options — same underlying
                     RDMA/GPUDirect mechanism from
                     07_rdma_roce_infiniband.md, GCP's own network-fabric
                     implementation of it
  A2 (A100)         Older-generation GPU family, GCP's equivalent
                     positioning to Azure's NC-series

OCI (Oracle Cloud Infrastructure)
  BM.GPU.H100.8     Bare-metal (not virtualized) 8× H100 offering —
                     worth naming specifically because OCI's GPU
                     positioning has leaned harder into bare-metal
                     availability than the other three, relevant if a
                     workload's performance requirements make
                     virtualization overhead itself a concern
```

**The organizing fact underneath this comparison**: every cloud's flagship 8-GPU offering
converges on the same physical shape — 8× H100 (or newer), NVSwitch intra-node, some
RDMA-capable fabric cross-node — because that shape is dictated by NVIDIA's reference
architecture (the DGX/HGX platform design), not by each cloud independently
reinventing GPU-server design. **This is why `05_nvlink_nvswitch_topology.md`'s and
`03_gpu_architecture.md`'s reasoning transfers directly across clouds** — the hardware
topology claims aren't AWS-specific facts that happen to also be true elsewhere, they're
facts about NVIDIA's reference platform that every hyperscaler's flagship offering
implements.

### What's genuinely cloud-specific — the narrow, real delta

| Layer | AWS | Azure | GCP | OCI |
|---|---|---|---|---|
| Cross-node fabric | EFA | InfiniBand (NDR) | GPUDirect-TCPX / newer fabric | RoCE-based |
| Parallel filesystem | FSx for Lustre | Azure Managed Lustre | Parallelstore / Filestore | (varies, often self-managed Lustre) |
| Managed serving/training orchestration | SageMaker (LMI containers, HyperPod) | Azure Machine Learning | Vertex AI | OCI Data Science / self-managed |
| Bare-metal option | Not the default posture | Not the default posture | Not the default posture | **Explicit bare-metal GPU shapes** |

**Why this table, not the instance-naming table, is the one worth memorizing**: the
instance names change yearly as new GPU generations ship; the *categories* in this table
— fabric, parallel filesystem, managed orchestration, virtualization posture — are the
stable questions worth asking about any cloud, new or unfamiliar, rather than
memorizing a name that will be outdated by the next hardware generation.

### What transfers unchanged, stated explicitly

Everything this track has built *except* the specific product names in the table above
transfers directly to any cloud, because it describes either NVIDIA hardware behavior or
general distributed-systems mechanism, not an AWS-specific fact:

- GPU architecture, HBM bandwidth, Tensor Cores (Phase 2) — pure hardware, zero cloud
  dependency.
- NCCL's algorithm selection and topology-awareness (Phase 3) — NCCL is NVIDIA's library,
  runs identically everywhere; only the underlying fabric provider it dispatches to
  (EFA vs. InfiniBand vs. GCP's fabric) changes, per
  [`07_rdma_roce_infiniband.md`](../phase3_gpu_networking/07_rdma_roce_infiniband.md#infiniband-roce-and-efa-three-implementations-of-the-same-idea).
- Kubernetes GPU Operator, device plugin, MIG, Kueue/Volcano gang scheduling (Phase 4) —
  Kubernetes-native, works identically on EKS, AKS, GKE, or self-managed Kubernetes on
  OCI.
- Quantization, TTFT/TPOT tuning, memory estimation (Phase 5) — model/workload
  mathematics, no cloud dependency at all.
- FSDP/ZeRO, MoE (Phase 7) — training-framework mechanics, cloud-agnostic.
- Fleet lifecycle, XID errors, the metric catalog (Phase 6, this chapter's siblings) — the
  *concepts* transfer everywhere; only the specific managed-service names for
  implementing each stage change.

**The interview-ready framing this produces**: "I know AWS's specific implementation in
depth, and everything underneath it — the hardware, NCCL, Kubernetes, the model math —
is identical on any cloud; the part that's genuinely new when moving clouds is narrow:
which fabric product, which parallel filesystem, which managed orchestration layer."

## Deep-Dive: bare-metal vs. virtualized GPU access, and why OCI's positioning is worth naming specifically

A detail worth being precise about rather than glossing over: AWS, Azure, and GCP's GPU
instances are virtualized (running on a hypervisor, even if GPU access itself is
passed through with near-native performance via PCIe passthrough/SR-IOV). OCI has
leaned harder into offering **bare-metal** GPU shapes as a first-class, default-path
option — no hypervisor layer between the OS and the physical hardware at all. The
practical implication, connecting to
[`02_computer_architecture_pcie_numa.md`](../phase1_systems/02_computer_architecture_pcie_numa.md):
bare-metal removes any hypervisor-introduced overhead from the PCIe/NUMA path this
chapter's sibling already covers, which can matter for workloads sensitive to the last
few percent of interconnect latency — a genuine, if narrow, differentiator worth naming
rather than treating all four clouds as interchangeable at this level.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| Deep expertise on one cloud (e.g. AWS, per this track's existing depth) | Fast, confident execution on that platform | Risk of the "AWS-specific knowledge presented as universal" mistake this chapter opened with |
| Broad, shallow multi-cloud familiarity | Can speak to any platform in an interview | Less deployable expertise on any single one without further depth |
| Bare-metal GPU access (OCI-style) | Removes hypervisor overhead entirely | Less operational flexibility (live migration, some virtualization-dependent management features) than a virtualized offering |

## Failure Modes to Raise Proactively

- **Presenting AWS-specific product names (EFA, FSx for Lustre, SageMaker) as if they're
  universal GPU-infrastructure vocabulary** — the exact mistake this chapter exists to
  correct; naming the vendor-neutral mechanism underneath (RDMA, parallel filesystem,
  managed orchestration) first, then the AWS-specific instance, is the stronger pattern.
- **Assuming every cloud's GPU instances are virtualized the same way** — OCI's
  bare-metal-first posture is a real, checkable difference, not a marketing distinction.
- **Treating instance-name comparisons as the valuable part of multi-cloud knowledge**
  — as argued above, the category-level comparison (fabric, filesystem, orchestration,
  virtualization posture) ages far better than specific instance names.

## Make It Yours

- Practice restating any AWS-specific claim from
  `aws-production-architecture.md` in cloud-neutral terms first ("a fast, RDMA-capable
  cross-node fabric" before "EFA specifically"), then naming the AWS product — the habit
  that prevents the failure mode this chapter opened with.

## Practice Questions

1. Why does `05_nvlink_nvswitch_topology.md`'s NVSwitch reasoning apply identically to
   Azure's ND H100 v5 instances without modification, despite that chapter never
   mentioning Azure?
2. What's the one narrow category of difference that actually matters when moving a
   GPU-infrastructure design from AWS to GCP, and what stays completely unchanged?
3. Why might a workload choose OCI's bare-metal GPU shapes specifically, in terms of the
   PCIe/NUMA mechanism from `02_computer_architecture_pcie_numa.md`?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "Every hyperscaler's flagship GPU offering converges on the
same physical shape — 8× H100-class GPUs, NVSwitch intra-node, an RDMA-capable fabric
cross-node — because that shape comes from NVIDIA's reference platform design, not
independent cloud engineering. What's actually cloud-specific is narrow: which fabric
product (EFA vs. InfiniBand vs. GCP's own), which parallel filesystem, and which managed
orchestration layer sits on top. Everything about the hardware, NCCL, Kubernetes GPU
scheduling, and the model math is identical regardless of cloud."

**The follow-up-proof version**: be ready to restate any cloud-specific claim in
vendor-neutral terms first, then name the specific product — demonstrating the knowledge
generalizes rather than being memorized as AWS trivia.

**Vocabulary builder**: *reference platform* (NVIDIA's own DGX/HGX server design that
every cloud's flagship GPU instance implements), *bare-metal* (no hypervisor layer between
OS and physical hardware, OCI's differentiated positioning), *PCIe passthrough/SR-IOV*
(the mechanisms virtualized clouds use to give a VM near-native GPU access despite the
hypervisor layer).

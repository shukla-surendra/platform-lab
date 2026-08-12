# Security & Multi-Tenant GPU Isolation: What Actually Enforces the Boundary

Part of [Phase 6 — Production Operations](../README.md#phase-6-production-operations).
Closes out Phase 6. Builds directly on
[`10_gpu_scheduling_mig_sharing.md`](../phase4_kubernetes_gpu/10_gpu_scheduling_mig_sharing.md)'s
MIG-vs-time-slicing isolation distinction — this chapter is where that distinction becomes
a security property, not just a performance-isolation one, and extends it to the other
layers a genuinely multi-tenant GPU fleet has to secure.

## Clarify

"Multi-tenant GPU security" sounds like it might mean encryption or access control in the
generic cloud-security sense — and those apply, but they're not the hard, GPU-specific
part. The hard part, and the part worth being precise about in an interview, is: **what
physically/architecturally prevents one tenant's workload from reading another tenant's
data or interfering with their performance when both share the same physical GPU or
node** — a question generic cloud security knowledge doesn't answer, because it's
specific to how GPUs are actually partitioned (or not) at the hardware level.

## Core Concepts

### The isolation spectrum, revisited as a security property

[`10_gpu_scheduling_mig_sharing.md`](../phase4_kubernetes_gpu/10_gpu_scheduling_mig_sharing.md)
already established MIG vs. time-slicing as a *performance*-isolation distinction (noisy
neighbor risk). The same distinction is the actual answer to "is this GPU-sharing
approach safe for mutually untrusted tenants":

```
MIG — hardware-partitioned instances, each with dedicated SM slice,
      dedicated HBM slice, dedicated memory bandwidth
  → Genuine security boundary: one tenant's MIG instance cannot read
    another's memory or observe its computation, because the hardware
    itself enforces separate address spaces and separate compute
    resources — this is the same category of guarantee as separate
    physical machines, not a software promise layered on shared
    hardware.

Time-slicing — software-scheduled sharing of the SAME physical SMs
               and HBM, sequentially in time
  → NOT a security boundary. Different tenants' processes run on the
    identical physical memory cells and compute units, just at
    different moments — this is a performance-sharing mechanism, and
    presenting it as tenant isolation in a security-sensitive context
    is a real, checkable mistake (the same failure mode
    10_gpu_scheduling_mig_sharing.md names for performance reasons,
    now stated as a security gap specifically).

Whole-GPU allocation (the device plugin's default,
09_gpu_operator_and_device_plugin.md) — one tenant per physical GPU,
no sharing at all
  → Trivially secure (no sharing means no cross-tenant surface at all)
    but wastes capacity for tenants that don't need a whole GPU — the
    same under-utilization problem 10_gpu_scheduling_mig_sharing.md
    names, now viewed as the cost of choosing security over efficiency
    by default.
```

**The interview-ready one-line rule**: MIG or dedicated whole-GPU allocation for
genuinely untrusted, security-sensitive multi-tenancy; time-slicing only for trusted
internal workloads where the risk is purely performance interference, never data
exposure — because time-slicing provides no protection against the latter at all.

### Confidential computing — extending the boundary against the infrastructure operator itself

A distinct, additional threat model worth naming: MIG protects tenants from *each other*,
but does it protect a tenant's data from the **cloud provider or infrastructure operator**
itself (a hypervisor-level or host-OS-level actor with elevated privileges)? For
particularly sensitive workloads, **confidential computing** extends isolation to cover
this case — NVIDIA H100-class GPUs support a confidential computing mode that encrypts
GPU memory and establishes a hardware-attested trusted execution environment, so that
even someone with host-level access cannot inspect the GPU's memory contents or
computation. This is a meaningfully stronger (and more expensive/complex to operate)
guarantee than MIG alone, and the two solve different threat models — MIG assumes the
infrastructure operator is trusted and only tenants need isolation from each other;
confidential computing removes that assumption.

### Network-layer isolation for the multi-node case

Everything above addresses one physical GPU or node. A multi-tenant *cluster* spanning
many nodes needs the network-layer equivalent: ensuring one tenant's cross-node NCCL
traffic (per
[`06_nccl_and_collective_communication.md`](../phase3_gpu_networking/06_nccl_and_collective_communication.md))
cannot be observed or interfered with by another tenant sharing the same physical
fabric. In Kubernetes terms, this is standard **network policy** enforcement (restricting
which pods/namespaces can communicate) applied to RDMA/EFA traffic specifically, not just
ordinary pod-to-pod networking — worth naming explicitly because RDMA's kernel-bypass
property (per
[`07_rdma_roce_infiniband.md`](../phase3_gpu_networking/07_rdma_roce_infiniband.md#core-concepts))
means it doesn't automatically inherit the same enforcement points ordinary, kernel-
mediated networking does — this has to be a deliberate configuration choice, not an
assumed default.

### Credential and secrets isolation — the ordinary-but-still-necessary layer

Alongside the GPU-specific mechanisms above, genuinely multi-tenant serving still needs
the standard cloud-security fundamentals: per-tenant API credentials, secrets management
(model weights, API keys) scoped so one tenant's serving pod cannot access another
tenant's secrets, and namespace/RBAC boundaries in Kubernetes. This layer isn't
GPU-specific — it's worth naming explicitly in an interview answer specifically to show
the full picture (hardware isolation AND access control together), rather than treating
GPU-specific isolation as the whole answer to "how do you secure a multi-tenant AI
platform."

## Deep-Dive: the layered answer to "is this multi-tenant deployment actually secure"

Putting every layer from this chapter into one ordered checklist, the way a real security
review would actually proceed:

```
1. Compute isolation: MIG (or whole-GPU) for untrusted tenants sharing
   physical hardware — NOT time-slicing, per the isolation spectrum
2. Memory/compute confidentiality from the infrastructure operator
   itself: confidential computing, if the threat model requires it
3. Network isolation: RDMA/EFA traffic scoped by network policy, not
   just ordinary pod networking, for multi-node multi-tenant clusters
4. Credential/secrets isolation: standard per-tenant RBAC/secrets
   scoping, the non-GPU-specific but still load-bearing layer
```

A strong answer to a security-focused system-design question names all four layers
explicitly and states which threat each one addresses — a common, weaker answer
conflates them, most often by treating "we use Kubernetes namespaces" (layer 4) as
sufficient without addressing layer 1's much harder, GPU-specific compute-isolation
question at all.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| MIG for multi-tenant sharing | Real hardware-enforced isolation, still allows sub-GPU sharing/efficiency | Coarse, fixed partition sizes (per `10_gpu_scheduling_mig_sharing.md`) |
| Whole-GPU-per-tenant | Simplest, trivially secure | Most wasteful for tenants needing less than a full GPU |
| Confidential computing | Protects against infrastructure-operator-level threats, not just cross-tenant | Real performance overhead and operational complexity; only justified when that specific threat model applies |

## Failure Modes to Raise Proactively

- **Presenting time-slicing as a security/isolation mechanism** — the single most
  important correction this chapter makes; it provides zero protection against one
  tenant's process reading another's data on the same physical SMs/HBM.
- **Addressing only credential/RBAC isolation (layer 4) and treating that as sufficient
  for a multi-tenant GPU platform** — misses the much harder compute-isolation question
  entirely, a common, checkable gap in a security-focused answer.
- **Assuming RDMA/EFA traffic is automatically covered by standard Kubernetes network
  policy the same way ordinary pod networking is** — RDMA's kernel-bypass property means
  this needs deliberate, explicit configuration, not an assumed default.

## Make It Yours

- Next time a multi-tenant GPU deployment is discussed (in this workspace or elsewhere),
  explicitly ask which of the four layers in this chapter's deep-dive checklist are
  actually in place, rather than accepting "it's isolated" as a sufficient answer on its
  own.

## Practice Questions

1. Why does time-slicing provide meaningfully weaker guarantees than MIG specifically for
   security-sensitive multi-tenancy, even though both let multiple tenants share one
   physical GPU?
2. What threat does confidential computing protect against that MIG alone does not, and
   why would a team need both rather than treating them as interchangeable?
3. A team secures a multi-tenant GPU cluster with strict Kubernetes RBAC and namespace
   isolation but uses time-slicing for GPU sharing — what's the actual security gap in
   this setup?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "Multi-tenant GPU security has a layer generic cloud security
doesn't cover: what actually enforces the boundary when two tenants share a physical GPU.
MIG is a real hardware-enforced boundary — separate SM and HBM slices, no shared address
space. Time-slicing is not — it's software-scheduled sharing of the identical physical
memory and compute, fine for trusted internal workloads but not a security boundary for
untrusted tenants. On top of that, confidential computing extends isolation to protect
against the infrastructure operator itself, and standard RBAC/secrets scoping is still
needed as the non-GPU-specific fourth layer."

**The follow-up-proof version**: be ready to state precisely why time-slicing fails as a
security mechanism — same physical memory cells, sequential not simultaneous access,
meaning a sufficiently motivated co-tenant process could in principle observe residual
data — rather than a vague "it's less isolated" claim.

**Vocabulary builder**: *trusted execution environment (TEE)* (a hardware-attested,
encrypted execution context — the mechanism behind confidential computing), *threat model*
(explicitly naming who/what a security mechanism protects against — cross-tenant vs.
infrastructure-operator-level threats are different models requiring different
mechanisms), *RBAC* (role-based access control — the standard Kubernetes mechanism for
credential/secrets scoping, layer 4 of this chapter's checklist).

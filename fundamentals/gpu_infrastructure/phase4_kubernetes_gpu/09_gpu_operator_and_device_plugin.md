# The GPU Operator & Device Plugin: How a GPU Becomes a Schedulable Kubernetes Resource

Part of [Phase 4 — Kubernetes GPU Infrastructure](../README.md#phase-4-kubernetes-gpu-infrastructure).
This chapter assumes Kubernetes fundamentals (pods, nodes, scheduling primitives) are
already solid, per this workspace's `k8n_explorer/` background — it covers only the
GPU-specific layer that sits on top of that, per the roadmap doc's skill-level framing.

## Clarify

`kubectl get nodes -o json` on an ordinary Kubernetes cluster shows CPU and memory as
schedulable resources — never GPUs, by default. Kubernetes has no built-in concept of a
GPU. Everything that makes `resources.limits: {nvidia.com/gpu: 1}` in a pod spec actually
mean something — visibility, allocation, health monitoring — is added on by a specific,
nameable set of components. This chapter is what those components are and how they fit
together, since "install the GPU Operator" is otherwise a black-box instruction.

## Core Concepts

### Why Kubernetes needs help to see a GPU at all

Kubernetes's scheduler allocates based on **extended resources** — named, quantifiable
things a node advertises (`cpu`, `memory` are built in; anything else, including GPUs,
has to be advertised by something running on the node). Nothing in Kubernetes core knows
what a GPU is, how many exist on a node, or how to expose one into a container. That gap
is filled by the **device plugin framework** — a Kubernetes extension point specifically
designed for hardware resources like this (also used for other specialized hardware:
FPGAs, other accelerators) — and NVIDIA's implementation of it, the **NVIDIA device
plugin**.

### The NVIDIA device plugin — the actual mechanism

```
Node with 8 GPUs, before device plugin:
  kubectl describe node → no nvidia.com/gpu entry at all, GPUs invisible
                            to the scheduler

NVIDIA device plugin (runs as a DaemonSet, one pod per GPU node):
  1. Discovers GPUs on the node via NVML (the same library from
     04_cuda_ecosystem.md that nvidia-smi is built on)
  2. Registers "nvidia.com/gpu" as an extended resource with the
     kubelet, advertising a count (e.g. 8)
  3. When a pod requests nvidia.com/gpu: 1, the plugin is responsible
     for actually granting that container access to one specific
     physical GPU device (via the container runtime's device
     mounting mechanism) — the pod's process gets a real GPU it can
     call CUDA against, not a virtualized/simulated one

Node with device plugin running:
  kubectl describe node → Capacity: nvidia.com/gpu: 8
                           Allocatable: nvidia.com/gpu: 8
```

**The critical, easy-to-miss default behavior**: the stock NVIDIA device plugin allocates
GPUs as **whole units** — `nvidia.com/gpu: 1` means one entire physical GPU, exclusively,
for that container's lifetime. There's no built-in fractional/shared GPU support at this
layer — that's what MIG and time-slicing (covered in
[`10_gpu_scheduling_mig_sharing.md`](10_gpu_scheduling_mig_sharing.md)) exist to add on
top, not something the base device plugin does itself.

### The NVIDIA GPU Operator — bundling the whole stack as Kubernetes-managed components

The device plugin alone isn't sufficient for a working GPU node — it assumes the NVIDIA
driver, container toolkit, and monitoring stack are already correctly installed on the
host. Historically, that meant manually installing drivers matching each node's OS/kernel
version outside Kubernetes entirely — a real operational burden at fleet scale, and a
direct source of the version-mismatch failures already named in
[`04_cuda_ecosystem.md`](../phase2_gpu_fundamentals/04_cuda_ecosystem.md#deep-dive-diagnosing-a-version-mismatch-failure-by-layer).

The **GPU Operator** is NVIDIA's answer: it packages the entire stack this track has
already named — driver, container toolkit, device plugin, DCGM (for monitoring), GPU
Feature Discovery — as Kubernetes-native components (mostly DaemonSets and a controller),
so the whole stack is installed, versioned, and upgraded *through Kubernetes itself*
rather than through separate host-level configuration management:

```
NVIDIA GPU Operator (installed via Helm, one release):
  ├── NVIDIA Driver (as a containerized DaemonSet — installs the driver
  │     onto the host from inside a privileged container, rather than a
  │     separate host-provisioning step)
  ├── NVIDIA Container Toolkit (lets the container runtime expose GPUs
  │     into containers at all — the low-level plumbing the device
  │     plugin's "grant access" step in the diagram above relies on)
  ├── Device Plugin (the component described above)
  ├── DCGM + dcgm-exporter (from 04_cuda_ecosystem.md — now deployed
  │     as a DaemonSet automatically, feeding Prometheus per-node)
  ├── GPU Feature Discovery (labels each node with its actual GPU
  │     model, driver version, CUDA capability — see below)
  └── MIG Manager (if MIG is enabled — 10_gpu_scheduling_mig_sharing.md)
```

**Why this matters as an operational decision, not just a convenience**: running the
driver as a Kubernetes-managed DaemonSet means a driver version upgrade is a Kubernetes
rollout (with all the rollout-control tooling that implies), not a fleet-wide manual SSH
operation — directly reducing the surface area for the version-mismatch class of incident
`04_cuda_ecosystem.md` walked through, by making "which driver version is on this node"
a Kubernetes-visible, Kubernetes-managed fact instead of host-level drift.

### GPU Feature Discovery — making heterogeneous fleets schedulable correctly

A real fleet is rarely one GPU model — A100 nodes, H100 nodes, and older nodes coexist.
**GPU Feature Discovery (GFD)** labels each node with detailed, specific facts about its
actual GPU hardware (`nvidia.com/gpu.product=NVIDIA-H100-80GB-HBM3`, driver version, CUDA
compute capability, MIG configuration if any). This is what lets a pod spec use a
**node selector or affinity rule** to require a specific GPU generation — e.g. a workload
depending on FP8 support (from
[`13_quantization.md`](../phase5_llm_serving/13_quantization.md#the-precision-ladder))
can require H100-or-newer nodes specifically, rather than landing on an A100 node where
that code path silently isn't accelerated the way it was assumed to be.

## Deep-Dive: the full path from pod spec to running CUDA code

Tracing one request through every layer named so far:

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
```

1. The **scheduler** sees this pod requests an extended resource `nvidia.com/gpu` and
   only considers nodes where the **device plugin** has advertised availability.
2. The device plugin, on the chosen node, grants the container access to one specific
   physical GPU via the **NVIDIA Container Toolkit**'s runtime hook.
3. Inside the container, `nvidia-smi` now shows exactly one GPU — the driver (installed
   by the GPU Operator's driver DaemonSet on the host, per
   [`04_cuda_ecosystem.md`](../phase2_gpu_fundamentals/04_cuda_ecosystem.md#driver-vs-toolkit-the-version-rule-that-prevents-the-most-common-failure))
   is what makes that visible.
4. Application code (PyTorch, vLLM) calls into cuBLAS/cuDNN/NCCL as already covered,
   ultimately reaching the Tensor Cores from
   [`03_gpu_architecture.md`](../phase2_gpu_fundamentals/03_gpu_architecture.md).
5. **DCGM**, deployed by the same Operator, is simultaneously scraping this GPU's real
   utilization/HBM-bandwidth/health metrics into Prometheus, independent of what the
   application itself reports.

Every layer in this track's Phases 2-3 has a corresponding, concrete Kubernetes-managed
component in this trace — nothing here is a new concept, just the Kubernetes plumbing
that makes those concepts reachable from a pod spec.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| GPU Operator (full stack via Kubernetes) | Consistent, versioned, auditable driver/toolkit state across the fleet; upgrades are Kubernetes rollouts | Adds the Operator's own upgrade/compatibility surface to manage |
| Manually install drivers/toolkit on hosts, device plugin only via Kubernetes | More direct control per-node | Reintroduces the exact host-level drift/version-mismatch risk the Operator exists to remove |
| Whole-GPU allocation (device plugin default) | Simple, predictable, no noisy-neighbor risk between pods on the same GPU | Wastes capacity for workloads that don't need a full GPU — the problem `10_gpu_scheduling_mig_sharing.md` addresses |

## Failure Modes to Raise Proactively

- **Assuming `nvidia.com/gpu: 1` in a pod spec is self-sufficient without checking the
  Operator/device plugin is actually healthy on that node** — a node where the device
  plugin pod has crashed or hasn't started still shows as GPU-less to the scheduler; pods
  simply stay Pending, which reads as a scheduling problem rather than the actual
  device-plugin-health problem.
- **Treating all nodes as GPU-interchangeable in pod specs without GFD-based node
  selectors** — in a mixed-generation fleet, a workload that needs FP8 or a specific
  memory footprint can silently land on hardware that doesn't support it, without an
  explicit affinity rule constraining placement.
- **Upgrading the GPU Operator without checking driver/CUDA compatibility against running
  workloads' container images first** — the exact version-pairing rule from
  `04_cuda_ecosystem.md`, now at fleet-upgrade scale rather than single-container scale.

## Make It Yours

- On any Kubernetes cluster with GPU nodes you have access to, run
  `kubectl describe node <gpu-node>` and find the `nvidia.com/gpu` capacity line and the
  GFD-applied labels — name which specific GPU Operator component produced each piece of
  information you're looking at.
- Compare `k8n_explorer/`'s existing Kubernetes fundamentals against this chapter: name
  precisely which Kubernetes primitive (DaemonSet, extended resource, node label/affinity)
  each GPU Operator component reuses, rather than treating GPU support as an entirely
  separate system bolted on.

## Practice Questions

1. Why can't the Kubernetes scheduler place a GPU workload correctly with no device
   plugin running, even if the driver and CUDA toolkit are both correctly installed on
   the host?
2. What specific operational risk does running the NVIDIA driver as a GPU-Operator-managed
   DaemonSet reduce, compared to installing it via host-level configuration management?
3. In a fleet with both A100 and H100 nodes, what mechanism ensures an FP8-dependent
   workload doesn't get scheduled onto an A100 node, and what happens if that mechanism
   isn't configured?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "Kubernetes has no built-in concept of a GPU — the NVIDIA
device plugin, running as a DaemonSet, discovers GPUs via NVML and advertises them to the
scheduler as an extended resource, then grants container access to a specific physical
GPU when scheduled. The GPU Operator bundles that plugin together with the driver,
container toolkit, DCGM monitoring, and GPU Feature Discovery as Kubernetes-managed
components, so the whole GPU stack is installed and upgraded through Kubernetes instead
of separate host-level provisioning."

**The follow-up-proof version**: be ready to trace a pod spec's `nvidia.com/gpu: 1`
request all the way to a running CUDA call, naming which specific component is
responsible at each step — scheduler, device plugin, container toolkit, driver — rather
than describing GPU support as one undifferentiated "GPU Operator does it" black box.

**Vocabulary builder**: *extended resource* (Kubernetes's mechanism for scheduling
non-CPU/memory resources like GPUs, FPGAs), *device plugin framework* (the Kubernetes
extension point the NVIDIA device plugin implements), *DaemonSet* (one pod per matching
node — the deployment shape used by the device plugin, driver, and DCGM exporter alike,
because each needs to run on every GPU node specifically).

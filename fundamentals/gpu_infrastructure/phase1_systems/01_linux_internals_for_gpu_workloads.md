# Linux Internals for GPU Workloads: The GPU-Specific Layer on Familiar Ground

Part of [Phase 1 — Systems Foundations](../README.md#phase-1-systems-foundations).
Per [`00_mental_model_and_roadmap.md`'s skill-level table](../00_mental_model_and_roadmap.md#three-skill-levels-and-where-you-already-are),
this is rated "Have it" given 10+ years of AIOps/MLOps background — procfs, scheduling,
and NUMA fundamentals are assumed, not re-derived here. This chapter is scoped tightly to
what's actually GPU-specific on top of that foundation: the handful of Linux mechanisms
that behave differently, or matter differently, once a GPU is in the picture.

## Clarify

Ordinary Linux process/scheduling knowledge transfers almost entirely to a GPU-hosting
machine — a CUDA application is still just a Linux process, still scheduled by the same
kernel scheduler, still subject to the same memory management. What's genuinely different
is narrow and specific: how the kernel exposes GPU-relevant hardware topology, how CPU-
GPU affinity actually gets set (not just CPU-CPU affinity, already familiar), and how
interrupts from the GPU get routed. This chapter is only that delta.

## Core Concepts

### `/proc` and `/sys` — where GPU-adjacent hardware facts actually live

Standard procfs/sysfs knowledge extends directly here — the GPU-specific facts worth
knowing the exact location of:

```bash
# PCIe topology and device info (the kernel's view, independent of
# nvidia-smi — useful when nvidia-smi itself is the thing misbehaving)
lspci -vvv -s <gpu-pci-address>       # detailed PCIe link info: negotiated
                                        # generation and width — see
                                        # 02_computer_architecture_pcie_numa.md
                                        # for why this specific number matters

# NUMA topology — which CPU socket/memory node a GPU is physically
# attached to (the kernel-level ground truth behind nvidia-smi topo -m's
# "CPU Affinity" column from 03_gpu_architecture.md)
cat /sys/class/pci_bus/*/device/numa_node
numactl --hardware                     # full NUMA topology, already
                                        # familiar territory, now read
                                        # specifically for GPU placement
```

**The one fact worth internalizing over the specific commands**: `nvidia-smi topo -m`'s
CPU-affinity column isn't NVIDIA-proprietary information — it's reading the same
NUMA-topology facts the kernel already exposes via sysfs, presented in GPU-relevant
form. Knowing the underlying sysfs source is what lets you cross-check or debug when
`nvidia-smi` itself isn't available or trusted.

### CPU-GPU NUMA affinity — why "just use `taskset`" isn't quite the full picture

Ordinary NUMA-aware CPU pinning (`taskset`, `numactl --cpunodebind`) is already familiar.
The GPU-specific extension: a process feeding data to a GPU should run on a CPU core in
the **same NUMA node the GPU is physically attached to** — otherwise every data transfer
between host RAM and the GPU crosses a NUMA boundary before it even reaches PCIe, adding
latency to a path that's already the comparatively slow leg (per
[`03_gpu_architecture.md`](../phase2_gpu_fundamentals/03_gpu_architecture.md)'s HBM-vs.-
host-RAM bandwidth gap) of getting data onto the GPU in the first place.

```bash
# Find the GPU's NUMA node, then pin the feeding process to a CPU on
# that same node — the GPU-specific refinement of ordinary NUMA pinning
numactl --cpunodebind=<numa_node_of_gpu> --membind=<same_node> python train.py
```

This is a narrow, checkable extension of NUMA knowledge already established elsewhere in
this workspace's AIOps background — the only new fact is *which* NUMA node matters
(the GPU's), not a new NUMA concept itself.

### IRQ affinity — routing GPU interrupts to the right CPU

A GPU (and its NIC, for the RDMA path from
[`07_rdma_roce_infiniband.md`](../phase3_gpu_networking/07_rdma_roce_infiniband.md))
generates hardware interrupts that the kernel routes to a specific CPU core for handling.
By default, interrupt routing isn't necessarily NUMA-aware — an interrupt from a GPU on
NUMA node 0 could be routed to a CPU on NUMA node 1, adding the same kind of avoidable
cross-node latency as the CPU-GPU affinity case above, but for the interrupt-handling
path rather than the data path.

```bash
cat /proc/interrupts | grep nvidia    # find the IRQ numbers associated
                                        # with the GPU
cat /proc/irq/<irq_number>/smp_affinity_list   # check which CPU(s) that
                                                 # IRQ is currently routed to
```

Setting IRQ affinity explicitly to match GPU/NIC NUMA locality is a standard tuning step
in high-performance GPU cluster setups (often handled automatically by tuned profiles or
the GPU Operator's node-configuration components, per
[`09_gpu_operator_and_device_plugin.md`](../phase4_kubernetes_gpu/09_gpu_operator_and_device_plugin.md),
rather than done by hand on every node) — worth knowing this knob exists and what it's
for, even if it's rarely tuned manually at the individual-engineer level.

## Deep-Dive: how this connects to a symptom already covered elsewhere in this track

This chapter's content is the root-cause layer underneath a symptom
[`19_storage_for_gpu_clusters.md`](../phase6_production_operations/19_storage_for_gpu_clusters.md)
already named without full explanation: "data starvation" — GPUs sitting idle waiting on
data, with no GPU-level fault. NUMA-mismatched CPU-GPU affinity is one concrete,
Linux-level cause of exactly this symptom — a data-loading process pinned to the wrong
NUMA node relative to its GPU adds latency to every batch of data fed to that GPU, which
can manifest identically to a storage-throughput problem in
[`17_observability_for_gpu_fleets.md`](../phase6_production_operations/17_observability_for_gpu_fleets.md)'s
metrics (low SM utilization, no XID errors, no obvious fault) — meaning a real diagnostic
process needs to check NUMA affinity as one specific hypothesis, not just storage
throughput, when that symptom appears.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| Explicit NUMA-aware CPU-GPU pinning | Removes a real, avoidable source of host-to-device latency | Extra deployment-configuration complexity; easy to get wrong or let drift on a heterogeneous fleet |
| Default (non-NUMA-aware) scheduling | Simplest to configure | Silent, hard-to-diagnose latency cost exactly as described above — a real, checkable cause of the "data starvation" symptom |

## Failure Modes to Raise Proactively

- **Diagnosing "GPU sitting idle" purely as a storage-throughput problem without checking
  NUMA/CPU affinity** — as the deep-dive shows, both can produce an identical-looking
  symptom in GPU-level metrics; ruling out the Linux-level cause is a necessary step, not
  an optional one.
- **Assuming `nvidia-smi topo -m`'s CPU-affinity column is NVIDIA-specific magic rather
  than a presentation of standard kernel NUMA topology** — the practical cost of this
  misunderstanding is not knowing to cross-check via `numactl`/sysfs when `nvidia-smi`
  itself isn't trusted or available.

## Make It Yours

- On any machine with a GPU you have shell access to, run `numactl --hardware` and
  `nvidia-smi topo -m` side by side, and confirm you can map the GPU's reported CPU
  affinity in the second command back to a specific NUMA node in the first — the exact
  cross-check this chapter argues is worth being able to do without relying on NVIDIA
  tooling alone.

## Practice Questions

1. Why can a CPU-GPU NUMA mismatch produce a symptom that looks identical to a storage-
   throughput problem in fleet observability metrics, and what would distinguish the two?
2. Where does `nvidia-smi topo -m`'s CPU-affinity information actually originate at the
   kernel level, and why does knowing that matter when `nvidia-smi` itself is unavailable?
3. Why does IRQ affinity matter for a GPU/RDMA-NIC setup specifically, beyond the CPU-GPU
   data-path affinity already covered?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "Most Linux/systems knowledge for GPU workloads is the same as
for any workload — the GPU-specific delta is narrow: NUMA-aware CPU-GPU pinning (feeding
processes should run on the CPU node the GPU is physically attached to, or every transfer
pays an avoidable cross-node cost), IRQ affinity for the GPU and its RDMA NIC, and
knowing that `nvidia-smi`'s topology output is really just kernel sysfs/NUMA data
presented in GPU-relevant form."

**The follow-up-proof version**: be ready to connect a NUMA-affinity misconfiguration
directly to a real symptom — GPU underutilization that looks like a storage problem — 
rather than presenting NUMA pinning as an abstract best practice with no diagnostic
payoff.

**Vocabulary builder**: *IRQ affinity* (which CPU core handles a given hardware
interrupt), *sysfs/procfs* (the kernel interfaces exposing hardware topology, the ground
truth underneath NVIDIA's own tooling), *host-to-device transfer* (moving data from CPU-
accessible host RAM to GPU HBM — the path NUMA mismatch adds latency to).

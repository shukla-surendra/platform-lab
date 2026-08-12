# Computer Architecture: PCIe Topology and the Memory Hierarchy Underneath Everything Else

Part of [Phase 1 — Systems Foundations](../README.md#phase-1-systems-foundations).
Closes Phase 1 — and the full 28-domain roadmap this track set out to cover. Per
[`00_mental_model_and_roadmap.md`'s skill-level table](../00_mental_model_and_roadmap.md#three-skill-levels-and-where-you-already-are),
rated "Partial" — general computer-architecture literacy is assumed; this chapter is
scoped to the specific PCIe facts this track's earlier chapters have referenced without
deriving, now made explicit as the foundation they always were.

## Clarify

Nearly every chapter in Phases 2-6 has silently rested on one architectural fact this
chapter finally states directly: **a GPU is a PCIe device**, full stop — NVLink is an
*addition* on top of PCIe for GPU-to-GPU traffic specifically, not a replacement for it,
and every GPU's connection to host RAM and to the rest of the system still goes through
PCIe regardless of how fast its NVLink fabric is. This chapter is the PCIe-and-memory-
hierarchy foundation that makes sense of a half-dozen "why does this matter" claims made
earlier in the roadmap without their mechanism spelled out.

## Core Concepts

### PCIe generations and lanes — the numbers that show up in every topology check

```
PCIe generation × lane count → bandwidth (aggregate, both directions
combined typically quoted per-direction):

  PCIe Gen4 x16   ≈ 32 GB/s per direction   (H100-class hosts, common)
  PCIe Gen5 x16   ≈ 64 GB/s per direction   (newer platforms)

A GPU's PCIe connection is described by BOTH numbers together — "Gen4
x16" — and BOTH matter: a device that negotiates a LOWER generation or
FEWER lanes than its hardware supports (e.g. a Gen5-capable card
running at Gen4 speeds because of a motherboard/riser/BIOS limitation)
silently loses bandwidth with no error, exactly the "everything works,
just slower" pattern this entire track keeps surfacing at every layer.
```

**The direct, checkable diagnostic**: `lspci -vvv` (from
[`01_linux_internals_for_gpu_workloads.md`](01_linux_internals_for_gpu_workloads.md#proc-and-sys-where-gpu-adjacent-hardware-facts-actually-live))
reports both the **negotiated** link speed/width and the **maximum capable** speed/width
for a device — comparing the two is the direct way to catch this specific silent-
degradation failure, the PCIe-layer instance of a pattern this track has now named at
every layer from NVLink topology to RDMA transport selection.

### Why PCIe bandwidth is the ceiling under everything NVLink and HBM don't cover

Recall the bandwidth hierarchy already established piecemeal across this track — now
placed in one explicit order:

```
HBM (GPU-internal)         ~3.35 TB/s (H100)   — 03_gpu_architecture.md
NVLink (GPU-to-GPU)        ~900 GB/s (H100)    — 05_nvlink_nvswitch_topology.md
PCIe Gen4 x16               ~32 GB/s            — THIS CHAPTER
EFA / InfiniBand (cross-    ~50 GB/s (≈400Gbps) — 07_rdma_roce_infiniband.md
  node network)
```

**The fact this ordering makes visible that wasn't stated explicitly before**: PCIe
bandwidth and cross-node network bandwidth are actually in the *same rough tier* —
both dramatically slower than NVLink, both roughly two orders of magnitude slower than
HBM. This is *why* host-to-device transfer (moving data from CPU RAM to GPU HBM, over
PCIe) gets treated with the same care as cross-node network transfer in a well-designed
pipeline — both are "the slow leg" relative to on-GPU and GPU-to-GPU bandwidth, and both
deserve the same scrutiny this track has applied to network transport (checking negotiated
speed, checking topology) rather than being assumed to be fast by default.

### GPUDirect (again, at the PCIe layer) — why the PCIe path matters even with GPUDirect RDMA

[`07_rdma_roce_infiniband.md`](../phase3_gpu_networking/07_rdma_roce_infiniband.md#gpudirect-rdma-skipping-the-cpus-memory-entirely)
already covered GPUDirect RDMA's HBM-to-HBM path across nodes. The PCIe-layer detail that
completes that picture: GPUDirect RDMA's NIC-to-GPU-memory path still travels over PCIe
locally, on each end — the NIC and the GPU are both PCIe devices, and data moving between
them (even without touching host RAM) still consumes PCIe bandwidth and is subject to the
same topology considerations (which PCIe switch/root complex each device sits behind)
as any other PCIe traffic. **A NIC and GPU that sit behind different PCIe switches, or
worse, different NUMA-node root complexes** (connecting back to
[`01_linux_internals_for_gpu_workloads.md`](01_linux_internals_for_gpu_workloads.md#cpu-gpu-numa-affinity-why-just-use-taskset-isnt-quite-the-full-picture)'s
NUMA discussion) pay a real, checkable latency cost even with GPUDirect RDMA correctly
configured — a detail worth naming specifically because it shows GPUDirect RDMA isn't a
single on/off switch, it's a mechanism whose *effectiveness* still depends on the
underlying PCIe/NUMA topology being favorable.

### Root complexes and PCIe switches — why topology, not just generation/lanes, matters

```
Typical multi-GPU server PCIe topology (simplified):

CPU Socket 0 (NUMA node 0)          CPU Socket 1 (NUMA node 1)
   │                                    │
Root Complex 0                      Root Complex 1
   │                                    │
PCIe Switch A                       PCIe Switch B
 ├── GPU 0                           ├── GPU 4
 ├── GPU 1                           ├── GPU 5
 ├── GPU 2                           ├── GPU 6
 └── NIC 0                           └── NIC 1
```

Two devices under the **same** PCIe switch can often communicate peer-to-peer without
involving the CPU/root complex at all (a further optimization beyond ordinary PCIe
traffic) — meaning GPU 0 and GPU 1 above are better-positioned for fast PCIe-level
communication than GPU 0 and GPU 4, which must cross both a PCIe switch boundary and a
NUMA/socket boundary. This is the PCIe-topology-level version of exactly the same
"which GPUs are actually well-connected" question
[`05_nvlink_nvswitch_topology.md`](../phase2_gpu_fundamentals/05_nvlink_nvswitch_topology.md)
asked at the NVLink layer — the same discipline (check real topology, don't assume
uniform connectivity from a spec sheet) applies one layer down, at PCIe, and is
particularly relevant for the NIC-to-GPU placement question GPUDirect RDMA's
effectiveness depends on.

## Deep-Dive: tracing every bandwidth-tier claim in this track back to one hierarchy

This chapter's real payoff is retroactive — every "X is fast, Y is slow" claim made
across 19 prior chapters now traces to one physical hierarchy:

```
HBM (03) > NVLink (05) > { PCIe (this chapter) ≈ EFA/InfiniBand (07) } > host RAM/NVMe (19)
```

- TP stays intra-node because it needs the HBM/NVLink tier
  ([`03`](../phase2_gpu_fundamentals/03_gpu_architecture.md)).
- PP tolerates crossing nodes because it uses the network tier infrequently
  ([`06`](../phase3_gpu_networking/06_nccl_and_collective_communication.md)).
- GPUDirect RDMA matters because it removes an unnecessary hop through host RAM,
  but the remaining hops still ride PCIe on each end (this chapter).
- Checkpoint staging uses local NVMe first specifically because it's faster than the
  network/object-storage tier ([`19`](../phase6_production_operations/19_storage_for_gpu_clusters.md)).

Every one of these decisions is the same underlying logic — route traffic onto the
fastest tier the data's actual lifetime and frequency can tolerate — applied at a
different layer of one shared hierarchy. This is the single mental model this entire
28-domain roadmap has been building toward from its first chapter.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| Placing GPUs and their paired NICs under the same PCIe switch | Fastest possible PCIe-level GPU-NIC communication, best GPUDirect RDMA effectiveness | Requires deliberate hardware/BIOS configuration and verification, not a default guarantee |
| Ignoring PCIe topology, trusting spec sheets alone | Simpler procurement/deployment | Risks the exact silent-degradation pattern this track has named at every other layer, now at the PCIe layer |

## Failure Modes to Raise Proactively

- **Assuming a GPU is running at its rated PCIe generation/lane count without checking**
  — `lspci -vvv`'s negotiated-vs.-capable comparison is the direct, checkable way to
  catch this; assuming it from the spec sheet alone is exactly the failure mode this
  track has warned against at NVLink, RDMA, and now PCIe layers.
- **Treating GPUDirect RDMA as fully eliminating PCIe from the picture** — it removes the
  host-RAM detour, not the PCIe hops themselves; NIC-GPU PCIe topology still matters.
- **Placing a GPU and its intended paired NIC behind different PCIe switches or NUMA
  nodes** — a real, checkable latency cost, and the PCIe-layer version of the topology-
  awareness discipline this track has applied at every other layer.

## Make It Yours

- Run `lspci -vvv -s <gpu-address>` on any machine with a GPU you have access to and find
  both the negotiated and maximum-capable PCIe link speed/width — confirm they match, and
  explain what it would mean if they didn't.
- Walk through the full bandwidth hierarchy from this chapter's deep-dive out loud,
  connecting each tier to a specific decision made in an earlier chapter of this track —
  this is the single exercise that ties the entire 28-domain roadmap together into one
  coherent mental model rather than 20 separate facts.

## Practice Questions

1. Why does it matter whether a GPU and its paired RDMA NIC sit behind the same or
   different PCIe switches, even with GPUDirect RDMA correctly configured?
2. A GPU's spec sheet says PCIe Gen5 x16, but `lspci -vvv` reports it's negotiated at
   Gen4 x8 — what's the practical bandwidth impact, and how would this failure mode
   typically be discovered without deliberately checking?
3. Trace the full bandwidth hierarchy (HBM → NVLink → PCIe/network → NVMe/object
   storage) and name one specific architectural decision from earlier in this track that
   depends on each tier boundary.

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "Every GPU is fundamentally a PCIe device — NVLink adds a much
faster path for GPU-to-GPU traffic specifically, but host-to-device transfers and
NIC-to-GPU traffic (even under GPUDirect RDMA) still ride PCIe, at roughly the same
bandwidth tier as cross-node networking, both dramatically slower than NVLink or HBM.
PCIe topology — which switch and NUMA node a GPU and its paired NIC sit behind — matters
for the same reason NVLink topology matters: uniform connectivity is a topology property
to verify, not a default to assume from a spec sheet."

**The follow-up-proof version**: be ready to place PCIe explicitly in the full bandwidth
hierarchy (HBM > NVLink > PCIe ≈ network > NVMe) rather than treating it as a separate,
unranked concern — this is the detail that shows the mental model is unified across every
layer this track has covered, not memorized per-chapter.

**Vocabulary builder**: *root complex* (the CPU-side component PCIe devices ultimately
connect through, tied to a specific NUMA node), *negotiated vs. capable link speed* (what
a PCIe link is actually running at vs. what the hardware supports — the direct diagnostic
for silent PCIe-layer degradation), *peer-to-peer PCIe transfer* (two devices under the
same switch communicating without CPU/root-complex involvement).

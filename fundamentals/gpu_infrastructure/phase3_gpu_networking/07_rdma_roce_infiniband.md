# RDMA, RoCE, InfiniBand, and GPUDirect: What "EFA" Was Actually Standing In For

Part of [Phase 3 — GPU Networking](../README.md#phase-3-gpu-networking). Builds directly
on [`06_nccl_and_collective_communication.md`](06_nccl_and_collective_communication.md) —
that chapter named EFA/InfiniBand as "the network fabric" NCCL uses cross-node without
explaining what makes that fabric different from ordinary networking. This chapter is that
explanation.

## Clarify

Every earlier chapter in this track (and the whole `13_large_model_multi_gpu_inference/`
folder) has used "EFA" as a name without explaining the actual mechanism that makes it
fast — just "AWS's answer to NCCL needing a fast network." This chapter opens that up:
EFA is AWS's specific implementation of a general concept called **RDMA**, and
understanding RDMA is what lets the same reasoning transfer to InfiniBand (on-prem HPC
clusters, other clouds) and RoCE (Ethernet-based RDMA) rather than memorizing "EFA is
AWS's fast network" as an isolated fact.

## Core Concepts

### RDMA: the actual mechanism, not just "fast networking"

**RDMA (Remote Direct Memory Access)** lets one machine read/write another machine's
memory directly, without involving that remote machine's CPU or operating system kernel
in the transfer. Contrast with ordinary (TCP/IP socket) networking:

```
Ordinary TCP/IP transfer:
  App → OS kernel copy → network stack processing → NIC → wire → NIC
      → network stack processing → OS kernel copy → App (remote)

  Every hop costs CPU cycles on BOTH machines, and data gets copied
  multiple times (app buffer → kernel buffer → NIC buffer, and reverse).

RDMA transfer:
  App → NIC (reads directly from app's memory) → wire → NIC (writes
      directly into remote app's memory) → App (remote)

  The OS kernel and CPU on both ends are bypassed entirely during the
  transfer itself — this is "kernel bypass," the term that shows up in
  RDMA literature, and it's the actual mechanism, not marketing language.
```

**Why this matters specifically for GPU collective communication**: NCCL's cross-node
all-reduce needs to move large tensors between nodes very frequently (once per layer, per
forward pass, from `06_nccl_and_collective_communication.md`). If every one of those
transfers paid ordinary TCP/IP's CPU-copy and kernel-involvement overhead, that overhead
alone — separate from raw wire bandwidth — would meaningfully slow down every collective
call. RDMA removing that overhead is *why* it's the technology GPU-to-GPU networking
standardizes on, not an incidental choice.

### GPUDirect RDMA: skipping the CPU's memory entirely

Plain RDMA (as described above) still typically involves data passing through host
(CPU-side) RAM on its way to/from the GPU — an extra copy the GPU-to-GPU path doesn't
strictly need. **GPUDirect RDMA** is NVIDIA's extension that lets the NIC read/write
**GPU memory (HBM) directly**, bypassing host RAM entirely:

```
RDMA without GPUDirect:  GPU HBM → host RAM → NIC → wire → NIC → host RAM → GPU HBM
GPUDirect RDMA:          GPU HBM ─────────────→ NIC → wire → NIC ─────────→ GPU HBM
```

This is the detail that makes "the network fabric" and "HBM bandwidth" (from
[`03_gpu_architecture.md`](../phase2_gpu_fundamentals/03_gpu_architecture.md#hbm-why-gpu-memory-bandwidth-not-just-capacity-is-the-real-budget))
a connected story rather than two separate concerns: a cross-node NCCL transfer, done
right, moves data straight from one GPU's HBM to another's, with the network fabric as
the only intermediate hop — no host-RAM detour, no extra copy, no extra latency.

### InfiniBand, RoCE, and EFA — three implementations of the same idea

| | InfiniBand | RoCE (RDMA over Converged Ethernet) | EFA (AWS Elastic Fabric Adapter) |
|---|---|---|---|
| Physical layer | Its own dedicated fabric, not Ethernet | Standard Ethernet, with RDMA layered on top | AWS's own custom network fabric |
| Where it's used | On-prem HPC/AI clusters, some other clouds | Data centers wanting RDMA without dedicated IB hardware | AWS-specific, on `p5`/`p4d`-class instances and similar |
| Relationship to RDMA | The original/canonical RDMA transport | RDMA verbs implemented over Ethernet framing | AWS's own RDMA-capable fabric, exposed through the same `libfabric`/OFI software interface NCCL already speaks |

**The point worth remembering over the specific names**: all three exist to deliver the
same RDMA property (kernel-bypass, low-latency, high-bandwidth, ideally with GPUDirect
support) — a team choosing between them is choosing an implementation and a cloud/vendor
ecosystem, not a fundamentally different networking model. This is why NCCL doesn't need
separate code paths for "AWS" vs. "on-prem Infiniered" — it talks to all of them through
the same `libfabric`/OFI abstraction layer, with a provider plugin per fabric (this is the
concrete meaning behind `FI_PROVIDER` from
[`aws-production-architecture.md`](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/aws-production-architecture.md#networking-efa-and-placement-groups)
and `06_nccl_and_collective_communication.md`'s `NCCL_DEBUG` output).

### Why this needs cluster placement groups, concretely

[`aws-production-architecture.md`](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/aws-production-architecture.md#networking-efa-and-placement-groups)
already names cluster placement groups as reducing hop count — this chapter adds the
mechanism: RDMA's latency advantage over TCP/IP is largest when the physical path is
short and switch-hop-light; placing instances close together in the data center (what a
cluster placement group requests) is what keeps the actual achievable RDMA latency close
to its theoretical best, rather than being eaten by extra switch hops between physically
distant racks — the "measurably slower, no single obvious cause" failure mode named there
is, specifically, extra hops degrading RDMA's latency advantage without breaking anything
outright.

## Deep-Dive: the full path a cross-node all-reduce actually takes

Putting every piece from this track's Phase 3 chapters together into one trace:

1. TP or PP determines a cross-node transfer is needed (from `03_gpu_architecture.md`'s
   deep-dive and `06_nccl_and_collective_communication.md`'s placement rule).
2. NCCL selects the appropriate collective algorithm and, for the cross-node hop
   specifically, a hierarchical strategy that minimizes what crosses the slow link
   (`06_nccl_and_collective_communication.md`).
3. NCCL issues the transfer via `libfabric`/OFI, which dispatches to the EFA (or
   InfiniBand/RoCE) provider (this chapter).
4. If GPUDirect RDMA is correctly configured, the transfer moves directly from source
   GPU HBM to destination GPU HBM, with the NIC as the only intermediate hop — no host
   RAM copy on either side.
5. Cluster placement group membership determines the actual physical distance/hop-count
   this transfer travels, directly affecting realized latency.

Every one of these steps has to be correct for the "EFA (~3200Gbps)" bandwidth number in
`aws-production-architecture.md`'s instance table to actually be realized in practice —
this is the full chain that number was always resting on.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| RDMA (any implementation) over TCP/IP for cross-node NCCL | Removes CPU-copy/kernel overhead from every collective call | Requires correctly configured drivers/NICs — a real, non-trivial setup surface |
| GPUDirect RDMA over plain RDMA | Removes the host-RAM detour entirely | Needs both NIC and GPU driver support, and correct configuration to actually engage |
| InfiniBand (dedicated fabric) vs. RoCE (Ethernet-based) | IB: purpose-built, often lower latency ceiling. RoCE: reuses existing Ethernet infrastructure/tooling | IB: separate physical infrastructure to operate. RoCE: correctly configuring lossless Ethernet (PFC/ECN) for RDMA is its own real operational burden |

## Failure Modes to Raise Proactively

- **Treating "the network is fast" as binary rather than checking whether RDMA (and
  GPUDirect specifically) is actually engaged** — a misconfiguration can silently fall
  back to plain TCP/IP or to RDMA-without-GPUDirect (still working, just slower at each
  step), the same class of "everything works, just far slower" failure this whole track
  keeps surfacing — `NCCL_DEBUG=INFO`'s transport log line
  (`06_nccl_and_collective_communication.md`) is the direct way to catch it here too.
- **Skipping cluster placement groups and assuming RDMA's latency advantage is
  location-independent** — as shown above, extra physical hops erode exactly the
  advantage RDMA is meant to provide.
- **Assuming "InfiniBand" and "RoCE" are interchangeable in every practical sense** — both
  deliver RDMA, but RoCE's dependence on correctly configured lossless Ethernet is a real
  operational difference worth naming, not a detail to gloss over.

## Make It Yours

- Next time `NCCL_DEBUG=INFO` output is checked (per the prior chapter's Make It Yours),
  specifically look for whether GPUDirect RDMA is reported as active for GPU-to-NIC
  transfers, not just whether EFA/IB is the selected provider — two separate things that
  both need to be true for the full-speed path.

## Practice Questions

1. Why does RDMA's CPU-bypass property matter more for GPU collective communication
   specifically than it would for, say, a typical microservice-to-microservice HTTP call?
2. What does GPUDirect RDMA remove from the transfer path that plain RDMA (without it)
   still has, and why does that extra hop matter given HBM bandwidth is already the
   scarce resource (per `03_gpu_architecture.md`)?
3. A team migrates a training cluster from InfiniBand (on-prem) to EFA (AWS) — what,
   mechanically, stays the same in how NCCL uses the network, and what's actually
   different?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "RDMA lets one machine read/write another's memory directly,
bypassing the CPU and OS kernel on both ends — that's what makes it fast enough for GPU
collective communication, where transfers happen very frequently. GPUDirect RDMA extends
that further, letting the NIC talk straight to GPU memory instead of routing through host
RAM. EFA, InfiniBand, and RoCE are three different implementations of this same idea —
NCCL talks to all of them through the same libfabric abstraction, which is why the
placement rules and performance reasoning transfer across clouds and on-prem clusters."

**The follow-up-proof version**: be ready to trace the full path — TP/PP triggers a
transfer, NCCL picks an algorithm, libfabric dispatches to the fabric's provider,
GPUDirect (if configured) moves HBM-to-HBM directly, placement groups bound the physical
hop count — rather than stopping at "EFA makes it fast."

**Vocabulary builder**: *kernel bypass* (the defining RDMA property — the OS kernel isn't
involved in the data path during a transfer), *libfabric/OFI* (the vendor-neutral
abstraction layer NCCL uses to talk to whichever RDMA fabric is present, via a
per-fabric provider plugin), *lossless Ethernet / PFC/ECN* (the Ethernet-level
configuration RoCE depends on to behave reliably enough for RDMA, distinct from ordinary
best-effort Ethernet).

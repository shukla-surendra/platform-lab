# NVLink & NVSwitch: The Physical Topology Behind "Intra-Node Is Fast"

Part of [Phase 2 — GPU Fundamentals](../README.md#phase-2-gpu-fundamentals). This chapter
makes concrete what
[`03_gpu_architecture.md`'s deep-dive](03_gpu_architecture.md#deep-dive-why-tensor-parallelism-stays-intra-node)
asserted with one bandwidth number (NVLink ~900GB/s) — the actual wiring that number
describes, why it differs by GPU-count-per-node, and how to read it directly off real
hardware rather than trust a spec sheet.

## Clarify

Every claim so far in this track about "intra-node is fast" has quietly assumed all GPUs
in a node are equally, fully connected to each other. That assumption is **topology-
dependent** — it's true on an 8-GPU NVSwitch-equipped node like `p5.48xlarge`, and false
on cheaper, partially-connected configurations. Treating "has NVLink" as a binary
(present/absent) rather than checking the actual topology is a real, checkable mistake —
this chapter is about making that check a habit, not a spec-sheet assumption.

## Core Concepts

### NVLink: point-to-point, generation-versioned bandwidth

NVLink is NVIDIA's proprietary high-speed interconnect between GPUs (and, in some
configurations, GPU-to-CPU), replacing the much slower PCIe path for GPU-to-GPU traffic.
Each generation roughly doubles per-link bandwidth:

| GPU generation | NVLink gen | Per-GPU aggregate bandwidth |
|---|---|---|
| A100 | 3rd gen | ~600 GB/s |
| H100/H200 | 4th gen | ~900 GB/s |
| B200 | 5th gen | ~1.8 TB/s |

These are the same numbers
[`03_gpu_architecture.md`'s lineup table](03_gpu_architecture.md#the-current-nvidia-data-center-lineup-and-what-actually-changes-generation-to-generation)
already listed — this chapter is about the physical arrangement that delivers them, not a
new number.

### Point-to-point NVLink vs. NVSwitch — the topology distinction that actually matters

Two genuinely different physical arrangements both get casually called "NVLink":

```
Point-to-point (partial mesh) — e.g. some 4-GPU workstation configs:

    GPU0 ─── GPU1
      │  ╲   ╱  │
      │   ╲ ╱   │
      │   ╱ ╲   │
      │  ╱   ╲  │
    GPU2 ─── GPU3

  Not every GPU pair necessarily has a direct link — some pairs may have
  to route traffic through another GPU, or fall back to PCIe, depending
  on exactly which links exist in that config.

NVSwitch (full crossbar) — e.g. p5.48xlarge (8× H100):

    GPU0 ─┐                    ┌─ GPU4
    GPU1 ─┤                    ├─ GPU5
    GPU2 ─┼──   NVSwitch(es)  ──┤
    GPU3 ─┘                    └─ GPU7... GPU6

  Every GPU reaches every other GPU through the switch fabric at full,
  uniform NVLink bandwidth — no GPU pair is worse-connected than any
  other, and there's no multi-hop penalty for any pair.
```

**Why this distinction is the practically important one**: tensor parallelism assumes
every GPU in the TP group can all-reduce with every other GPU at consistent bandwidth
(the mechanism in
[`03_gpu_architecture.md`'s deep-dive](03_gpu_architecture.md#deep-dive-why-tensor-parallelism-stays-intra-node)).
On an NVSwitch node, that assumption holds uniformly. On a partial-mesh node, some GPU
pairs are worse-connected than others — meaning **which GPUs get placed in the same TP
group actually matters**, not just "are they in the same box." This is a second, more
granular version of the "everything works, just far slower" failure mode already named in
[`03_gpu_architecture.md`'s failure modes](03_gpu_architecture.md#failure-modes-to-raise-proactively)
— it can happen *within* a single node, not just across nodes.

### Reading real topology: `nvidia-smi topo -m`, in detail

This chapter goes one level deeper than
[`03_gpu_architecture.md`'s introduction of this command](03_gpu_architecture.md#reading-nvidia-smi-and-nvidia-smi-topo-m-against-this-model)
— the actual matrix values and what each one means:

```
        GPU0  GPU1  GPU2  GPU3  GPU4  GPU5  GPU6  GPU7  CPU Affinity
GPU0     X    NV18  NV18  NV18  NV18  NV18  NV18  NV18   0-51
GPU1   NV18    X    NV18  NV18  NV18  NV18  NV18  NV18   0-51
...

Legend:
  X    = self
  NV#  = connected via NVLink, # = number of NVLink connections between
         this pair (higher generally means higher aggregate bandwidth
         for that specific pair)
  NODE = connected via PCIe, but crossing a NUMA/CPU-socket boundary —
         meaningfully slower and higher-latency than either NVLink or
         same-socket PCIe
  SYS  = crossing not just NUMA but the whole system interconnect —
         the slowest tier that still counts as "in the same machine"
  PIX/PXB = various PCIe-switch-level distinctions, all slower than NVLink
```

**A uniform `NV18` (or similar) across every pair is the direct, checkable signature of
an NVSwitch full-mesh topology** — every pair identical means the switch fabric, not a
partial point-to-point mesh, is doing the connecting. Any `NODE`/`SYS`/`PIX` entry mixed
in among otherwise-`NV#` entries is the signal that at least one GPU pair on that host
falls back to a slower path — the exact thing a TP-group placement decision needs to
avoid, and the exact thing a spec sheet alone won't reveal (it takes running the command
on the actual instance).

## Deep-Dive: why `p5.48xlarge`'s 8-GPU NVSwitch design is the relevant AWS fact, not just a spec

[`aws-production-architecture.md`'s instance table](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/aws-production-architecture.md#compute-which-instances-and-why-multi-node-changes-the-calculus)
lists `p5.48xlarge` as "NVLink (intra-node)" without specifying the topology — this
chapter fills that in precisely: `p5.48xlarge`'s 8× H100 are wired through NVSwitch, full
crossbar, meaning a TP=8 group spanning all 8 GPUs on one node gets uniform, full-bandwidth
connectivity for every pair in the all-reduce — which is *why* that instance is the
"default building block — one full TP=8 group per node" the AWS doc calls it, not an
arbitrary choice. A hypothetical 8-GPU instance without NVSwitch (point-to-point only)
would not support that same claim, even with an identical GPU count and identical
per-GPU NVLink generation — the topology, not just the link generation, is what makes the
claim true.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| NVSwitch (full crossbar) node | Uniform bandwidth for any TP-group GPU subset, no placement planning needed | More expensive, more complex hardware than point-to-point |
| Point-to-point mesh | Cheaper for smaller GPU counts (4 or fewer) | Requires topology-aware placement — not every subset of GPUs is equally good for a TP group |
| PCIe-only (no NVLink at all) | Simplest, cheapest | Falls back to
[`03_gpu_architecture.md`'s bandwidth-gap argument](03_gpu_architecture.md#deep-dive-why-tensor-parallelism-stays-intra-node) — tensor parallelism across PCIe-only GPUs pays a real, measurable throughput cost even within one machine |

## Failure Modes to Raise Proactively

- **Assuming "8 GPUs in one box" implies uniform NVLink connectivity** — only true on an
  NVSwitch design; a partial-mesh 8-GPU box (rare at datacenter scale but real on some
  workstation/prosumer configurations) would not have this property, and the only way to
  know for certain is `nvidia-smi topo -m`, not the spec sheet's GPU count.
- **Placing a TP group across a `NODE`/`SYS` boundary on a partial-mesh host** — silent
  throughput loss with no error, the same "looks like a software problem" failure
  pattern named repeatedly across this track's chapters.

## Make It Yours

- Run `nvidia-smi topo -m` on any multi-GPU instance available to you and identify: is
  this a uniform NVSwitch topology, or does the matrix show mixed `NV#`/`NODE`/`SYS`
  entries? State which GPU subset you'd choose for a TP group if it's the latter.

## Practice Questions

1. Two 8-GPU nodes both advertise "NVLink" — one is NVSwitch-based, one is point-to-point
   mesh. Why might a TP=8 job perform identically well on one and measurably worse on the
   other, despite identical GPU counts and NVLink generation?
2. Why does `nvidia-smi topo -m` matter even on a single, known-good NVSwitch instance
   type like `p5.48xlarge` — what would still be worth verifying?
3. If forced to run tensor parallelism across a `NODE`-level (NUMA-crossing) connection
   instead of NVLink, what's the mechanism (from `03_gpu_architecture.md`'s deep-dive)
   that predicts the actual performance impact?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "NVLink is the point-to-point wiring, but the topology it's
arranged in matters as much as the link speed itself — an NVSwitch design gives every GPU
pair in the box uniform, full-bandwidth connectivity, which is what makes an 8-GPU
NVSwitch node like `p5.48xlarge` a clean single tensor-parallel group. A partial mesh
doesn't have that guarantee, so which GPUs you group together actually matters, and the
only way to know the real topology is `nvidia-smi topo -m`, not the spec sheet."

**The follow-up-proof version**: be ready to read an actual topology matrix out loud and
say which pairs are NVLink-connected, which cross a NUMA boundary, and what that implies
for TP-group placement — the interview-proof move is demonstrating you'd check, not
assume.

**Vocabulary builder**: *full crossbar / full mesh* (every node reachable from every other
node at uniform cost — the NVSwitch property), *partial mesh* (some pairs connected,
others not, requiring routing or fallback), *NUMA boundary* (a CPU-socket/memory-locality
boundary that PCIe traffic crossing it pays a real latency cost to cross, distinct from
GPU-to-GPU NVLink entirely).

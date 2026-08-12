# The Mental Model: One Stack, Seven Phases

## Why this track exists, and how it relates to the interview-prep deadlines

`private_profile/ml-platform-prep-plan-v2.md` has real dates: Phase 1 ready 2026-09-06,
Phase 2 ready 2026-10-04, Phase 3 ready 2026-11-01. Nothing in this track has a deadline
— it targets a different, broader role (GPU Fleet / AI Infrastructure Architect) than
what those phases are optimizing for (ML Platform Engineer loops at Google, Stripe,
Atlassian, Amazon, Microsoft, Adobe, VMware). That's fine, but it means this track has to
be paced *around* the dated work, not compete with it:

- If a session is explicitly aimed at one of the named companies' upcoming loop, work
  from `ml-platform-prep-plan-v2.md` Part 3's week table, not this roadmap.
- This track is the right thing to reach for in open, undated time — evenings/weekends
  with no specific interview looming — or when a `system_design_foundation` tutorial
  (most often [`13_large_model_multi_gpu_inference/`](../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/README.md))
  raises a question ("what's actually inside an H100 SM?", "what does NCCL do under the
  hood?") worth chasing to the bottom.
- VMware's infra-depth round and the general system-design "why not just add more GPUs"
  follow-up are the two places this track's depth pays back directly into the dated
  prep — worth flagging explicitly when a session touches both.

## The full stack, one diagram

Every one of the 28 original domains sits at exactly one layer of this stack. Confusing
which layer a tool or concept belongs to is the single most common source of "wait, how
does X relate to Y" confusion in this space — keep this picture as the anchor.

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 6: Production Operations                               │
│ Fleet lifecycle · Reliability (XID) · Observability · FinOps │
│ Storage · Multi-tenant security                               │
├─────────────────────────────────────────────────────────────┤
│ Phase 5: LLM Serving          │ Phase 7: Training Infra       │
│ vLLM/TRT-LLM/TGI/SGLang       │ FSDP/DeepSpeed/ZeRO            │
│ Quantization · KV cache math  │ MoE/Expert Parallelism         │
├─────────────────────────────────────────────────────────────┤
│ Phase 4: Kubernetes GPU Infrastructure                        │
│ GPU Operator · Device Plugin · MIG · Kueue/Volcano · Slurm    │
├─────────────────────────────────────────────────────────────┤
│ Phase 3: GPU Networking                                       │
│ NCCL collectives · RDMA/RoCE/InfiniBand · GPUDirect · nccl-tests│
├─────────────────────────────────────────────────────────────┤
│ Phase 2: GPU Fundamentals                                     │
│ SM/CUDA cores/Tensor cores/HBM · NVLink/NVSwitch · CUDA stack │
├─────────────────────────────────────────────────────────────┤
│ Phase 1: Systems Foundations                                  │
│ Linux internals (procfs, NUMA, sched) · PCIe topology         │
└─────────────────────────────────────────────────────────────┘
        ↑ Local & Prototyping tier (LM Studio) sits OUTSIDE this stack —
          single-machine, no fleet, the fast path to intuition before
          any of the above matters.
```

Read bottom-up for "how does this actually work" (a request travels: Linux schedules the
process → PCIe gets data to the GPU → the GPU's SMs execute it → NCCL moves results
between GPUs → RDMA/InfiniBand moves them between nodes → Kubernetes decided which nodes
→ the serving engine batches and returns tokens → observability/fleet-ops keep it alive).
Read top-down for "what do I actually operate day to day" (a GPU Fleet/Infra Architect
spends more real time in Phases 4/6 than in Phase 1/2, even though 1/2 are the conceptual
foundation everything above stands on).

## Three skill levels, and where you already are

Borrowing the framing from `private_profile/Personal_Learning_Profile.md`'s pipeline
(mental model before code): each domain below is rated for **current depth**, based on
the 10+ years AIOps/MLOps/Kubernetes/AWS/Databricks background already established in
this workspace's `CLAUDE.md`.

| Level | Meaning |
|---|---|
| **Have it** | Already fluent from existing background — skim for GPU-specific vocabulary only, don't rebuild from zero |
| **Partial** | Know the adjacent/general version, need the GPU-specific layer added on top |
| **Gap** | Genuinely new — this is where real study time belongs |

| Phase | Domain | Level | Why |
|---|---|---|---|
| 1 | Linux internals | Have it | 10+ years AIOps background covers procfs/scheduling/NUMA generally |
| 1 | PCIe/computer architecture | Partial | General systems knowledge exists; PCIe topology specifics for GPU fleets don't |
| 2 | GPU architecture (SM/cores/HBM) | **Gap** | Named explicitly as a current weak spot |
| 2 | CUDA ecosystem | **Gap** | Same |
| 2 | NVLink/NVSwitch | **Gap** | Same |
| 3 | GPU networking (NCCL/RDMA) | **Gap** | Named explicitly — "GPU Arch, Networking, Distributed Systems" are the stated biggest gaps |
| 4 | Kubernetes GPU layer | Partial | Kubernetes itself: Have it (existing EKS/k8n_explorer background). GPU Operator/MIG/Kueue specifics: Gap |
| 4 | Slurm | **Gap** | No prior HPC-scheduler background in this workspace |
| 5 | LLM serving architecture | Have it | Already built in depth in `13_large_model_multi_gpu_inference/` |
| 5 | Quantization | Partial | Concept understood; tooling depth (GPTQ/AWQ internals) is newer |
| 6 | Observability | Have it | Prometheus/Grafana/Loki/ELK already hands-on in `mlops_aiops/` — only the GPU-specific exporters (DCGM) are new |
| 6 | FinOps/capacity planning | Partial | General cloud cost background exists; GPU-hour/token-cost specifics are newer |
| 7 | Distributed training parallelism | Have it | Already built in `07_distributed_training_serving.md` |
| 7 | FSDP/DeepSpeed/ZeRO internals | **Gap** | The strategy is known; the implementation internals aren't |

**Practical implication**: don't spend equal time per phase. Phases 2 and 3 are where
the real gap is — that's why [GPU Architecture](phase2_gpu_fundamentals/03_gpu_architecture.md)
was written first, not Phase 1.

## Articulate It: Interview Framing & Vocabulary

**The 30-second version** (when a system-design round asks "why not just add more
GPUs"): "Because past a point, the bottleneck isn't compute, it's the interconnect —
GPUs sit behind PCIe or NVLink locally and RDMA/InfiniBand across nodes, and if the
parallelism strategy doesn't match the bandwidth tier of the link it's using, adding GPUs
makes the network the bottleneck instead of removing one."

**The follow-up-proof version**: be ready to name the actual bandwidth numbers (NVLink
~900GB/s intra-node vs. EFA ~400Gbps ≈ 50GB/s inter-node — roughly 18x difference), and
why that gap is *why* tensor parallelism stays intra-node and pipeline parallelism is the
one that crosses nodes, not the reverse.

**Vocabulary builder**: *interconnect topology* (the physical/logical map of how GPUs are
wired to each other), *bandwidth tier* (NVLink > PCIe > EFA/InfiniBand, in that order, and
why), *fleet* (the operational unit — many nodes managed as one lifecycle, not "a GPU").

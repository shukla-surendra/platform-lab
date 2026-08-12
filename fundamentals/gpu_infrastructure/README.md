# GPU Fleet / AI Infrastructure — Roadmap

This track is a different, larger scope than the rest of `system_design_foundation/`:
that section is **ML Platform Engineer interview prep** (dated, capped by
`private_profile/ml-platform-prep-plan-v2.md`'s phase deadlines). This one is **GPU
Fleet / AI Infrastructure Architect** depth — the systems-and-hardware layer underneath
everything `13_large_model_multi_gpu_inference/` already assumes. It's undated and
genuinely multi-session; read [`00_mental_model_and_roadmap.md`](00_mental_model_and_roadmap.md)
before anything else for how to pace it against the interview-prep deadlines instead of
letting it silently displace them.

**Where each domain actually lives** — several of the 28 original domains already have a
real home elsewhere in this repo or in `platform-lab`; this track doesn't duplicate them,
it fills the gap and cross-links the rest into one coherent path.

**[Tools Reference](TOOLS_REFERENCE.md)** — every CLI command/tool introduced across all
23 chapters, indexed by diagnostic question ("is the GPU actually busy or just showing
high utilization," "is the network healthy," "is this a NUMA problem") rather than by
chapter — the fast lookup to use during a real incident or interview prep session, once
the concepts below are already familiar.

## Phase 1 — Systems Foundations

| # | Topic | Status |
|---|---|---|
| 1 | [Linux Internals for GPU Workloads](phase1_systems/01_linux_internals_for_gpu_workloads.md) | **written** |
| 2 | [Computer Architecture: PCIe, NUMA, Memory Hierarchy](phase1_systems/02_computer_architecture_pcie_numa.md) | **written** |

Given 10+ years of AIOps/MLOps background, this phase is a *refresher*, not a from-zero
build — the roadmap below flags it accordingly.

## Phase 2 — GPU Fundamentals

| # | Topic | Status |
|---|---|---|
| 3 | [GPU Architecture: SMs, Cores, HBM, Warps](phase2_gpu_fundamentals/03_gpu_architecture.md) | **written** |
| 4 | [CUDA Ecosystem: Driver/Toolkit/cuBLAS/cuDNN/NVML/DCGM](phase2_gpu_fundamentals/04_cuda_ecosystem.md) | **written** |
| 5 | [NVLink / NVSwitch Topology](phase2_gpu_fundamentals/05_nvlink_nvswitch_topology.md) | **written** |

## Phase 3 — GPU Networking

| # | Topic | Status |
|---|---|---|
| 6 | [NCCL & Collective Communication](phase3_gpu_networking/06_nccl_and_collective_communication.md) | **written** |
| 7 | [RDMA, RoCE, InfiniBand, GPUDirect](phase3_gpu_networking/07_rdma_roce_infiniband.md) | **written** |
| 8 | [NCCL Testing (`nccl-tests`)](phase3_gpu_networking/08_nccl_testing.md) | **written** |

## Phase 4 — Kubernetes GPU Infrastructure

Base Kubernetes mechanics (Deployments, Services, scheduling primitives) are already
covered in `platform-lab/k8n_explorer/` — this phase covers only the **GPU-specific**
layer on top of that foundation, not Kubernetes from scratch.

| # | Topic | Status |
|---|---|---|
| 9 | [NVIDIA GPU Operator & Device Plugin](phase4_kubernetes_gpu/09_gpu_operator_and_device_plugin.md) | **written** |
| 10 | [GPU Scheduling: MIG, Sharing, Kueue, Volcano, Gang Scheduling](phase4_kubernetes_gpu/10_gpu_scheduling_mig_sharing.md) | **written** |
| 11 | [Slurm vs. Kubernetes for GPU Clusters](phase4_kubernetes_gpu/11_slurm_vs_kubernetes.md) | **written** |

## Phase 5 — LLM Serving & Inference

The multi-node serving architecture itself (tensor/pipeline parallelism, KV cache math,
vLLM/TensorRT-LLM/TGI/SGLang comparison, AWS reference architecture) is **already fully
built** — see
[`../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/`](../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/README.md).
This phase adds what that folder doesn't cover: the performance-engineering and
memory-estimation math underneath it, and quantization as its own topic.

| # | Topic | Status |
|---|---|---|
| — | Multi-GPU/multi-node serving architecture | done, see link above |
| 12 | [LLM Performance Engineering](phase5_llm_serving/12_llm_performance_engineering.md) | **written** |
| 13 | [Quantization: FP32 → FP8 → INT4](phase5_llm_serving/13_quantization.md) | **written** |
| 14 | [Model Memory Estimation](phase5_llm_serving/14_model_memory_estimation.md) | **written** |

## Phase 6 — Production Operations

Observability tooling (Prometheus/Grafana/Loki/ELK) already has hands-on build-outs in
`platform-lab/mlops_aiops/` and `platform-lab/k8n_mlops/` — this phase covers the
**GPU-fleet-specific** signals and lifecycle on top of that general stack.

| # | Topic | Status |
|---|---|---|
| 15 | [GPU Fleet Lifecycle Management](phase6_production_operations/15_gpu_fleet_lifecycle.md) | **written** |
| 16 | [Reliability & Failure Management (XID errors, draining)](phase6_production_operations/16_reliability_and_failure_management.md) | **written** |
| 17 | [Observability for GPU Fleets (DCGM exporter, OTel)](phase6_production_operations/17_observability_for_gpu_fleets.md) | **written** |
| 18 | [Capacity Planning & FinOps ($/GPU-hour, $/M tokens)](phase6_production_operations/18_capacity_planning_and_finops.md) | **written** |
| 19 | [Storage for GPU Clusters (NVMe/Lustre/Ceph/S3)](phase6_production_operations/19_storage_for_gpu_clusters.md) | **written** |
| 20 | [Security & Multi-Tenant GPU Isolation](phase6_production_operations/20_security_and_multi_tenancy.md) | **written** |
| 24 | [Multi-Cloud GPU Landscape (Azure/GCP/OCI vs. AWS)](phase6_production_operations/24_multi_cloud_gpu_landscape.md) | **written** |
| 25 | [Single-GPU Instance Selection (g5/g6, A10G/L4)](phase6_production_operations/25_single_gpu_instance_selection_g5_g6.md) | **written** |

## Phase 7 — Advanced Distributed Training Infra

Parallelism strategy fundamentals (DP/TP/PP, Ray) are already covered in
[`07_distributed_training_serving.md`](../system_design_foundation/01_ml_system_design/07_distributed_training_serving.md).
This phase goes deeper into the specific systems that implement it at scale.

| # | Topic | Status |
|---|---|---|
| — | DP/TP/PP fundamentals, Ray Train | done, see link above |
| 21 | [FSDP, DeepSpeed, ZeRO Stages 1-3](phase7_advanced_training_infra/21_fsdp_deepspeed_zero.md) | **written** |
| 22 | [Mixture-of-Experts & Expert Parallelism](phase7_advanced_training_infra/22_moe_expert_parallelism.md) | **written** |

## Local & Prototyping Tier

A genuinely different scale than everything above — single-machine, not fleet — but
included because it's the fastest path to hands-on intuition before touching a real
cluster.

| # | Topic | Status |
|---|---|---|
| 23 | [LM Studio & Local Inference](local_and_prototyping/23_lmstudio_and_local_inference.md) | **written** |

## Reading order

1. [`00_mental_model_and_roadmap.md`](00_mental_model_and_roadmap.md) — the full stack
   diagram, skill-level framework, and how to pace this against `private_profile`'s dated
   phases.
2. Phase 2, in order: [GPU Architecture](phase2_gpu_fundamentals/03_gpu_architecture.md) →
   [CUDA Ecosystem](phase2_gpu_fundamentals/04_cuda_ecosystem.md) →
   [NVLink/NVSwitch Topology](phase2_gpu_fundamentals/05_nvlink_nvswitch_topology.md) — the
   full hardware+software mental model everything from NCCL to Kubernetes GPU scheduling
   to quantization assumes. All three written.
3. Phase 3, in order: [NCCL & Collective Communication](phase3_gpu_networking/06_nccl_and_collective_communication.md)
   → [RDMA, RoCE, InfiniBand, GPUDirect](phase3_gpu_networking/07_rdma_roce_infiniband.md)
   → [NCCL Testing](phase3_gpu_networking/08_nccl_testing.md) — the networking layer
   underneath every cross-node claim in `13_large_model_multi_gpu_inference/`, plus how to
   actually verify it on real hardware. All three written — Phase 3 is complete.
4. Phase 4, in order: [GPU Operator & Device Plugin](phase4_kubernetes_gpu/09_gpu_operator_and_device_plugin.md)
   → [GPU Scheduling: MIG/Sharing/Gang Scheduling](phase4_kubernetes_gpu/10_gpu_scheduling_mig_sharing.md)
   → [Slurm vs. Kubernetes](phase4_kubernetes_gpu/11_slurm_vs_kubernetes.md) — assumes
   Kubernetes fundamentals from `k8n_explorer/`, covers only the GPU-specific layer on
   top. All three written — Phase 4 is complete.
5. Phase 5, in order: [LLM Performance Engineering](phase5_llm_serving/12_llm_performance_engineering.md)
   → [Quantization](phase5_llm_serving/13_quantization.md) →
   [Model Memory Estimation](phase5_llm_serving/14_model_memory_estimation.md) — the TTFT/
   TPOT diagnostic method, precision trade-offs, and the full memory-budget formula for
   both inference and training. All three written — Phase 5 is complete. Also see
   [LM Studio](local_and_prototyping/23_lmstudio_and_local_inference.md), usable
   independently.
6. Phase 7, in order: [FSDP/DeepSpeed/ZeRO](phase7_advanced_training_infra/21_fsdp_deepspeed_zero.md)
   → [MoE & Expert Parallelism](phase7_advanced_training_infra/22_moe_expert_parallelism.md)
   — the sharding mechanism behind training's memory savings, and the fourth parallelism
   axis MoE models require. Both written — Phase 7 is complete.
7. Phase 6, in order: [Fleet Lifecycle](phase6_production_operations/15_gpu_fleet_lifecycle.md)
   → [Reliability & Failure Management](phase6_production_operations/16_reliability_and_failure_management.md)
   → [Observability](phase6_production_operations/17_observability_for_gpu_fleets.md) →
   [Capacity Planning & FinOps](phase6_production_operations/18_capacity_planning_and_finops.md)
   → [Storage](phase6_production_operations/19_storage_for_gpu_clusters.md) →
   [Security & Multi-Tenancy](phase6_production_operations/20_security_and_multi_tenancy.md)
   — the nine-stage lifecycle loop and the six operational disciplines that keep a fleet
   running once it exists. All six written — Phase 6 is complete. Every chapter in Phase 6
   assumes Prometheus/Grafana/Loki/ELK fundamentals from `mlops_aiops/`/`k8n_mlops/` and
   covers only the GPU-specific layer on top.
8. Phase 1, in order: [Linux Internals for GPU Workloads](phase1_systems/01_linux_internals_for_gpu_workloads.md)
   → [Computer Architecture: PCIe, NUMA, Memory Hierarchy](phase1_systems/02_computer_architecture_pcie_numa.md)
   — the narrow, GPU-specific delta on top of already-solid Linux/systems background, and
   the PCIe/bandwidth-hierarchy foundation retroactively underneath every earlier
   chapter's "X is fast, Y is slow" claim. Both written — **Phase 1 is complete, closing
   the full 28-domain roadmap.**

9. [Multi-Cloud GPU Landscape](phase6_production_operations/24_multi_cloud_gpu_landscape.md)
   — the narrow, genuinely cloud-specific delta (fabric product, parallel filesystem,
   managed orchestration) on top of everything else in this track, which transfers to any
   cloud unchanged. Closes the "cloud GPU infrastructure across AWS/Azure/GCP/OCI" domain
   from the original roadmap.
10. [Single-GPU Instance Selection: g5/g6 (A10G/L4)](phase6_production_operations/25_single_gpu_instance_selection_g5_g6.md)
    — the opposite end of the AWS-instance spectrum from `aws-production-architecture.md`'s
    flagship 8-GPU clusters: single-GPU dev/inference-tier instances, why NVLink and MIG
    are absent from this hardware entirely (not a smaller-tier restriction but a
    different die family), and the real parallelization/sharing options once both are
    off the table.

All 7 phases are now written (24 chapters total, plus the mental-model/roadmap doc, the
[Tools Reference](TOOLS_REFERENCE.md), and the multi-node serving folder this track
builds on) — the complete 28-domain roadmap, plus a practical single-GPU-instance
companion to the flagship-scale AWS material. The roadmap doc's skill-level table still
governs *review* pacing — re-read Phases 2-3 first if returning after a long gap, since
those cover the stated biggest gaps, before treating this as "done and shelved."

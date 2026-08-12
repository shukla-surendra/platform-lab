# Tools Reference: Every Command Introduced in This Track, One Lookup Table

Not a tutorial — a consolidated index of every CLI tool and command this track's 21
chapters introduced, organized by **diagnostic question** rather than by chapter, so a
real incident ("GPU utilization looks wrong," "is the network actually fast," "is this
node healthy") has a direct path to the right command without re-reading the chapter
that first introduced it. Each entry links back to the chapter with the full explanation
— use this page to find the right tool fast, then follow the link for the mechanism.

## "Is the GPU actually being used efficiently, or just busy?"

| Command | What it shows | Chapter |
|---|---|---|
| `nvidia-smi` | Coarse GPU utilization %, memory used, power, temperature | [`03_gpu_architecture.md`](phase2_gpu_fundamentals/03_gpu_architecture.md#reading-nvidia-smi-and-nvidia-smi-topo-m-against-this-model) |
| `nvidia-smi topo -m` | Interconnect matrix — NVLink vs. PCIe vs. NUMA-crossing, per GPU pair | [`03`](phase2_gpu_fundamentals/03_gpu_architecture.md), [`05_nvlink_nvswitch_topology.md`](phase2_gpu_fundamentals/05_nvlink_nvswitch_topology.md#reading-real-topology-nvidia-smi-topo-m-in-detail) |
| DCGM `DCGM_FI_DEV_GPU_UTIL` / `DCGM_FI_PROF_SM_ACTIVE` | SM utilization, more precisely than `nvidia-smi` alone | [`17_observability_for_gpu_fleets.md`](phase6_production_operations/17_observability_for_gpu_fleets.md#the-metric-catalog-organized-by-what-it-catches) |
| DCGM `DCGM_FI_PROF_DRAM_ACTIVE` | HBM bandwidth utilization — **must be read alongside SM utilization**, never alone, to distinguish compute-bound from memory-bound | [`17`](phase6_production_operations/17_observability_for_gpu_fleets.md) |
| Nsight Systems | Timeline-level profiler — is the GPU idle/starved by something upstream? | [`12_llm_performance_engineering.md`](phase5_llm_serving/12_llm_performance_engineering.md#deep-dive-profiling-the-actual-bottleneck-instead-of-guessing) |
| PyTorch Profiler | Per-operator time breakdown (which cuBLAS/cuDNN calls dominate) | [`12`](phase5_llm_serving/12_llm_performance_engineering.md) |

## "Is the interconnect/network actually healthy?"

| Command | What it shows | Chapter |
|---|---|---|
| `nvidia-smi topo -m` | Static topology check (see above) | [`05`](phase2_gpu_fundamentals/05_nvlink_nvswitch_topology.md) |
| `all_reduce_perf` (nccl-tests) | Measured collective bandwidth/latency vs. theoretical ceiling | [`08_nccl_testing.md`](phase3_gpu_networking/08_nccl_testing.md) |
| `NCCL_DEBUG=INFO` | Which transport NCCL actually selected per connection (NVLink, EFA/IB, or a slow fallback) | [`06_nccl_and_collective_communication.md`](phase3_gpu_networking/06_nccl_and_collective_communication.md#checking-nccl-is-actually-using-the-fast-path-nccl_debug) |
| DCGM `DCGM_FI_PROF_NVLINK_TX_BYTES`/`RX_BYTES` | Ongoing NVLink throughput vs. expected baseline | [`17`](phase6_production_operations/17_observability_for_gpu_fleets.md) |
| `lspci -vvv -s <addr>` | Negotiated vs. maximum-capable PCIe generation/lane width | [`02_computer_architecture_pcie_numa.md`](phase1_systems/02_computer_architecture_pcie_numa.md#pcie-generations-and-lanes-the-numbers-that-show-up-in-every-topology-check) |

## "Is there a hardware fault?"

| Command | What it shows | Chapter |
|---|---|---|
| `dmesg \| grep Xid` | XID error codes — the driver's structured hardware-fault signal | [`16_reliability_and_failure_management.md`](phase6_production_operations/16_reliability_and_failure_management.md#xid-errors-nvidias-structured-hardwaredriver-error-reporting-mechanism) |
| DCGM `DCGM_FI_DEV_ECC_DBE_VOL_TOTAL` / `DCGM_FI_DEV_ROW_REMAP_FAILURE` | ECC errors and row-remapping events, scrapeable via Prometheus | [`16`](phase6_production_operations/16_reliability_and_failure_management.md), [`17`](phase6_production_operations/17_observability_for_gpu_fleets.md) |
| DCGM `DCGM_FI_DEV_POWER_USAGE` / `DCGM_FI_DEV_GPU_TEMP` | Power/thermal — catches throttling that looks like an unexplained slowdown | [`17`](phase6_production_operations/17_observability_for_gpu_fleets.md) |

## "Is the driver/CUDA stack correctly installed and version-matched?"

| Command | What it shows | Chapter |
|---|---|---|
| `nvidia-smi` (top-right corner) | Maximum CUDA version the installed **driver** supports | [`04_cuda_ecosystem.md`](phase2_gpu_fundamentals/04_cuda_ecosystem.md#driver-vs-toolkit-the-version-rule-that-prevents-the-most-common-failure) |
| `nvcc --version` | Actually-installed CUDA **toolkit** version — a separate number from the driver's ceiling | [`04`](phase2_gpu_fundamentals/04_cuda_ecosystem.md) |

## "Is CPU/GPU/NIC placement NUMA-correct?"

| Command | What it shows | Chapter |
|---|---|---|
| `numactl --hardware` | Full NUMA topology of the host | [`01_linux_internals_for_gpu_workloads.md`](phase1_systems/01_linux_internals_for_gpu_workloads.md#proc-and-sys-where-gpu-adjacent-hardware-facts-actually-live) |
| `cat /sys/class/pci_bus/*/device/numa_node` | Which NUMA node a given PCI device (GPU) is attached to | [`01`](phase1_systems/01_linux_internals_for_gpu_workloads.md) |
| `numactl --cpunodebind=<n> --membind=<n>` | Pin a process to the GPU's own NUMA node | [`01`](phase1_systems/01_linux_internals_for_gpu_workloads.md) |
| `cat /proc/interrupts \| grep nvidia` + `/proc/irq/<n>/smp_affinity_list` | GPU/NIC interrupt routing vs. NUMA locality | [`01`](phase1_systems/01_linux_internals_for_gpu_workloads.md) |

## "Is this a Kubernetes-level GPU scheduling problem?"

| Command | What it shows | Chapter |
|---|---|---|
| `kubectl describe node <gpu-node>` | `nvidia.com/gpu` capacity/allocatable, GPU Feature Discovery labels | [`09_gpu_operator_and_device_plugin.md`](phase4_kubernetes_gpu/09_gpu_operator_and_device_plugin.md#deep-dive-the-full-path-from-pod-spec-to-running-cuda-code) |
| Kueue/Volcano job status | Whether a distributed job is stuck partially scheduled (gang-scheduling failure) | [`10_gpu_scheduling_mig_sharing.md`](phase4_kubernetes_gpu/10_gpu_scheduling_mig_sharing.md#the-gang-scheduling-problem-a-completely-different-concern) |

## Quick index: which chapter to open for which concept

| If the question is about... | Go to |
|---|---|
| SM/Tensor Core/HBM fundamentals | [`03_gpu_architecture.md`](phase2_gpu_fundamentals/03_gpu_architecture.md) |
| driver/toolkit/cuBLAS/cuDNN version issues | [`04_cuda_ecosystem.md`](phase2_gpu_fundamentals/04_cuda_ecosystem.md) |
| NVLink/NVSwitch topology | [`05_nvlink_nvswitch_topology.md`](phase2_gpu_fundamentals/05_nvlink_nvswitch_topology.md) |
| all-reduce/reduce-scatter/all-gather mechanics | [`06_nccl_and_collective_communication.md`](phase3_gpu_networking/06_nccl_and_collective_communication.md) |
| RDMA/EFA/InfiniBand/GPUDirect | [`07_rdma_roce_infiniband.md`](phase3_gpu_networking/07_rdma_roce_infiniband.md) |
| benchmarking the network fabric | [`08_nccl_testing.md`](phase3_gpu_networking/08_nccl_testing.md) |
| how a GPU becomes schedulable in K8s | [`09_gpu_operator_and_device_plugin.md`](phase4_kubernetes_gpu/09_gpu_operator_and_device_plugin.md) |
| MIG, time-slicing, gang scheduling | [`10_gpu_scheduling_mig_sharing.md`](phase4_kubernetes_gpu/10_gpu_scheduling_mig_sharing.md) |
| Slurm vs. Kubernetes | [`11_slurm_vs_kubernetes.md`](phase4_kubernetes_gpu/11_slurm_vs_kubernetes.md) |
| TTFT/TPOT tuning, batching | [`12_llm_performance_engineering.md`](phase5_llm_serving/12_llm_performance_engineering.md) |
| quantization (GPTQ/AWQ/FP8/GGUF) | [`13_quantization.md`](phase5_llm_serving/13_quantization.md) |
| KV cache / training memory math | [`14_model_memory_estimation.md`](phase5_llm_serving/14_model_memory_estimation.md) |
| the nine-stage fleet lifecycle | [`15_gpu_fleet_lifecycle.md`](phase6_production_operations/15_gpu_fleet_lifecycle.md) |
| XID errors, draining, remediation | [`16_reliability_and_failure_management.md`](phase6_production_operations/16_reliability_and_failure_management.md) |
| the GPU metric catalog, dashboards, tracing | [`17_observability_for_gpu_fleets.md`](phase6_production_operations/17_observability_for_gpu_fleets.md) |
| $/GPU-hour, $/M tokens, spot vs. reserved | [`18_capacity_planning_and_finops.md`](phase6_production_operations/18_capacity_planning_and_finops.md) |
| NVMe/Lustre/S3, checkpoint I/O | [`19_storage_for_gpu_clusters.md`](phase6_production_operations/19_storage_for_gpu_clusters.md) |
| MIG-as-security-boundary, confidential computing | [`20_security_and_multi_tenancy.md`](phase6_production_operations/20_security_and_multi_tenancy.md) |
| FSDP/DeepSpeed/ZeRO stages | [`21_fsdp_deepspeed_zero.md`](phase7_advanced_training_infra/21_fsdp_deepspeed_zero.md) |
| MoE routing, expert parallelism | [`22_moe_expert_parallelism.md`](phase7_advanced_training_infra/22_moe_expert_parallelism.md) |
| LM Studio, local/single-machine inference | [`23_lmstudio_and_local_inference.md`](local_and_prototyping/23_lmstudio_and_local_inference.md) |
| Azure/GCP/OCI vs. AWS | [`24_multi_cloud_gpu_landscape.md`](phase6_production_operations/24_multi_cloud_gpu_landscape.md) |
| g5/g6 (A10G/L4) single-GPU instances | [`25_single_gpu_instance_selection_g5_g6.md`](phase6_production_operations/25_single_gpu_instance_selection_g5_g6.md) |
| Linux/NUMA/PCIe fundamentals for GPUs | [`01_linux_internals_for_gpu_workloads.md`](phase1_systems/01_linux_internals_for_gpu_workloads.md), [`02_computer_architecture_pcie_numa.md`](phase1_systems/02_computer_architecture_pcie_numa.md) |

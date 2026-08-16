# Single-GPU Instance Selection: g5.2xlarge, g6.2xlarge, and Why Flagship-Instance Rules Don't Apply

Part of [Phase 6 — Production Operations](../README.md#phase-6-production-operations),
sibling to [`18_capacity_planning_and_finops.md`](18_capacity_planning_and_finops.md) and
[`24_multi_cloud_gpu_landscape.md`](24_multi_cloud_gpu_landscape.md). Everything else in
this track's AWS coverage —
[`aws-production-architecture.md`](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/aws-production-architecture.md) —
is scoped to flagship 8-GPU clusters (`p5.48xlarge`-class) for 1TB-scale multi-node
serving. This chapter is the opposite end of the spectrum: the single-GPU dev/inference
tier (`g5`/`g6` families) most day-to-day work — prototyping, small-model serving, cost-
constrained deployments — actually runs on, where several assumptions from the flagship
material don't hold at all.

## Clarify

`g5.2xlarge` and `g6.2xlarge` are **single-GPU** instances — the "2xlarge" names the
vCPU/RAM tier within the family, not GPU count. That one fact invalidates several
flagship-instance assumptions immediately: no NVLink topology to check (there's one GPU),
no tensor-parallel group to place, no gang scheduling to worry about. The questions that
actually matter here are different: does the model even fit in 24GB, what's the real
memory-bandwidth ceiling, and — since MIG isn't available on this hardware at all — how
do you actually share the GPU if you need to.

## Core Concepts

### What's actually inside each instance

| | `g5.2xlarge` | `g6.2xlarge` |
|---|---|---|
| GPU | 1× NVIDIA **A10G** | 1× NVIDIA **L4** |
| Architecture die | Ampere, **GA102** — the gaming/prosumer die family, not the GA100 compute die A100 uses | Ada Lovelace, **AD104** — newer generation than A10G |
| GPU memory | 24GB **GDDR6** (not HBM) | 24GB **GDDR6** (not HBM) |
| Memory bandwidth | ~600 GB/s | ~300 GB/s — **lower than the older A10G**; L4 is a 72W, single-slot, power/density-optimized card, not a raw-bandwidth part |
| Tensor Core generation | 3rd-gen, no native FP8 | 4th-gen, **native FP8 support** |
| CPU interconnect | PCIe Gen4 | PCIe Gen4 |

**Why "same generation as A100" is a misleading way to think about A10G**: both are
Ampere, but A10G is built on a genuinely different die (GA102, the same lineage as
consumer RTX 3080/3090) than A100's GA100 compute die. This is the concrete reason A10G
lacks two features this track has treated as standard on datacenter-class Ampere/Hopper
parts — NVLink and MIG — neither of which is a driver limitation, both are physically
absent from the silicon.

### No HBM changes the memory-bound-decode math this track has built everywhere else

[`03_gpu_architecture.md`'s HBM chapter](../phase2_gpu_fundamentals/03_gpu_architecture.md#hbm-why-gpu-memory-bandwidth-not-just-capacity-is-the-real-budget)
and [`14_model_memory_estimation.md`](14_model_memory_estimation.md) build their
decode-throughput reasoning around H100-class HBM at ~3.35 TB/s. Both `g5` and `g6`
use GDDR6 instead — 5-10x less bandwidth than that reference point. The *mechanism*
transfers directly (decode is still memory-bandwidth-bound, per
[`03_gpu_architecture.md`](../phase2_gpu_fundamentals/03_gpu_architecture.md#hbm-why-gpu-memory-bandwidth-not-just-capacity-is-the-real-budget)),
but the *ceiling* is much lower — TPOT on these instances will be noticeably worse per
token than flagship-instance math would predict for an equivalently-sized model, even
before accounting for anything else. Budget for this explicitly rather than
extrapolating from H100-class numbers.

### 24GB is a hard ceiling — run the memory math before picking a model

Applying [`14_model_memory_estimation.md`'s inference formula](14_model_memory_estimation.md#the-inference-memory-budget-complete)
directly: a 7B model at FP16 is ~14GB of weights alone, leaving roughly 10GB for KV
cache, activations, and runtime overhead — real, immediate headroom pressure with almost
no concurrency or long-context margin. This is the instance class where
[`13_quantization.md`](13_quantization.md)'s precision ladder stops being a throughput
lever and becomes the deciding factor in whether a model fits *at all* — a model that
needs FP16 to fit a flagship GPU's HBM might need INT4 just to fit here.

### Native FP8 is the real reason to prefer L4 over A10G for inference

Per [`13_quantization.md`'s precision ladder](13_quantization.md#the-precision-ladder),
FP8 is natively accelerated only on 4th-gen-Tensor-Core-and-newer hardware. A10G's 3rd-gen
Tensor Cores don't have it — quantization there means INT8/INT4 via GPTQ/AWQ-style
calibration, not FP8's comparatively simple, hardware-accelerated path. For a
quantization-tolerant inference workload, this is usually the deciding factor over raw
spec comparison — L4's lower memory bandwidth can be offset by FP8's throughput
advantage in a way A10G structurally cannot match, but this should be benchmarked on the
actual model rather than assumed from the spec sheet alone.

### No MIG on either card — a hard scope boundary, not a driver gap

[`10_gpu_scheduling_mig_sharing.md`'s MIG section](10_gpu_scheduling_mig_sharing.md#mig-multi-instance-gpu-real-hardware-partitioning)
already scopes MIG to "A100/H100-class GPUs" — this chapter makes that boundary concrete:
MIG requires the GA100/GH100 compute dies specifically. A10G (GA102) and L4 (AD104) are
both built on different die families that never implemented MIG's hardware partitioning
circuitry. **No instance size in either the `g5` or `g6` family supports MIG** — this
isn't a smaller/cheaper-tier restriction, it's a fact about which chips exist on which
die, and it directly shapes the sharing options covered below.

### AMI choice determines whether `nvidia-smi` works at boot — not the instance type

`nvidia-smi` ships with the NVIDIA **driver** package, not with the GPU hardware and not
with the `g5`/`g6` instance family itself — picking a GPU instance type says nothing about
whether the AMI you boot on it has a driver installed. Concretely:

- **AWS Deep Learning AMI (DLAMI)** — both the GPU "Base" variant and the framework-specific
  ones (PyTorch DLAMI, etc.) — ships with the NVIDIA driver, CUDA toolkit, and `nvidia-smi`
  pre-installed and working immediately at boot. This is the standard recommendation
  specifically to skip the driver-bootstrap step, especially for a first GPU session.
- **NVIDIA GPU-Optimized AMI** (AWS Marketplace, published by NVIDIA) — also ships drivers
  pre-installed, sometimes a more current driver version than AWS's own DLAMI.
- **EKS/ECS GPU-optimized AMIs** — also pre-installed, since the Kubernetes device plugin and
  ECS GPU support both depend on a working driver already being present.
- **A stock/generic Ubuntu Server AMI or Amazon Linux 2023 AMI** on a `g5`/`g6` instance —
  **no driver pre-installed**, even though the GPU hardware is physically there. `nvidia-smi`
  returns "command not found" until a driver is installed manually (`ubuntu-drivers
  autoinstall`, NVIDIA's official `.run` installer, or AWS's own GPU driver installation
  guide).

**The practical rule**: pick a GPU-ready AMI (DLAMI or the NVIDIA Marketplace AMI) to skip
driver bootstrap entirely, unless there's a specific reason to control the driver version by
hand.

### First-boot verification checklist

Three commands worth running immediately after first SSH-ing into a freshly provisioned
`g5`/`g6` instance, before trusting it for any real work:

1. **`nvidia-smi`** — confirms the driver actually loaded, and shows the maximum CUDA
   version the installed driver supports (top-right of the header) — see
   [`04_cuda_ecosystem.md`'s driver-vs-toolkit distinction](../phase2_gpu_fundamentals/04_cuda_ecosystem.md#driver-vs-toolkit-the-version-rule-that-prevents-the-most-common-failure)
   for why that number and `nvcc --version`'s number are not the same thing and don't have
   to match exactly.
2. **`nvidia-smi -q`** once — the full field dump, worth reading cold at least once rather
   than only ever looking at the summary table: ECC error counts, throttle reasons, PCIe
   link width/generation.
3. **`nvcc --version`** — only if the workload compiles CUDA code directly rather than using
   a framework's prebuilt CUDA wheels (PyTorch's GPU wheel bundles its own CUDA runtime and
   doesn't need a system-wide toolkit install to run).

### `nvidia-smi dmon` — the streaming monitor, not just a snapshot

Plain `nvidia-smi` prints one point-in-time snapshot. `nvidia-smi dmon` (device monitor)
streams continuously updating rows instead — what you actually want while a training or
inference job is running, to watch behavior change over time rather than checking a single
instant repeatedly. The `-s` flag selects metric groups by a string of one-letter codes:

| Code | Metric group |
|---|---|
| `p` | Power usage and temperature |
| `u` | Utilization |
| `c` | SM/memory clocks |
| `v` | Power/thermal violations |
| `m` | Frame-buffer + BAR1 memory usage |
| `e` | ECC errors + PCIe replay errors |
| `t` | PCIe RX/TX throughput |

`nvidia-smi dmon -s pucvmet` streams all seven groups together, one refreshed row per
interval. **Verify this against `nvidia-smi dmon --help` on the actual instance before
relying on it in a real session** — the exact supported codes can shift slightly across
driver versions, so treat the table above as a starting point to confirm live, not
unchanging gospel.

## Deep-Dive: parallelization options, and why flagship-instance TP assumptions break

"Parallelize" splits into two genuinely different questions at this instance size:

**Scaling up (`g5.12xlarge`/`g5.48xlarge`, 4/8× A10G; `g6.12xlarge`/`g6.48xlarge`, 4/8×
L4)** — more GPUs in one box, but **neither A10G nor L4 supports NVLink at all**. Every
multi-GPU instance in these families connects its GPUs over plain PCIe — no NVSwitch
fabric, unlike the `p5.48xlarge` reference architecture
[`05_nvlink_nvswitch_topology.md`](../phase2_gpu_fundamentals/05_nvlink_nvswitch_topology.md#point-to-point-nvlink-vs-nvswitch-the-topology-distinction-that-actually-matters)
builds its uniform-connectivity assumption around. This is exactly the cautionary case
that chapter's trade-offs table names: tensor parallelism across PCIe-only GPUs pays a
real, measurable throughput cost, even within a single physical machine. Don't assume TP
"just works" at flagship speed here — running `nvidia-smi topo -m` on a multi-GPU `g5`/
`g6` instance shows `PIX`/`PXB`/`NODE` entries, never `NV#`, the direct, checkable
confirmation of this before committing an architecture to it.

**Scaling out (multiple `.2xlarge` instances)** — the more natural fit for this tier:
independent model replicas, one per instance, behind a load balancer — ordinary
data-parallel serving, not tensor/pipeline parallel. EFA isn't available at this instance
size (it shows up on the larger `.48xlarge` variants in each family), so cross-instance
traffic is ordinary networking — a non-issue for independent replicas that never need to
communicate, but it rules out real multi-node TP/PP the way
[`13_large_model_multi_gpu_inference/`](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/README.md)
describes for 1TB-class models. This tier is architecturally "many small independent
servers," not "one coordinated distributed job" — a different design pattern, not a
smaller version of the same one.

## Deep-Dive: sharing one GPU without MIG

With MIG off the table entirely, the real options, in order of isolation strength:

```
1. CUDA MPS (Multi-Process Service)
   Lets multiple processes submit work to the same GPU CONCURRENTLY
   rather than the GPU's default behavior of switching between them —
   reduces context-switch overhead, improves throughput for several
   small co-located jobs. Same caveat as time-slicing in
   10_gpu_scheduling_mig_sharing.md: NO hardware memory isolation.
   Fine for trusted, co-located workloads; not a security boundary,
   per 20_security_and_multi_tenancy.md's isolation-spectrum framing.

2. Kubernetes device-plugin time-slicing
   The same mechanism from
   10_gpu_scheduling_mig_sharing.md#time-slicing-software-scheduling-no-hardware-isolation
   — scheduler-level sharing, independent of MIG hardware support.
   On A10G/L4, this is the ONLY multi-tenant sharing option available
   at all, not one of two options weighed against MIG the way
   10_gpu_scheduling_mig_sharing.md frames it for A100/H100 fleets.

3. Default behavior (no special configuration)
   Multiple processes can already submit to the same GPU without any
   opt-in — each gets its own CUDA context, the GPU's own hardware
   scheduler time-slices between them. The baseline every option above
   improves on.
```

**The practical rule this produces**: if isolation between tenants genuinely matters on
this hardware, the answer isn't a sharing mechanism at all — it's separate `.2xlarge`
instances per tenant, since neither MPS nor Kubernetes time-slicing provides the hardware
guarantee MIG would on A100/H100-class hardware.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| `g6.2xlarge` (L4) over `g5.2xlarge` (A10G) for inference | Native FP8, generally better throughput-per-dollar on quantization-tolerant workloads | Lower raw memory bandwidth (~300 vs. ~600 GB/s) — worth benchmarking the specific model, not assuming |
| Scaling up to multi-GPU `g5`/`g6` for more capacity | More GPU memory/compute in one instance | No NVLink — TP pays a real PCIe-bound cost; often scaling out is the better answer instead |
| MPS/time-slicing for GPU sharing | The only sharing option available on this hardware at all | No hardware isolation — never appropriate for genuinely untrusted multi-tenancy |

## Failure Modes to Raise Proactively

- **Extrapolating H100-class HBM-bandwidth throughput expectations onto A10G/L4** — the
  memory-bound mechanism is identical, the ceiling is 5-10x lower; a TPOT estimate built
  from flagship-instance numbers will be wrong here.
- **Assuming multi-GPU `g5.48xlarge`/`g6.48xlarge` behaves like `p5.48xlarge` for tensor
  parallelism** — no NVLink means a real, checkable throughput cost that flagship-instance
  intuition will miss; verify with `nvidia-smi topo -m` before assuming.
- **Reaching for MIG as a sharing option on this hardware** — it doesn't exist on either
  die family; the only real options are MPS and time-slicing, both without hardware
  isolation.
- **Booting a stock OS AMI on a `g5`/`g6` instance and being confused when `nvidia-smi`
  isn't found** — the instance has the GPU hardware; it just has no driver installed yet.
  This reads like a hardware or provisioning failure but is actually an AMI-choice mistake —
  a DLAMI or NVIDIA Marketplace AMI would have had the driver ready at boot.

## Make It Yours

- Before provisioning either instance for a specific model, run
  [`14_model_memory_estimation.md`](14_model_memory_estimation.md)'s formula by hand
  against the actual 24GB ceiling — confirm the model fits with real KV-cache headroom
  at your expected concurrency, not just weights alone.
- If a multi-GPU `g5`/`g6` instance is ever provisioned, run `nvidia-smi topo -m` and
  confirm the interconnect is PCIe (`PIX`/`PXB`/`NODE`), not NVLink — the direct
  verification this chapter argues for rather than assuming from GPU count alone.

## Practice Questions

1. Why does "A10G is Ampere, same generation as A100" not imply A10G has NVLink or MIG,
   and what's the actual architectural reason for the gap?
2. A team picks `g6.2xlarge` over `g5.2xlarge` expecting better performance purely because
   L4 is newer — what spec should give them pause, and under what condition does L4 still
   win despite it?
3. Why is scaling out across multiple `g5.2xlarge` instances usually a better fit than
   scaling up to `g5.48xlarge` for a workload that needs more serving capacity but no
   cross-GPU communication?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "`g5` and `g6` are single-GPU AWS instances — A10G and L4
respectively — built on gaming/prosumer-lineage dies rather than the GA100/GH100 compute
dies A100/H100 use, which is why neither supports NVLink or MIG at any instance size in
either family. Both use GDDR6, not HBM, so the memory-bandwidth ceiling is 5-10x lower
than flagship instances, and 24GB caps model+KV-cache size directly. Scaling up to
multi-GPU variants doesn't get you NVSwitch-class tensor parallelism — it's PCIe-only,
with a real throughput cost — so scaling out with independent replicas is usually the
better fit, and GPU sharing has to fall back to MPS or Kubernetes time-slicing since MIG
isn't available on this hardware at all. And picking the instance is only half the
provisioning decision — the AMI is the other half, since `nvidia-smi` comes from the
driver, not the GPU: a DLAMI or NVIDIA Marketplace AMI has it working at boot, a stock
Ubuntu/Amazon Linux AMI doesn't, and that gap looks exactly like a hardware problem the
first time someone hits it."

**The follow-up-proof version**: be ready to name the specific die (GA102/AD104 vs.
GA100/GH100) as the root cause of the NVLink/MIG gap, rather than describing it as a
generic "smaller instance" limitation — this is what shows the reasoning is grounded in
real hardware facts, not a memorized instance-comparison table. On the provisioning side,
be ready to say *why* DLAMI avoids the driver-bootstrap problem (driver ships pre-installed
and version-matched to the AMI's bundled CUDA toolkit) rather than just naming it as "the
easy option" — and be able to name the actual verification commands (`nvidia-smi`,
`nvidia-smi -q`, `nvcc --version`) rather than gesturing at "checking if it works."

**Vocabulary builder**: *compute die vs. gaming/prosumer die* (the actual silicon-level
distinction behind which features a given GPU SKU supports), *GDDR6 vs. HBM* (a real
bandwidth-tier difference, not just a naming difference), *MPS* (CUDA's concurrent
multi-process sharing mechanism, distinct from both MIG and time-slicing), *driver vs.
toolkit* (the driver is what makes `nvidia-smi` work and sets the CUDA-version ceiling;
the toolkit — `nvcc` — is a separate, optional install for compiling CUDA code directly),
*snapshot vs. streaming monitor* (`nvidia-smi`'s single point-in-time read vs. `nvidia-smi
dmon`'s continuously updating rows — reach for `dmon` specifically when watching a live
job's behavior over time, not just checking current state once).


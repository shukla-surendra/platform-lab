# AWS Solution: Deploying and Managing a ~1TB Model in Production

Companion to [`tutorial.md`](tutorial.md) (the parallelism/memory
mental model) and [`tools-and-frameworks.md`](tools-and-frameworks.md)
(the serving-engine comparison). This doc is the concrete AWS answer:
which instances, how they're networked and loaded, how the deployment
is orchestrated, and — the part a system-design answer often skips —
how it's actually *operated* once it's live: monitored, scaled, and
updated without downtime, at a scale where a mistake is expensive.

**A note on precision**: instance families and their core capabilities
below are stable, well-established parts of AWS's GPU lineup — exact
current pricing, newest-generation availability in a given region, and
service-limit specifics change often enough that they should be
re-verified against AWS's own docs before being used in a real design,
the same discipline the [DeepSeek-OCR-2 AWS hosting
deep-dive](../04_model_serving_deployment_deepseek_ocr_aws_hosting.md#deep-dive-the-full-deployment-option-matrix)
already models for this section of the book — its disqualification
table (SageMaker Serverless, Lambda, Fargate all lack GPU support at
any tier) applies here too, more decisively, since a 1TB model
disqualifies them even more obviously than a 6.8GB one does.

## Compute: which instances, and why multi-node changes the calculus

| Instance | GPUs | Total GPU memory | Interconnect | Fit for this use case |
|---|---|---|---|---|
| `p5.48xlarge` | 8× H100 80GB | 640GB | NVLink (intra-node) + EFA (inter-node, ~3200 Gbps) | The default building block — one full TP=8 group per node |
| `p5e.48xlarge` / `p5en.48xlarge` | 8× H100 with more HBM, or H200 variants | Higher per-GPU memory than plain `p5` | Same EFA-based inter-node fabric | Fewer nodes needed for the same weight budget — worth pricing against "more p5 nodes" directly, not assumed better by default |
| `trn2.48xlarge` | AWS Trainium2 (custom silicon) | Large per-chip memory, competitive with H100-class | AWS's own high-bandwidth fabric (NeuronLink/EFA) | Real option once the serving engine's [Neuron SDK support for the specific model architecture](../04_model_serving_deployment_deepseek_ocr_aws_hosting.md#deep-dive-the-full-deployment-option-matrix) is confirmed — the same "verify architecture support before betting the launch on it" discipline as the OCR deep-dive, not a default pick |
| `inf2.48xlarge` | AWS Inferentia2 | Inference-optimized, lower cost/inference at volume for supported architectures | Neuron fabric | Same architecture-support caveat as `trn2` — a strong cost play *if* the model is on Neuron's supported list, a real risk if not |

**Why the instance count in this table isn't the whole story**: from
[`tutorial.md`'s worked
example](tutorial.md#deep-dive-sizing-the-cluster-a-worked-example), a
~1TB model needs roughly 2 full `p5.48xlarge` nodes for weights alone,
before KV cache headroom — meaning the actual production sizing
decision is never "how many GPUs," it's "how many *nodes*, each
contributing a full tensor-parallel group," which is why partial-node
autoscaling (adding one GPU) isn't a meaningful lever here the way it
is for a model that fits on a single GPU.

## Networking: EFA and placement groups

Cross-node pipeline-parallel activations move on every forward pass —
this has to ride on EFA, not ordinary VPC networking, or cross-node
communication becomes the dominant latency cost (named explicitly as a
failure mode in [`tutorial.md`](tutorial.md#failure-modes-to-raise-proactively)).
Two AWS-specific things that make this actually work in practice:

- **Cluster placement groups** — request that the node group's
  instances be provisioned physically close together in the data
  center, minimizing network hop count and maximizing the achievable
  EFA bandwidth between them. Skipping this is a common, quiet mistake:
  the instances still launch, EFA still technically works, it's just
  measurably slower than it would be with instances placed close
  together — a cost that shows up as "worse than expected throughput"
  with no obvious single cause.
- **EFA driver + NCCL configuration** — the GPU instances need the EFA
  driver installed and NCCL configured to actually use it (`NCCL
  _PROTO`/`FI_PROVIDER` environment variables pointing NCCL at the EFA
  libfabric provider) — this is infrastructure-as-code territory
  (baked into the AMI or container image), not something to configure
  by hand per deployment.

## Storage: getting ~1TB of weights onto GPUs quickly

**S3 is the source of truth, not the load path.** Loading 1TB directly
from S3 to every node on every cold start is slow enough to matter for
both initial deployment and autoscale responsiveness (named as a
failure mode in [`tutorial.md`](tutorial.md#failure-modes-to-raise-proactively)).
The standard pattern:

```
S3 (durable source of truth, versioned model artifacts)
   ↓  one-time or infrequent sync
FSx for Lustre (parallel filesystem, mounted on inference nodes)
   ↓  fast parallel read at instance boot
GPU memory (weights loaded into VRAM)
```

FSx for Lustre is a parallel filesystem specifically built for
high-throughput, low-latency access to large files across many compute
nodes simultaneously — the same shape of problem as loading a 1TB
model's shards onto 16+ GPUs at once. An FSx file system can be linked
directly to an S3 bucket, lazily (or eagerly) pulling objects in,
turning "cold-start load time" into a bounded, predictable number
instead of "however long S3 takes under whatever load it's under right
now."

## Orchestration: the actual deployment shape

Two realistic paths, matching [`tools-and-frameworks.md`'s
orchestration
section](tools-and-frameworks.md#orchestration-the-layer-that-actually-spans-nodes):

**SageMaker (Large Model Inference containers)** — the managed path.
SageMaker's LMI containers are specifically built for exactly this
scenario: a model too large for one instance, needing tensor/pipeline
parallelism across a multi-instance endpoint, with SageMaker owning the
underlying EC2 fleet, health checks, and endpoint management. The
trade, consistent with the [OCR deep-dive's framing of managed vs.
self-hosted](../04_model_serving_deployment_deepseek_ocr_aws_hosting.md#deep-dive-the-full-deployment-option-matrix):
less control over the exact serving-engine configuration, in exchange
for not operating the multi-node coordination layer directly.

**EKS + KubeRay + vLLM (or TensorRT-LLM)** — the self-managed path.
Node groups built from the GPU instances above, in a cluster placement
group, with EFA enabled; KubeRay manages the Ray cluster spanning those
nodes; the serving engine runs its multi-node TP+PP configuration on
top. Full control over routing, scaling policy, and multi-model
serving, at the cost of operating that control plane — the same
trade-off named generically in the tools doc, concretely instantiated
here.

## How it's managed and improved in production

This is the part a purely architectural answer tends to skip, and
where real staff-level signal shows up:

### Monitoring: the metrics that actually matter here

Generic CPU/memory dashboards don't answer the right questions for this
workload. The metrics that do:

- **GPU utilization AND cross-node network utilization, together** — 
  high GPU utilization alone doesn't rule out the network being the
  actual bottleneck (a GPU can look "busy" while its useful work is
  gated on waiting for a cross-node activation to arrive) — this exact
  gap is named as a failure mode in
  [`tutorial.md`](tutorial.md#failure-modes-to-raise-proactively).
  DCGM (NVIDIA Data Center GPU Manager) exporting to Prometheus is the
  standard source for the GPU side.
- **TTFT and TPOT, as separate distributions, not one blended latency
  number** — time-to-first-token and time-per-output-token behave
  differently under load (TTFT is dominated by the prefill/prompt
  processing pass, TPOT by the decode loop) and respond differently to
  batching changes, so collapsing them into one "latency" metric hides
  which one actually degraded.
- **KV cache occupancy** — how close the cluster is to the KV-cache
  ceiling sized in [`tutorial.md`'s worked
  example](tutorial.md#deep-dive-sizing-the-cluster-a-worked-example),
  as a leading indicator before it becomes an OOM incident rather than
  a metric only checked after one.
- **Queue depth at the batching scheduler** — the leading indicator for
  "we need to scale" that arrives *before* latency SLOs are actually
  breached, giving autoscaling a head start instead of reacting after
  the fact.

### Autoscaling: by node group, not by pod

Named in [`tutorial.md`](tutorial.md#reference-architecture) — scaling
has to add or remove whole tensor-parallel groups (whole nodes), not
individual GPUs or pods, because a partial shard of a sharded model is
useless in isolation. Concretely, this means the autoscaling trigger
(queue depth or TPOT breach, from the metrics above) drives a **node
group** scaling action (adding another full `p5.48xlarge` worth of
capacity as one more replica of the whole multi-node serving unit, not
a smaller increment), and the cold-start time for that new unit
includes the FSx-backed weight load above — which is exactly why that
load path being fast is an autoscaling-responsiveness concern, not
just a startup-convenience one.

### Rolling updates: why blue/green at this scale is a real cost decision

Updating to a new model checkpoint (a fine-tune, a quantization change,
a version bump) normally means standing up new capacity alongside the
old before cutting over — at this scale, that means **temporarily
doubling an already-expensive multi-node GPU fleet**, a cost decision
worth surfacing explicitly rather than assuming away:

- **Canary on a small traffic slice first** — route a small percentage
  of live traffic to one new multi-node replica before committing to a
  full rollout, catching a regression on real traffic patterns without
  paying for a fully doubled fleet, consistent with the [eval-gate
  discipline in LLMOps](../11_llmops.md#deep-dive-wiring-the-eval-gate-into-the-deployment-pipeline)
  — the canary here is a production-traffic extension of that same
  offline gate, not a separate practice.
- **Accept brief reduced capacity instead of doubling** — take one old
  replica out, bring one new replica up in its place, repeat — cheaper
  than blue/green, at the cost of reduced serving capacity (and
  possibly breached latency SLOs under peak load) during the rollover
  window. The right choice depends on whether the deployment has
  enough steady-state headroom to absorb one replica's worth of
  capacity loss — a question worth having a real, load-tested answer
  to before the first production rollout, not discovered during one.

### Cost management

- **On-demand or Reserved/Savings Plans for the serving fleet** — spot
  instances are a poor fit for a stateful, multi-node serving
  deployment (an interrupted node breaks the whole TP group it belongs
  to, not just itself) — spot is a much better fit for the *training*
  side of this system, not inference serving.
- **Right-sizing precision** — the fp8/quantization trade-off from
  [`tutorial.md`](tutorial.md#quantization-buying-back-memory-headroom-without-buying-more-gpus),
  revisited as an ongoing cost lever, not a one-time launch decision —
  as newer hardware/quantization tooling matures, the right trade-off
  point can shift.
- **Scale-to-zero for genuinely bursty, non-latency-critical traffic**
  — if the workload tolerates it (closer to the OCR deep-dive's async,
  queue-based traffic shape than a live chat endpoint), SageMaker
  Async Inference-style scale-to-zero avoids paying for idle multi-node
  GPU capacity between bursts — a real option to name explicitly rather
  than defaulting to always-on capacity out of habit.

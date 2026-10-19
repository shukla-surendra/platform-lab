# Kubernetes for AI — Working Notes

Seven topic areas on running AI/ML workloads on Kubernetes: storage fundamentals, GPU
scheduling, StatefulSets, ML-specific Operators, advanced Helm templating, scaling training
with Kubeflow, and security. Originally assembled from separate notes sessions (each was
independently numbered); reorganized here under one structure with cross-links between
related sections, but every fact, example, YAML snippet, and table from the original is
still present.

A complementary, more fundamentals-level file — Pods/Nodes/Clusters, Deployments/Services,
ConfigMaps/Secrets/Volumes, HPA, and *basic* Helm chart anatomy — lives alongside this one
at [`Kubernetes in AI.md`](./Kubernetes%20in%20AI.md). That file is a beginner-level course;
this one assumes those basics and goes deeper into AI-specific concerns. Its own Helm section
(Part 6, "What Is Helm," chart anatomy) is a reasonable prerequisite read before this file's
[Helm for AI](#helm-for-ai-advanced-templating-for-ml-infrastructure) section, which jumps
straight to conditionals, loops, and named templates.

## Table of contents

1. [Kubernetes PVC + EBS — Storage Fundamentals](#kubernetes-pvc--ebs--storage-fundamentals)
2. [GPU Scheduling in Kubernetes](#gpu-scheduling-in-kubernetes)
3. [StatefulSets for Data-Heavy Workloads](#statefulsets-for-data-heavy-workloads)
4. [Kubernetes Operators for ML](#kubernetes-operators-for-ml)
5. [Helm for AI: Advanced Templating for ML Infrastructure](#helm-for-ai-advanced-templating-for-ml-infrastructure)
6. [Scaling AI Training with Kubeflow](#scaling-ai-training-with-kubeflow)
7. [Kubernetes Security Best Practices for AI Workloads](#kubernetes-security-best-practices-for-ai-workloads)

---

## Kubernetes PVC + EBS — Storage Fundamentals

### The three objects, and the chain between them

| Object | What it actually is |
|---|---|
| **PVC** (PersistentVolumeClaim) | A **request for storage** made by a workload — it does not itself hold any data, it's a claim/ticket. |
| **PV** (PersistentVolume) | The **actual storage resource** that fulfills a PVC. |
| **StorageClass** | Defines **how** Kubernetes should provision the storage — e.g. an AWS StorageClass can dynamically create an EBS volume on demand. |

The chain a Pod's data actually flows through:

```
Pod → PVC → PV → EBS Volume
```

(This is the same chain worked through hands-on, with real captured output, in
`../k8s/k8s_explorer/docs/statefulset-walkthrough.md` — that walkthrough proves this exact
mechanism live against a running cluster, down to reading the backing volume's file directly.)

### EBS survives EC2, on purpose

- **EBS is a separate AWS resource from the EC2 node it's attached to.** Even though a volume
  is attached to an instance, it's independently provisioned — so EC2 node failure does not
  normally mean EBS data is lost.
- **EC2 can be deleted while EBS remains** — whether the volume is deleted along with the
  instance depends entirely on its `DeleteOnTermination` setting. Configured to retain it, the
  volume survives instance termination.
- **The same EBS volume can be detached from one EC2 and reattached to another.** This is the
  literal mechanism, not just a K8s abstraction:

  ```
  EC2-A 💥
    ↓
  EBS Volume ✅
    ↓
  EC2-B
  ```

### How Kubernetes uses this for pod recovery

```
Node A 💥
  ↓
EBS remains
  ↓
Node B
  ↓
Pod recreated
  ↓
Same PVC/EBS
  ↓
Same data ✅
```

A Pod dying with a node doesn't lose its data, because the actual bytes were never on the
node in the first place — they were on EBS the whole time, and Kubernetes just reattaches the
same volume when the replacement Pod lands (possibly on a different node).

### The one real limitation

Standard EBS volumes are generally **ReadWriteOnce (RWO)** — normally attached read/write to
**one node at a time**. For storage that multiple nodes need to access *simultaneously*, EBS
alone isn't the right tool; you typically need something like **EFS, NFS, or another
RWX-capable storage system** instead.

> **Pod is temporary. Node is replaceable. EBS/Persistent storage is what keeps your data
> alive.**

---

## GPU Scheduling in Kubernetes

*A practical guide for AI infrastructure teams and Kubernetes engineers.*

### The Kubernetes Scheduler

**What it is**: a control-plane component that **decides which node a Pod should run on**.

**Main job, as a sequence**:

```
Pod created → Scheduler → selects suitable Node → kubelet starts Pod on that Node
```

**How it chooses a node** — it checks the Pod's requirements against every available node's
actual state, including:

- CPU / Memory
- GPU resources
- Node selectors
- Node affinity
- Taints & tolerations
- Pod affinity / anti-affinity

**GPU example** — a Pod declaring:

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
```

The scheduler looks specifically for a node that has an **available GPU** and satisfies every
other scheduling constraint at the same time.

**Important distinction**: the Scheduler **does not run the Pod** — it only makes the
*placement decision* (Pod → Node). The **kubelet** on the selected node is what actually
starts it.

> **One-line definition**: the Kubernetes Scheduler is the component that selects the most
> suitable node for a newly created Pod based on its resource requirements and scheduling
> constraints.

### Why GPU scheduling matters

GPUs are expensive, scarce resources that require efficient allocation for AI workloads. The
**standard Kubernetes scheduler isn't GPU-aware by default** — it needs special configuration
to:

- Properly assign GPUs to pods
- Prevent resource underutilization
- Avoid resource conflicts between workloads
- Maximize return on GPU infrastructure investment

### Kubernetes and GPU support — the three pieces

- **NVIDIA Device Plugin** — enables Kubernetes to recognize and manage NVIDIA GPUs as
  schedulable resources at all.
- **Resource Requests** — Pods request GPUs the same syntactic way they request CPU/memory.
- **Cluster Support** — works across single-node and multi-node clusters for distributed AI
  workloads.

This infrastructure is essential for both AI inference and training workloads, ensuring pods
are scheduled only on nodes with the GPU resources they actually need.

### Requesting a GPU in a Pod

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
```

This specification:

- Guarantees **exactly one GPU** for the pod
- **Cannot request fractional GPUs** except through MIG (see below)
- The scheduler ensures the pod lands on a GPU-enabled node
- Prevents any other pod from using that same GPU

### Example — full GPU Pod specification

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  containers:
    - name: gpu-container
      image: pytorch/pytorch:latest
      resources:
        limits:
          nvidia.com/gpu: 1
```

This pod:

- **Runs a PyTorch container** — the official PyTorch image, with CUDA support
- **Requests a single GPU** — guarantees exclusive access to one NVIDIA GPU
- **Gets scheduled appropriately** — Kubernetes ensures it lands on a node with an available GPU

### NVIDIA Device Plugin, in more depth

**Key components**:

- Deploys as a **DaemonSet** across every GPU node (see
  [`../k8s/k8s_explorer/practice/daemonset-sidecar-demo/`](../k8s/k8s_explorer/practice/daemonset-sidecar-demo)
  for a from-scratch DaemonSet built and verified in this same repo — the device plugin is a
  real-world instance of exactly that pattern: one Pod per node, automatically).
- Advertises available GPUs to the Kubernetes scheduler.
- Handles GPU discovery and initialization on each node.

**Hardware support**:

- NVIDIA A100, H100, and other datacenter GPUs
- Multi-Instance GPU (MIG) technology
- Multi-GPU configurations (NVLink, etc.)

> **Without this plugin, Kubernetes cannot schedule workloads on GPUs at all.**

### Multi-GPU & MIG scheduling

**Multi-GPU requests**:

```yaml
resources:
  limits:
    nvidia.com/gpu: 4
```

Assigns **4 full GPUs to a single pod** — ideal for distributed training workloads.

**MIG slices for inference**:

```yaml
resources:
  limits:
    nvidia.com/mig-1g.5gb: 2
```

Requests **2 MIG slices**, each representing 1 compute instance with 5 GB memory.
**MIG (Multi-Instance GPU)** enables fractional GPU allocation, significantly improving
resource utilization for inference workloads that don't need a full GPU.

### Scheduling across nodes — three mechanisms

**1. Node Selectors**

```yaml
nodeSelector:
  accelerator: nvidia-gpu
```

Ensures pods run only on **labeled GPU nodes**.

**2. Taints and Tolerations**

```yaml
tolerations:
  - key: "gpu"
    operator: "Exists"
    effect: "NoSchedule"
```

Reserves GPU nodes for **GPU workloads only**.

**3. Affinity Rules**

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: gpu-type
              operator: In
              values:
                - "a100"
```

Provides **fine-grained control for specific GPU types**.

Together, these three mechanisms ensure workloads run on appropriate hardware across the
cluster.

### Monitoring GPU usage in Kubernetes

**Basic monitoring**:

- `kubectl describe node` shows allocated GPUs
- `kubectl describe pod` shows GPU assignments

**Advanced monitoring**:

- **NVIDIA DCGM Exporter** → Prometheus metrics
- **Grafana dashboards** for GPU utilization
- **Custom alerts** for idle or overutilized GPUs

Comprehensive monitoring is **critical for cost optimization** — idle GPU waste can cost
thousands of dollars per month.

### Challenges in GPU scheduling

- **No native GPU preemption** — long-running jobs can block critical workloads, leading to
  wasted capacity and potential SLA violations.
- **Mixed workload inefficiency** — training and inference workloads have different resource
  patterns but often share the same GPU, causing resource contention.
- **Multi-tenant fairness** — ensuring equitable GPU access across teams without dedicated
  hardware silos requires advanced policies.
- **Auto-scaling complexity** — GPU nodes are expensive and slow to provision, making cluster
  auto-scaling challenging and potentially costly.

Advanced schedulers like **KubeFlow, Slurm, and Volcano** address some of these challenges but
add operational complexity of their own.

### Key takeaways — GPU scheduling

- **GPU scheduling is vital for AI infrastructure efficiency** — proper configuration can save
  thousands of dollars in GPU utilization.
- **The NVIDIA device plugin enables K8s GPU support** — required for any GPU workload in
  Kubernetes.
- **Pods request GPUs via resource limits** — simple syntax for hardware allocation with
  granular control options.
- **MIG allows fractional GPU sharing** — significantly improves utilization for inference
  workloads.

For production AI clusters, implement comprehensive **monitoring, fairness policies, and
resource quotas** to maximize GPU infrastructure ROI.

---

## StatefulSets for Data-Heavy Workloads

*A comprehensive guide for cloud-native engineers and ML infrastructure teams.*

> **Live, hands-on companion to this section**: every guarantee described below is proven
> against a real 3-replica cluster — ordered creation, per-replica DNS, a deleted Pod
> reattaching to its exact same PVC (verified down to reading the actual file on the node's
> disk), and reverse-order scale-down — in
> [`../k8s/k8s_explorer/docs/statefulset-walkthrough.md`](../k8s/k8s_explorer/docs/statefulset-walkthrough.md),
> built on [`../k8s/k8s_explorer/practice/statefulset-identity-demo/`](../k8s/k8s_explorer/practice/statefulset-identity-demo).
> The notes below are the concept; that page is the proof.

### Why StatefulSets for AI?

- **Persistent data & identity** — AI workloads require consistent data access and stable
  network identities that standard Deployments can't provide.
- **Data-heavy requirements** — feature stores, distributed training, and vector databases
  need guaranteed storage persistence and ordered operations.
- **Consistency guarantees** — StatefulSets maintain predictable pod naming and network
  addressing, critical for distributed ML systems.

### What is a StatefulSet?

A specialized Kubernetes workload designed specifically for applications that require:

- **Stable identity** — predictable pod names that persist across rescheduling.
- **Persistent storage** — dedicated volumes that remain bound to specific pods.
- **Ordered operations** — controlled pod startup/shutdown sequences.

> **Unlike Deployments**, each StatefulSet pod maintains a unique identity critical for
> stateful applications.

### StatefulSet characteristics

1. **Stable network identity** — predictable DNS names (`pod-0`, `pod-1`, `pod-2`) that
   persist even after pod rescheduling.
2. **Persistent Volume Claims** — each pod receives its own dedicated storage volume that
   remains bound to it throughout its lifecycle.
3. **Ordered pod management** — controlled pod creation, deletion, and updates in sequential
   order, critical for distributed systems.
4. **Identity preservation** — when scaling, existing pod-to-storage mappings are preserved,
   maintaining data consistency.

### Example use cases in AI infrastructure

- **Distributed training** — parameter servers that require stable identity and consistent
  data access across training runs.
- **Vector databases** — Pinecone, Weaviate, and Milvus deployments that maintain embeddings
  and indexes.
- **Feature stores** — centralized repositories that need persistent storage and reliable
  retrieval mechanisms.
- **Data preprocessing** — large-scale ETL jobs that require deterministic ordering and
  consistent state.
- **Stream processing** — Kafka and Spark clusters that process data in ordered, stateful
  pipelines.
- **Model serving** — production inference systems with cached weights and persistent
  configuration.

### Example — full StatefulSet specification

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: data-ai
spec:
  serviceName: "data-svc"
  replicas: 3
  selector:
    matchLabels:
      app: data-ai
  template:
    metadata:
      labels:
        app: data-ai
    spec:
      containers:
        - name: worker
          image: pytorch/pytorch:latest
          volumeMounts:
            - name: data-volume
              mountPath: /data
  volumeClaimTemplates:
    - metadata:
        name: data-volume
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 50Gi
```

**Key components**:

- **`serviceName`** — creates a headless service for stable network identity.
- **`volumeClaimTemplates`** — each pod gets dedicated 50GB storage.
- **`volumeMounts`** — maps that storage into the container filesystem.

Each pod will be named `data-ai-0`, `data-ai-1`, `data-ai-2`, each with its own persistent
volume.

### Benefits for data-heavy workloads

- **Consistent identity** — pods maintain the same network identity across restarts, ensuring
  distributed systems function properly.
- **Data sharding** — each replica can manage its own dataset shard or cache, enabling
  horizontal data partitioning.
- **High availability** — ordered scaling ensures ML pipelines remain functional during
  upgrades and scaling operations.
- **Long-running jobs** — perfect for AI workloads that run for days or weeks with consistent
  storage access requirements.

> These benefits make StatefulSets **essential infrastructure** for production ML systems that
> process large volumes of data.

### StatefulSets vs Deployments

| Feature | Deployment | StatefulSet |
|---|---|---|
| **Pod Identity** | Random, replaceable | Stable, sequential (`pod-0`, `pod-1`, `pod-2`) |
| **Storage** | Shared or ephemeral | Persistent per pod |
| **Use Case** | Stateless applications | Data-heavy ML infrastructure |
| **Scaling Behavior** | Any order, parallel | Ordered, predictable |
| **Pod Replacement** | Completely new instance | Same identity, storage retained |
| **Network Requirements** | Basic | Headless Service recommended |

### Challenges with StatefulSets

- **Increased complexity** — more configuration and management overhead compared to simple
  Deployments.
- **Recovery complexity** — data recovery and volume management require more careful
  procedures.
- **Storage cost scaling** — storage expenses increase linearly with replicas, requiring
  careful capacity planning.
- **Networking requirements** — infrastructure must support stable DNS and network identity
  features.
- **Sequential operations** — slower scaling due to ordered pod creation and termination
  requirements.
- **Cloud provider limitations** — some managed K8s services have StatefulSet implementation
  limitations.

> ⚠️ **The additional complexity of StatefulSets is justified only when your workload truly
> requires stable identity and persistent storage.**

### Best practices

1. **Use when appropriate** — deploy StatefulSets only for workloads that genuinely need
   persistent storage and ordered operations. Use Deployments for everything else.
2. **Headless Services** — always pair StatefulSets with Headless Services (`clusterIP: None`)
   to enable stable DNS names for pods, in the format
   `<pod-name>.<service-name>.<namespace>.svc.cluster.local`.
3. **Storage management** — implement storage monitoring and scaling alerts. Use
   StorageClasses with appropriate reclaim policies for dynamic volume provisioning.
4. **Backup strategies** — create consistent backups of StatefulSet data with tools like Velero
   that understand the relationship between pods and their volumes.
5. **Pod Disruption Budgets** — implement PDBs to prevent too many StatefulSet pods from being
   unavailable simultaneously during maintenance events.

### Key takeaways — StatefulSets

- **Essential for data-heavy AI** — StatefulSets are the foundation for reliable AI data
  infrastructure, providing the stability and persistence ML systems require.
- **Unique capabilities** — stable pod identities and persistent storage address the specific
  needs of databases, feature stores, and distributed ML workloads.
- **Strategic implementation** — while more complex than Deployments, the benefits outweigh
  the costs for truly stateful applications in your ML infrastructure.

By understanding when and how to use StatefulSets, you can build robust, scalable AI
infrastructure that handles data-heavy workloads with confidence.

**Next steps**:

- Review existing Deployments for stateful workloads
- Implement monitoring for StatefulSet volumes
- Test backup and recovery procedures

---

## Kubernetes Operators for ML

*Automating machine learning workflows in Kubernetes for scalable, reproducible, and
efficient ML operations.*

### Why operators for ML?

Machine learning workloads have unique complexity combining data processing, model training,
and serving requirements. Manual Kubernetes configurations lead to error-prone, repetitive
work that slows down development cycles.

- **Operators = "AI admins in code"** — automate the complete lifecycle: deployment, scaling,
  and monitoring of ML applications.
- **Bridge MLOps + Kubernetes** — unify ML best practices with container orchestration power.

### What is a Kubernetes Operator?

- **Extensions of the Kubernetes control plane** — custom controllers that extend Kubernetes
  functionality.
- **Uses Custom Resource Definitions (CRDs)** — defines domain-specific objects that
  Kubernetes can manage.
- **Reconciliation loop** — continuously watches resources and reconciles them to the desired
  state.
- **Operational knowledge as code** — e.g. an ML Operator handles model training + serving
  automatically.

### Why ML needs operators

Machine learning workloads have unique complexity combining data processing, model training,
and serving requirements:

- **Automates distributed training** — handles multi-GPU, multi-node coordination.
- **Simplifies model serving** — deployment, scaling, and traffic management.
- **Manages ML infrastructure** — pipelines, feature stores, drift detection.
- **Reduces DevOps overhead** — ML engineers focus on models, not infrastructure.

### Examples of ML operators

1. **Kubeflow TFJob** — handles TensorFlow distributed training across multiple nodes.
2. **PyTorchJob Operator** — manages PyTorch multi-node, multi-GPU training workloads.
3. **KFServing / KServe** — deploys models with canary rollouts and autoscaling capabilities.
4. **MLflow Operator** — integrates experiment tracking and model deployment workflows.
5. **Ray Operator** — facilitates distributed ML and reinforcement learning at scale.

### Example — PyTorchJob CRD

```yaml
apiVersion: "kubeflow.org/v1"
kind: PyTorchJob
metadata:
  name: pytorch-job
spec:
  pytorchReplicaSpecs:
    Master:
      replicas: 1
      template:
        spec:
          containers:
            - name: pytorch
              image: pytorch/pytorch:latest
    Worker:
      replicas: 2
      template:
        spec:
          containers:
            - name: pytorch
              image: pytorch/pytorch:latest
```

**Key points**:

- ✓ Defines distributed PyTorch training with **1 master + 2 workers**
- ✓ No need to manually configure networking between nodes
- ✓ Automatic recovery if pods fail

(A second, fuller PyTorchJob example — 1 master + 4 workers, with the reasoning behind each
field — is walked through in the
[Kubeflow Training Operators](#3-kubeflow-training-operators) section below; this one is the
minimal shape, that one is the annotated version.)

### Benefits of ML operators

- **Declarative ML workloads** — define entire ML systems in YAML, not complex scripts.
- **Seamless scaling** — scale training & inference based on demand or resource availability.
- **Automated fault recovery** — self-healing infrastructure with automatic retries.
- **Infrastructure-as-code** — ML systems defined as code, with GPU/TPU integration across
  clouds.

### Operators in model serving

- **KServe / KFServing** — deploy models with YAML.
- **Advanced deployment strategies** — A/B testing, canary rollouts, and autoscaling built
  into the operator.
- **Framework agnostic** — works with TensorFlow, PyTorch, XGBoost, ONNX, and custom models.
- **Integrated monitoring** — built-in hooks for metrics collection and drift detection.

### Challenges with operators

- **Learning curve** — steeper than standard Kubernetes resources like Deployments.
- **Resource overhead** — extra controllers running in your cluster consume resources.
- **Debugging complexity** — troubleshooting failures across custom resources can be
  challenging.
- **Framework coverage** — not all ML frameworks have mature operator implementations.
- **Kubernetes expertise** — requires deeper understanding of Kubernetes architecture.

### Best practices — ML operators

- **Start with community operators** — use established operators from Kubeflow, KServe, and
  Ray before building custom ones.
- **Keep configs in Git** — store operator configurations in version control for
  reproducibility.
- **Monitor operator health** — regularly check operator controllers for proper functioning.
- **Focus on scalable infrastructure** — use operators for scalable + repeatable ML
  infrastructure that needs to be standardized across teams.

### Key takeaways — ML operators

> **Operators = Kubernetes-native automation for ML** — automate the complete ML lifecycle:
> training workflows, model serving, dynamic scaling, production monitoring.

**Popular options**: TFJob, PyTorchJob, KServe, Ray.

> "The future of AI infrastructure is fully declarative via Kubernetes Operators."

Critical for enterprise-scale ML infrastructure and mature MLOps.

---

## Helm for AI: Advanced Templating for ML Infrastructure

### 1. First — what problem is Helm solving?

Suppose you deploy an AI inference server. Without Helm, you might have separate manifests:

```
deployment.yaml
service.yaml
configmap.yaml
pvc.yaml
servicemonitor.yaml
hpa.yaml
```

...each containing hardcoded values like:

```
replicas: 3
image: myrepo/llama:v2
memory: 16Gi
cpu: "4"
gpu: 2
```

Now your environments differ:

| | Dev | Staging | Production |
|---|---|---|---|
| replicas | 1 | 2 | 5 |
| GPU | 0 | 1 | 2 |
| memory | 8Gi | 16Gi | 32Gi |

You **could** copy all the YAML files three times, but then you have a maintenance nightmare —
one drifted value in one copy and your environments silently diverge.

> Helm's answer: **keep the Kubernetes structure in templates, and put the things that change
> into values.**

### 2. Think of Helm like this

A very useful mental model:

```
            Helm Chart
                 │
       ┌─────────┴─────────┐
       │                   │
   Templates            Values
       │                   │
       │              values.yaml
       │                   │
       └─────────┬─────────┘
                 ↓
        Helm renders templates
                 ↓
          Kubernetes YAML
                 ↓
        Kubernetes API Server
```

For example — **Template**:

```yaml
replicas: {{ .Values.app.replicas }}
```

**values.yaml**:

```yaml
app:
  replicas: 3
```

Helm combines them into:

```yaml
replicas: 3
```

That's the fundamental idea.

### 3. What is `.Values`?

One of the most important concepts. Suppose:

```yaml
# values.yaml
image:
  repository: myrepo/ai-app
  tag: v2.0.3
```

Your template can say:

```yaml
image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
```

Helm reads `.Values.image.repository` → `myrepo/ai-app`, and `.Values.image.tag` → `v2.0.3`,
producing:

```yaml
image: "myrepo/ai-app:v2.0.3"
```

So: `.Values` = the configuration supplied to your Helm chart.

### 4. Why use `--set`?

You don't necessarily have to edit `values.yaml`. You can instead do:

```bash
helm install ai-app ./chart \
  --set app.replicas=5 \
  --set image.tag=v2.0.3
```

Conceptually: `values.yaml` + `--set` overrides → final Helm values → Templates → Kubernetes
manifests.

So if `values.yaml` says `app.replicas: 3` but you run `--set app.replicas=5`, the effective
value becomes `5`.

### 5. Conditionals — where Helm becomes genuinely useful for AI

```yaml
{{- if .Values.gpu.enabled }}
resources:
  limits:
    nvidia.com/gpu: {{ .Values.gpu.count | default 1 }}
{{- else }}
resources:
  limits:
    cpu: {{ .Values.cpu.limit }}
    memory: {{ .Values.memory.limit }}
{{- end }}
```

This means: **GPU enabled? → yes → GPU pod. No → CPU pod.**

If:

```yaml
gpu:
  enabled: true
  count: 2
```

Helm generates:

```yaml
resources:
  limits:
    nvidia.com/gpu: 2
```

But if `gpu.enabled: false`, it generates:

```yaml
resources:
  limits:
    cpu: "4"
    memory: "16Gi"
```

That's extremely useful for AI infrastructure — **one chart**, deployed differently: dev →
GPU disabled, staging → 1 GPU, production → 2 GPUs.

### 6. What does `range` do?

Another important advanced feature. Imagine you want to deploy three models:

```yaml
models:
  - name: llama
    version: v1
  - name: qwen
    version: v2
  - name: mistral
    version: v3
```

Instead of manually creating `deployment-llama.yaml`, `deployment-qwen.yaml`,
`deployment-mistral.yaml`, you can loop:

```yaml
{{- range .Values.models }}
...
deployment for this model
...
{{- end }}
```

So `range` basically means: **for every item in this list, generate this YAML.** This becomes
very powerful for multi-model serving.

### 7. Named templates

Suppose every resource needs the same labels:

```yaml
app: ai-inference
team: ml-platform
environment: production
```

You don't want to copy this everywhere. Create a reusable template in `_helpers.tpl`:

```yaml
{{- define "ai.labels" }}
app: {{ .Values.app.name }}
team: ml-platform
{{- end }}
```

Then use it anywhere with:

```yaml
{{ include "ai.labels" . }}
```

Define once → include everywhere. This is basically **functions for your Helm templates**.

### 8. Why Helm is particularly useful for AI

An AI serving deployment may have many moving pieces at once: the model server itself, a GPU,
model weights, PVC/object storage, a Service, an Ingress, an HPA, Prometheus monitoring,
logging, and configuration — and different models need very different resources:

| Model | Resources |
|---|---|
| Llama 7B | 1 GPU, 16 GB memory |
| Qwen 30B | 2 GPUs, 40+ GB memory |
| Large model | Multiple GPUs, multiple nodes |

Rather than hard-code these into Kubernetes manifests, Helm lets you express them as
configuration.

### 9. One important correction

A common claim is something like "configure GPU requests based on model size, with fallbacks
to CPU when GPUs aren't available." Be careful here:

> **Helm itself does not detect whether GPUs are available on your Kubernetes cluster.**

Helm is primarily generating manifests. For example, `nvidia.com/gpu: 2` — Helm simply puts
that into the generated Kubernetes YAML. Then **Kubernetes scheduling** determines whether a
node can satisfy it. The actual flow:

```
Helm → generates → nvidia.com/gpu: 2 → Kubernetes scheduler → finds suitable GPU node → Pod scheduled
```

Helm doesn't magically inspect your cluster and say "oh, there is no GPU, I'll use CPU" — you
have to explicitly configure that behavior yourself (e.g. via the conditional pattern above).

### 10. Environment-specific values — probably the most practical pattern

A common structure:

```
ai-chart/
├── Chart.yaml
├── values.yaml
├── values-dev.yaml
├── values-staging.yaml
├── values-prod.yaml
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── pvc.yaml
    ├── hpa.yaml
    └── servicemonitor.yaml
```

Then:

```bash
# Development
helm install ai ./ai-chart -f values-dev.yaml

# Staging
helm install ai ./ai-chart -f values-staging.yaml

# Production
helm install ai ./ai-chart -f values-prod.yaml
```

Same templates. Different configuration.

### 11. The real DevOps mental model

```
                HELM CHART
                     │
       ┌─────────────┴─────────────┐
       │                           │
   Templates                    Values
       │                     ┌─────┴─────┐
       │                     │           │
       │                    Dev        Prod
       │                     │           │
       │                    1 GPU       2 GPUs
       │                    1 replica   5 replicas
       │                    8Gi         32Gi
       │                           │
       └─────────────┬─────────────┘
                     ↓
               Helm rendering
                     ↓
              Kubernetes YAML
                     ↓
              Kubernetes cluster
                     ↓
              AI application
```

The key distinction:

- **Kubernetes YAML** describes *what* you want.
- **Helm templates** describe *how to generate* that YAML.
- **`values.yaml`** describes *what should vary*.

### 12. The connection to real GPU/LLM work

Suppose you're experimenting with multi-GPU LLM serving. You might create:

```yaml
model:
  name: qwen
  version: "30b"
gpu:
  enabled: true
  count: 2
resources:
  memory: 64Gi
replicas: 1
monitoring:
  enabled: true
```

Your Helm chart can then generate the complete deployment: Deployment + Service + GPU
configuration + Model configuration + Storage + Monitoring + Autoscaling, all from that one
values file. And tomorrow you could change `gpu.count: 4` without rewriting the Kubernetes
manifests at all. That's the real value of advanced Helm templating for AI infrastructure.

> **One sentence to remember**: Helm is a parameterized YAML generator + Kubernetes release
> manager; advanced templates let you turn one Kubernetes deployment definition into many
> configurable deployments.

---

## Scaling AI Training with Kubeflow

> A comprehensive guide for ML engineers and MLOps practitioners looking to scale AI training
> workloads efficiently using Kubernetes-native tools.

### 1. Why Kubeflow for AI training?

AI training workloads have requirements that are different from ordinary applications. For
example, large-scale training may require:

- Multiple GPUs
- Multiple Kubernetes nodes
- Distributed communication between workers
- Checkpointing and recovery
- Hyperparameter optimization
- Experiment tracking
- Model evaluation
- Automated retraining
- Model deployment

**Kubeflow** provides Kubernetes-native components specifically designed to handle these ML
requirements.

**Three major reasons to use Kubeflow**:

| Capability | What it provides |
|---|---|
| **Native Kubernetes Integration** | Purpose-built for ML workflows running on Kubernetes infrastructure |
| **Simplified Distributed Training** | Orchestrates multi-GPU and multi-node training jobs with minimal configuration |
| **Enterprise-Scale MLOps** | Integrates training pipelines, model serving, monitoring, and other ML lifecycle components |

**Big picture**:

```
                Kubeflow
                    │
       ┌────────────┼────────────┐
       │            │            │
   Training      Pipelines     Katib
       │            │            │
       ↓            ↓            ↓
 Distributed      ML DAGs    Hyperparameter
  Training                    Optimization
       │
       ↓
 Kubernetes
       │
 ┌─────┼─────┐
 GPU   GPU   GPU
```

### 2. What is Kubeflow?

**Open-source ML toolkit** — Kubeflow is an open-source machine learning toolkit built
specifically for Kubernetes environments. It brings ML capabilities to cloud-native
infrastructure.

> **In simple terms**: Kubeflow is a collection of Kubernetes-native tools for running and
> managing machine-learning workloads.

**Modular components** — Kubeflow isn't one giant component that does everything. It consists
of different components that can work together or independently, e.g. training operators,
pipelines, hyperparameter tuning, model serving, experiment management, monitoring/integration
components.

**MLOps simplification** — Kubeflow attempts to make machine learning on Kubernetes resemble
standard DevOps practices:

```
Traditional DevOps          ML / MLOps (Kubeflow)
Git                          Data
 ↓                            ↓
CI/CD                        Training
 ↓                            ↓
Kubernetes                   Evaluation
 ↓                            ↓
Application                  Model
                              ↓
                              Deployment
                              ↓
                              Monitoring
                              ↓
                              Retraining
```

> **Core idea**: Kubeflow bridges the gap between ML research and production by leveraging
> Kubernetes' scheduling and orchestration capabilities for resource-intensive AI workloads.

### 3. Kubeflow Training Operators

One of the most important parts of Kubeflow is its **Training Operators**, implemented using
**Kubernetes Custom Resource Definitions (CRDs)**. These CRDs extend Kubernetes with resources
specifically designed for different ML frameworks. Instead of creating and manually managing
many Pods, you can create something like `kind: PyTorchJob` and let the operator manage the
distributed training workload.

**Major training operators**:

1. **TFJob** — used for distributed TensorFlow training. Manages distributed TensorFlow
   training across parameter servers and workers (`TFJob → TensorFlow training → parameter
   servers / workers`).
2. **PyTorchJob** — used for distributed PyTorch training, particularly relevant when using
   **PyTorch Distributed Data Parallel (DDP)** (`PyTorchJob → PyTorch DDP → Worker 1..4`).
3. **MXNetJob** — handles MXNet's parameter-server-based distributed training.
4. **XGBoostJob** — coordinates distributed training for gradient-boosted decision trees using
   XGBoost.

**Why training operators?** Without one, you might have to manually manage Pods, networking,
worker discovery, process startup, failure handling, restarting, distributed configuration,
and lifecycle. The Training Operator provides an abstraction over much of this complexity.

> **Key idea**: Training Operators allow you to describe the desired distributed training job
> declaratively, instead of manually orchestrating every Pod.

### 4. Example: PyTorchJob, annotated

A simplified PyTorchJob:

```yaml
apiVersion: "kubeflow.org/v1"
kind: PyTorchJob
metadata:
  name: resnet-train
spec:
  pytorchReplicaSpecs:
    Master:
      replicas: 1
      template:
        spec:
          containers:
            - image: pytorch/pytorch:latest
              name: pytorch
    Worker:
      replicas: 4
      template:
        spec:
          containers:
            - image: pytorch/pytorch:latest
              name: pytorch
```

**What this means**: `Master.replicas: 1` and `Worker.replicas: 4`, so conceptually:

```
              PyTorchJob
                   │
          ┌────────┴────────┐
          │                 │
       Master            Workers
        1 Pod             4 Pods
          │                 │
          │       ┌─────────┼─────────┐
          │       │         │         │
          │     GPU/CPU   GPU/CPU   GPU/CPU
          │
          └───────────────┐
                          ↓
                   Distributed
                    Training
```

### 5. What does Kubeflow handle here?

This example defines a ResNet training job with 1 master and 4 workers, using standard
Kubernetes Pod specifications for configuring containers. The Training Operator handles
important distributed-training concerns such as:

- Creating the required Pods
- Setting up communication between workers
- Managing Pod lifecycle
- Handling failures and recovery

So instead of manually creating and coordinating many Kubernetes resources, you describe the
desired training job. **The important abstraction**:

```
Without Kubeflow:  You manage distributed training infrastructure → lots of details

With PyTorchJob:    PyTorchJob YAML → Training Operator → Distributed workers → PyTorch training
```

> This simple YAML can replace a large amount of manual setup for distributed PyTorch
> training.

### 6. Benefits of Kubeflow training

**6.1 Declarative ML workloads** — you define the desired state in YAML. For example,
`Worker.replicas: 4` is you saying "I want four worker replicas" — Kubernetes + Kubeflow
handle the implementation. This brings **Infrastructure-as-Code principles to ML workloads**.

**6.2 Automatic resource scheduling** — Kubernetes can schedule CPUs, GPUs, TPUs, and memory
based on requested resources + available cluster resources → the scheduler → a suitable node.
For GPU workloads, `resources.limits.nvidia.com/gpu: 1` indicates a Pod requires one NVIDIA
GPU.

**6.3 Seamless scaling** — the same basic training configuration can be adapted from
development to production:

| Environment | GPUs | Workers |
|---|---|---|
| Development | 1 | 1 |
| Staging | 2 | 2 |
| Production | 8 | 8 |

The infrastructure can scale without completely redesigning the training workload.

**6.4 Fault tolerance** — large distributed training jobs can run for hours or days, and
infrastructure failures can happen. Kubeflow training workflows can incorporate automatic
retries, checkpointing, and recovery mechanisms:

```
Training → Checkpoint → Training → Worker failure → Restart → Load checkpoint → Continue training
```

This prevents having to restart a long training run from the beginning.

**6.5 Multi-cloud compatibility** — the same Kubernetes/Kubeflow concepts can be used across
on-premises infrastructure, Google Cloud, AWS, Azure, and hybrid environments. The exact
underlying infrastructure differs, but Kubernetes provides a common orchestration layer.

### 7. Hyperparameter tuning with Katib

**Katib** is Kubeflow's component for **automated hyperparameter optimization**. Suppose your
model has `learning_rate`, `batch_size`, `dropout`, `weight_decay` — you could manually try
Experiment 1 (`learning_rate = 0.001`), Experiment 2 (`learning_rate = 0.0005`), Experiment 3
(`learning_rate = 0.0001`)... but this becomes extremely expensive and time-consuming. Katib
automates this process.

**Katib workflow**:

```
            Katib
               │
       Hyperparameter Search
               │
       ┌───────┼────────┐
       ↓       ↓        ↓
   Experiment Experiment Experiment
       1          2         3
       ↓          ↓         ↓
    Training   Training  Training
       ↓          ↓         ↓
     Score      Score     Score
       └──────────┼─────────┘
                  ↓
           Better parameters
```

### 8. Katib search strategies

- **Grid Search** — systematically tries combinations (e.g. `learning_rate: [0.1, 0.01,
  0.001]` × `batch_size: [16, 32, 64]`). **Advantage**: exhaustive. **Disadvantage**: can
  require many experiments.
- **Random Search** — randomly samples configurations from the search space
  (`Search space → random configuration → training → result → another random configuration`).
  Can explore a large space more efficiently than exhaustive grid search in some situations.
- **Bayesian Optimization** — uses information from previous experiments to intelligently
  select promising configurations (`previous experiments → learn which regions look promising
  → choose next configuration → training → update knowledge → choose next configuration`). The
  goal is to find good hyperparameters with fewer experiments.

**Katib + Training Operators**: Katib creates experiments → PyTorchJob / TFJob → GPU training
→ metric → Katib evaluates result → next experiment. This connection between the components is
important — Katib doesn't train models itself, it drives the training operators.

### 9. Kubeflow Pipelines for training

Training is usually not the only step in an ML workflow. A real ML workflow might look like:
Data → Data preprocessing → Training → Evaluation → Model registration → Deployment →
Monitoring. Kubeflow Pipelines allows these steps to be represented as an orchestrated
workflow.

### 10. Typical Kubeflow training pipeline — four stages

- **Stage 1 — Data Ingestion**: extract and transform data from various sources
  (`Data Sources → Extract → Transform → Training Dataset`).
- **Stage 2 — Model Training**: run the training workload
  (`Dataset → PyTorchJob → Distributed Training → Trained Model`).
- **Stage 3 — Evaluation**: evaluate the trained model
  (`Model → Evaluation dataset → Metrics → Accuracy / F1 / Loss / etc.`).
- **Stage 4 — Deployment**: deploy the resulting model for inference, e.g. via **KFServing** or
  **TF Serving** (`Training → Evaluation → Approved Model → Model Serving → Inference
  Endpoint`).

### 11. Pipeline as a DAG

A Kubeflow Pipeline can be visualized as a **DAG — Directed Acyclic Graph**:

```
            Data
              │
              ↓
        Preprocessing
              │
              ↓
          Training
              │
         ┌────┴────┐
         ↓         ↓
    Evaluation   Metrics
         │
         ↓
      Deployment
```

Each step is a component in the pipeline. This makes the ML workflow reproducible,
version-controlled, parameterized, and automatable.

### 12. What Kubeflow Pipelines enable

- **End-to-end experiment tracking** — track experiments across the complete workflow.
- **Automatic metadata capture** — capture information about pipeline runs and their outputs.
- **Visualized DAG execution** — see the workflow and its execution graph visually.
- **Parameterized runs** — change parameters between runs, useful for experiments, A/B
  testing, and different model configurations.
- **Scheduled retraining** — e.g. every Sunday: fetch latest data → train → evaluate → deploy
  if better.
- **CI/CD integration for ML** — connect ML workflows with software engineering practices.

### 13. Challenges of scaling with Kubeflow

**1. Steeper learning curve** — Kubeflow is significantly more complex than running basic
Kubernetes workloads. You need to understand concepts from Kubernetes + Containers +
Distributed systems + Machine learning + Kubeflow itself.

**2. Complex multi-component architecture** — there are multiple components that need to work
together (Kubernetes → Training Operator, Pipelines, Katib, Serving, Monitoring). Proper
configuration and integration can require significant operational knowledge.

**3. Distributed training debugging** — distributed training introduces additional failure
modes across worker-to-worker communication. Problems can involve networking, worker failures,
GPU availability, synchronization, distributed process startup, and resource allocation —
debugging therefore requires specialized knowledge.

### 14. Resource considerations

**GPU-aware cluster** — you need a Kubernetes cluster configured correctly for GPU workloads,
generally involving appropriate GPU device-plugin/runtime support: `GPU Hardware → GPU driver →
Container runtime / device plugin → Kubernetes → Kubeflow training workload`. (See
[GPU Scheduling in Kubernetes](#gpu-scheduling-in-kubernetes) above for the device-plugin
mechanics this depends on — this section and that one describe the same underlying
infrastructure from two different angles: general-purpose GPU scheduling vs. Kubeflow's
training-specific use of it.)

**Infrastructure cost** — Kubeflow can be resource-intensive. For a small team running a few
experiments, the operational complexity may not always justify the platform.

**Network bandwidth** — distributed training involves communication between workers
(`GPU 1 ←→ GPU 2`, `GPU 3 ←→ GPU 4`, all interconnected). Large models and distributed
training can generate substantial network traffic.

> **Network bandwidth can become a bottleneck in large-scale distributed training.**

### 15. Best practices for Kubeflow training

**15.1 Use custom training operators** — prefer PyTorchJob/TFJob over manually managing raw
Pods for distributed ML training, because operators provide specialized lifecycle management
and resilience.

**15.2 Implement checkpointing** — store checkpoints on persistent storage
(`Training → Checkpoint → Persistent Volume / Storage → Training continues`). If the job
fails: `Failure → Restart → Load checkpoint → Continue training`. Particularly important for
long-running GPU jobs.

**15.3 Structured hyperparameter optimization** — instead of manually trying
`LR = 0.1, 0.01, 0.001...`, use **Katib** to systematically explore the hyperparameter space.

**15.4 Monitor resource utilization** — use Prometheus + Grafana to monitor GPU utilization,
GPU memory, CPU utilization, memory, training progress, and job health. For distributed
training, GPU utilization is particularly important — if your GPUs are sitting at 10%
utilization while you're paying for expensive GPU infrastructure, something may be wrong.

**15.5 GitOps for ML** — store Kubeflow manifests in Git (`pytorchjob.yaml`, `pipeline.yaml`,
`katib.yaml`, `configs/`). This provides versioning, reproducibility, collaboration, and
auditability, and makes infrastructure changes reviewable.

### 16. Putting everything together

This is probably the most important architecture to understand from the entire Kubeflow
section:

```
                       Kubeflow
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ↓                ↓                ↓
    Training            Pipelines          Katib
    Operators              │                │
          │                │                │
     ┌────┴────┐      Orchestrates     Hyperparameter
     │         │           │             Optimization
 PyTorchJob  TFJob         │                │
     │         │           │                │
     └────┬────┘           │                │
          │                │                │
          ↓                ↓                ↓
       Training ───────→ Evaluation ←── Experiments
          │                │
          └────────────────┘
                   ↓
                 Model
                   ↓
                Serving
                   ↓
             Inference API
```

### 17. Kubeflow vs Kubernetes

This distinction is important:

- **Kubernetes provides the infrastructure orchestration layer** — it knows about Pods, Nodes,
  Services, Volumes, Scheduling, Resources, Networking.
- **Kubeflow adds ML-specific abstractions** — it knows about concepts such as training jobs,
  distributed ML, ML pipelines, hyperparameter optimization, model workflows.

So: Kubernetes = general container orchestration. Kubeflow = an ML platform built around
Kubernetes.

### 18. Key takeaways — Kubeflow

1. **Kubernetes-native ML** — Kubeflow provides a purpose-built framework for running ML
   workloads on Kubernetes.
2. **Simplified distributed training** — Training Operators abstract away much of the
   complexity involved in scaling training across multiple GPUs and nodes
   (`PyTorchJob → Master + Workers → Distributed PyTorch training`).
3. **Automated optimization** — Katib enables systematic exploration of hyperparameter spaces
   (`Hyperparameters → Katib → Many experiments → Compare metrics → Better configuration`).
4. **End-to-end orchestration** — Kubeflow Pipelines connect different stages of the ML
   lifecycle (`Data → Training → Evaluation → Deployment → Monitoring → Retraining`).

### 19. Final mental model

If you are coming from a **DevOps/Kubernetes background**, this is perhaps the simplest way
to remember the whole thing:

```
                KUBERNETES
                      │
            Infrastructure Layer
                      │
        ┌─────────────┴─────────────┐
        │                           │
       Pods                       GPUs
        │                           │
        └─────────────┬─────────────┘
                      │
                   KUBEFLOW
                      │
       ┌──────────────┼──────────────┐
       │              │              │
       ↓              ↓              ↓
   Training       Pipelines        Katib
   Operators         │          Hyperparameter
       │             │           Optimization
       ↓             ↓
 PyTorchJob      ML Workflow
 TFJob               │
       │             │
       └──────┬──────┘
              ↓
         ML Training
              ↓
           Model
              ↓
          Serving
```

> **In one sentence**: Kubernetes gives you the infrastructure and scheduling; Kubeflow adds
> the ML-specific machinery needed to train, optimize, orchestrate, and eventually serve
> models at scale.

---

## Kubernetes Security Best Practices for AI Workloads

> A comprehensive guide for DevOps/SREs and ML engineers to secure critical AI infrastructure.

### 1. Why security in Kubernetes matters for AI workloads

Kubernetes security is important for any production workload, but **AI workloads introduce
additional value and attack surfaces**. An AI platform may contain models, data, and GPUs —
which respectively represent intellectual property, sensitive information, and expensive
compute. An attacker gaining access to the cluster may potentially access not just
applications, but also model weights, training datasets, credentials, inference endpoints,
GPU resources, and internal services.

**1.1 High-value targets** — Kubernetes clusters running AI workloads contain valuable
intellectual property, sensitive data, and expensive computational resources, making them
attractive targets: `Attacker → Kubernetes cluster → Model weights + Training data +
Credentials + GPU resources`.

**1.2 Complex attack surface** — multiple potential attack vectors exist: the API Server
(authentication/authorization), Containers (vulnerabilities/escapes), Secrets
(credentials/tokens), Network (lateral movement). An attacker doesn't necessarily need to
directly attack the model — they may instead compromise a chain like
`Pod → Service Account → API → Secret → Model/Data`.

**1.3 Costly consequences** — a successful breach can result in:

- **Model theft** — attackers obtain proprietary model weights
  (`Private Model → Attacker → Model copied`).
- **Training data exfiltration** — sensitive datasets are extracted.
- **Inference manipulation** — an attacker changes or interferes with inference behavior.
- **Service disruption** — AI inference or training infrastructure becomes unavailable.
- **Resource theft** — attackers can potentially use expensive GPU infrastructure for
  unauthorized workloads.

The financial impact of a major AI infrastructure breach can therefore be substantial.

### 2. Security is a shared responsibility

Security cannot be handled by only one team:

```
          Security
              │
       ┌──────┼──────┐
       ↓      ↓      ↓
    DevOps    SRE     ML
       │      │      │
       └──────┼──────┘
              ↓
        Secure AI Platform
```

Different teams may own different layers:

| Team | Typical responsibility |
|---|---|
| DevOps/SRE | Cluster, networking, infrastructure |
| Security | Policies, threat detection, compliance |
| ML engineers | Models, training code, datasets, application behavior |

> **Security is a shared responsibility across infrastructure, application, and ML teams.**

### 3. Common Kubernetes security vulnerabilities

**3.1 Exposed API servers** — the Kubernetes API server is extremely powerful. If exposed
without proper authentication and authorization (`Attacker → Kubernetes API → Pods / Secrets /
Resources`), this can potentially give an attacker significant control over the cluster.

**3.2 Container escape** — a vulnerable or improperly configured container may allow an
attacker to escape the container and interact with the underlying host
(`Container → Container Escape → Kubernetes Node → Other workloads / infrastructure`). This is
particularly serious when the node contains expensive GPU resources or multiple sensitive
workloads.

**3.3 Plaintext secrets** — a dangerous pattern is putting credentials directly into YAML,
e.g. `password: my-secret-password`. If that YAML is committed to Git
(`Git repository → Credential exposed → Attacker gains access`), the credential is now
compromised. Secrets should therefore be managed separately and securely.

### 4. Other operational security gaps

- **Privilege escalation** — a compromised process attempts to gain more permissions than it
  should have (`Low privilege → Privilege escalation → Higher privilege`).
- **Unvetted container images** — an image may contain vulnerable packages, outdated
  dependencies, malicious code, or unnecessary tools. Blindly deploying arbitrary images is
  risky.
- **Misconfigured network policies** — if all Pods can freely communicate
  (`Pod A ←→ Pod B ←→ Pod C ←→ Pod D`), compromising one Pod may allow an attacker to move
  laterally. A better architecture only allows explicitly permitted paths
  (`Pod A → allowed → Pod B`, `Pod A → blocked → Pod C`).

### 5. Principle of Least Privilege (PoLP)

One of the most important security principles:

> **Give users, services, and workloads only the permissions they actually need — and nothing
> more.**

Different access levels each need only what their responsibilities require: Admins →
Operators → Developers → Services/Pods.

### 6. RBAC — Role-Based Access Control

Kubernetes provides **RBAC** to control what identities can do. For example, a Developer role
might be able to `get pods`, `list pods`, `watch pods` — but **not** `delete namespaces`,
`modify cluster-wide resources`, or `access unrelated secrets`.

**Key RBAC practices**:

- **Define granular roles** — instead of "give everything," define specific permissions such
  as `get`/`list`/`watch` for specific resources.
- **Avoid wildcards** — avoid overly broad permissions such as `verbs: ["*"]` or
  `resources: ["*"]`, which create excessive privileges.
- **Avoid unnecessary cluster-wide access** — prefer namespace-scoped access where possible,
  rather than access to the entire cluster.
- **Regularly audit RoleBindings** — remove unused accounts, unused permissions, old service
  accounts, and unnecessary role bindings.

**Why RBAC matters** — strong RBAC reduces attack surface + reduces blast radius + limits
lateral movement + creates team boundaries.

### 7. Secure Pod configurations for AI workloads

A Pod should not automatically run with maximum privileges. A simplified secure configuration:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-ml-inference
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
    readOnlyRootFilesystem: true
    allowPrivilegeEscalation: false
  containers:
    - name: inference-service
      image: ml-model:v1
      securityContext:
        capabilities:
          drop: ["ALL"]
```

What each setting means:

- **`runAsUser: 1000`** — the container runs as a non-root user (UID 1000, not `root`),
  reducing the consequences of a compromised application.
- **`runAsGroup: 3000`** — specifies the group under which the container processes run.
- **`fsGroup: 2000`** — controls group ownership/access behavior for supported mounted
  volumes.
- **`readOnlyRootFilesystem: true`** — prevents processes from modifying the container's root
  filesystem (`Attacker compromises application → Attempts to modify filesystem → Root
  filesystem is read-only → Attack becomes harder`). Particularly useful for model-serving
  containers, since attackers should not be able to easily modify inference logic or
  application files.
- **`allowPrivilegeEscalation: false`** — prevents processes from gaining additional
  privileges through supported escalation mechanisms.
- **`capabilities.drop: [ALL]`** — Linux capabilities provide subsets of traditionally
  powerful root privileges; if the application doesn't need them, remove them
  (`Container → Drop unnecessary capabilities → Smaller privilege surface`).

### 8. Pod Security Admission

Using **Pod Security Admission (PSA)** with the **restricted** profile establishes
standardized security requirements for Pods:

```
Developer creates Pod → Pod Security Admission → Does Pod meet security policy? → Allowed / Rejected
```

This is better than relying on every developer to manually remember every security setting.

### 9. Network security for AI clusters

Network security is especially important because AI platforms often contain many
interconnected components (`Training → Data pipeline → Storage → Model registry → Inference →
Monitoring`). If one component is compromised, unrestricted network access could allow an
attacker to move through the entire environment.

### 10. Default Deny NetworkPolicy

A strong starting point:

> **Deny everything by default, then explicitly allow required communication.**

```
                   Cluster
                       │
                 Default DENY
                       │
          ┌────────────┼────────────┐
          ↓            ↓            ↓
      Training      Inference      Data
          │            │            │
       Explicit     Explicit     Explicit
       allowed      allowed      allowed
       traffic      traffic      traffic
```

This limits lateral movement — if an inference Pod gets compromised, a NetworkPolicy means it
can only reach permitted destinations, rather than everything being reachable.

### 11. Workload segmentation

AI platforms can contain different workload categories: Training, Inference, Data pipelines,
Monitoring, Storage. Separate these into namespaces with strict boundaries — e.g. `training
namespace`, `inference namespace`, `data namespace` — then apply appropriate RBAC,
NetworkPolicies, Resource quotas, and Pod security policies/controls to each.

### 12. Encryption in transit

Communication between Pods should be protected where appropriate, one approach being
**mutual TLS (mTLS)**. Service-mesh technologies such as **Istio** and **Linkerd** can help
implement encrypted service-to-service communication.

**Why mTLS?** Normal communication is `Pod A ──── Pod B`, unauthenticated and unencrypted.
With mTLS, `Pod A → encrypted + authenticated → Pod B` — both sides can verify the identity of
the other.

### 13. Important AI consideration: network performance

Security controls shouldn't accidentally destroy training performance. Distributed AI training
can generate significant network traffic between GPUs (`GPU 1 ←→ GPU 2 ←→ GPU 3 ←→ GPU 4`).

> **Network policies and security mechanisms should be designed carefully so they maintain
> security boundaries without creating unacceptable performance bottlenecks.**

### 14. Secrets management for ML workflows

AI workloads often require many credentials — common examples include model registry
credentials, dataset API keys, GPU cloud-provider tokens, monitoring service-account
credentials, and inference endpoint credentials. These secrets should not be casually embedded
in application manifests.

### 15. External secret managers

Instead of relying exclusively on native Kubernetes Secrets, use external secret-management
systems such as **HashiCorp Vault** or **AWS Secrets Manager**
(`External Secret Manager → Application → Secret`).

> **Keep sensitive credentials outside ordinary application configuration and Git repositories
> whenever possible.**

### 16. Secret rotation

Credentials should not remain valid forever. Implement automatic rotation according to your
organization's security requirements — **30–90 days** is a commonly recommended schedule
(`Secret v1 → expires/rotates → Secret v2 → application continues`). Automatic rotation
reduces the window of opportunity if credentials are compromised.

### 17. Scan Git and CI/CD for secrets

A common accidental exposure path: `Developer → puts API key in YAML → git commit → Git
repository → credential exposed`. Therefore, secret scanning should be a step in the pipeline
itself: `Developer → Git → Secret scanning → CI/CD → Deployment`.

### 18. Container image security for AI models

AI workloads frequently use specialized container images, particularly for GPU workloads —
NVIDIA NGC containers, official PyTorch images, official TensorFlow images, and distroless
images where appropriate.

### 19. Use secure base images

Prefer a trusted source + minimal image + known dependencies, rather than arbitrary images
from unknown sources. For GPU workloads, NVIDIA NGC containers can provide appropriately
packaged GPU software stacks.

### 20. Why minimal images matter

Suppose your application only needs Python + PyTorch + CUDA libraries + your application code,
but your image also contains a compiler, an SSH server, shell utilities, debugging tools, and
unused libraries. Every additional component potentially increases the attack surface:
`Smaller image → Fewer components → Fewer potential vulnerabilities → Smaller attack surface`.

A typical **45% size/attack-surface reduction** is cited when using minimal base images (see
the honesty caveat on this figure under [§22](#22-important-security-statistics-from-the-material)
below).

### 21. Continuous vulnerability scanning

Don't scan images only once — a production image can become vulnerable later when a new CVE is
discovered. Recommended workflow:

```
Build image → Vulnerability scan → Deploy → Rescan regularly → New CVE? → Patch / Continue
```

Tools mentioned: **Trivy**, **Clair**. Recommended practice: scan during builds, block
deployments with critical CVEs, and rescan running containers daily.

### 22. Important security statistics from the material

- **87%** — the presentation states that 87% of AI breaches involve vulnerable container
  components that were unpatched or using outdated dependencies.
- **14 days** — the recommended maximum age for production AI container images before
  rebuilding.
- **45%** — the typical size reduction in attack surface when using minimal base images (cited
  above in §20).

> These figures should be treated as the source presentation's stated benchmarks rather than
> universal industry constants; actual risk varies by environment.

### 23. Monitoring & detection for AI workloads

Preventing attacks is only one part of security — you also need to detect suspicious behavior.
Think: **Prevent + Detect + Respond**.

### 24. API server audit logs

Kubernetes API activity should be audited, paying particular attention to privilege changes,
secret access, resource modifications, authentication/authorization events, and administrative
operations (`Kubernetes API → Audit Logs → Central logging / SIEM → Security analysis →
Alert`). Forward logs to **SIEM systems** for centralized analysis.

### 25. Runtime security

Tools such as **Falco** and **Sysdig** can detect suspicious runtime behavior — container
escape, privilege escalation, suspicious processes, unexpected system calls, unusual container
behavior. For an AI platform, suspicious behavior could potentially indicate attempts to
access model files, copy a model, and exfiltrate it.

### 26. Resource anomaly detection

GPU resources are expensive, so monitor unusual resource consumption. Normal: GPU utilization
follows the training schedule. Unexpected: a GPU suddenly runs at high utilization during
non-training hours — which could indicate cryptojacking, unauthorized training jobs, resource
abuse, or compromised workloads. Monitor GPU, CPU, memory, and network for abnormal patterns.

### 27. AI-specific detection

Traditional Kubernetes monitoring isn't always enough — also look for anomalies in AI
behavior. Normal inference has an expected request volume; a sudden anomaly (millions of
requests) could indicate a potential model extraction attempt. Monitor for unusual inference
patterns, high-volume requests, unexpected data transfers, and abnormal model access — these
could indicate attempts to steal models or data.

### 28. Multi-tenancy security for shared AI platforms

Imagine an organization has a shared AI Kubernetes cluster with multiple teams running
different workloads (Team A/Training, Team B/Training, Team C/Inference). The teams should not
automatically be able to access one another's workloads.

### 29. Multi-tenant isolation mechanisms

Several layers, together:

- **Namespace boundaries** — `team-a`, `team-b`, `team-c` namespaces.
- **Strict resource quotas** — prevent one tenant from consuming all available resources
  (e.g. Team A max GPU = 4, Team B max GPU = 8).
- **Pod Security Admission** — apply appropriate security profiles to tenant workloads.
- **Network segmentation** — prevent `Team A Pod ───→ Team B Pod` unless explicitly allowed.
- **Custom admission controllers** — enforce organizational policies before workloads are
  admitted into the cluster (`kubectl apply → Admission Controller → Policy check → Allowed /
  Rejected`).

### 30. Important risk: GPU multi-tenancy

GPU environments have an additional concern: **"noisy neighbor" attacks**. One tenant's heavy
workload can potentially degrade another tenant's normal workload's performance, even across
namespace isolation. There's also the possibility of **side-channel information leakage** in
multi-tenant GPU environments. GPU sharing therefore requires additional consideration beyond
ordinary namespace isolation.

### 31. Defense in depth

Perhaps the most important security principle overall:

> **Do not rely on one security mechanism.**

Instead, create multiple layers: Cluster Security + Network Security → Pod Security →
Container Security → Application → AI Model. If one layer fails, another layer should still
provide protection.

### 32. Shift left + monitor right

Another useful principle:

> **Secure workloads early in the development pipeline, and continue monitoring them after
> deployment.**

- **Shift left** — security checks happen before production: Code → Container build → Image
  scanning → Manifest validation → Secret scanning → Policy checks → Deployment.
- **Monitor right** — once deployed: Production → Runtime monitoring → Audit logs → Resource
  monitoring → Network monitoring → Security alerts.

Shift left **prevents** problems before deployment; monitor right **detects** problems after
deployment.

### 33. Complete security architecture

Putting everything together:

```
                        AI Kubernetes Platform
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ↓                         ↓                         ↓
     RBAC                  Network Security          Container Security
        │                         │                         │
 Least privilege          Default deny               Trusted images
 Granular roles            NetworkPolicies            Minimal images
 No wildcards             Segmentation                CVE scanning
        │                   mTLS where needed                 │
        └─────────────────────────┼─────────────────────────┘
                                  ↓
                           Pod Security
                                  │
                     ┌────────────┼────────────┐
                     ↓            ↓            ↓
                Non-root      Read-only     No privilege
                 user         filesystem     escalation
                     │
                     ↓
               AI Workloads
                     │
          ┌──────────┼──────────┐
          ↓          ↓          ↓
       Training   Inference    Data
          │          │          │
          └──────────┼──────────┘
                     ↓
                Monitoring
                     │
       ┌─────────────┼─────────────┐
       ↓             ↓             ↓
   Audit logs     Runtime       Resource
                  security      anomalies
       │             │             │
       └─────────────┼─────────────┘
                     ↓
                   SIEM
                     ↓
                 Detection
                     ↓
                  Response
```

### 34. Security layers to remember

For a DevOps/SRE engineer, the entire document reduces to these seven layers:

1. **Identity** — who can do what? → RBAC
2. **Pod** — what privileges does the workload have? → SecurityContext / PSA
3. **Network** — who can communicate with whom? → NetworkPolicy / mTLS
4. **Container** — what code/dependencies are running? → Trusted images / scanning
5. **Secrets** — where are credentials stored? → Vault / Secrets Manager
6. **Runtime** — what is actually happening? → Falco / audit logs / monitoring
7. **Multi-tenancy** — can tenants interfere with each other? → Namespaces / quotas / network
   isolation

### 35. Key takeaways — security

**1. Defense in depth** — layer security controls across Cluster → Network → Pod → Container →
Application. No single security mechanism is sufficient for AI workloads.

**2. Principle of Least Privilege** — strict RBAC, minimal service-account permissions, secure
Pod security contexts, non-root containers, disabled privilege escalation. The goal is to
minimize the impact of a compromise.

**3. Shift Left + Monitor Right** — secure workloads before deployment (image scanning, secret
scanning, policy validation, configuration checks), and monitor them after deployment (audit
logs, runtime security, GPU/CPU anomalies, network behavior, inference anomalies).

**4. Protect the AI assets** — ultimately, Kubernetes security isn't just about protecting
Kubernetes. You are protecting Models (intellectual property), Data (sensitive), and GPUs
(expensive resources). A compromise can therefore affect **confidentiality, integrity,
availability, and cost**.

### 36. Final mental model — security

If you're learning this from a **Kubernetes/DevOps → AI infrastructure** perspective:

> **Secure identity, secure workloads, secure networks, secure images, secure secrets, and
> continuously monitor what happens at runtime.**

```
                    Kubernetes AI Security
                              │
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
     WHO?                    WHAT?                 WHERE?
      RBAC                Pod/Container           Network
     Identity              Security             Security
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ↓
                         WHAT SECRET?
                              │
                       Secret Management
                              │
                              ↓
                         IS IT SAFE?
                              │
                    Image / CVE Scanning
                              │
                              ↓
                     WHAT IS HAPPENING?
                              │
                  Runtime + Audit Monitoring
                              │
                              ↓
                         AI Platform
                              │
                    ┌─────────┼─────────┐
                    ↓         ↓         ↓
                 Training  Inference   Data
                    │         │         │
                    └─────────┼─────────┘
                              ↓
                     Protected AI System
```

**The core idea**: Kubernetes provides the platform, but for AI workloads you need to
deliberately secure access, Pods, containers, networks, secrets, GPUs, models, data, and
runtime behavior.

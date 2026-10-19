# Kubernetes Architecture & Extension Concepts — Discussion Summary

## 1. Big Picture

A useful way to think about Kubernetes is in three layers:

- **Control plane** — makes decisions and maintains the desired state of the cluster.
- **Worker nodes (node side)** — provide compute capacity and run workloads.
- **Cluster-level extensions/add-ons** — additional components that extend Kubernetes capabilities without modifying Kubernetes core.

> Important: Deployments, StatefulSets, Services, HPAs, and KEDA ScaledObjects are **Kubernetes API resources**, not components that live "on the worker node." They are represented through the Kubernetes API and stored in `etcd`; controllers act on them.

---

# 2. Control Plane

The control plane is responsible for managing the cluster.

### Main components

| Component | What it does |
|---|---|
| **kube-apiserver** | Entry point to the Kubernetes API. kubectl, controllers, operators, and other clients communicate through it. |
| **etcd** | Distributed key-value store containing Kubernetes cluster state and configuration. |
| **kube-scheduler** | Decides which worker node should run a newly created Pod. |
| **kube-controller-manager** | Runs built-in Kubernetes controllers that continuously reconcile desired state with actual state. |
| **cloud-controller-manager** | Integrates Kubernetes with a cloud provider when applicable, such as AWS or Azure. |

### Controller

A **controller** is a control loop.

Conceptually:

```text
Desired state
     ↓
Kubernetes API
     ↓
Controller observes state
     ↓
Controller takes action
     ↓
Actual state moves toward desired state
```

For example, if a Deployment says:

```text
replicas: 5
```

but only 4 Pods are running, the Deployment/ReplicaSet controller works to create the missing Pod.

---

# 3. Worker Node / Node Side

Worker nodes provide the actual compute capacity where Pods run.

### Main node components

| Component | What it does |
|---|---|
| **kubelet** | Agent running on each node. Ensures the Pods assigned to the node are running. |
| **Container runtime** | Runs containers. Commonly containerd. |
| **kube-proxy** | Implements Kubernetes Service networking behavior on nodes (implementation can vary depending on networking setup). |
| **Pods** | The smallest deployable workload unit in Kubernetes. Containers run inside Pods. |

Conceptually:

```text
                 Kubernetes Cluster
                        |
          +-------------+-------------+
          |                           |
     Control Plane               Worker Nodes
          |                           |
   API Server / etcd          kubelet / runtime
   Scheduler                  kube-proxy
   Controllers                     |
          |                       Pods
          +-------------------------+
```

---

# 4. Kubernetes Resources vs Components

This distinction is important.

Things such as:

- Pod
- Deployment
- StatefulSet
- Service
- ConfigMap
- Secret
- HorizontalPodAutoscaler (HPA)
- KEDA ScaledObject

are generally **API resources/objects**.

They are not equivalent to control-plane processes such as the API server or scheduler.

For example:

```text
Deployment
    ↓
ReplicaSet
    ↓
Pods
    ↓
Scheduled onto worker nodes
```

The Deployment object expresses desired state; controllers make that desired state happen.

---

# 5. What Is a Plugin?

A **plugin** is an extension that integrates with Kubernetes through a defined extension interface.

The word "plugin" is more specific than simply saying "extra software."

Three examples:

## CNI — Container Network Interface

CNI provides the networking interface used to configure networking for containers/Pods.

Examples of CNI implementations:

- **Calico**
- **Cilium**
- **Flannel**

For example:

```text
Kubernetes
    ↓
CNI interface
    ↓
Calico / Cilium / Flannel
    ↓
Pod networking
```

## CSI — Container Storage Interface

CSI provides the standard interface for integrating storage systems with Kubernetes.

Examples:

- AWS EBS CSI Driver
- Azure Disk CSI Driver
- Azure Files CSI Driver

Conceptually:

```text
Kubernetes
    ↓
CSI interface
    ↓
CSI driver
    ↓
Cloud/storage system
```

## Device Plugin API — e.g. NVIDIA device plugin

Not networking, not storage — kubelet-facing hardware discovery (GPUs, etc.). No CRD involved.

- Runs as a DaemonSet, one Pod per GPU node
- Registers with the **local kubelet** over a Unix socket (not via kube-apiserver/etcd)
- Discovers GPUs, kubelet advertises them as an extended resource on the Node: `status.allocatable["nvidia.com/gpu"]`
- Pod requests `resources.limits: {nvidia.com/gpu: 1}` → scheduler treats it like any countable resource
- kubelet calls the plugin's `Allocate()` to get the device paths (`/dev/nvidia0`) to mount into the container

```text
Kubernetes
    ↓
Device Plugin API (kubelet-local, not apiserver)
    ↓
NVIDIA / AMD / SR-IOV device plugin
    ↓
GPU (or other hardware) visible to a Pod
```

Note: the **NVIDIA GPU Operator** (the thing people actually install) *is* a CRD/Operator (`ClusterPolicy` CRD, see section 11) that installs and manages the raw device plugin above as one of its pieces — an Operator managing a Plugin, not either replacing the other.

### Key point

CNI, CSI, and Device Plugin are **plugin interfaces/extension mechanisms**. The individual implementations (such as Cilium, an EBS CSI driver, or the NVIDIA device plugin) plug into those interfaces.

---

# 6. What Is an Add-on?

An **add-on** is a broader term.

It generally means **additional software installed into a Kubernetes cluster to provide functionality that is not part of the minimal Kubernetes core installation**.

Examples include:

- **KEDA** — event-driven autoscaling
- **cert-manager** — automates TLS certificate management
- **Metrics Server** — provides resource metrics used by mechanisms such as HPA
- **Ingress controllers** — provide HTTP/HTTPS ingress functionality
- **Prometheus** — monitoring/metrics ecosystem
- **CoreDNS** — DNS service commonly deployed as part of a Kubernetes cluster

An add-on does **not necessarily mean a plugin**.

A useful mental model:

```text
Kubernetes core
      +
Additional components
      =
Kubernetes cluster with add-ons
```

---

# 7. Plugin vs Add-on

They are related, but they are **not interchangeable terms**.

| Concept | Meaning | Examples |
|---|---|---|
| **Plugin** | Software integrating through a defined extension interface | CNI, CSI |
| **Add-on** | Broader term for additional cluster functionality | KEDA, cert-manager, Metrics Server |
| **Controller** | A reconciliation loop that watches state and takes action | Deployment controller, KEDA controller |
| **Operator** | Usually a controller plus domain-specific operational knowledge | Prometheus Operator, database operators |
| **CRD** | Mechanism for defining a new Kubernetes API resource type | KEDA ScaledObject, cert-manager Certificate |

An add-on can contain one or more controllers, CRDs, webhooks, APIs, or other components.

---

# 8. What Is a CRD?

**CRD = CustomResourceDefinition**

A CRD allows you to extend the Kubernetes API with a **new resource type**.

Kubernetes already has resources such as:

```text
Pod
Deployment
Service
ConfigMap
Secret
```

A CRD allows an extension to introduce something new, for example:

```text
ScaledObject
Certificate
Issuer
ServiceMonitor
```

The CRD defines the structure/schema of the new resource.

Then a controller watches instances of that resource and performs actions.

---

# 9. CRD + Controller

This is one of the most important relationships to understand.

For example, KEDA can define a resource such as:

```text
ScaledObject
```

You might create:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: my-app
spec:
  scaleTargetRef:
    name: my-app
```

The flow is conceptually:

```text
User creates ScaledObject
          ↓
     kube-apiserver
          ↓
       etcd stores it
          ↓
     KEDA controller
          ↓
     Watches ScaledObject
          ↓
  Gets external event/metric
          ↓
     Influences scaling
          ↓
        HPA / Pods
```

So:

**CRD = defines the new type**

**Custom Resource = an instance of that type**

**Controller = watches it and makes it actually do something**

---

# 10. What Is an Operator?

An **Operator** is essentially the Kubernetes controller pattern applied to managing a particular application/system, often using CRDs.

A simplified model:

```text
CRD
 ↓
Custom Resource
 ↓
Operator/Controller
 ↓
Manage application/system
```

For example, an operator might allow you to declare:

```yaml
kind: MyDatabase
spec:
  replicas: 3
```

The operator could then create and manage:

- StatefulSets
- Services
- ConfigMaps
- Secrets
- PersistentVolumes/PVCs
- Backups
- Failover configuration

The operator continuously reconciles the system.

### Important

Not every controller is necessarily called an Operator.

"Controller" is the broader Kubernetes concept.

"Operator" usually means a controller that contains operational knowledge for managing a particular application or system.

### How Operators get developed

- Built with a framework, not from scratch: **Operator SDK**, **Kubebuilder**, or `client-go`/`controller-runtime` directly (Go-based; `controller-runtime` is the shared library underneath all of these)
- Scaffolding generates two things: the CRD (from a Go struct → generated CRD YAML) + a `Reconcile()` function (the controller loop)
- `Reconcile()` = read the CR's desired spec → compare to current cluster state → create/update/delete objects to match (same loop shape as section 2's controller diagram)
- Packaged as a container image, deployed like any other workload (Helm chart is the common distribution method)

### Where an Operator resides / runs

- A normal **Pod**, usually via a **Deployment**, running *inside* the cluster it manages
- Talks to **kube-apiserver**, same as kubectl — watches Custom Resources through the API server/etcd
- Needs RBAC (ServiceAccount + Role/ClusterRole) to read/write whatever it manages
- Contrast with the Device Plugin (section 5): Operator = apiserver-facing, cluster-wide; Device Plugin = kubelet-local, per-node, no apiserver round-trip for its core protocol

```text
Operator            → talks to → kube-apiserver/etcd  (cluster-wide)
Device Plugin (GPU)  → talks to → local kubelet only  (per-node)
```

---

# 11. Popular Tools Built Using Kubernetes CRDs

CRD + controller/operator (sections 8-10) isn't just a KEDA/cert-manager pattern — it's how most of the Kubernetes ecosystem extends the platform. Instead of Kubernetes core growing a built-in feature for every use case, the project exposes CRDs as the extension point, and each of these tools ships its own CRD(s) plus a controller that watches them.

## GitOps / continuous delivery

| Tool | CRD(s) | What the controller manages |
|---|---|---|
| **Argo CD** | `Application`, `AppProject` | Syncs a cluster's live state to match a Git repo's declared manifests |
| **Flux CD** | `GitRepository`, `Kustomization`, `HelmRelease` | Same GitOps goal as Argo CD, via a different set of CRDs/controllers |
| **Argo Rollouts** | `Rollout`, `AnalysisTemplate` | Progressive delivery — canary/blue-green rollout with automated analysis instead of a plain Deployment rollout |

## Service mesh

| Tool | CRD(s) | What the controller manages |
|---|---|---|
| **Istio** | `VirtualService`, `DestinationRule`, `Gateway`, `PeerAuthentication` | Traffic routing, mTLS, and traffic policy between services |
| **Linkerd** | `ServiceProfile`, `AuthorizationPolicy` | Lighter-weight mesh — retries/timeouts and authorization per service |

## Certificates, secrets, policy

| Tool | CRD(s) | What the controller manages |
|---|---|---|
| **cert-manager** | `Certificate`, `Issuer`, `ClusterIssuer` | Requests/renews TLS certs (e.g. via Let's Encrypt) and stores them as Secrets |
| **External Secrets Operator** | `ExternalSecret`, `SecretStore` | Syncs secrets from an external vault (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault) into native K8s Secrets |
| **OPA Gatekeeper** | `ConstraintTemplate`, `Constraint` | Admission-time policy enforcement ("no Pod without resource limits", etc.) |
| **Kyverno** | `Policy`, `ClusterPolicy` | Same policy-enforcement goal as Gatekeeper, using plain YAML instead of Rego |

## Observability

| Tool | CRD(s) | What the controller manages |
|---|---|---|
| **Prometheus Operator** (kube-prometheus-stack) | `ServiceMonitor`, `PodMonitor`, `PrometheusRule`, `Alertmanager` | Declares what to scrape and what to alert on, instead of hand-editing `prometheus.yml` |

## Databases / stateful systems (Operator pattern)

| Tool | CRD(s) | What the controller manages |
|---|---|---|
| **Strimzi** | `Kafka`, `KafkaTopic`, `KafkaUser` | Runs and manages a Kafka cluster on Kubernetes |
| **CloudNativePG** / Zalando Postgres Operator | `Cluster` / `postgresql` | Runs Postgres with replication, failover, backups |
| **MongoDB Community Operator** | `MongoDBCommunity` | Runs a MongoDB replica set |
| **Elastic Cloud on Kubernetes (ECK)** | `Elasticsearch`, `Kibana` | Runs an Elastic stack |

## Backup/DR and infra-as-CRDs

| Tool | CRD(s) | What the controller manages |
|---|---|---|
| **Velero** | `Backup`, `Restore`, `Schedule` | Backs up/restores cluster resources and volumes |
| **Crossplane** | Composite Resource Definitions (XRDs) + provider-specific managed resources (e.g. `RDSInstance`, `Bucket`) | Provisions real *cloud* infrastructure (an actual AWS RDS instance, an Azure Storage Account) by applying a Kubernetes manifest — the CRD instance IS the cloud resource's desired state |

## Networking (beyond the CNI interface itself)

| Tool | CRD(s) | What the controller manages |
|---|---|---|
| **Traefik** | `IngressRoute` | Ingress routing with more expressiveness than the core `Ingress` resource |
| **Cilium** | `CiliumNetworkPolicy` | eBPF-based network policy — Cilium is a CNI plugin (section 5) that also ships CRDs on top |

## ML / AI platform (Kubeflow ecosystem)

Directly relevant to ML platform/infra work — these are the CRDs behind `platform-lab/k8s/k8s_explorer`'s Kubeflow/KServe notes.

| Tool | CRD(s) | What the controller manages |
|---|---|---|
| **Kubeflow Training Operator** | `PyTorchJob`, `TFJob` | Runs a distributed training job (multiple worker/PS Pods coordinated as one job) |
| **Kubeflow Notebooks** | `Notebook` | Runs a Jupyter server as a managed Kubernetes workload |
| **Katib** | `Experiment` | Hyperparameter tuning as a Kubernetes-native job |
| **KServe** | `InferenceService` | Deploys a trained model behind an autoscaling inference endpoint |
| **NVIDIA GPU Operator** | `ClusterPolicy` | Installs/manages the whole GPU stack on a node (driver, container-toolkit, DCGM metrics, MIG manager) — including the plain (non-CRD) NVIDIA device plugin, see section 5 |

### Why this pattern is everywhere

```text
Instead of:
  "Kubernetes core adds a Kafka feature, a Postgres feature, a training-job feature..."

The ecosystem does:
  New CRD (new resource type)
       +
  A controller/operator that understands it
       =
  Kubernetes API extended for that domain, without touching Kubernetes core
```

That's the same CRD + controller relationship from sections 8-10 — KEDA (next section) is simply one specific, very common instance of it.

---

# 12. KEDA — Where Does It Fit?

**KEDA = Kubernetes Event-Driven Autoscaling**

KEDA is an **add-on** that uses the Kubernetes controller/operator pattern.

It also introduces Kubernetes API resources through **CRDs**, such as `ScaledObject`.

KEDA can scale workloads based on external event sources such as:

- Azure Service Bus
- Kafka
- RabbitMQ
- AWS SQS
- Prometheus metrics
- Other supported scalers

A simplified architecture:

```text
External event source
        |
        | queue length / events / metrics
        ↓
       KEDA
   (controller)
        |
        ↓
      HPA / scaling
        |
        ↓
      Deployment
        |
        ↓
       Pods
```

So don't think of KEDA as changing Kubernetes core code.

Instead:

```text
Kubernetes
    +
KEDA add-on
    +
KEDA CRDs
    +
KEDA controller
```

---

# 13. HPA vs KEDA

### HPA

**Horizontal Pod Autoscaler** changes the number of Pod replicas based on metrics.

For example:

```text
CPU > target
    ↓
HPA
    ↓
Increase replicas
```

### KEDA

KEDA enables event-driven/external-metric-based autoscaling.

For example:

```text
Azure Service Bus queue
        ↓
    Queue has 500 messages
        ↓
       KEDA
        ↓
       HPA
        ↓
Increase Pod replicas
```

KEDA can therefore be thought of as extending Kubernetes autoscaling with event/external-system awareness.

---

# 14. Pod Scaling vs Node Scaling

This distinction is extremely important.

## Pod scaling

Usually handled by:

- HPA
- KEDA
- other workload autoscaling mechanisms

Example:

```text
3 Pods
  ↓
traffic increases
  ↓
HPA/KEDA
  ↓
8 Pods
```

But those additional Pods need somewhere to run.

---

# 15. Node Scaling

Node scaling means increasing or decreasing the number of worker nodes.

Common mechanisms include:

### Cluster Autoscaler

Cluster Autoscaler adjusts node groups/node pools when Pods cannot be scheduled because there is insufficient capacity.

### Karpenter

Karpenter is another node provisioning/autoscaling solution, especially common in AWS environments.

It can provision nodes based on the resource requirements and scheduling constraints of pending Pods rather than simply scaling a predefined node group.

---

# 16. Example: Why Karpenter/Cluster Autoscaler Is Needed

Suppose:

```text
Node 1
Capacity = 4 Pods
Running = 4 Pods
```

Now your Deployment increases from:

```text
4 Pods → 8 Pods
```

The scheduler attempts to place the additional Pods.

But there is no available capacity.

Therefore:

```text
Extra Pods
    ↓
Pending
    ↓
Scheduler cannot place them
    ↓
Cluster Autoscaler / Karpenter
    ↓
Provision/add node
    ↓
New node joins cluster
    ↓
Scheduler places pending Pods
```

This is the key relationship:

```text
HPA/KEDA
   ↓
More Pods
   ↓
Scheduler
   ↓
Pods Pending if capacity is insufficient
   ↓
Cluster Autoscaler / Karpenter
   ↓
More Nodes
   ↓
Scheduler
   ↓
Pods get scheduled
```

---

# 17. EKS / AKS Perspective

Cloud Kubernetes services such as:

- Amazon EKS
- Azure AKS

do support node scaling.

The cloud provider supplies the underlying infrastructure, while Kubernetes/cloud integrations participate in managing the cluster.

For EKS, common node-scaling/provisioning approaches include:

```text
Cluster Autoscaler
Karpenter
Managed Node Groups
```

For AKS, a common approach is:

```text
Cluster Autoscaler
Node pools
```

The exact implementation depends on the cluster configuration.

---

# 18. Final Mental Model

The easiest way to remember everything is:

```text
                    KUBERNETES CLUSTER
                           |
          +----------------+----------------+
          |                                 |
     CONTROL PLANE                     WORKER NODES
          |                                 |
     API Server                         kubelet
     etcd                               runtime
     Scheduler                          kube-proxy*
     Controllers                            |
          |                               Pods
          |
          +----------------------+
                                 |
                       Kubernetes API Resources
                                 |
            +--------------------+--------------------+
            |                    |                    |
       Deployment             Service               HPA
            |
           Pods

                EXTENSIONS / ADD-ONS
                        |
          +-------------+-------------+
          |             |             |
        KEDA       cert-manager    Metrics Server
          |
        CRDs
          |
    ScaledObject
          |
    KEDA Controller
```

`*` kube-proxy is common but can be replaced/implemented differently depending on the networking architecture.

---

# 19. Interview-Friendly Definitions

### Controller
A Kubernetes controller is a reconciliation loop that watches the Kubernetes API and continuously works to make the actual state match the desired state.

### Plugin
A plugin is an extension that integrates through a defined interface, such as CNI for networking or CSI for storage.

### Add-on
An add-on is additional software installed into a Kubernetes cluster to provide functionality beyond the minimal Kubernetes core.

### CRD
A CustomResourceDefinition extends the Kubernetes API by defining a new resource type.

### Custom Resource
A Custom Resource is an actual instance of a resource type defined by a CRD.

### Operator
An Operator is generally a controller that uses Kubernetes APIs, often CRDs, to automate the management of a particular application or system.

### KEDA
KEDA is a Kubernetes add-on that uses controllers and CRDs to enable event-driven autoscaling based on external metrics/events.

### Cluster Autoscaler
Cluster Autoscaler adjusts node capacity when Pods cannot be scheduled because the cluster lacks sufficient node capacity.

### Karpenter
Karpenter is a node provisioning/autoscaling solution that can dynamically provision suitable nodes for pending Pods.

---

# 20. One Sentence to Remember

> **Kubernetes provides the core control plane and node machinery; controllers reconcile resources, CRDs extend the Kubernetes API, operators use controllers to manage systems, plugins integrate through defined interfaces such as CNI/CSI, and add-ons provide additional cluster capabilities such as KEDA and cert-manager.**

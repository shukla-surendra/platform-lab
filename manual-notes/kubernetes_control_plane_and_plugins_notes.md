# Kubernetes Control Plane & Plugins — Conversation Notes

## 1. Kubernetes Control Plane

The Kubernetes control plane is responsible for managing cluster state, making scheduling decisions, and coordinating the cluster.

### Main Components

| Component | Basic role | Mental model |
|---|---|---|
| **kube-apiserver** | Entry point for the Kubernetes API. Authenticates, authorizes, validates, and processes API requests. | Front door / API interface |
| **etcd** | Distributed key-value database that stores Kubernetes cluster state. | Cluster database |
| **kube-scheduler** | Selects a suitable node for newly created Pods. | Placement engine |
| **kube-controller-manager** | Runs controllers that continuously reconcile actual state with desired state. | Reconciliation engine |
| **cloud-controller-manager** | Integrates Kubernetes with cloud-provider resources such as load balancers, routes, and nodes. | Cloud integration layer |

### kube-apiserver

Almost everything in Kubernetes goes through the API server.

Typical flow:

```text
kubectl create deployment nginx
            |
            v
     kube-apiserver
            |
            v
          etcd
```

Responsibilities include:

- Authentication
- Authorization
- Object validation
- Admission control
- Reading/writing cluster state
- Providing the API used by `kubectl`, controllers, scheduler, kubelets, and other clients

Important distinction:

> The API server does not normally run Pods itself. It provides the central API through which Kubernetes components coordinate and manipulate cluster state.

### etcd

`etcd` is the persistent data store for Kubernetes.

It stores information such as:

- Pods
- Deployments
- Services
- ConfigMaps
- Secrets
- Nodes
- RBAC objects
- CRDs
- Other Kubernetes API objects

Conceptually:

```text
             kube-apiserver
                    |
                    v
                  etcd
             +-------------+
             | Cluster     |
             | state       |
             +-------------+
```

Important distinction:

> etcd stores Kubernetes state; it does not execute workloads.

### kube-scheduler

When a Pod is created without a node assignment, the scheduler determines which node should run it.

It considers factors such as:

- CPU and memory availability
- Resource requests
- Node selectors
- Node affinity/anti-affinity
- Taints and tolerations
- Topology constraints
- Scheduling policies

Conceptually:

```text
Pod
 |
 v
Scheduler
 |
 +--> Node A  X
 +--> Node B  X
 +--> Node C  OK
             |
             v
       Pod assigned to Node C
```

Important distinction:

> The scheduler decides **where** a Pod should run; it does not actually start the container.

### kube-controller-manager

This runs multiple Kubernetes controllers, for example:

- Deployment controller
- ReplicaSet controller
- Node controller
- Job controller
- EndpointSlice controller
- Namespace controller
- ServiceAccount controller

The general controller pattern is:

```text
Desired state
     |
     v
  Controller
     |
     v
Observe current state
     |
     v
Take corrective action
     |
     v
Current state -> Desired state
```

Example:

If a ReplicaSet specifies:

```yaml
replicas: 5
```

but only 3 Pods exist, the controller works toward creating 2 more.

Important Kubernetes idea:

> Controllers continuously reconcile actual state toward desired state.

### cloud-controller-manager

This integrates Kubernetes with cloud-provider APIs.

It can be involved with resources such as:

- Cloud load balancers
- Cloud routes
- Cloud nodes

For example:

```yaml
kind: Service
spec:
  type: LoadBalancer
```

may result in cloud-provider integration creating a corresponding cloud load balancer.

---

## 2. Important Node Components

These are **not control-plane components**, but they are essential for understanding the full Kubernetes architecture.

### kubelet

The kubelet runs on nodes and makes sure Pods assigned to that node are actually running.

Conceptually:

```text
Control Plane
     |
     | Pod specification
     v
  kubelet
     |
     v
Container Runtime
     |
     v
Containers
```

### kube-proxy

`kube-proxy` is a node component involved in implementing Kubernetes Service networking.

Conceptually:

```text
Client
  |
  v
Service
  |
  v
Pod
```

It historically uses mechanisms such as iptables or IPVS depending on configuration.

### Container Runtime

Examples:

- containerd
- CRI-O

The kubelet communicates with the container runtime through the **CRI (Container Runtime Interface)**.

```text
kubelet
   |
   | CRI
   v
containerd / CRI-O
   |
   v
containers
```

---

# 3. Kubernetes Plugins

The word **plugin** is used broadly in Kubernetes. There is not one single plugin category.

A useful definition is:

> A Kubernetes plugin/extension adds or integrates a capability without requiring changes to Kubernetes core code.

Major extension/plugin areas include:

| Type | Extends | Examples | Purpose |
|---|---|---|---|
| **CNI plugin** | Networking | Cilium, Calico, Flannel | Gives Pods network connectivity |
| **CSI plugin** | Storage | AWS EBS CSI, Ceph CSI | Provides persistent storage integration |
| **Device plugin** | Hardware | NVIDIA device plugin | Exposes GPUs and other special hardware |
| **Admission webhook/plugin** | API request processing | Kyverno, OPA Gatekeeper | Validates or mutates Kubernetes objects |
| **Scheduler plugin** | Scheduling | Custom scheduler plugins | Adds custom scheduling logic |
| **kubectl plugin** | CLI | Community `kubectl-*` tools | Extends the kubectl command line |
| **Operator / Controller** | Kubernetes API/control behavior | Prometheus Operator, cert-manager, Strimzi | Automates domain-specific resources |

## CNI Plugins — Networking

**CNI = Container Network Interface**

When a Kubernetes Pod is created, it needs networking.

A CNI plugin can handle:

- Creating the Pod network interface
- Assigning a Pod IP
- Configuring networking/routing

Examples:

- Cilium
- Calico
- Flannel

Conceptually:

```text
kubelet
   |
   | create Pod
   v
Container Runtime
   |
   | CNI
   v
CNI Plugin
   |
   +--> Network interface
   +--> Pod IP
   +--> Network configuration
```

## CSI Plugins — Storage

**CSI = Container Storage Interface**

CSI allows Kubernetes to interact with storage systems.

Conceptually:

```text
Pod
 |
 v
PersistentVolumeClaim
 |
 v
PersistentVolume
 |
 v
CSI Driver
 |
 v
AWS EBS / Ceph / SAN / etc.
```

Examples:

- AWS EBS CSI Driver
- Azure Disk CSI Driver
- GCE Persistent Disk CSI Driver
- Ceph CSI

## Device Plugins — GPUs and Special Hardware

Device plugins allow Kubernetes to discover and expose special hardware resources.

For example, with an NVIDIA GPU, a Pod might request:

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
```

The NVIDIA device plugin makes the GPU resource available to Kubernetes.

Conceptually:

```text
Node
 ├── CPU
 ├── RAM
 └── GPU
       ^
       |
NVIDIA Device Plugin
       |
       v
 Kubernetes
       |
       v
 Pod requesting GPU
```

This is particularly important for AI/ML Kubernetes clusters.

## Admission Plugins / Webhooks

Admission happens around the API server request-processing path.

An admission mechanism can:

- Allow a request
- Reject a request
- Modify/mutate a request

Example policy:

> Every Pod must have resource limits.

Conceptually:

```text
kubectl
   |
   v
API Server
   |
   v
Authentication
   |
   v
Authorization
   |
   v
Admission
   |
   +----> Policy webhook/plugin
   |
   v
etcd
```

Popular policy systems include:

- Kyverno
- OPA Gatekeeper

## Scheduler Plugins

The Kubernetes scheduler has a plugin architecture that allows custom scheduling behavior.

For example:

```text
Pod requires:
GPU + high memory

        |
        v
Scheduler plugin
        |
        v
Prefer nodes with:
GPU type X
+
large memory
+
desired topology
```

This is different from simply creating a completely separate scheduler.

## kubectl Plugins

These extend the `kubectl` command-line experience.

A plugin can follow the naming convention:

```text
kubectl-foo
```

and then be invoked as:

```bash
kubectl foo
```

These plugins extend the CLI; they do not necessarily extend the Kubernetes control plane.

## Operators / Controllers

Operators are not technically identical to every type of Kubernetes plugin, but they are commonly discussed as Kubernetes extensions.

An operator generally combines Kubernetes APIs such as:

- CRDs (CustomResourceDefinitions)
- Controllers

For example:

```text
Prometheus resource
       |
       v
Prometheus Operator
       |
       v
Create/manage Prometheus resources
       |
       v
Prometheus running
```

Other examples include:

- Prometheus Operator
- cert-manager
- Argo CD
- Strimzi Kafka Operator

---

# 4. Overall Mental Model

A useful high-level picture is:

```text
                         USER
                          |
                       kubectl
                          |
                          v
                  +----------------+
                  | kube-apiserver |
                  +-------+--------+
                          |
                 +--------+--------+
                 |                 |
                 v                 v
               etcd          Controllers
                                   |
                                   v
                              Desired state
                                   |
                                   v
                              Scheduler
                                   |
                                   v
                             Node selected
                                   |
                                   v
                                kubelet
                                   |
                                   v
                           Container Runtime
                                   |
                                   v
                               Container
```

And around Kubernetes are extension points:

```text
                         Kubernetes
                              |
             +----------------+----------------+
             |                |                |
          Network           Storage         Hardware
             |                |                |
            CNI              CSI        Device Plugins
             |
       Cilium / Calico


                      Kubernetes API
                            |
                        Admission
                            |
                  Webhooks / Policies


                         Scheduler
                            |
                    Scheduler Plugins


                      Kubernetes API
                            |
                           CRD
                            |
                       Controller
                            |
                        Operator
```

---

# 5. Key Interview-Level Distinctions

If evaluating whether someone has genuine Kubernetes expertise, don't only ask:

> "What Kubernetes plugins have you used?"

That is too broad.

A better question is:

> **"Which Kubernetes extension points have you worked with—CNI, CSI, device plugins, admission webhooks, scheduler plugins, or CRD/controllers? What problem did you solve with each?"**

Then drill into the actual architecture.

For example:

### Networking

- Which CNI did you use?
- How does a Pod get an IP?
- How does Pod-to-Pod networking work across nodes?
- How does NetworkPolicy get enforced?
- What happens when the CNI fails?

### Storage

- Which CSI driver did you use?
- What happens when a PVC is created?
- How does Kubernetes provision a volume?
- What happens during Pod rescheduling?
- How does the CSI controller interact with the node-side CSI components?

### Scheduling

- What exactly does the scheduler do?
- What happens between Pod creation and Pod assignment?
- How do taints/tolerations differ from node affinity?
- Have you written or configured scheduler plugins?

### Control Plane

- What happens when you run `kubectl apply`?
- What gets stored in etcd?
- Which controller reacts to a Deployment?
- When does the scheduler get involved?
- How does the kubelet eventually start the container?

---

# 6. One-Sentence Summary

The core Kubernetes architecture can be remembered as:

> **API server = communication, etcd = state, controllers = reconciliation, scheduler = placement, kubelet = execution.**

And the major extension points are:

> **CNI = networking, CSI = storage, device plugins = hardware, admission = API policy, scheduler plugins = placement logic, and CRD/controllers/operators = custom Kubernetes behavior.**

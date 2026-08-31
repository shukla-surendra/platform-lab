# Kubernetes Nodes: EKS Node Groups vs On-Prem Nodes

## 1. Kubernetes Scheduler

The **Kubernetes Scheduler** is a control-plane component that decides **which Node should run a Pod**.

Its fundamental job is:

> **Pod → Node placement**

It considers:
- CPU and memory requests
- GPU resource requests
- Node selectors
- Node affinity / anti-affinity
- Taints and tolerations
- Other scheduling constraints

### Important distinction

The Scheduler **does not run the Pod**.

```text
Pod created
    ↓
Kubernetes Scheduler
    ↓
Selects suitable Node
    ↓
Kubelet starts Pod on that Node
```

---

# 2. EKS Node Group

In **Amazon EKS**, AWS officially uses the term **Node Group**.

A Node Group is a group of worker nodes with a common configuration.

Example:

```text
EKS Cluster
│
├── CPU Node Group
│     ├── EC2 Node
│     ├── EC2 Node
│     └── EC2 Node
│
└── GPU Node Group
      ├── EC2 Node
      └── EC2 Node
```

A Node Group can have configuration such as:

```text
Instance type
AMI
Minimum nodes
Desired nodes
Maximum nodes
Labels / taints
```

For example:

```text
GPU Node Group
instance: GPU EC2 instance
min: 0
desired: 2
max: 8
```

---

# 3. Does EKS Automatically Create Nodes?

You define the **Node Group configuration**, and EKS manages the underlying worker nodes for a **managed node group**.

However, an important distinction is:

> **Min/max settings define scaling boundaries. They do not by themselves mean that EKS automatically scales based on Pod demand.**

For workload-driven scaling, you typically use an autoscaling mechanism such as:
- Cluster Autoscaler
- Karpenter

Example:

```text
Node Group
min = 2
desired = 2
max = 10

        ↓

More Pods require capacity
        ↓
Autoscaler
        ↓
Additional nodes
        ↓
2 → 3 → 4 ... nodes
```

When capacity is no longer needed, the autoscaler can reduce the node count, subject to the configured minimum.

---

# 4. GPU Example in EKS

You might have:

```text
EKS Cluster
│
├── CPU Node Group
│     min: 2
│     max: 10
│
└── GPU Node Group
      min: 0
      max: 8
      GPU EC2 instances
```

A Pod can request a GPU:

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
```

The overall flow is:

```text
GPU Pod
  │
  │ requests 1 GPU
  ↓
Kubernetes Scheduler
  │
  │ selects a suitable GPU node
  ↓
GPU Node
  │
  ↓
Kubelet starts Pod
```

---

# 5. On-Prem Kubernetes

On-prem is different because Kubernetes itself does **not have a cloud provider creating physical machines for you**.

You typically start with physical servers or VMs:

```text
Physical Servers / VMs
       │
       ├── Server 1
       ├── Server 2
       ├── Server 3
       └── Server 4
              ↓
       Kubernetes Nodes
```

You provision the machines yourself (or use an infrastructure automation platform), install the required software, and join them to the cluster.

Vanilla Kubernetes fundamentally works with **Nodes**. It does not require an EKS-style `Node Group` object.

---

# 6. Can On-Prem Still Have Node Pools?

Yes.

The term **node pool** can still be used by a Kubernetes distribution or infrastructure-management platform.

For example:

```text
Kubernetes Cluster
│
├── CPU Pool
│     ├── Node 1
│     ├── Node 2
│     └── Node 3
│
└── GPU Pool
      ├── Node 4
      └── Node 5
```

But this is a higher-level management/infrastructure concept.

The fundamental Kubernetes object is still the **Node**.

---

# 7. Creating and Registering an On-Prem Node

A typical on-prem Kubernetes cluster created with **kubeadm** follows this process.

## Step 1 — Prepare the new machine

Start with a physical server or VM.

Install/configure:

```text
Linux
Container runtime
kubeadm
kubelet
```

`kubectl` is usually needed on an administrator/control-plane machine, but is not required on every worker node.

The node must have network connectivity to the control plane.

---

## Step 2 — Initialize the Control Plane

On the first control-plane machine:

```bash
kubeadm init
```

This sets up the initial Kubernetes control plane.

Conceptually:

```text
Control Plane
├── kube-apiserver
├── etcd
├── kube-scheduler
├── kube-controller-manager
└── certificates / cluster configuration
```

---

## Step 3 — Get the Join Command

After initialization, `kubeadm` provides a command similar to:

```bash
kubeadm join 10.0.0.10:6443   --token <token>   --discovery-token-ca-cert-hash sha256:<hash>
```

This is essentially an invitation for a new machine to join the cluster.

---

## Step 4 — Run `kubeadm join` on the Worker

On the new worker machine:

```bash
kubeadm join 10.0.0.10:6443   --token <token>   --discovery-token-ca-cert-hash sha256:<hash>
```

The worker contacts the Kubernetes API server.

```text
Worker Node
     │
     │ kubeadm join
     ↓
kube-apiserver
     │
     ↓
Control Plane
```

Authentication and certificate/bootstrap steps happen during this process.

---

# 8. Kubelet Registers the Node

The worker node runs **kubelet**.

After joining, kubelet communicates with the API server and the machine becomes a Kubernetes Node.

You can check:

```bash
kubectl get nodes
```

Example:

```text
NAME       STATUS   ROLES           AGE
master     Ready    control-plane   10d
worker-1   Ready    <none>          2m
worker-2   Ready    <none>          1m
```

Once the node is `Ready`, the Scheduler can consider it for Pod placement.

---

# 9. What Does "Adding a Node to the Control Plane" Mean?

Technically, a worker node is **not added inside the control plane**.

A better description is:

> **The worker node registers itself with the Kubernetes API server, and the control plane can then manage and schedule workloads on that node.**

The relationship looks like:

```text
                 Control Plane
                      │
                kube-apiserver
                      ▲
                      │
                  kubelet
                      │
                Worker Node
```

---

# 10. Full On-Prem Flow

```text
Create physical server / VM
          ↓
Install Linux
          ↓
Install container runtime
          ↓
Install kubeadm + kubelet
          ↓
kubeadm join <control-plane>
          ↓
Worker authenticates with API Server
          ↓
Kubelet registers Node
          ↓
Node becomes Ready
          ↓
Scheduler can place Pods on it
```

---

# 11. EKS vs On-Prem — Mental Model

| | EKS | On-Prem Vanilla Kubernetes |
|---|---|---|
| Basic worker unit | Node | Node |
| AWS terminology | Node Group | No required Node Group |
| Underlying machine | Usually EC2 | Physical server or VM |
| Who provides machine? | AWS/infrastructure | You/infrastructure platform |
| Node joining | Largely managed by EKS for managed node groups | Usually performed/automated by you |
| Min/max | Available at Node Group level | Not a core Kubernetes Node concept |
| Automatic node scaling | Autoscaler such as Karpenter/Cluster Autoscaler | Requires infrastructure/provisioning automation |
| Scheduler | Kubernetes Scheduler | Kubernetes Scheduler |

---

# 12. Three Responsibilities to Remember

This is the most useful mental model:

```text
1. Infrastructure
   "Give me a machine"
          ↓
2. Kubernetes
   "This machine is now a Node"
          ↓
3. Scheduler
   "Put this Pod on this Node"
```

For GPU infrastructure:

```text
Physical GPU Server
       ↓
Kubernetes Node
       ↓
NVIDIA Device Plugin
       ↓
Node advertises GPU resources
       ↓
Kubernetes Scheduler
       ↓
GPU Pod → suitable GPU Node
```

## One-line Summary

> **EKS Node Groups are an AWS-managed way to organize and manage worker nodes, while vanilla on-prem Kubernetes fundamentally works with individual Nodes that are provisioned and joined to the cluster by your infrastructure/automation. The Kubernetes Scheduler then decides which available Node should run each Pod.**

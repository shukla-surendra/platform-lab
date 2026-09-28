# Kubernetes Architecture

## 1. High-Level Architecture

Kubernetes has two major parts:

- **Control Plane** — the "brain" of the cluster. It decides what should happen.
- **Worker Nodes** — the execution layer where application Pods actually run.

```text
                 Kubernetes Cluster
                        |
          +-------------+-------------+
          |                           |
     CONTROL PLANE                WORKER NODE
        (Brain)                (Runs Workloads)
          |                           |
   +------+------+             +------+------+
   |      |      |             |      |      |
 API   Scheduler  |          Kubelet Kube-Proxy
Server           |             |
             Controller        |
             Manager           |
                              Container
                              Runtime
                                 |
                                Pods
```

---

# 2. Control Plane

The Control Plane manages the overall state of the Kubernetes cluster.

Its main components are:

1. kube-apiserver
2. etcd
3. kube-scheduler
4. kube-controller-manager
5. cloud-controller-manager (mainly in cloud environments)

## 2.1 kube-apiserver

The **API Server** is the main entry point to Kubernetes.

Everything that wants to interact with the Kubernetes cluster generally communicates through the API Server.

For example:

```bash
kubectl get pods
kubectl create deployment nginx --image=nginx
```

The flow is:

```text
kubectl
   |
   v
kube-apiserver
   |
   +----> Authentication / Authorization
   |
   +----> Kubernetes API
   |
   v
Cluster State
```

### Important points

- Exposes the Kubernetes API.
- `kubectl` communicates with it.
- Validates API requests.
- Handles authentication and authorization.
- Reads/writes Kubernetes objects and state.
- Other Kubernetes components also communicate through the API Server.

Think:

> **API Server = Front door of Kubernetes**

---

# 3. etcd

**etcd** is the distributed key-value database used by Kubernetes to store cluster state.

It stores information such as:

- Deployments
- Pods
- Services
- ConfigMaps
- Secrets
- Nodes
- ReplicaSets
- Desired state
- Cluster configuration

Example:

```text
User says:

"Run 3 nginx replicas"

        |
        v
   API Server
        |
        v
       etcd

Desired state:
nginx replicas = 3
```

Kubernetes components then work to make the actual cluster state match this desired state.

Think:

> **etcd = Kubernetes' source of truth**

Important:

> etcd does NOT run containers. It stores Kubernetes state.

---

# 4. kube-scheduler

The **Scheduler** decides which worker node should run a newly created Pod.

Suppose you have:

```text
Worker Node 1
CPU: 2
Memory: 4 GB

Worker Node 2
CPU: 8
Memory: 16 GB

Worker Node 3
CPU: 4
Memory: 8 GB
```

A new Pod is created requiring:

```text
CPU: 2
Memory: 4 GB
```

The scheduler evaluates available nodes and selects a suitable node.

```text
              New Pod
                 |
                 v
           kube-scheduler
                 |
       +---------+---------+
       |         |         |
       v         v         v
    Node 1     Node 2    Node 3
       |
       |   scheduler selects
       +---------------------> Node 2
```

The scheduler considers things such as:

- CPU/memory availability
- Node selectors
- Affinity/anti-affinity
- Taints and tolerations
- Topology constraints
- Resource requests

Think:

> **Scheduler = Decides where a Pod should run**

Important:

> Scheduler does NOT start the container.

It only makes the scheduling decision. The **kubelet** on the selected node ultimately gets the Pod running.

---

# 5. kube-controller-manager

The **Controller Manager** runs various controllers.

Controllers continuously compare:

```text
Desired State
      vs
Actual State
```

and take action when they differ.

Example:

You request:

```yaml
replicas: 3
```

But currently only 2 Pods are running.

```text
Desired State: 3 Pods
Actual State:  2 Pods

        |
        v
Controller detects difference
        |
        v
Creates another Pod
        |
        v
Actual State = 3 Pods
```

Examples of controllers include:

- Deployment controller
- ReplicaSet controller
- Node controller
- Job controller
- Namespace controller
- EndpointSlice-related controllers

Think:

> **Controller Manager = Keeps the cluster aligned with the desired state**

---

# 6. cloud-controller-manager

The **Cloud Controller Manager (CCM)** integrates Kubernetes with cloud-provider APIs.

It is relevant when Kubernetes is running on platforms such as:

- AWS
- Azure
- Google Cloud

For example, Kubernetes can request cloud resources such as:

```text
Kubernetes Service
       |
       v
Cloud Controller Manager
       |
       v
Cloud Provider API
       |
       v
Cloud Load Balancer
```

Think:

> **Cloud Controller Manager = Kubernetes ↔ Cloud provider integration**

---

# 7. Worker Node

Worker Nodes are where application workloads actually run.

A typical worker node contains:

```text
Worker Node
|
+-- kubelet
|
+-- kube-proxy
|
+-- Container Runtime
|      |
|      +-- containerd / CRI-O
|
+-- Pods
       |
       +-- Container
       +-- Container
```

The main components are:

1. kubelet
2. kube-proxy
3. Container Runtime
4. Pods

---

# 8. kubelet

The **kubelet** is the Kubernetes agent running on every worker node.

Its main responsibility is:

> Make sure the Pods assigned to this node are running correctly.

Example:

```text
API Server
     |
     | Pod specification
     v
  kubelet
     |
     v
Container Runtime
     |
     v
Container
```

The kubelet:

- Watches for Pods assigned to its node.
- Talks to the API Server.
- Tells the container runtime to create/start/stop containers.
- Performs health checks.
- Reports node and Pod status back to the API Server.

Think:

> **kubelet = Agent responsible for running Pods on a node**

Important distinction:

```text
Scheduler
   |
   +--> Decides WHICH node

kubelet
   |
   +--> Makes the Pod run ON that node
```

---

# 9. Container Runtime

The **Container Runtime** is responsible for actually running containers.

Common examples:

- containerd
- CRI-O

Historically Docker was commonly used, but modern Kubernetes does not use Docker Engine directly as its runtime interface.

The relationship is approximately:

```text
kubelet
   |
   | CRI
   v
Container Runtime
   |
   v
OCI Runtime
   |
   v
Container
```

For example:

```text
kubelet
   |
   v
containerd
   |
   v
runc
   |
   v
Linux Container
```

Think:

> **Container Runtime = Actually starts and stops containers**

---

# 10. kube-proxy

`kube-proxy` is a node-level networking component associated with Kubernetes Services.

It helps implement Service networking and traffic forwarding on nodes.

Example:

```text
Client
   |
   v
Service
10.96.0.10
   |
   +------> Pod A
   |
   +------> Pod B
   |
   +------> Pod C
```

The Service provides a stable virtual endpoint while Pods can be created and destroyed.

`kube-proxy` traditionally programs networking rules on nodes so traffic can be forwarded to the appropriate backend Pods.

Depending on the cluster/networking implementation, kube-proxy may use mechanisms such as:

- iptables
- IPVS

Some modern Kubernetes networking implementations can replace or eliminate kube-proxy functionality.

Think:

> **kube-proxy = Helps implement Service networking and traffic forwarding**

---

# 11. Pods

A **Pod** is the smallest deployable unit in Kubernetes.

Your application containers run inside Pods.

Example:

```text
Worker Node
|
+-- Pod A
|    |
|    +-- nginx container
|
+-- Pod B
     |
     +-- application container
```

A Pod can contain one or multiple containers.

For most applications:

```text
1 Pod
  |
  +-- 1 main application container
```

Multiple containers in a Pod share things such as:

- Network namespace
- IP address
- localhost
- Volumes

---

# 12. Complete Request Flow

Consider this command:

```bash
kubectl create deployment nginx --image=nginx --replicas=3
```

A simplified flow is:

```text
                    kubectl
                       |
                       v
                kube-apiserver
                       |
                       v
                     etcd
                       |
                       |
              Desired state = 3
                       |
                       v
          Controller Manager
                       |
                       v
               Creates Pod objects
                       |
                       v
                kube-scheduler
                       |
              Chooses worker node
                       |
          +------------+------------+
          |                         |
          v                         v
       Worker 1                  Worker 2
          |                         |
       kubelet                   kubelet
          |                         |
    containerd                 containerd
          |                         |
          v                         v
       Pod/NGINX                 Pod/NGINX
```

The same process happens until all 3 desired replicas are running.

---

# 13. Control Plane vs Worker Node

| Component | Location | Main Responsibility |
|---|---|---|
| kube-apiserver | Control Plane | Kubernetes API |
| etcd | Control Plane | Stores cluster state |
| kube-scheduler | Control Plane | Chooses node for Pods |
| kube-controller-manager | Control Plane | Maintains desired state |
| cloud-controller-manager | Control Plane | Cloud integration |
| kubelet | Worker Node | Manages Pods on node |
| kube-proxy | Worker Node | Service networking/traffic forwarding |
| Container Runtime | Worker Node | Runs containers |
| Pod | Worker Node | Runs application workload |

---

# 14. Easy Interview Memory Trick

## Control Plane

Remember:

> **API → STORE → DECIDE → CONTROL**

```text
API Server          → API
etcd                → STORE
Scheduler           → DECIDE
Controller Manager  → CONTROL
```

## Worker Node

Remember:

> **WATCH → NETWORK → RUN**

```text
kubelet             → WATCH/MANAGE Pods
kube-proxy          → NETWORK
container runtime   → RUN containers
```

---

# 15. Most Important Interview Distinctions

### Scheduler vs kubelet

```text
Scheduler
    ↓
Which node should run this Pod?

kubelet
    ↓
Make that Pod actually run on my node.
```

### etcd vs API Server

```text
API Server
    ↓
Provides access to Kubernetes state

etcd
    ↓
Stores Kubernetes state
```

### kubelet vs container runtime

```text
kubelet
    ↓
Tells runtime what should be running

container runtime
    ↓
Actually runs the containers
```

### Pod vs Container

```text
Pod
 └── Container(s)
```

A Pod is the Kubernetes workload unit; containers are the processes running inside it.

---

# 16. One-Line Architecture Summary

> **The Control Plane manages and makes decisions about the cluster, while Worker Nodes execute the workloads through kubelet, the container runtime, networking components, and Pods.**

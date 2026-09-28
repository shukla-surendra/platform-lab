# Kubernetes Pod Creation — Controllers, Scheduler, Kubelet & Runtime

This note explains what actually happens when Kubernetes needs to create a Pod, especially in the context of a Deployment, ReplicaSet, and ReplicaSet Controller.

---

# 1. The Most Important Question

If an interviewer asks:

> **"What creates a Pod?"**

The strongest answer is:

> **At the Kubernetes API level, a controller such as the ReplicaSet Controller creates the Pod object through the API Server. The scheduler assigns that Pod to a node, and the kubelet on that node instructs the container runtime to actually create and run the Pod's containers.**

There are therefore several different steps involved.

```text
Controller
    |
    | creates Pod object
    v
API Server
    |
    v
Pod Object
    |
    v
Scheduler
    |
    | selects Worker Node
    v
kubelet
    |
    v
Container Runtime
    |
    v
Containers
```

---

# 2. Who Does What?

| Component | Responsibility |
|---|---|
| API Server | Accepts API requests and exposes Kubernetes resources |
| etcd | Stores Kubernetes cluster state |
| Controller | Creates/updates/deletes objects to reconcile desired state |
| ReplicaSet Controller | Ensures the requested number of matching Pods exist |
| Scheduler | Selects a Worker Node for an unscheduled Pod |
| kubelet | Manages Pods assigned to its node |
| Container Runtime | Actually creates and runs containers |

The important distinction:

```text
Controller
    ↓
Creates Pod OBJECT

kubelet + container runtime
    ↓
Actually make the workload RUN
```

---

# 3. Example: ReplicaSet Wants 2 Pods

Suppose we have:

```yaml
apiVersion: apps/v1
kind: ReplicaSet

metadata:
  name: nginx-rs

spec:
  replicas: 2

  selector:
    matchLabels:
      app: nginx

  template:
    metadata:
      labels:
        app: nginx

    spec:
      containers:
        - name: nginx
          image: nginx
```

The important part is:

```yaml
replicas: 2
```

This means:

> The desired number of matching Pods is 2.

---

# 4. Initial State

Suppose there are currently no matching Pods:

```text
Desired State:

2 Pods

Actual State:

0 Pods
```

The ReplicaSet Controller compares them:

```text
Desired = 2
Actual  = 0

Difference = 2
```

Therefore it needs to create Pods.

```text
ReplicaSet Object
       |
       | replicas = 2
       v
ReplicaSet Controller
       |
       | sees:
       | Desired = 2
       | Actual  = 0
       v
Create 2 Pod Objects
```

---

# 5. Does ReplicaSet Controller Directly Create Containers?

No.

This is extremely important.

The ReplicaSet Controller does **not**:

```text
ReplicaSet Controller
       |
       X
       └── directly contact containerd
```

Instead:

```text
ReplicaSet Controller
       |
       v
API Server
       |
       v
Pod Objects
```

The controller works through the Kubernetes API.

---

# 6. What Happens After the Pod Object Is Created?

The Pod now exists as a Kubernetes API object.

But it may not yet be assigned to a Worker Node.

Conceptually:

```text
Pod Object

name: nginx-abc
status: Pending
node: not assigned
```

Then the scheduler sees the unscheduled Pod.

```text
Pod Object
    |
    | node not assigned
    v
Scheduler
```

---

# 7. Scheduler Chooses a Node

Suppose the cluster has:

```text
Worker Node 1
Worker Node 2
Worker Node 3
```

The scheduler evaluates the available nodes and chooses a suitable one.

```text
                 Pod
                  |
                  v
             Scheduler
                  |
        +---------+---------+
        |         |         |
        v         v         v
      Node 1    Node 2    Node 3
                  |
                  |
              selected
```

The scheduler does NOT run the container.

It makes the placement decision.

> **Scheduler = Which node should run this Pod?**

---

# 8. What Happens on the Selected Node?

Suppose the scheduler selects Worker Node 2.

```text
Scheduler
    |
    v
Worker Node 2
```

The kubelet on Node 2 is responsible for making sure the Pod actually runs.

```text
Worker Node 2
    |
    +-- kubelet
    |
    +-- container runtime
    |
    +-- Pod
```

The kubelet reads the Pod specification and works with the container runtime.

---

# 9. Kubelet + Container Runtime

The simplified flow is:

```text
Pod assigned to Node
        |
        v
      kubelet
        |
        | CRI
        v
Container Runtime
        |
        v
Container
```

Typical container runtimes include:

- containerd
- CRI-O

The runtime creates and starts the actual containers.

---

# 10. Complete Pod Creation Flow

Putting everything together:

```text
                         CONTROL PLANE

ReplicaSet Object
       |
       v
ReplicaSet Controller
       |
       | Desired = 2
       | Actual  = 0
       |
       v
   API Server
       |
       v
   Pod Object(s)
       |
       v
   Scheduler
       |
       | chooses Worker Node
       v

                    WORKER NODE
       |
       v
     kubelet
       |
       v
Container Runtime
       |
       v
   Containers
```

---

# 11. What If Desired = 2 and Actual = 2?

Suppose:

```text
ReplicaSet:
replicas = 2

Running Pods:
Pod A
Pod B
```

Then:

```text
Desired = 2
Actual  = 2
```

The ReplicaSet Controller does nothing.

```text
Desired == Actual
       |
       v
No corrective action
```

This is the normal steady state.

---

# 12. What If One Pod Dies?

Suppose:

```text
Desired = 2

Pod A ✓
Pod B ✗
```

Now:

```text
Desired = 2
Actual  = 1
```

The ReplicaSet Controller detects the difference.

```text
ReplicaSet Controller
        |
        | Desired = 2
        | Actual  = 1
        v
Creates another Pod Object
        |
        v
API Server
        |
        v
New Pod
```

Then:

```text
New Pod
   |
   v
Scheduler
   |
   v
Worker Node
   |
   v
kubelet
   |
   v
Container Runtime
```

Eventually:

```text
Desired = 2
Actual  = 2
```

The system returns to the desired state.

---

# 13. What If There Are Too Many Pods?

This is equally important.

Suppose:

```text
Desired = 2

Pod A ✓
Pod B ✓
Pod C ✓
```

Now:

```text
Desired = 2
Actual  = 3
```

The ReplicaSet Controller reconciles the difference.

```text
ReplicaSet Controller
        |
        | Actual > Desired
        v
Deletes an excess matching Pod
        |
        v
Actual = 2
```

Therefore:

```text
Desired < Actual
        |
        v
Remove excess Pods
```

---

# 14. The Fundamental ReplicaSet Rule

The ReplicaSet Controller continuously tries to make:

```text
Actual matching Pods = spec.replicas
```

So:

```text
             ReplicaSet
                 |
          replicas: 2
                 |
                 v
       ReplicaSet Controller
                 |
        +--------+--------+
        |                 |
   Actual < 2        Actual > 2
        |                 |
        v                 v
  Create Pods        Remove excess
        |                 |
        +--------+--------+
                 |
                 v
             Actual = 2
```

This is called **reconciliation**.

---

# 15. "New Entry in Pod" — Important Correction

A common misunderstanding is:

> "If a new entry appears in the Pod, will ReplicaSet create another Pod?"

Not exactly.

The ReplicaSet Controller watches the **ReplicaSet object and the current state of matching Pods**.

For example:

```text
ReplicaSet:
Desired = 2

Current:
Pod A
Pod B
```

Everything is correct.

If you manually create another matching Pod:

```text
ReplicaSet:
Desired = 2

Current:
Pod A
Pod B
Pod C
```

Now:

```text
Desired = 2
Actual  = 3
```

The controller may remove an excess matching Pod.

It does NOT create another Pod just because another Pod appeared.

---

# 16. Deployment Makes This One Level More Interesting

If you are using a Deployment, the hierarchy is:

```text
Deployment
     |
     v
Deployment Controller
     |
     v
ReplicaSet
     |
     v
ReplicaSet Controller
     |
     v
Pods
```

For example:

```text
Deployment
replicas = 3
      |
      v
ReplicaSet
replicas = 3
      |
      v
Pod 1
Pod 2
Pod 3
```

So the Deployment Controller and ReplicaSet Controller have different responsibilities.

---

# 17. Deployment Controller vs ReplicaSet Controller

### Deployment Controller

Main responsibility:

```text
Deployment
    |
    v
ReplicaSets
```

It manages rollout and revision behavior.

### ReplicaSet Controller

Main responsibility:

```text
ReplicaSet
    |
    v
Pods
```

It maintains the desired number of Pods.

So:

```text
Deployment Controller
        |
        v
    ReplicaSet

ReplicaSet Controller
        |
        v
       Pods
```

---

# 18. Full Deployment Pod Creation Flow

```text
User
 |
 | kubectl apply
 v
API Server
 |
 v
Deployment Object
 |
 v
etcd
 |
 v
Deployment Controller
 |
 v
ReplicaSet Object
 |
 v
etcd
 |
 v
ReplicaSet Controller
 |
 v
Pod Object
 |
 v
Scheduler
 |
 | selects node
 v
Worker Node
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

This is the most useful diagram to remember for interviews.

---

# 19. Does the Controller Talk Directly to the Scheduler?

No.

The controller creates/updates the Pod object through the API Server.

Then the scheduler watches for unscheduled Pods.

```text
Controller
    |
    v
API Server
    |
    v
Pod Object
    |
    v
Scheduler
```

The controller does not normally say:

> "Scheduler, please put this Pod on Node 2."

Instead, the scheduler independently makes the scheduling decision based on the Pod specification and cluster state.

---

# 20. Does the Scheduler Talk Directly to kubelet?

The conceptual architecture is API-driven.

```text
Scheduler
    |
    v
API Server
    |
    v
Pod gets node assignment
    |
    v
kubelet observes Pod assigned to its node
```

The kubelet then works to make the Pod actually run.

---

# 21. Why Does Kubernetes Use This Design?

Because Kubernetes separates responsibilities.

```text
Controller
    |
    | What should exist?
    v

Scheduler
    |
    | Where should it run?
    v

kubelet
    |
    | Make it run here
    v

Container Runtime
    |
    | Actually start containers
    v

Container
```

This separation makes Kubernetes extensible and resilient.

---

# 22. Special Case: Directly Creating a Pod

You don't always need a Deployment or ReplicaSet.

You can directly create a Pod:

```bash
kubectl run nginx --image=nginx
```

Conceptually:

```text
kubectl
   |
   v
API Server
   |
   v
Pod Object
   |
   v
Scheduler
   |
   v
Worker Node
   |
   v
kubelet
   |
   v
Container Runtime
```

There may be **no Deployment or ReplicaSet** in this case.

But the Pod still goes through the API Server, scheduler, kubelet, and container runtime.

---

# 23. Direct Pod vs Deployment

### Direct Pod

```text
kubectl
   ↓
API Server
   ↓
Pod
   ↓
Scheduler
   ↓
kubelet
   ↓
Runtime
```

### Deployment

```text
kubectl
   ↓
API Server
   ↓
Deployment
   ↓
Deployment Controller
   ↓
ReplicaSet
   ↓
ReplicaSet Controller
   ↓
Pod
   ↓
Scheduler
   ↓
kubelet
   ↓
Runtime
```

This is why Pods can exist without Deployments, but Deployments ultimately result in Pods.

---

# 24. Interview Question: "Who Creates the Pod?"

A precise answer:

> **"It depends on the context. If a Deployment is being used, the Deployment Controller creates/manages a ReplicaSet, and the ReplicaSet Controller creates the Pod objects through the API Server. The scheduler assigns those Pods to nodes, and the kubelet uses the container runtime to actually create and run their containers. A Pod can also be created directly through the API without a Deployment or ReplicaSet."**

---

# 25. Interview Question: "Who Actually Runs the Pod?"

A precise answer:

> **"The kubelet on the assigned worker node manages the Pod, while the container runtime such as containerd or CRI-O actually creates and runs the containers inside the Pod."**

---

# 26. Interview Question: "Who Decides Where the Pod Runs?"

Answer:

> **"The kube-scheduler selects a suitable worker node for an unscheduled Pod."**

```text
Pod
 |
 v
Scheduler
 |
 v
Worker Node
```

---

# 27. Interview Question: "Where Does ReplicaSet Controller Run?"

Answer:

> **"The ReplicaSet Controller runs as part of kube-controller-manager in the Kubernetes control plane."**

```text
Control Plane
     |
     v
kube-controller-manager
     |
     v
ReplicaSet Controller
```

---

# 28. Final Mental Model

Remember this chain:

```text
                    DESIRED STATE
                         |
                         v
                 Kubernetes Object
                         |
                         v
                    Controller
                         |
                         | Reconcile
                         v
                  Pod Object Created
                         |
                         v
                     Scheduler
                         |
                         | Select Node
                         v
                    Worker Node
                         |
                         v
                      kubelet
                         |
                         | CRI
                         v
                 Container Runtime
                         |
                         v
                    Containers
```

For a Deployment:

```text
Deployment
    ↓
Deployment Controller
    ↓
ReplicaSet
    ↓
ReplicaSet Controller
    ↓
Pod Object
    ↓
Scheduler
    ↓
Worker Node
    ↓
kubelet
    ↓
containerd / CRI-O
    ↓
Container
```

## The four questions to always separate

```text
WHO DECIDES WHAT SHOULD EXIST?
        ↓
Controller

WHO CREATES THE POD API OBJECT?
        ↓
Controller through API Server
(or direct API request for a standalone Pod)

WHO DECIDES WHERE IT RUNS?
        ↓
Scheduler

WHO ACTUALLY RUNS THE CONTAINERS?
        ↓
kubelet + Container Runtime
```

> **This separation is the key to understanding Pod creation in Kubernetes.**

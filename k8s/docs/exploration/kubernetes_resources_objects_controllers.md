# Kubernetes — Resources, Objects & Controllers

This note builds on `architecture.md` and focuses on the concepts discussed afterward:

- Where Deployment, StatefulSet, Job, CronJob, etc. fit
- Resource vs Object
- API Server vs Controller
- How workload controllers govern resources
- Deployment → ReplicaSet → Pod flow
- StatefulSet, Job, and CronJob flows
- Complete control-plane-to-worker flow

---

# 1. Kubernetes Architecture — Where Workload Resources Fit

```text
                 KUBERNETES CLUSTER
                       |
          +------------+------------+
          |                         |
     CONTROL PLANE              WORKER NODE
     (components)               (components)
          |                         |
    +-----+------+             +----+------+
    |     |      |             |    |      |
   API  Sched  Controller     kube  proxy  runtime
  Server        Manager       let
    |                            |
    |     Kubernetes Objects     |
    +------------+---------------+
                 |
        +--------+---------+
        |                  |
    Deployment          Service
        |
    ReplicaSet
        |
       Pods
        |
    Containers
```

The important distinction is:

- **Control Plane components** are Kubernetes system components.
- **Deployment, ReplicaSet, Pod, Service, etc.** are Kubernetes API resources/objects.
- **Controllers** implement the behavior that makes the desired state become reality.

---

# 2. What Is a Kubernetes Object?

A Kubernetes **object** is a concrete instance representing some desired/current state in the cluster.

Example:

```yaml
apiVersion: apps/v1
kind: Deployment

metadata:
  name: nginx

spec:
  replicas: 3
```

After applying this manifest:

```bash
kubectl apply -f deployment.yaml
```

Kubernetes has a Deployment object:

```text
Deployment Object
    |
    +-- name: nginx
    +-- replicas: 3
```

You can have multiple Deployment objects:

```text
Deployment Objects
|
+-- nginx
+-- frontend
+-- backend
```

Think:

> **Object = actual instance**

---

# 3. What Is a Kubernetes Resource?

A **resource** is an API-defined type/category through which Kubernetes exposes objects.

For example:

```text
Deployment Resource
        |
        +-- nginx object
        +-- frontend object
        +-- backend object
```

Similarly:

```text
Pod Resource
        |
        +-- nginx-abc object
        +-- nginx-def object
        +-- frontend-xyz object
```

A useful analogy is a database:

```text
Database Table / Type
        |
        +-- Row 1
        +-- Row 2
        +-- Row 3
```

In Kubernetes:

```text
API Resource
        |
        +-- Object
        +-- Object
        +-- Object
```

Another programming analogy:

```text
class Deployment:       # Type
    pass

nginx = Deployment()    # Object
frontend = Deployment() # Object
```

### Simple rule

> **Resource = type/category**
>
> **Object = concrete instance of that type**

---

# 4. What Does `kind` Mean?

In a Kubernetes manifest:

```yaml
kind: Deployment
```

`kind` specifies what type of Kubernetes object you want to create.

Examples:

```text
kind: Deployment
        |
        +-- Deployment object

kind: Service
        |
        +-- Service object

kind: Pod
        |
        +-- Pod object

kind: ConfigMap
        |
        +-- ConfigMap object
```

So:

```text
kind: Deployment
        |
        v
Deployment type
        |
        v
Deployment object
```

---

# 5. API Resources

You can see the API resources available in a Kubernetes cluster with:

```bash
kubectl api-resources
```

Typical examples include:

```text
NAME            SHORTNAMES
pods            po
deployments     deploy
replicasets     rs
statefulsets    sts
jobs
cronjobs        cj
services        svc
configmaps      cm
secrets
```

Conceptually:

```text
                 Kubernetes API
                       |
       +---------------+---------------+
       |               |               |
  Deployments      StatefulSets       Jobs
       |               |               |
     Objects         Objects         Objects
```

The API Server exposes these API resources.

---

# 6. API Server vs Controller

This is one of the most important distinctions.

Do NOT think:

```text
Deployment is inside API Server
```

Instead think:

```text
                 kube-apiserver
                       |
             exposes API resources
                       |
       +---------------+---------------+
       |               |               |
 Deployment       StatefulSet        Job
 Resource          Resource         Resource
       |               |               |
       +---------------+---------------+
                       |
                      etcd
                       |
                       v
                  Controllers
```

The API Server primarily provides the API and persists/serves Kubernetes state.

The controllers implement behavior.

---

# 7. Controllers

A controller continuously observes Kubernetes state and works to make:

```text
Desired State
      =
Actual State
```

If the states differ, the controller takes action.

Example:

```text
Desired State
3 nginx Pods
      |
      | compare
      v
Actual State
2 nginx Pods
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

Think:

> **Controller = reconciliation loop**

---

# 8. kube-controller-manager

Many built-in Kubernetes controllers run under the control-plane component:

```text
kube-controller-manager
```

Conceptually:

```text
kube-controller-manager
|
+-- Deployment Controller
|
+-- ReplicaSet Controller
|
+-- StatefulSet Controller
|
+-- Job Controller
|
+-- CronJob Controller
|
+-- Node Controller
|
+-- Namespace Controller
|
+-- Other Controllers
```

Therefore, workload resources such as Deployment, ReplicaSet, StatefulSet, Job, and CronJob are not themselves control-plane components.

They are API resources/objects, and their corresponding controllers implement their behavior.

---

# 9. Workload Controllers

Common workload-related resources include:

```text
Workload Resources
|
+-- Pod
|
+-- Deployment
|
+-- ReplicaSet
|
+-- StatefulSet
|
+-- DaemonSet
|
+-- Job
|
+-- CronJob
```

They have different purposes.

```text
Deployment
    |
    +-- Manages application rollout
    +-- Usually manages ReplicaSets
    +-- ReplicaSets manage Pods

StatefulSet
    |
    +-- Manages stateful workloads
    +-- Provides stable Pod identity
    +-- Manages Pods

DaemonSet
    |
    +-- Ensures Pods run on selected nodes

Job
    |
    +-- Runs batch work to completion

CronJob
    |
    +-- Creates Jobs according to a schedule
```

---

# 10. Deployment — API Resource + Controller

A Deployment is an API resource.

Example:

```yaml
apiVersion: apps/v1
kind: Deployment

metadata:
  name: nginx

spec:
  replicas: 3
```

The flow is:

```text
kubectl
   |
   v
API Server
   |
   v
Deployment Object
   |
   v
etcd
```

The Deployment Controller watches the Deployment object:

```text
Deployment Object
       |
       v
Deployment Controller
       |
       v
ReplicaSet
       |
       v
Pods
```

The Deployment Controller does not itself run the containers.

---

# 11. Deployment → ReplicaSet → Pod

This is the key workload hierarchy:

```text
Deployment
     |
     v
ReplicaSet
     |
     v
Pods
     |
     v
Containers
```

For example:

```text
Deployment: nginx
replicas: 3
        |
        v
ReplicaSet: nginx-abc
        |
        +---- Pod 1
        |
        +---- Pod 2
        |
        +---- Pod 3
```

The Deployment generally manages the ReplicaSet.

The ReplicaSet maintains the requested number of Pods.

---

# 12. ReplicaSet Controller

Suppose:

```text
Desired Pods = 3
```

Current state:

```text
Pod 1  ✓
Pod 2  ✓
Pod 3  ✓
```

Everything is correct.

Now suppose Pod 2 crashes:

```text
Desired = 3

Pod 1  ✓
Pod 2  ✗
Pod 3  ✓
```

The ReplicaSet Controller detects:

```text
Desired = 3
Actual  = 2
```

It creates another Pod:

```text
Pod 1  ✓
Pod 2  ✓
Pod 3  ✓
```

Conceptually:

```text
ReplicaSet
     |
     | "I need 3 Pods"
     v
+----+----+----+
|    |    |    |
Pod  Pod  Pod
```

---

# 13. Deployment Complete Flow

A simplified end-to-end flow:

```text
                  kubectl
                     |
                     v
                API Server
                     |
                     v
                    etcd
                     |
              Deployment Object
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
                     |
                     v
                Scheduler
                     |
              Chooses Worker Node
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

# 14. StatefulSet

StatefulSet is also an API resource.

Conceptually:

```text
StatefulSet Resource
        |
        v
StatefulSet Object
        |
        v
StatefulSet Controller
        |
        v
      Pods
```

StatefulSet is designed for workloads where stable identity and/or ordered behavior matters.

Conceptually:

```text
StatefulSet: database
       |
       +-- database-0
       +-- database-1
       +-- database-2
```

The Pods have stable names/identities compared with ordinary Deployment Pods.

---

# 15. StatefulSet Flow

```text
kubectl
   |
   v
API Server
   |
   v
StatefulSet Object
   |
   v
etcd
   |
   v
StatefulSet Controller
   |
   +----> database-0
   |
   +----> database-1
   |
   +----> database-2
```

The StatefulSet Controller manages the desired StatefulSet behavior.

---

# 16. Job

Job is also an API resource.

Its purpose is batch work that should complete.

Example:

```yaml
apiVersion: batch/v1
kind: Job

metadata:
  name: data-processing

spec:
  completions: 5
```

Conceptually:

```text
Job Resource
     |
     v
Job Object
     |
     v
Job Controller
     |
     v
Pods
     |
     v
Batch work
     |
     v
Completion
```

The Job Controller works toward the requested successful completions.

---

# 17. CronJob

CronJob is also an API resource.

Its purpose is to create Jobs according to a schedule.

Example:

```yaml
apiVersion: batch/v1
kind: CronJob

metadata:
  name: nightly-backup

spec:
  schedule: "0 0 * * *"
```

The conceptual hierarchy is:

```text
CronJob
   |
   | schedule fires
   v
 Job
   |
   v
 Pods
   |
   v
 Containers
```

More explicitly:

```text
CronJob Object
      |
      v
CronJob Controller
      |
      | creates Job
      v
Job Object
      |
      v
Job Controller
      |
      | creates/manages Pods
      v
Pods
```

So CronJob does not normally directly manage the application container.

---

# 18. DaemonSet

DaemonSet is another workload resource.

Its purpose is to ensure a Pod runs on each selected node.

Conceptually:

```text
DaemonSet
    |
    v
DaemonSet Controller
    |
    +-------- Worker Node 1
    |              |
    |             Pod
    |
    +-------- Worker Node 2
    |              |
    |             Pod
    |
    +-------- Worker Node 3
                   |
                  Pod
```

Typical use cases include node-level agents such as:

- Logging agents
- Monitoring agents
- Node-level networking components

---

# 19. Workload Controller Summary

```text
                     WORKLOAD RESOURCES
                             |
        +--------------------+--------------------+
        |                    |                    |
   Deployment            StatefulSet            Job
        |                    |                    |
 Deployment Controller  StatefulSet Controller  Job Controller
        |                    |                    |
   ReplicaSet               Pods                 Pods
        |
 ReplicaSet Controller
        |
       Pods


                    CronJob
                       |
                CronJob Controller
                       |
                      Job
                       |
                 Job Controller
                       |
                      Pods


                    DaemonSet
                       |
                DaemonSet Controller
                       |
            Pods on selected nodes
```

---

# 20. API Server + etcd + Controllers

This is the central mental model.

```text
                         CONTROL PLANE

                       kube-apiserver
                              |
                              |
                 +------------+------------+
                 |                         |
                 v                         v
          API Resources                 etcd
                 |                         |
                 |                    Stores state
                 |
       +---------+---------+
       |         |         |
 Deployment  StatefulSet   Job
       |         |         |
     Objects   Objects   Objects
                 |
                 v
             Controllers
                 |
       +---------+---------+
       |         |         |
 Deployment  StatefulSet  Job
 Controller  Controller  Controller
       |         |         |
       v         v         v
   ReplicaSet   Pods      Pods
       |
       v
      Pods
```

---

# 21. Scheduler Comes After Pods Are Created

A subtle but important point:

The controller does not necessarily choose the worker node.

For example:

```text
Deployment
    |
    v
ReplicaSet
    |
    v
Pod object created
    |
    | Pod does not have a node yet
    v
Scheduler
    |
    v
Chooses Worker Node
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

So:

> **Controller creates/manages workload objects. Scheduler decides where unscheduled Pods run. kubelet makes the assigned Pods run on its node.**

---

# 22. Complete Architecture Mental Model

Put everything together:

```text
                         KUBERNETES CLUSTER
                                |
                +---------------+---------------+
                |                               |
                |          CONTROL PLANE        |
                |                               |
                |  +-------------------------+  |
                |  |     kube-apiserver      |  |
                |  +------------+------------+  |
                |               |               |
                |               v               |
                |             etcd              |
                |                               |
                |  +-------------------------+  |
                |  | kube-controller-manager |  |
                |  +------------+------------+  |
                |               |               |
                |       +-------+-------+       |
                |       |       |       |       |
                |       v       v       v       |
                |   Deployment StatefulSet Job  |
                |    Controller Controller Controller
                |       |       |       |       |
                |       +-------+-------+       |
                |               |               |
                |              Pods             |
                |               |               |
                |       +-------v-------+       |
                |       | kube-scheduler |       |
                |       +-------+-------+       |
                |               |               |
                +---------------|---------------+
                                |
                                v
                     +----------------------+
                     |     WORKER NODE      |
                     |                      |
                     |       kubelet        |
                     |          |           |
                     |          v           |
                     |  Container Runtime   |
                     |          |           |
                     |          v           |
                     |      Containers      |
                     |          |           |
                     |         Pods         |
                     +----------------------+
```

---

# 23. The Most Important Separation

Keep these four layers mentally separate:

```text
1. API Resources / Objects
   |
   | Deployment
   | StatefulSet
   | Job
   | CronJob
   | Pod
   | Service
   | ConfigMap
   | Secret
   |
   v

2. Controllers
   |
   | Watch objects
   | Reconcile desired state
   |
   v

3. Scheduler
   |
   | Chooses node for unscheduled Pods
   |
   v

4. Worker Node
   |
   | kubelet
   | container runtime
   | networking
   |
   v
   Containers
```

---

# 24. Interview-Level Summary

### What is a resource?

> A Kubernetes API resource is a type/category exposed through the Kubernetes API, such as Deployment, Pod, Service, Job, or StatefulSet.

### What is an object?

> An object is a concrete instance of a Kubernetes resource representing state in the cluster.

### What does the API Server do?

> It exposes the Kubernetes API and handles requests and access to Kubernetes state. Persistent cluster state is stored in etcd.

### What does a controller do?

> A controller watches Kubernetes objects and continuously reconciles actual state toward desired state.

### Where do workload controllers run?

> Built-in controllers are generally run by control-plane components such as `kube-controller-manager`.

### Does the API Server run Deployment?

> No. The API Server exposes/stores the Deployment resource and its objects. The Deployment Controller implements Deployment behavior.

### Does the Deployment Controller run containers?

> No. It manages Deployment state, generally resulting in ReplicaSets and Pods.

### Who decides where a Pod runs?

> The kube-scheduler.

### Who actually manages the Pod on the selected node?

> The kubelet.

### Who actually runs the container?

> The container runtime, such as containerd or CRI-O.

---

# 25. One Final Mental Model

Remember this chain:

```text
                 USER
                  |
                  v
             kubectl/API
                  |
                  v
             API SERVER
                  |
                  v
                etcd
                  |
                  v
             K8s OBJECT
                  |
                  v
             CONTROLLER
                  |
                  v
          Creates/updates objects
                  |
                  v
                 POD
                  |
                  v
              SCHEDULER
                  |
                  v
             WORKER NODE
                  |
                  v
               KUBELET
                  |
                  v
          CONTAINER RUNTIME
                  |
                  v
             CONTAINER
```

The key idea is:

> **API Server provides the API, etcd stores state, controllers reconcile objects, scheduler places Pods, kubelet manages Pods on nodes, and the container runtime runs the containers.**

# Kubernetes Workload Controllers — Mental Model and Architecture

## 1. The big picture

Kubernetes has several **workload controllers** that manage Pods, but they solve different problems.

The most useful way to understand them is to ask:

> **What requirement do I have for my Pods?**

```text
                 Kubernetes Workload Controllers
                            │
          ┌─────────────────┼──────────────────┐
          │                 │                  │
     Long-running       Node-oriented      Batch-oriented
      workloads            workload          workloads
          │                 │                  │
    ┌─────┴─────┐           │            ┌─────┴─────┐
    │           │           │            │           │
Deployment  StatefulSet  DaemonSet      Job       CronJob
    │           │           │             │           │
    ▼           ▼           ▼             ▼           ▼
ReplicaSet    Pods        Pods           Pods       Jobs
    │                                               │
    ▼                                               ▼
  Pods                                             Pods
```

A more precise controller relationship is:

```text
Deployment
    │
    ▼
ReplicaSet
    │
    ▼
Pods


StatefulSet
    │
    ▼
Pods


DaemonSet
    │
    ▼
Pods


Job
    │
    ▼
Pods


CronJob
    │
    ▼
Job
    │
    ▼
Pods
```

**Important:** Deployment is the workload controller that uses a ReplicaSet as an intermediate layer. StatefulSet and DaemonSet do not use ReplicaSets.

---

# 2. The common idea: controllers maintain desired state

A useful Kubernetes mental model is:

```text
Desired State
      │
      ▼
Controller
      │
      ▼
Actual Kubernetes Objects
```

For example:

```text
Desired: 3 application Pods
             │
             ▼
        Controller
             │
             ▼
       Actual: 3 Pods
```

Different controllers implement different meanings of "desired state."

```text
ReplicaSet
→ N interchangeable Pods

Deployment
→ application rollout/version management using ReplicaSets

StatefulSet
→ N Pods with stable identity and stateful lifecycle semantics

DaemonSet
→ one Pod on every applicable node

Job
→ enough successful Pod completions to finish a finite task

CronJob
→ create Jobs according to a schedule
```

---

# 3. Deployment

## What is a Deployment?

### Interview answer

> **A Deployment is a Kubernetes workload controller used to manage long-running, usually stateless applications. It maintains the desired number of interchangeable Pods and provides declarative rolling updates, rollout history, and rollback. Internally, a Deployment manages ReplicaSets, and ReplicaSets manage the Pods.**

Short version:

> **Deployment manages the rollout and lifecycle of a stateless application, using ReplicaSets to maintain the desired number of Pods.**

---

## Deployment architecture

```text
Deployment
    │
    ├── ReplicaSet-v1
    │       │
    │       ├── Pod-v1
    │       ├── Pod-v1
    │       └── Pod-v1
    │
    └── ReplicaSet-v2
            │
            ├── Pod-v2
            ├── Pod-v2
            └── Pod-v2
```

During a rollout, both old and new ReplicaSets may temporarily exist.

For example:

```text
Start:

Deployment
    │
    └── ReplicaSet-v1
          ├── Pod-v1
          ├── Pod-v1
          └── Pod-v1


During rollout:

Deployment
    ├── ReplicaSet-v1
    │      ├── Pod-v1
    │      └── Pod-v1
    │
    └── ReplicaSet-v2
           └── Pod-v2


Finished:

Deployment
    │
    └── ReplicaSet-v2
           ├── Pod-v2
           ├── Pod-v2
           └── Pod-v2
```

The old ReplicaSet can remain as rollout history, allowing rollback.

Useful commands:

```bash
kubectl get deployments
kubectl get replicasets
kubectl get pods
kubectl rollout status deployment <name>
kubectl rollout history deployment <name>
kubectl rollout undo deployment <name>
```

---

# 4. Why does Deployment need ReplicaSet?

A Deployment has a higher-level responsibility:

> **Manage application versions and rollouts.**

A ReplicaSet has a simpler responsibility:

> **Maintain the desired number of matching Pods.**

Therefore:

```text
Deployment
"I want version 2 and I want 3 replicas."
        │
        ▼
ReplicaSet-v2
"I must maintain 3 v2 Pods."
        │
        ▼
      Pods
```

During an update:

```text
                 Deployment
                 /        \
                /          \
       ReplicaSet-v1    ReplicaSet-v2
            │                │
         old Pods          new Pods
```

The Deployment can scale the old ReplicaSet down and the new ReplicaSet up according to the rollout strategy.

This separation also supports rollout history and rollback.

---

# 5. ReplicaSet

## What is a ReplicaSet?

A ReplicaSet is a controller whose primary responsibility is:

> **Ensure that a specified number of matching Pods are running.**

For example:

```yaml
spec:
  replicas: 3
```

Conceptually:

```text
ReplicaSet
    │
    ├── Pod
    ├── Pod
    └── Pod
```

If one Pod disappears:

```text
Before:

Pod-A
Pod-B
Pod-C

Pod-B disappears:

Pod-A
Pod-C
```

The ReplicaSet notices:

```text
Desired = 3
Actual  = 2
```

and creates another Pod.

The replacement Pod does not need to preserve the identity of the deleted Pod.

### Important practical point

You normally do **not** create ReplicaSets directly for normal application deployment.

Instead:

```text
Deployment
    ↓
ReplicaSet
    ↓
Pods
```

The Deployment manages the ReplicaSet for you.

---

# 6. StatefulSet

## What is a StatefulSet?

### Interview answer

> **A StatefulSet is a Kubernetes workload controller for stateful or identity-sensitive applications. It manages multiple Pods directly while providing stable Pod identities, stable network identities, persistent storage associations, and ordered lifecycle behavior. Unlike a Deployment, a StatefulSet does not use ReplicaSets.**

Short version:

> **StatefulSet manages Pods that need stable identity and often stable storage, such as database or distributed-system members.**

---

## StatefulSet architecture

```text
StatefulSet
    │
    ├── db-0
    │     └── PVC-0
    │
    ├── db-1
    │     └── PVC-1
    │
    └── db-2
          └── PVC-2
```

Notice:

```text
StatefulSet
    │
    ▼
Pods
```

There is **no ReplicaSet layer**.

---

# 7. How does StatefulSet manage N Pods without a ReplicaSet?

This is an important concept.

Suppose:

```yaml
spec:
  replicas: 3
```

The StatefulSet controller itself makes sure the desired Pods exist:

```text
StatefulSet
    │
    ├── db-0
    ├── db-1
    └── db-2
```

If `db-1` dies:

```text
db-0   Running
db-1   Failed
db-2   Running
```

The StatefulSet controller notices that the desired state is not satisfied and recreates:

```text
db-1
```

It does not simply create an arbitrary Pod such as:

```text
db-x7k29
```

The identity matters.

---

# 8. Deployment vs StatefulSet

This is one of the most important Kubernetes comparisons.

| Property | Deployment | StatefulSet |
|---|---|---|
| Typical use | Stateless/replaceable application | Stateful/identity-sensitive application |
| Pod identity | Interchangeable | Stable |
| Pod names | Generated | Predictable, e.g. `db-0`, `db-1` |
| ReplicaSet layer | Yes | No |
| Storage association | Usually external/independent | Can provide stable PVC association |
| Replacement identity | New Pod can be different | Same ordinal identity is recreated |
| Rollouts | Deployment-managed | StatefulSet-managed |
| Typical examples | API, frontend, web service | Database, Kafka-like clustered system |

### Mental model

Deployment:

```text
"I need 3 equivalent copies."

Pod
Pod
Pod
```

StatefulSet:

```text
"I need 3 specific members."

db-0
db-1
db-2
```

---

# 9. DaemonSet

## What is a DaemonSet?

A DaemonSet is a controller that ensures a Pod runs on **every applicable node**.

Mental model:

> **One Pod per applicable node.**

```text
DaemonSet
    │
    ├── Node 1 → Pod
    ├── Node 2 → Pod
    └── Node 3 → Pod
```

If a new applicable node joins:

```text
Node 4
```

the DaemonSet creates:

```text
Node 4 → Pod
```

If a node is removed, its DaemonSet Pod disappears with the node.

---

## Important correction

Do not define DaemonSet as:

> "One Pod on every node."

More accurately:

> **One Pod on every node that satisfies the DaemonSet's scheduling requirements.**

Scheduling can be restricted by:

- node affinity
- node selectors
- taints/tolerations
- OS requirements
- other scheduling constraints

---

# 10. Your Azure CNS example

Your AKS cluster has:

```text
DaemonSet: azure-cns
```

Its architecture is:

```text
DaemonSet: azure-cns
        │
        ▼
    Pod template
        │
        ▼
azure-cns Pod
   │
   ├── Init container: cni-installer
   ├── Init container: telemetry-sidecar-init
   │
   ├── Container: cns-container
   └── Container: cni-telemetry-sidecar
```

The Pod uses `hostNetwork: true` and several `hostPath` volumes.

Examples from your DaemonSet:

```text
/opt/cni/bin
/etc/cni/net.d
/var/run
/var/lib/azure-network
/var/run/azure-vnet
```

These are node-level paths.

Conceptually:

```text
Kubernetes Node
│
├── /opt/cni/bin
├── /etc/cni/net.d
├── /var/run
├── /var/lib/azure-network
│
└── azure-cns Pod
       │
       ├── cns-container
       └── cni-telemetry-sidecar
              │
              └── HostPath mounts → Node filesystem
```

This is a strong real-world example of why a DaemonSet is useful: Azure CNS is node-level networking infrastructure.

Useful commands:

```bash
kubectl get daemonsets -A
kubectl get daemonset azure-cns -n kube-system
kubectl describe daemonset azure-cns -n kube-system
kubectl get daemonset azure-cns -n kube-system -o yaml
kubectl get pods -n kube-system -o wide
```

---

# 11. DaemonSet vs ReplicaSet

These are directly comparable because both are controllers that maintain Pods, but their desired-state rules differ.

### ReplicaSet

> Maintain N matching/interchangeable Pods.

```text
ReplicaSet
    │
    ├── Pod
    ├── Pod
    └── Pod
```

Example:

```text
replicas = 3
```

means:

```text
3 Pods
```

The Pods do not have to be distributed one per node.

### DaemonSet

> Maintain one Pod on each applicable node.

```text
DaemonSet
    │
    ├── Node 1 → Pod
    ├── Node 2 → Pod
    └── Node 3 → Pod
```

So:

```text
ReplicaSet:
"How many Pods?"

DaemonSet:
"Which nodes need a Pod?"
```

---

# 12. Job

A Job is for a **finite task that should eventually complete**.

Mental model:

```text
Job
 │
 ▼
Pod
 │
 ▼
Task finishes
 │
 ▼
Job completed
```

Unlike a Deployment, the Pod is not expected to run forever.

Example:

```text
Run a database migration
Run a batch ML preprocessing task
Generate a report
Process a finite data set
```

---

# 13. Can a Job have multiple Pods?

Yes.

A Job can use concepts such as:

```yaml
completions:
parallelism:
```

For example:

```yaml
spec:
  completions: 5
  parallelism: 2
```

Mental model:

```text
Job
 │
 ├── Pod 1 → completed
 ├── Pod 2 → completed
 ├── Pod 3 → completed
 ├── Pod 4 → completed
 └── Pod 5 → completed
```

`parallelism: 2` means up to two Pods can work concurrently.

The important distinction is that the Pods are being used to **complete work**, not to provide a permanently running service.

---

# 14. CronJob

A CronJob is a scheduler for Jobs.

Mental model:

```text
CronJob
   │
   ├── Job 1
   │     └── Pods
   │
   ├── Job 2
   │     └── Pods
   │
   └── Job 3
         └── Pods
```

Example:

```yaml
schedule: "0 2 * * *"
```

means:

> Create a Job according to that schedule.

So:

```text
CronJob
   ↓
Job
   ↓
Pods
   ↓
Task completes
```

If each Job itself uses multiple completions, each scheduled Job can create/manage multiple Pods.

---

# 15. Long-running vs batch workloads

A very useful boundary is:

```text
Long-running workloads
        │
        ├── Deployment
        ├── StatefulSet
        └── DaemonSet

Batch workloads
        │
        ├── Job
        └── CronJob
```

Long-running:

> Pods are expected to remain running.

Batch:

> Pods are expected to perform work and eventually finish.

---

# 16. Quick decision framework

Ask:

### "Do I need a continuously running application?"

If yes:

```text
Stateless/interchangeable?
        │
        └── Yes → Deployment

Stable identity/storage?
        │
        └── Yes → StatefulSet

One copy per applicable node?
        │
        └── Yes → DaemonSet
```

If it is a finite task:

```text
Run once/on demand?
        │
        └── Yes → Job

Run periodically?
        │
        └── Yes → CronJob
```

---

# 17. Interview-ready definitions

## "What is a Deployment in Kubernetes?"

A strong answer:

> **A Deployment is a Kubernetes workload controller used primarily for stateless, long-running applications. It declares the desired number and version of application Pods and manages their rollout. A Deployment creates and manages ReplicaSets, and the ReplicaSets maintain the actual Pods. This allows Kubernetes to perform rolling updates, maintain availability, keep rollout history, and support rollback.**

If the interviewer wants a shorter answer:

> **Deployment manages stateless application Pods and their versioned rollouts. It uses ReplicaSets underneath to maintain the desired number of Pods.**

---

## "What is a StatefulSet in Kubernetes?"

A strong answer:

> **A StatefulSet is a Kubernetes workload controller designed for applications where Pod identity and state matter. It manages Pods directly rather than through ReplicaSets and provides stable Pod identities, predictable names, stable network identities, and persistent storage associations. It is commonly used for databases and distributed systems where individual members need stable identity.**

Shorter answer:

> **StatefulSet manages stateful or identity-sensitive Pods with stable identities and storage associations. Unlike Deployment, it does not use ReplicaSets.**

---

# 18. Interview comparison: Deployment vs StatefulSet vs DaemonSet

If asked:

> "What's the difference between Deployment, StatefulSet, and DaemonSet?"

A concise answer:

> **Deployment is for interchangeable, generally stateless application replicas; StatefulSet is for Pods that need stable identity and often persistent storage; DaemonSet is for node-level workloads where one Pod should run on every applicable node.**

Example:

```text
Deployment
    → API servers / frontend

StatefulSet
    → database cluster

DaemonSet
    → node networking / logging / monitoring agent
```

---

# 19. Final mental model

Memorize this:

```text
Deployment
    ↓
ReplicaSet
    ↓
Pods

"I need N interchangeable application Pods,
and I need rollout/version management."


StatefulSet
    ↓
Pods

"I need N Pods, but each Pod has stable identity
and potentially stable storage."


DaemonSet
    ↓
Pods

"I need one Pod on every applicable node."


Job
    ↓
Pods

"I need Pods to perform a finite task and finish."


CronJob
    ↓
Jobs
    ↓
Pods

"I need those finite tasks to run on a schedule."
```

And the most important conceptual distinction:

```text
Deployment  → version/rollout management
ReplicaSet  → number of interchangeable Pods
StatefulSet → identity/state
DaemonSet   → node placement
Job         → completion
CronJob      → scheduling Jobs
```

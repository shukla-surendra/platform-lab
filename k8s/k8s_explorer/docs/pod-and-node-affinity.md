# Affinity: node affinity, pod affinity, pod anti-affinity

Affinity is a **scheduling-time** rule: it tells the Kubernetes scheduler *where* a Pod is
allowed or preferred to land. Nothing in this doc changes *how many* Pods exist — that's the
job of `HorizontalPodAutoscaler` / KEDA `ScaledObject` (see
[`resource-management.md`](./resource-management.md) and the comparison at the bottom of this
page). Affinity and scaling are orthogonal and compose: scaling decides the replica count, the
scheduler (honoring affinity) decides which node each replica lands on.

No production chart in this repo uses affinity (`grep -r affinity` across `full-stack-app`,
`my-app`, etc. turns up nothing), so the examples below are illustrative rather than pulled from
one of those. For a hands-on version you can actually apply and watch the scheduler act on, see
[`affinity-demo/`](../affinity-demo) — five manifests plus a walkthrough covering every rule
below on a real (`minikube`) cluster, including the two "gotchas" (unsatisfiable anti-affinity
on a single node, and the `IgnoredDuringExecution` label-drift behavior) proven live rather than
just described.

## First principles: why this exists at all

The default scheduler already does bin-packing: given a Pod's `resources.requests`, it picks
any Node with enough free CPU/memory (see
[`resource-management.md`](./resource-management.md#requests-and-limits-per-container)). That
alone answers "does this Node have room?" but not "should this Pod specifically avoid/prefer
this Node?" — questions like:

- This Pod needs a GPU or SSD — only some Nodes have one.
- This Pod talks to another Pod constantly — put them on the same Node.
- This Pod has 3 replicas — don't stack all of them on one Node, or a single Node failure takes
  the whole app down.

Affinity is the mechanism that answers those. It works by matching **labels**: Node affinity
matches labels on the *Node object* (`kubectl get nodes --show-labels`); Pod (anti-)affinity
matches labels on *other Pods already running* (or being scheduled) via a `labelSelector` plus a
`topologyKey` that defines what "close" or "apart" means (usually
`kubernetes.io/hostname` for "same/different Node", but can be a zone/region label for
"same/different AZ").

```
                     ┌────────────────────────┐
   Node labels  ───▶ │  Node Affinity          │  "run on a Node matching X"
                     └────────────────────────┘
                     ┌────────────────────────┐
  Other Pods'  ───▶  │  Pod Affinity           │  "run near Pods matching X"
  labels             │  Pod Anti-Affinity      │  "run away from Pods matching X"
                     └────────────────────────┘
```

## 1. Node affinity — which Nodes a Pod can run on

Say the cluster has:

```
Node-1: zone=us-east, disk=ssd
Node-2: zone=us-west, disk=hdd
```

A Pod that needs SSD:

```yaml
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: disk
            operator: In
            values: [ssd]
```

Only `Node-1` satisfies this — the Pod will never land on `Node-2`, and if no Node matches at
all, the Pod sits in `Pending` (`kubectl describe pod` shows `0/N nodes are available: node(s)
didn't match Pod's node affinity/selector`).

## 2. Pod affinity — schedule near other Pods

Given a `frontend` that wants to sit on the same Node as `backend` (lower network latency —
same-Node traffic skips the overlay network entirely):

```yaml
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values: [backend]
        topologyKey: kubernetes.io/hostname
```

Reads as: "only schedule me on a Node that already has a running Pod labeled `app=backend`."

## 3. Pod anti-affinity — schedule away from other Pods

Given 3 replicas of `web`, without any rule the scheduler is free to (and often will, once bin
packing favors it) put all 3 on one Node:

```
Node-1
  web-1
  web-2
  web-3          ← Node-1 dies, the whole app is down
```

```yaml
spec:
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: web
        topologyKey: kubernetes.io/hostname
```

This is evaluated **per replica as it schedules** — replica 2 sees replica 1 already placed and
avoids its Node; replica 3 avoids both:

```
Node-1        Node-2        Node-3
web-1         web-2         web-3
```

Now a single Node failure only costs one replica, not all three. This is the standard pattern
for HA Deployments; `topologyKey: topology.kubernetes.io/zone` instead of
`kubernetes.io/hostname` spreads across AZs rather than Nodes.

**Sharp edge**: with `requiredDuringSchedulingIgnoredDuringExecution` anti-affinity, replica
count can't exceed the number of matching Nodes — 3 replicas with strict one-per-Node
anti-affinity on a 2-Node cluster leaves one Pod permanently `Pending`. This is exactly why
`PodDisruptionBudget` (see [`resource-management.md`](./resource-management.md#poddisruptionbudget-protecting-availability-during-voluntary-disruption))
and anti-affinity are usually reasoned about together — PDB protects availability during
*voluntary* disruption, anti-affinity protects it from the start by never co-locating replicas.

## Required vs. preferred

Both Node affinity and Pod (anti-)affinity come in two strengths:

| | Keyword | Behavior if unsatisfiable |
|---|---|---|
| Hard rule | `requiredDuringSchedulingIgnoredDuringExecution` | Pod stays `Pending` |
| Soft rule | `preferredDuringSchedulingIgnoredDuringExecution` | Scheduler falls back to best-effort placement anyway |

`preferred` also takes a `weight` (1–100) per term, letting you rank multiple soft preferences
against each other:

```yaml
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 80
      preference:
        matchExpressions:
        - {key: disk, operator: In, values: [ssd]}
    - weight: 20
      preference:
        matchExpressions:
        - {key: zone, operator: In, values: [us-east]}
```

In practice: use `required` when violating the rule breaks correctness (a Pod that *needs* a
GPU driver present has no business running without one); use `preferred` when it's an
optimization the app can live without (SSD is nicer but HDD still works).

## "IgnoredDuringExecution" — the part everyone misses

Every affinity rule in current Kubernetes ends in `...IgnoredDuringExecution`. That suffix means
the rule is checked **only at scheduling time**, once. If the Node's label changes after the Pod
is already running, the Pod is *not* evicted or re-evaluated:

```
1. Pod scheduled onto a Node labeled disk=ssd    → rule satisfied, Pod starts.
2. Someone later removes the disk=ssd label.
3. Kubernetes does nothing — the running Pod stays right where it is.
```

(There is a `RequiredDuringSchedulingRequiredDuringExecution` variant in the API types for
future use, but it isn't implemented by the scheduler as of current Kubernetes — every affinity
rule you can actually use today is schedule-time-only.)

## Affinity vs. `nodeSelector`

`nodeSelector` is the older, simpler mechanism — exact label match, ANDed together, no soft mode:

```yaml
spec:
  nodeSelector:
    disk: ssd
```

| | `nodeSelector` | Node affinity |
|---|:---:|:---:|
| Simple label match | ✅ | ✅ |
| AND/OR across multiple expressions | ❌ (AND only) | ✅ |
| Operators (`In`, `NotIn`, `Exists`, `DoesNotExist`, `Gt`, `Lt`) | ❌ (equality only) | ✅ |
| Soft/preferred rules | ❌ | ✅ |

If a plain `key: value` match is all you need, `nodeSelector` is fewer lines and easier to read
— reach for node affinity only when you need `NotIn`/`Exists` or a `preferred` fallback.

## Real-world use cases

- **GPU workloads** — `nodeAffinity` requiring `accelerator=nvidia-a100`, so ML Pods never land
  on CPU-only Nodes and fail at container-start.
- **SSD-backed databases** — `disk=ssd` required affinity for StatefulSet replicas.
- **High availability** — `podAntiAffinity` so replicas of the same Deployment spread across
  Nodes/zones (pairs naturally with a `PodDisruptionBudget`).
- **Low latency** — `podAffinity` to co-locate a cache/sidecar-like Pod with its consumer when
  they can't literally share a Pod.
- **Multi-zone spread or grouping** — `topologyKey: topology.kubernetes.io/zone` to either keep
  a service's Pods in one AZ (data-locality) or force them apart (AZ-outage resilience).

For the "spread evenly across zones/Nodes" case specifically, `topologySpreadConstraints` is
often a better fit than `podAntiAffinity` — anti-affinity only expresses "not with a match," not
"balance the count." Worth its own note if this repo starts using either.

## Affinity vs. scaling — different questions entirely

| | Affinity | Scaling (HPA / KEDA `ScaledObject`) |
|---|---|---|
| Answers | *Where* should a Pod run? | *How many* Pods should exist? |
| Owned by | Kubernetes scheduler | HPA controller / KEDA operator |
| Changes replica count? | No | Yes |
| Changes Pod placement? | Yes | No (it only changes desired count; scheduler places the result) |

They compose in one direction only: scaling changes the Deployment's `replicas`, and *then* the
scheduler places each new/removed replica, honoring whatever affinity rules that Pod template
carries. Affinity never triggers a scale event, and scaling never overrides an affinity rule.

```
SQS queue depth rises
        │
        ▼
KEDA ScaledObject → bumps Deployment replicas 2 → 5
        │
        ▼
3 new Pod objects created (same template, same affinity rules)
        │
        ▼
Scheduler places each new Pod, filtering to Nodes that satisfy
nodeAffinity (e.g. disk=ssd) and podAntiAffinity (spread across Nodes)
        │
        ▼
Pods start running on the eligible Nodes
```

Concretely: KEDA/HPA decides *5 replicas*; a `disk=ssd` node affinity on those Pods decides
*which* 5 Nodes are even eligible; a `podAntiAffinity` on `app=image-processor` decides that
those 5 don't stack onto the same one or two SSD Nodes. Three independent mechanisms, one
outcome.

## Quick reference

```bash
kubectl get nodes --show-labels                          # what labels exist to match against
kubectl label node <node> disk=ssd                        # add a label for testing
kubectl describe pod <pod> | grep -A5 Affinity            # what rule is actually on the Pod
kubectl describe pod <pod> | grep -A3 Events               # "didn't match node affinity" lives here when Pending
kubectl get pods -o wide -l app=web                        # confirm anti-affinity actually spread replicas across nodes
```

## Summary

| Type | Purpose |
|---|---|
| Node affinity | Choose which Nodes a Pod can run on |
| Pod affinity | Keep Pods together |
| Pod anti-affinity | Keep Pods apart |
| `required...` | Hard rule — unsatisfiable means `Pending` |
| `preferred...` | Soft rule — best effort, scheduler falls back if needed |
| Scaling (HPA/KEDA) | A different axis entirely — decides replica *count*, not placement |

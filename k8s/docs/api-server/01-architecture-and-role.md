# 1. Architecture and role

## What it is

`kube-apiserver` is a stateless HTTP server that implements the Kubernetes
REST API. "Stateless" is the load-bearing word: it holds no cluster state
in memory between requests — every single piece of cluster state (every
`Pod`, `Deployment`, `WebApp`, everything) lives in **etcd**, and the API
server is the *only* component allowed to talk to etcd directly.

Everything else in the cluster — `kube-scheduler`, `kube-controller-manager`,
every `kubelet` on every node, every operator you've ever written in this
repo (`webapp-operator`, `greeting-operator`), `kubectl`, Helm, ArgoCD — is
a **client** of the API server, exactly the same way `kubectl` is. There is
no backdoor: a controller's `client.Get(...)` call is an HTTP request to
`kube-apiserver`, same as `kubectl get`.

```
                    ┌─────────────────────────────┐
                    │        kube-apiserver        │
                    │   (stateless, horizontally    │
                    │    scalable, HTTP + REST)      │
                    └───────────────┬───────────────┘
                                    │  (only thing that talks to etcd)
                                    ▼
                              ┌──────────┐
                              │   etcd    │
                              └──────────┘
        ▲            ▲             ▲                ▲
        │            │             │                │
   kubectl    kube-scheduler  kube-controller-  every kubelet /
                              manager            operator / Helm
```

## Why "the only thing that talks to etcd" matters

This is what makes RBAC, admission control, and validation actually mean
something. If `kube-scheduler` or a `kubelet` could write to etcd directly,
every authorization/admission rule the API server enforces would be
trivially bypassable. Centralizing all reads and writes through one
component is what makes it possible to have a single, consistent security
boundary (see [`02-request-lifecycle.md`](./02-request-lifecycle.md)) and
a single, consistent way to watch for changes (see
[`04-watch-and-list.md`](./04-watch-and-list.md)).

## Stateless → horizontally scalable

Because it holds no state itself, a cluster typically runs **multiple**
`kube-apiserver` instances (2-3+ on any real HA control plane) behind a
load balancer — any instance can serve any request, since all of them read
from and write to the same etcd cluster. This is different from etcd
itself, which *is* stateful and runs its own separate leader-election/Raft
consensus among its own members — the API server has no equivalent
leadership concept for itself; it doesn't need one, because it isn't
coordinating anything between its own replicas beyond "all talk to the
same etcd."

(Other control-plane components *do* need leader election among their own
replicas — `kube-scheduler` and `kube-controller-manager` each elect one
active leader via a `Lease` object, itself just another object living in
etcd, written through the API server like anything else.)

## What it does NOT do

- **Scheduling** — deciding which node a Pod runs on is `kube-scheduler`'s
  job. The API server just stores the `Pod` object (with `spec.nodeName`
  empty until the scheduler sets it) and lets the scheduler watch for
  unscheduled Pods.
- **Reconciling** — turning a `Deployment` into `ReplicaSet`s into `Pod`s,
  or a `WebApp` into a `Deployment`+`Service`, is `kube-controller-manager`
  or your own operator's job. The API server has no idea what a
  `Deployment` "means" beyond its schema — see
  [`03-api-model-and-extensibility.md`](./03-api-model-and-extensibility.md)
  and `../../aks_crd_operator/docs/qna.md`'s "What is the operator?" entry for
  the same point made about `WebApp` specifically.
- **Running containers** — that's the `kubelet` (talking to a container
  runtime via CRI), on each node.

The API server's job is narrower than it looks from the outside: expose a
REST API, enforce who can do what, validate/default the data, persist it,
and notify watchers when it changes. Everything that makes those objects
*do* something is a separate client, watching and reacting — the same
split `aks_crd_operator/docs/qna.md` describes between a CRD (schema,
served by the API server) and an operator (behavior, a separate client).

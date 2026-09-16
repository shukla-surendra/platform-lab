# Plugins and add-ons — FAQ

## What's the actual difference between a "plugin" and an "add-on"?

A plugin implements a specific interface Kubernetes core already defined
(CNI, CSI, CRI, device plugins, scheduler plugins, the cloud-provider
interface). An add-on is a looser, no-formal-meaning term for anything
installed on top of a base cluster — some add-ons are plugins, but most of
the popular ones (cert-manager, Prometheus Operator, Argo CD) aren't
plugins at all, just CRD+operator. Full explanation:
[`01-first-principles.md`](./01-first-principles.md).

## Is a CRD a plugin?

No. A plugin fills a slot Kubernetes core already cut out, following a
fixed interface/spec. A CRD *creates a brand-new slot* of your own design
— there's no pre-existing interface it's conforming to. Full comparison:
[`04-relation-to-crd-and-operator.md`](./04-relation-to-crd-and-operator.md).

## Why doesn't a fresh cluster have working Pod networking out of the box?

Because CNI (Pod networking) is a plugin interface, not something
Kubernetes core ships an implementation of — a cluster with no CNI plugin
installed leaves Pods stuck `ContainerCreating` forever. Managed
offerings (AKS/EKS/GKE) install one for you by default, which is why this
is easy to not notice. See
[`02-plugin-interfaces-reference.md`](./02-plugin-interfaces-reference.md).

## Is Docker still used to run containers on a Kubernetes node?

Not directly — `kubelet` talks CRI (Container Runtime Interface), and the
old Docker-specific shim (`dockershim`) was removed from `kubelet` in
1.24. Nodes run `containerd` or `CRI-O` instead. Docker-*built* images
still work fine everywhere (they're standard OCI images), only the
runtime kubelet talks to changed. See
[`02-plugin-interfaces-reference.md`](./02-plugin-interfaces-reference.md).

## Is `metrics-server` a CRD-based add-on?

No — it's an aggregated API server (aka "Option B" extensibility from
`../api-server/03-api-model-and-extensibility.md`), the one common
real-world example of that mechanism. It serves live metrics on request,
which can't be backed by etcd/CRD storage the way `WebApp`/`Greeting`
are. See [`03-addons-reference.md`](./03-addons-reference.md).

## Give me one concrete example that uses *both* a plugin interface and CRD+operator.

A CSI storage driver: its node component implements the CSI gRPC plugin
interface directly; its controller-side sidecars reconcile built-in
objects (`PersistentVolumeClaim`, `VolumeAttachment`) the same
watch-then-reconcile way `webapp-operator` reconciles `WebApp`; some
drivers additionally ship their own CRDs on top for driver-specific
settings. Full breakdown:
[`04-relation-to-crd-and-operator.md`](./04-relation-to-crd-and-operator.md).

## Can I write an operator instead of implementing CSI/CNI to add storage/networking?

No — `kubelet` only ever calls a real CNI/CSI plugin at the fixed points
in the Pod lifecycle where it needs one; no other object in the cluster,
CRD-backed or not, substitutes for that call. The two mechanisms solve
genuinely different classes of problem, not two ways to solve the same
one. See the closing section of
[`04-relation-to-crd-and-operator.md`](./04-relation-to-crd-and-operator.md).

## Is a `kubectl` plugin (installed via krew) related to any of this?

No — it's a client-side CLI extension (an executable `kubectl` shells out
to), unrelated to every cluster-side extension point on this page beyond
sharing the word "plugin." Noted explicitly in
[`02-plugin-interfaces-reference.md`](./02-plugin-interfaces-reference.md)
to prevent exactly this mix-up.

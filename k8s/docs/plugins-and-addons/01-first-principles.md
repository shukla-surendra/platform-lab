# 1. Plugins and add-ons, from first principles

## Start from what Kubernetes core actually ships

`kube-apiserver`, `etcd`, `kube-scheduler`, `kube-controller-manager`,
`kubelet` — that's it. That's the whole thing Kubernetes-the-project
builds and versions together. Everything else — how Pods get an IP,
how storage gets attached, which container runtime actually runs a
container, how GPUs get allocated, DNS, ingress, certificates,
monitoring — is deliberately **left out** and delegated to a pluggable
interface instead.

**Q: If Kubernetes doesn't ship networking, storage, or DNS — how does a
freshly-installed cluster do any of that at all?**
A: It doesn't, until you install something that does. A cluster with no
CNI plugin installed can't give Pods working network connectivity at all
— Pods stay stuck in `ContainerCreating`. This isn't a bug; it's the
design. Managed offerings (AKS, EKS, GKE) just install a default set of
these for you so it isn't obvious anything was missing.

## Plugin — an implementation of a Kubernetes-defined *contract*

A **plugin**, precisely, is something that implements a specific,
versioned interface that a core Kubernetes component calls out to at a
fixed extension point — CNI, CSI, CRI, the device plugin API, a scheduler
framework plugin. The interface is the contract (often gRPC, sometimes an
older exec/HTTP-based one); the plugin is whichever concrete
implementation you install that speaks it. Kubelet/scheduler/CCM knows
*how* to call the interface; it has no idea *which* implementation is on
the other end, and doesn't need to.

**Q: Is a CRD + operator a "plugin" by this definition?**
A: No — and this is the whole point of `04-relation-to-crd-and-operator.md`.
A CRD doesn't implement any of Kubernetes' pre-defined interfaces; it
*adds a new one*, of your own design, served by the existing API server.
"Plugin" (this doc) means "fills in a slot Kubernetes core already
defined." CRD+operator means "defines a brand-new slot that didn't exist
before." Different mechanisms, easy to conflate because both end up
described as "extending Kubernetes."

## Add-on — a looser, deployment-shaped term

**Add-on** has no formal Kubernetes API meaning at all — it's just
"something you install on top of a base cluster to get functionality the
control plane doesn't include." An add-on can be:

- **A plugin implementation**, deployed as a `DaemonSet` (most CNI/CSI
  node components) or `Deployment` (a CSI driver's controller side) —
  e.g. `csi-azuredisk-node`, seen running live in this repo's own cluster
  (`aks_crd_operator/docs/qna.md`).
- **A CRD + operator**, with no plugin interface involved at all —
  cert-manager, Prometheus Operator, ArgoCD. Kubernetes core has no
  "certificate plugin slot" or "GitOps plugin slot" for these to fill;
  they're ordinary controllers reconciling their own custom resources,
  same shape as `webapp-operator`/`greeting-operator` in this repo.
- **Neither** — a plain `Deployment` with no CRD and no plugin interface,
  just watching/creating built-in resources. `metrics-server` is the
  cleanest example: it's an *aggregated API server* (Option B from
  `../api-server/03-api-model-and-extensibility.md`), not a plugin
  interface and not a CRD.

**Q: So is every plugin an add-on, and every add-on a plugin?**
A: Every plugin you install is an add-on (in the loose "thing you added to
the cluster" sense). The reverse is false — most of the add-ons people
reach for daily (cert-manager, ArgoCD, Prometheus Operator, Velero) are
not plugins at all in the strict interface sense; they're CRD+operator,
covered fully in `04-relation-to-crd-and-operator.md`.

## Why this distinction is worth holding onto

Debugging a broken CNI plugin (Pods stuck `ContainerCreating`, no IP) and
debugging a broken cert-manager install (a `Certificate` object stuck
`False` on its `Ready` condition) are structurally different problems —
one is "is the interface implementation running and correctly configured
on every node," the other is "is the controller running and does it have
the RBAC/permissions the reconcile loop needs" (the exact class of bug
`aks_crd_operator/docs/qna.md` walks through live for `greeting-operator`).
Knowing which category something falls into tells you where to even start
looking.

# 4. Relation to CRD and operator

The direct question: are plugins/add-ons "the same thing" as CRD+operator?
No — they're two separate extension mechanisms that happen to get lumped
under the same word ("extending Kubernetes") constantly. This doc is the
explicit comparison.

## Two different questions each mechanism answers

- **Plugin interfaces** (`02-plugin-interfaces-reference.md`) answer: *"How
  does Kubernetes core delegate a piece of functionality it deliberately
  didn't build in?"* The interface (CNI, CSI, CRI, ...) is fixed and
  versioned by a spec Kubernetes itself defines or adopts; you write to
  that spec.
- **CRD + operator** (`../api-server/03-api-model-and-extensibility.md`,
  and this repo's entire `aks_crd_operator/` tutorial) answers: *"How do I
  add a brand-new kind of object, with its own schema, that didn't exist
  before, and make something react to it?"* There's no pre-defined
  interface to implement — you design the schema (`WebApp`, `Greeting`,
  `Certificate`) and the reconcile behavior yourself, from nothing.

Put differently: a plugin *fills a slot Kubernetes core already cut out*.
A CRD *cuts a brand-new slot*, and an operator is what fills the slot it
just cut.

## Where they overlap in practice

Most real add-ons combine both, or pick one:

1. **Plugin only, no CRD** — `containerd` (CRI). It fully replaces a core
   contract; there's no new *kind* of Kubernetes object involved anywhere.
2. **CRD + operator only, no plugin interface** — cert-manager, Prometheus
   Operator, Argo CD, Velero (all from `03-addons-reference.md`). None of
   these fill any interface Kubernetes core defined; they're ordinary
   controllers watching ordinary (custom) resources, identical in
   structure to `webapp-operator`/`greeting-operator` in this repo.
3. **Both, in the same add-on** — a CSI driver. The **node** component
   (`csi-azuredisk-node`, seen live via `aks_crd_operator/docs/qna.md`)
   implements the CSI gRPC plugin interface directly. Its **controller**
   sidecars (`external-provisioner`, `external-attacher` — not covered
   elsewhere in this repo, named here for completeness) are ordinary
   controllers watching **built-in** objects (`PersistentVolumeClaim`,
   `VolumeAttachment`) — not a CRD, since the resources they watch are
   already built in, but structurally the exact same watch → reconcile
   loop as `webapp-operator`'s `Reconcile` function. Some CSI drivers
   *also* ship their own CRDs on top (e.g. driver-specific snapshot or
   replication settings) — at that point it's genuinely all three
   mechanisms (plugin interface + built-in-object reconciliation + custom
   CRD) inside one add-on.

## Why this distinction changes how you'd debug or extend something

- Want to add a new **network policy engine**, a new **storage backend**,
  or support a new **container runtime**? You implement the relevant
  *plugin interface* — there's a spec to follow, and it has to be exactly
  right (gRPC method signatures, exec protocol shape) because Kubernetes
  core calls into it generically, with no room to improvise the contract.
- Want to add **"declare a certificate/webapp/greeting/ML training job and
  have something make it real"**? That's CRD+operator — the entire path
  this repo builds from an empty folder in `aks_crd_operator/`, no
  pre-existing interface to conform to, full freedom over the schema and
  behavior.
- **A CRD can never replace a plugin interface, and vice versa.** You
  cannot solve "Pods have no network" with an operator watching a custom
  `NetworkConfig` CRD — `kubelet` never calls out to anything except a
  real CNI plugin binary at Pod-creation time, regardless of what other
  objects exist in the cluster. And you cannot get "declare a desired
  certificate" by implementing CSI — there's no cloud-native plugin
  interface for "arbitrary custom domain objects with arbitrary
  behavior," because that's precisely the generic case CRD+operator
  exists to cover instead of Kubernetes core needing to anticipate it.

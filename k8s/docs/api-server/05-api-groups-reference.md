# 5. What API groups actually exist

`03-api-model-and-extensibility.md` explained *how* a group/version/resource
gets addressed and discovered. This is the concrete list: what groups a
stock cluster actually serves, and what lives in each one. Confirm the
current, exact list on any live cluster with:

```bash
kubectl api-resources --api-group='' -o wide     # core group only
kubectl api-versions                             # every group/version being served
```

## The core group — `""` (no group name at all)

The oldest resources predate the group/version split, so they live under
an empty group string, addressed as `/api/v1` (not `/apis/.../v1`). This is
why `apiVersion: v1` (not `<something>/v1`) is correct for these — a common
first-timer confusion when everything else in a manifest is
`<group>/<version>`.

`Pod`, `Service`, `ConfigMap`, `Secret`, `Namespace`, `Node`,
`PersistentVolume`, `PersistentVolumeClaim`, `ServiceAccount`, `Event`,
`Endpoints`.

## Workload groups

- **`apps/v1`** — `Deployment`, `ReplicaSet`, `StatefulSet`, `DaemonSet`.
  Everything that turns a Pod template into a running, self-healing set of
  Pods.
- **`batch/v1`** — `Job`, `CronJob`. Run-to-completion workloads, not
  long-running services.
- **`autoscaling/v2`** — `HorizontalPodAutoscaler`.

## Networking

- **`networking.k8s.io/v1`** — `Ingress`, `IngressClass`, `NetworkPolicy`.
  `Service` itself stays in the core group (historical — it predates this
  group existing at all) — a common surprise when you'd expect it here.
- **`discovery.k8s.io/v1`** — `EndpointSlice`, the scalable successor to
  the core group's `Endpoints` (one object could get huge on a large
  Service; `EndpointSlice` shards it).
- **`gateway.networking.k8s.io`** — Gateway API (`Gateway`, `HTTPRoute`,
  ...), the newer, more expressive alternative to `Ingress`; not installed
  by default, needs its own CRDs applied first (same CRD mechanism from
  `03-api-model-and-extensibility.md` — this whole group is itself
  "just" a widely-adopted convention shipped as CRDs, not a built-in group).

## Storage

- **`storage.k8s.io/v1`** — `StorageClass`, `VolumeAttachment`,
  `CSIDriver`, `CSINode`. What a `PersistentVolumeClaim` (core group)
  actually resolves against.
- **`snapshot.storage.k8s.io`** — `VolumeSnapshot`,
  `VolumeSnapshotClass`, `VolumeSnapshotContent` — already documented,
  including why it showed up unexplained on a real AKS `kubectl get crd`,
  in `../../aks_crd_operator/docs/qna.md`.

## Access control — covered in depth in the upcoming `rbac/` docs

- **`rbac.authorization.k8s.io/v1`** — `Role`, `RoleBinding`,
  `ClusterRole`, `ClusterRoleBinding`. The authorization stage from
  `02-request-lifecycle.md` is what actually reads these.
- **`authentication.k8s.io/v1`** — `TokenReview`, `TokenRequest` — the
  authentication stage's own supporting objects (mostly used by webhook
  authenticators and by kubelets requesting bound service-account tokens),
  not something you write RBAC rules against directly.
- **`authorization.k8s.io/v1`** — `SubjectAccessReview`,
  `SelfSubjectAccessReview` (`kubectl auth can-i` is a thin wrapper over
  this), `LocalSubjectAccessReview` — lets a client *ask* the API server
  "would this action be allowed," without attempting it.
- **`certificates.k8s.io/v1`** — `CertificateSigningRequest` — the
  cluster's own CA-signing workflow.

## Extension mechanism itself

- **`apiextensions.k8s.io/v1`** — `CustomResourceDefinition` (Option A from
  `03-api-model-and-extensibility.md`). A built-in group every cluster
  ships with, no install required — confirmed directly in
  `../../aks_crd_operator/docs/qna.md`'s very first entry.
- **`apiregistration.k8s.io/v1`** — `APIService` (Option B — the
  aggregated API server registration object).
- **`admissionregistration.k8s.io/v1`** — `MutatingWebhookConfiguration`,
  `ValidatingWebhookConfiguration` — what wires a custom admission webhook
  into the pipeline from `02-request-lifecycle.md`.

## Cluster-internal plumbing (rarely written by hand)

- **`coordination.k8s.io/v1`** — `Lease` — backs leader election
  (`kube-scheduler`/`kube-controller-manager`'s own HA, per
  `01-architecture-and-role.md`) and node heartbeats.
- **`scheduling.k8s.io/v1`** — `PriorityClass`.
- **`node.k8s.io/v1`** — `RuntimeClass`.
- **`policy/v1`** — `PodDisruptionBudget`.
- **`events.k8s.io/v1`** — the newer, structured `Event` type (the core
  group's `Event` is the legacy shape; both exist simultaneously).

## Everything else: vendor and custom groups

Every third-party operator and every CRD you've built in this repo adds
its *own* group — `webapp.platformlab.dev`, `greeting.platformlab.dev`,
`cert-manager.io`, `serving.kserve.io`, `karpenter.sh`. Same mechanism,
same discovery API, same RBAC-by-plural-name — nothing structurally
different from a built-in group once it's registered. The full
Karpenter/snapshot-CRD walkthrough (what's pre-installed on AKS
specifically vs. what this tutorial added) is in
`../../aks_crd_operator/docs/qna.md`.

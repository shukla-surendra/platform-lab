# 6. Built-in resources — the complete list

Every resource `kube-apiserver` itself ships with, organized by group (see
`05-api-groups-reference.md` for what each group is *for*). This is the
"vanilla Kubernetes" list — no cloud-provider add-ons. **Confirm the exact
set your version/distribution actually serves** with:

```bash
kubectl api-resources -o wide
```

No live cluster was available while writing this (the AKS lab in
`aks_crd_operator/` was torn down — see `aks_crd_operator/docs/qna.md`'s
cleanup entry), so treat this as the standard reference list, not a
live-confirmed one — the same honesty this repo's other conceptual docs
use. Version note: a handful of entries below (marked) are newer, still
evolving features — their exact shape can differ by Kubernetes version.

Columns: **Resource** = plural name (what RBAC/`kubectl get` use, per
`00-resources-and-objects.md`) · **Kind** = the manifest's `kind:` field ·
**Ns** = namespaced (Y) or cluster-scoped (N).

## Core group (`""`, `apiVersion: v1`)

| Resource | Kind | Ns | What it's for |
|---|---|---|---|
| `pods` | `Pod` | Y | The smallest deployable unit — one or more containers sharing network/storage. |
| `services` | `Service` | Y | Stable virtual IP + DNS name in front of a set of Pods. |
| `endpoints` | `Endpoints` | Y | The Pod IPs currently backing a Service — **legacy**, superseded by `EndpointSlice` for scale (see below). |
| `configmaps` | `ConfigMap` | Y | Non-secret key/value config, mountable into Pods. |
| `secrets` | `Secret` | Y | Same idea as `ConfigMap`, base64-encoded at rest, RBAC'd separately. |
| `namespaces` | `Namespace` | N | A virtual cluster-within-a-cluster; the unit almost every other resource is scoped by. |
| `nodes` | `Node` | N | A worker machine registered with the cluster. |
| `persistentvolumes` | `PersistentVolume` | N | A piece of real storage provisioned/registered in the cluster. |
| `persistentvolumeclaims` | `PersistentVolumeClaim` | Y | A namespaced *request* for storage, bound to a `PersistentVolume`. |
| `serviceaccounts` | `ServiceAccount` | Y | The one real, stored identity object — see `../rbac/03-identity-and-subjects.md`. |
| `events` | `Event` | Y | A log entry other objects/controllers emit (`kubectl describe` reads these) — legacy shape; `events.k8s.io/v1` is the structured successor, both exist simultaneously. |
| `replicationcontrollers` | `ReplicationController` | Y | **Legacy** predecessor to `ReplicaSet` — avoid in new manifests. |
| `limitranges` | `LimitRange` | Y | Default/min/max compute resource constraints for objects in a namespace. |
| `resourcequotas` | `ResourceQuota` | Y | Aggregate resource-consumption caps for a whole namespace. |
| `podtemplates` | `PodTemplate` | Y | A reusable Pod spec template — rarely used directly; most controllers embed their own template instead. |
| `bindings` | `Binding` | Y | Internal: how the scheduler originally assigned a Pod to a Node — not something you write by hand. |
| `componentstatuses` | `ComponentStatus` | N | **Deprecated**, always returns stale/placeholder data on modern clusters — don't rely on it. |

## Workloads

| Resource | Kind | Group | Ns | What it's for |
|---|---|---|---|---|
| `deployments` | `Deployment` | `apps/v1` | Y | Declarative rollout/rollback for a set of identical Pods, via a `ReplicaSet`. |
| `replicasets` | `ReplicaSet` | `apps/v1` | Y | Keeps N identical Pod replicas running — normally managed *by* a `Deployment`, not created directly. |
| `statefulsets` | `StatefulSet` | `apps/v1` | Y | Like a `Deployment`, but with stable per-replica identity/name and ordered rollout — for anything stateful (databases, `system_design_practice`-style distributed stores). |
| `daemonsets` | `DaemonSet` | `apps/v1` | Y | Exactly one Pod per (matching) Node — log collectors, CNI/CSI node agents (`csi-azuredisk-node` etc., seen live in `aks_crd_operator/docs/qna.md`). |
| `controllerrevisions` | `ControllerRevision` | `apps/v1` | Y | Internal: how `StatefulSet`/`DaemonSet` implement rollback history — not hand-written. |
| `jobs` | `Job` | `batch/v1` | Y | Run-to-completion Pod(s), retried on failure up to a limit. |
| `cronjobs` | `CronJob` | `batch/v1` | Y | A `Job` created on a schedule. |
| `horizontalpodautoscalers` | `HorizontalPodAutoscaler` | `autoscaling/v2` | Y | Scales a `Deployment`/`StatefulSet`'s replica count based on metrics. |

## Networking

| Resource | Kind | Group | Ns | What it's for |
|---|---|---|---|---|
| `ingresses` | `Ingress` | `networking.k8s.io/v1` | Y | HTTP(S) routing rules into Services — needs an Ingress controller installed to do anything. |
| `ingressclasses` | `IngressClass` | `networking.k8s.io/v1` | N | Which Ingress controller implementation a given `Ingress` should use. |
| `networkpolicies` | `NetworkPolicy` | `networking.k8s.io/v1` | Y | Pod-to-Pod traffic firewall rules — needs a CNI that enforces them (not all do). |
| `endpointslices` | `EndpointSlice` | `discovery.k8s.io/v1` | Y | Scalable successor to core `Endpoints` — shards a large Service's backing IPs across multiple objects. |

Gateway API (`Gateway`, `HTTPRoute`, `gateway.networking.k8s.io`) is
**not** in this list on purpose — despite being the modern, more
expressive alternative to `Ingress`, it ships as CRDs you apply yourself,
not a built-in group. Same distinction as the next section.

## Storage

| Resource | Kind | Group | Ns | What it's for |
|---|---|---|---|---|
| `storageclasses` | `StorageClass` | `storage.k8s.io/v1` | N | A named storage "profile" (provisioner + params) a `PersistentVolumeClaim` requests by name. |
| `volumeattachments` | `VolumeAttachment` | `storage.k8s.io/v1` | N | Internal: tracks a volume's attachment to a node — not hand-written. |
| `csidrivers` | `CSIDriver` | `storage.k8s.io/v1` | N | Registers a CSI storage driver's capabilities with the cluster. |
| `csinodes` | `CSINode` | `storage.k8s.io/v1` | N | Per-node info about which CSI drivers are available there. |
| `csistoragecapacities` | `CSIStorageCapacity` | `storage.k8s.io/v1` | Y | Advertises available storage capacity, for capacity-aware scheduling. |

`VolumeSnapshot`/`VolumeSnapshotClass`/`VolumeSnapshotContent`
(`snapshot.storage.k8s.io`) are **not built-in** either, despite showing up
by default on AKS — they're CRDs installed by the external-snapshotter
project, pre-applied by the cloud provider. Full walkthrough of exactly
this distinction, confirmed against a live AKS cluster:
`aks_crd_operator/docs/qna.md`.

## Access control

Covered in full depth in `../rbac/` — table here for completeness only.

| Resource | Kind | Group | Ns |
|---|---|---|---|
| `roles` | `Role` | `rbac.authorization.k8s.io/v1` | Y |
| `rolebindings` | `RoleBinding` | `rbac.authorization.k8s.io/v1` | Y |
| `clusterroles` | `ClusterRole` | `rbac.authorization.k8s.io/v1` | N |
| `clusterrolebindings` | `ClusterRoleBinding` | `rbac.authorization.k8s.io/v1` | N |
| `tokenreviews` | `TokenReview` | `authentication.k8s.io/v1` | N — no persisted objects, pure RPC (see `00-resources-and-objects.md`) |
| `selfsubjectreviews` | `SelfSubjectReview` | `authentication.k8s.io/v1` | N — "who am I," same no-persistence pattern |
| `subjectaccessreviews` | `SubjectAccessReview` | `authorization.k8s.io/v1` | N — pure RPC |
| `selfsubjectaccessreviews` | `SelfSubjectAccessReview` | `authorization.k8s.io/v1` | N — what `kubectl auth can-i` calls |
| `selfsubjectrulesreviews` | `SelfSubjectRulesReview` | `authorization.k8s.io/v1` | N — what `kubectl auth can-i --list` calls |
| `localsubjectaccessreviews` | `LocalSubjectAccessReview` | `authorization.k8s.io/v1` | Y — namespace-scoped version of `SubjectAccessReview` |
| `certificatesigningrequests` | `CertificateSigningRequest` | `certificates.k8s.io/v1` | N |

`serviceaccounts/token` (a subresource of `ServiceAccount`, not a
top-level resource) is how a bound, time-limited token is minted for a
`ServiceAccount` on demand — see `00-resources-and-objects.md`'s
subresource section for what that split means mechanically.

## Extension mechanism

| Resource | Kind | Group | Ns |
|---|---|---|---|
| `customresourcedefinitions` | `CustomResourceDefinition` | `apiextensions.k8s.io/v1` | N |
| `apiservices` | `APIService` | `apiregistration.k8s.io/v1` | N |
| `mutatingwebhookconfigurations` | `MutatingWebhookConfiguration` | `admissionregistration.k8s.io/v1` | N |
| `validatingwebhookconfigurations` | `ValidatingWebhookConfiguration` | `admissionregistration.k8s.io/v1` | N |
| `validatingadmissionpolicies` *(newer)* | `ValidatingAdmissionPolicy` | `admissionregistration.k8s.io/v1` | N — CEL-expression admission rules without writing a webhook service |
| `validatingadmissionpolicybindings` *(newer)* | `ValidatingAdmissionPolicyBinding` | `admissionregistration.k8s.io/v1` | N |

## Cluster-internal plumbing

| Resource | Kind | Group | Ns | What it's for |
|---|---|---|---|---|
| `leases` | `Lease` | `coordination.k8s.io/v1` | Y | Backs leader election (`kube-scheduler`/`kube-controller-manager` HA — see `01-architecture-and-role.md`) and node heartbeats. |
| `priorityclasses` | `PriorityClass` | `scheduling.k8s.io/v1` | N | Names a scheduling priority tier Pods can reference. |
| `runtimeclasses` | `RuntimeClass` | `node.k8s.io/v1` | N | Selects a container runtime configuration (e.g. gVisor/Kata) per Pod. |
| `poddisruptionbudgets` | `PodDisruptionBudget` | `policy/v1` | Y | Caps how many replicas of a workload voluntary disruptions (node drain, etc.) may take down at once. |
| `events` | `Event` | `events.k8s.io/v1` | Y | Structured successor to the core group's `Event` — both exist simultaneously. |
| `flowschemas` *(newer)* | `FlowSchema` | `flowcontrol.apiserver.k8s.io/v1` | N | API Priority and Fairness: classifies requests into priority levels so one noisy client can't starve the API server for everyone else. |
| `prioritylevelconfigurations` *(newer)* | `PriorityLevelConfiguration` | `flowcontrol.apiserver.k8s.io/v1` | N | The concurrency-share buckets `FlowSchema`s route into. |

## Dynamic Resource Allocation — newer, still evolving

`resource.k8s.io` — `ResourceClaim`, `ResourceClaimTemplate`,
`DeviceClass`, `ResourceSlice` — a newer mechanism (beta as of recent
Kubernetes releases) for requesting specialized hardware (GPUs, and
`fundamentals/gpu_infrastructure/phase4_kubernetes_gpu/10_gpu_scheduling_mig_sharing.md`'s
kind of use case) more expressively than the older
`nvidia.com/gpu`-style extended-resource requests. Named here without a
full table on purpose — this group's exact resource names and shape have
changed across recent Kubernetes versions; confirm against
`kubectl api-resources` on the actual cluster/version in question before
relying on any specific name.

## Everything past this point is a CRD, not built-in

Any resource not listed above — `webapps` (`webapp.platformlab.dev`,
`aks_crd_operator/`), `greetings` (`greeting.platformlab.dev/v1alpha1`),
`certificates.cert-manager.io`, `inferenceservices.serving.kserve.io`,
`nodepools.karpenter.sh` — was added via a `CustomResourceDefinition` or an
aggregated `APIService`, per `03-api-model-and-extensibility.md`. Once
registered, it's indistinguishable from a built-in resource to `kubectl`,
RBAC, or a generic client — the built-in/custom line only matters at the
point something is *installed*, never at the point it's *used*.

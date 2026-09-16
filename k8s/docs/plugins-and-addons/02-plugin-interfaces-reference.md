# 2. Plugin interfaces — the full list

Every genuine "fills in a slot Kubernetes core defined" plugin point, with
example implementations. Distinct from `03-addons-reference.md`'s broader,
looser list — everything here is a plugin by `01-first-principles.md`'s
strict definition; not everything in `03` is.

## CNI — Container Network Interface

**What it's for:** giving each Pod a working network namespace, IP address,
and routes — the thing that's missing entirely on a cluster with no CNI
installed. Not actually a Kubernetes-invented spec — CNI is a CNCF
standard kubelet happens to call into; the same plugin binaries work with
other container runtimes/orchestrators too.

**Examples:** Calico, Cilium, Flannel, Azure CNI (`network_plugin: azure`
in `aks_crd_operator/infra/main.tf`), AWS VPC CNI, Weave Net.

## CSI — Container Storage Interface

**What it's for:** dynamic volume provisioning/attach/mount for a
`PersistentVolumeClaim`, backed by whatever real storage system the driver
talks to. Also a CNCF-wide standard (works outside Kubernetes too), not
Kubernetes-specific — same pattern as CNI. Registers itself via the
built-in `CSIDriver`/`CSINode` resources from
`../api-server/06-built-in-resources-reference.md`.

**Examples, confirmed running live in this repo's own cluster**
(`aks_crd_operator/docs/qna.md`): `csi-azuredisk-node`,
`csi-azurefile-node`. Others: `aws-ebs-csi-driver`, `gce-pd-csi-driver`,
Rook/Ceph CSI, Longhorn.

## CRI — Container Runtime Interface

**What it's for:** how `kubelet` talks to whatever actually runs
containers — pull images, start/stop/inspect containers — without needing
runtime-specific code baked into `kubelet` itself.

**Examples:** `containerd` (the default on almost every current cluster,
including this repo's AKS lab and minikube), `CRI-O`. Docker Engine itself
is **not** CRI-native anymore — `dockershim` (the old in-tree shim) was
removed from `kubelet` in 1.24; running Docker-built images still works
fine (they're OCI images either way), but `kubelet` itself now always
talks CRI to `containerd` or `CRI-O`, never to the Docker daemon directly.

## Device plugins

**What it's for:** letting `kubelet` discover and allocate specialized
hardware beyond standard CPU/memory — GPUs being the overwhelming common
case (`fundamentals/gpu_infrastructure/phase4_kubernetes_gpu/10_gpu_scheduling_mig_sharing.md`
covers this in depth). A device plugin runs as a `DaemonSet`, advertises a
custom resource name (`nvidia.com/gpu`) as allocatable on nodes that have
the hardware, and Pods request it in `resources.limits` exactly like
`cpu`/`memory`.

**Examples:** NVIDIA device plugin, AMD GPU device plugin, SR-IOV device
plugin (for specialized NICs). Newer alternative for more expressive
hardware requests: Dynamic Resource Allocation
(`resource.k8s.io`, noted as still-evolving in
`../api-server/06-built-in-resources-reference.md`).

## Scheduler extension points

**What it's for:** influencing which node a Pod lands on, beyond the
built-in filter/score logic. Two generations of mechanism:

- **Scheduler Extenders** (older, HTTP webhook-based) — the scheduler
  calls out to an external HTTP service at specific points in its
  decision.
- **Scheduler Framework plugins** (current) — compiled into a custom
  scheduler binary (or the default one, rebuilt with extra plugins),
  implementing specific Go interfaces (`Filter`, `Score`, `Bind`, ...) at
  named extension points in the scheduling cycle.

**Examples:** Volcano and Koordinator (batch/gang scheduling for
ML/HPC-style workloads), `kube-scheduler` itself running with a custom
`KubeSchedulerConfiguration` enabling extra built-in plugins.

## Cloud provider interface (Cloud Controller Manager)

**What it's for:** factoring cloud-specific logic — provisioning a load
balancer for a `Service` of `type: LoadBalancer`, setting node addresses
and zone/region labels, cleaning up a Node object when the underlying VM
is deleted — out of core Kubernetes into a separate, pluggable
per-provider component. This is exactly why the AKS cluster in
`aks_crd_operator/infra/main.tf` gets a real cloud load balancer without
this repo's own operators ever writing any Azure-specific code — the CCM
handles that translation.

**Examples:** `cloud-controller-manager` variants per cloud
(`azure-cloud-controller-manager`, `aws-cloud-controller-manager`,
`cloud-provider-gcp`). Older "in-tree" cloud providers (compiled directly
into `kube-controller-manager`) are being phased out in favor of these
"out-of-tree" ones specifically so cloud-specific code doesn't have to
ship on Kubernetes' own release cadence.

## Admission webhooks — the plugin point already covered elsewhere

Mutating/validating admission (`../api-server/02-request-lifecycle.md`)
is also, formally, a plugin point — `MutatingWebhookConfiguration`/
`ValidatingWebhookConfiguration` register an external HTTP(S) service the
API server calls into during every matching request. Not repeated in full
here; see that doc.

## A different meaning entirely: `kubectl` plugins

Worth naming only to rule it out: a `kubectl` plugin (installed via
[krew](https://krew.sigs.k8s.io/)) is a client-side CLI extension — an
executable named `kubectl-foo` on your `PATH` that `kubectl foo` invokes.
It doesn't touch any cluster extension point at all; it's unrelated to
every other entry on this page except sharing the word "plugin."

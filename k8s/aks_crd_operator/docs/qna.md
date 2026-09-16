# Q&A

Running log of questions asked while working through this tutorial, answered
against the actual deployed cluster/operator (`aks-crd-lab`) wherever a
question is about live behavior rather than just the code/docs. Newest at the
bottom.

## What is a CRD? Where does it live? Why is it needed? Where does an actual object created from it live?

**What it is:** a `CustomResourceDefinition` is itself a Kubernetes object —
`apiVersion: apiextensions.k8s.io/v1, kind: CustomResourceDefinition` (a
built-in group every cluster ships with, no install required). Confirmed on
the live cluster:

```
$ kubectl get crd webapps.webapp.platformlab.dev -o jsonpath='{.apiVersion}{" "}{.kind}'
apiextensions.k8s.io/v1 CustomResourceDefinition
```

Applying one tells the API server "there's a new kind called `WebApp`, group
`webapp.platformlab.dev`, version `v1alpha1`, validated by this OpenAPI
schema."

**Where the CRD itself lives:** etcd, the cluster's key-value store, at
`/registry/apiextensions.k8s.io/customresourcedefinitions/<name>` — same
storage every Kubernetes object uses. It's cluster-scoped, not
namespaced (same category as `Namespace` or `ClusterRole`).

The moment it's applied, kube-apiserver's built-in CRD controller reads it
and dynamically opens a new REST endpoint for the kind — no restart, no
extra API server process:

```
$ kubectl get --raw /apis/webapp.platformlab.dev/v1alpha1
{"kind":"APIResourceList",...,"resources":[{"name":"webapps","kind":"WebApp","verbs":["delete","get","list","patch","create","update","watch"],...}]}
```

That dynamic REST endpoint is the whole mechanism — it's what makes
`kubectl get webapp` a real, routable request instead of an error.

**Why it's needed:** Kubernetes only ships built-in kinds (Pod, Deployment,
Service, ConfigMap, ...). Modeling your own domain object as a first-class
citizen — `kubectl get/apply/describe`, schema validation, RBAC, watch
support — needs either your own aggregated API server (heavy) or a CRD
hosted by the existing one (what this tutorial, and every real operator —
KServe, Kargo, cert-manager — does). A CRD with nothing watching it is
still valid, just inert (see
[`crds-and-operators.md`](../../k8s_explorer/docs/crds-and-operators.md)) —
registering the type and reconciling it are two separate concerns.

**Where an actual object (a custom resource, not the CRD) lives once
created:** also etcd, under the path the CRD registered — e.g.
`/registry/webapp.platformlab.dev/webapps/default/hello-webapp` for the
live one on this cluster:

```
$ kubectl get webapp hello-webapp -o jsonpath='{.apiVersion}{" "}{.kind}{" "}{.metadata.name}{" "}{.metadata.namespace}'
webapp.platformlab.dev/v1alpha1 WebApp hello-webapp default
```

No separate database — serialized into etcd exactly like a Pod spec is, and
`kubectl api-resources` now lists it as a normal resource:

```
$ kubectl api-resources | grep webapp
webapps   webapp.platformlab.dev/v1alpha1   true   WebApp
```

(`true` = `NAMESPACED`, same column a built-in `Deployment` shows). The
*only* thing that makes a `WebApp` object actually do something — create a
Deployment+Service — is the operator watching it
([`05-controller-reconcile.md`](./05-controller-reconcile.md)); storage and
behavior are separate layers.

## Given the CRD is just the schema/API registration, what is "the operator" then?

**What it is:** a normal process, running as a `Deployment` in the cluster,
built with `controller-runtime`. Nothing magic about it — it's a client of
the same API server as `kubectl`. Confirmed live:

```
$ kubectl get deploy -n webapp-operator-scaffold-system
NAME                                       READY   UP-TO-DATE   AVAILABLE
webapp-operator-scaffold-controller-manager  1/1     1            1
```

**What it does**, in `operators/webapp-operator/internal/controller/webapp_controller.go`:

1. **Watches** — `SetupWithManager` (line 165) subscribes to `WebApp`
   create/update/delete events, plus events on the `Deployment`/`Service`
   objects it owns via `Owns(...)`.
2. **Reconciles** — `Reconcile` (line 42) runs on any watched event: fetch
   the current `WebApp`, then converge reality toward
   `WebApp.Spec` (image, replicas, port).
3. **Acts** — `reconcileDeployment`/`reconcileService` (lines 77, 120) turn
   that spec into a `Deployment` + `Service` via `controllerutil.CreateOrUpdate`.
4. **Reports back** — `updateStatus` (line 148) writes observed state
   (`AvailableReplicas`) into `WebApp.Status`.
5. **Self-heals** — `SetControllerReference` makes the operator the owner of
   the Deployment/Service, so `Owns()` re-triggers reconcile if either is
   edited or deleted out-of-band, putting them back.

Confirmed end-to-end on the live cluster — one `WebApp` CR produced a real,
running `Deployment`:

```
$ kubectl get webapp -A
NAMESPACE   NAME           IMAGE                         REPLICAS   AVAILABLE
default     hello-webapp   nginxdemos/hello:plain-text   2          2

$ kubectl get pods -n default
hello-webapp-96997c959-p5vgq   1/1   Running
hello-webapp-96997c959-stkh9   1/1   Running
```

**CRD vs operator, in one line:** the CRD is the noun — "`WebApp` is now a
valid kind the API server understands." The operator is the verb — the
control loop that watches that noun and continuously turns its spec into
real cluster objects. A CRD with no operator watching it is inert (see
above); an operator with no CRD has nothing to watch.

## Give an example where a CRD is actually required — what can't be solved without one?

**Example: "I want a valid, auto-renewing TLS certificate for my app."**

**Problem requirements:**
- Request a cert from a CA (e.g. Let's Encrypt) for `myapp.example.com`
- Prove domain ownership (solve an ACME HTTP-01 or DNS-01 challenge)
- Store the resulting cert+key somewhere workloads can use it
- Watch the expiry date and renew automatically ~30 days before it lapses
- Re-issue automatically if the cert is revoked or the config changes

**Why built-in Kubernetes objects can't do this:** there is no first-class
notion of "a certificate" in the stock API. The closest built-in is a
`Secret` — but that's just an inert blob of bytes. Nothing built-in knows
how to talk to an ACME CA, knows what "expiry" means for those bytes, runs
on a schedule to check/renew, or knows how to solve a domain-ownership
challenge. You could hack it with a `CronJob` + `certbot` script, but then
"cert for `myapp.example.com`, issuer = Let's Encrypt prod, renew at 30
days" lives as untracked shell logic — not something you can
`kubectl get/describe`, GitOps, or RBAC-restrict.

**What the CRD does:** registers new kinds — `Certificate`,
`Issuer`/`ClusterIssuer` (this is cert-manager) — so the same declarative
request becomes a real object:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata: {name: myapp-cert}
spec:
  secretName: myapp-tls
  dnsNames: [myapp.example.com]
  issuerRef: {name: letsencrypt-prod, kind: ClusterIssuer}
```

On its own this object does nothing but sit in etcd — same inert-without-a-
watcher point as the `WebApp` CRD above.

**What the operator does:** cert-manager's controller watches `Certificate`
objects and, per object, talks to the ACME CA, solves the challenge, writes
the cert+key into the named `Secret`, tracks expiry, and re-runs the whole
flow before it lapses — the same reconcile-loop shape as
`webapp_controller.go`, just for certs instead of Deployments.

### Famous CRD + operator pairs

| Operator | CRDs it introduces | Manages |
|---|---|---|
| cert-manager | `Certificate`, `Issuer`, `ClusterIssuer` | TLS cert issuance/renewal |
| Prometheus Operator | `Prometheus`, `ServiceMonitor`, `PrometheusRule`, `Alertmanager` | Metrics scraping & alerting config |
| Istio | `VirtualService`, `DestinationRule`, `Gateway` | Service mesh traffic routing |
| Argo CD | `Application`, `AppProject` | GitOps continuous deployment |
| Flux | `HelmRelease`, `Kustomization`, `GitRepository` | GitOps continuous deployment |
| Crossplane | `Composition`, provider-specific managed resources (e.g. `RDSInstance`) | Provisioning cloud infra via the k8s API |
| Zalando/CrunchyData Postgres Operator | `postgresql`/`PostgresCluster` | HA Postgres (failover, backups, scaling) |
| Strimzi | `Kafka`, `KafkaTopic`, `KafkaUser` | Running Kafka clusters |
| KEDA | `ScaledObject`, `ScaledJob` | Event-driven autoscaling |
| Velero | `Backup`, `Restore`, `Schedule` | Cluster backup/restore |
| Cluster API | `Cluster`, `Machine`, `MachineDeployment` | Provisioning/managing k8s clusters themselves |
| Sealed Secrets | `SealedSecret` | Encrypted secrets safe to commit to git |
| KServe | `InferenceService` | Serving ML models |

Same pattern every time: the CRD is the declarative noun, the operator is
the loop that makes reality match it.

## Why doesn't `kubectl get all` show the CRD, the `WebApp` CR, or the operator pod?

Confirmed on the live cluster — `kubectl get all` in the `default`
namespace only showed `hello-webapp`'s Pods/Service/Deployment/ReplicaSet,
nothing else. Three separate reasons:

1. **The CRD** (`webapps.webapp.platformlab.dev`) is cluster-scoped, and
   `CustomResourceDefinition` isn't in the hardcoded list of types `get all`
   queries (same reason `Namespace` or `Node` never show up either). Needs
   `kubectl get crd`.
2. **The `WebApp` custom resource** (`hello-webapp`) is a namespaced type,
   but it's also not in that hardcoded list — `get all` only covers a fixed
   set of built-ins, not every registered API resource. Needs
   `kubectl get webapp`.
3. **The operator pod** runs in its own namespace
   (`webapp-operator-scaffold-system`), not `default`, and `get all`
   defaults to the current namespace. Needs
   `kubectl get pods -n webapp-operator-scaffold-system` (or `-A`).

Full picture in one shot: `kubectl get crd,webapp -A` plus
`kubectl get pods -A | grep operator`.

## In *this* project specifically: what was the problem, what CRD did we introduce, what does the operator do?

**The problem:** run an arbitrary containerized web app on Kubernetes,
declaratively, as "run image X, with N replicas, on port P" — one clean
object, not a pile of YAML hand-assembled and kept in sync. Without a CRD,
"run this app" is really three separate built-in objects a user must create
and maintain by hand every time:

- a `Deployment` (pod template, replica count, image)
- a `Service` (so the pods are reachable, with the right selector/port
  mapping)
- keeping both consistent with each other (same labels/selector) and
  healed if either drifts (someone edits the Deployment directly, or
  deletes the Service by accident)

Nothing built-in bundles "image + replicas + port" into a single
reviewable, `kubectl get`-able unit, and nothing watches that unit to keep
the Deployment/Service in sync with it or each other. The alternative is a
Helm chart or raw manifests applied by a human/CI pipeline — config, not a
live, continuously-enforced object in the cluster.

**The CRD introduced:** `webapp.platformlab.dev/v1alpha1, Kind=WebApp`
(`api/v1alpha1/webapp_types.go`):

```yaml
apiVersion: webapp.platformlab.dev/v1alpha1
kind: WebApp
metadata: {name: hello-webapp}
spec:
  image: nginxdemos/hello:plain-text
  replicas: 2
  port: 80
```

- **Spec** — `image` (required, no default), `replicas` (`*int32`, default
  `1`; pointer so an explicit `0` is distinguishable from "unset" —
  see [`02-crd-design.md`](./02-crd-design.md)), `port` (default `8080`,
  the container's listening port; the generated Service always exposes it
  on port 80 regardless of this value).
- **Status** — a separate subresource (`+kubebuilder:subresource:status`),
  so a user's `spec` edit and the controller's `status` write go through
  separate API endpoints and can't race/clobber each other:
  `availableReplicas` (mirrors the real Deployment) plus a standard
  `conditions` list.

Deliberately the simplest possible operator example — one CRD, no child
CRDs, no external API calls — chosen to teach the full mechanism (schema,
defaulting/validation, status, garbage collection, self-healing) without
the domain logic itself being hard.

**What the operator does** (`internal/controller/webapp_controller.go`,
walked through in detail above):

1. Watches `WebApp` objects, plus the `Deployment`/`Service` it owns.
2. On any change, reconciles: reads `WebApp.Spec`, then `CreateOrUpdate`s a
   matching `Deployment` (image, replica count, container port) and
   `Service` (port 80 → container port).
3. Sets owner references from `WebApp` → Deployment/Service, so deleting
   the `WebApp` lets Kubernetes garbage-collect both automatically (no
   finalizer needed — see the "what's out of scope" note in
   `02-crd-design.md`).
4. Writes back `status.availableReplicas` from the real Deployment's
   status.
5. Self-heals: because it `Owns()` the Deployment/Service, editing or
   deleting either out-of-band re-triggers reconcile and puts them back to
   match `spec`.

**In one line:** the problem was "declare a running web app as one object,
keep it enforced continuously" — the CRD gives that one object (`WebApp`),
the operator is the loop that turns it into, and keeps it as, a real
Deployment + Service.

## `kubectl get crd` shows other CRDs I never installed — what are they?

```
$ kubectl get crd
NAME                                             CREATED AT
aksnodeclasses.karpenter.azure.com               2026-09-16T12:55:44Z
nodeclaims.karpenter.sh                          2026-09-16T12:55:44Z
nodeoverlays.karpenter.sh                        2026-09-16T12:55:44Z
nodepools.karpenter.sh                           2026-09-16T12:55:44Z
volumesnapshotclasses.snapshot.storage.k8s.io    2026-09-16T12:53:41Z
volumesnapshotcontents.snapshot.storage.k8s.io   2026-09-16T12:53:41Z
volumesnapshots.snapshot.storage.k8s.io          2026-09-16T12:53:41Z
webapps.webapp.platformlab.dev                   2026-09-16T13:00:55Z
```

All of these except `webapps.webapp.platformlab.dev` ship pre-installed
with AKS itself — not part of this tutorial. Checked for their
controllers: `kubectl get pods -A` (see the `get all` entry above) shows no
Karpenter or snapshot-controller pod anywhere. Expected — on AKS both run
inside Azure's managed control plane, hidden from the cluster operator. You
only ever see the CRD (the API surface) and its effects, never the
controller pod, unlike `webapp-operator-scaffold-controller-manager` which
*is* visible because it's a normal in-cluster Deployment we deployed
ourselves.

**`karpenter.azure.com` / `karpenter.sh` — Node Autoprovisioning (NAP):**
Karpenter is a node-autoscaling operator; AKS's managed integration of it is
called Node Autoprovisioning. Problem it solves: when Pods are
unschedulable (no node has capacity), something needs to provision a
right-sized new VM and join it to the cluster — not just scale a fixed node
pool by a fixed VM size.

- `nodepools.karpenter.sh` — declared constraints (VM sizes/families,
  zones, taints, spot-vs-on-demand) instead of a fixed node count.
- `aksnodeclasses.karpenter.azure.com` — the Azure-specific part of a
  node's config (VM image, OS disk, networking) a `NodePool` references.
- `nodeclaims.karpenter.sh` — one object per node the operator decides to
  provision; its own bookkeeping for that VM's lifecycle.
- `nodeoverlays.karpenter.sh` — pricing/capacity adjustments layered on top
  of a `NodePool`'s decisions.

What the operator does: watches for unschedulable Pods, picks a `NodePool`
that satisfies their requirements, creates a `NodeClaim`, provisions a real
Azure VM to back it, and deprovisions nodes that go empty/underutilized —
same watch-reconcile shape as `WebAppReconciler`, just reconciling against
Azure's VM API instead of a Deployment.

**`snapshot.storage.k8s.io` — CSI volume snapshots:** the standard
Kubernetes external-snapshotter API, preinstalled so the Azure Disk/File
CSI drivers (`csi-azuredisk-node`, `csi-azurefile-node`, both visible in
`kube-system`) can support snapshotting PVCs.

- `volumesnapshotclasses` — like a `StorageClass` but for snapshots (which
  CSI driver handles them, deletion policy).
- `volumesnapshots` — the user-facing request, "snapshot this PVC now";
  namespaced, analogous to a `PersistentVolumeClaim`.
- `volumesnapshotcontents` — the actual provisioned snapshot, analogous to
  a `PersistentVolume` backing a PVC; cluster-scoped.

What the operator does: the external-snapshot-controller watches
`VolumeSnapshot` objects and calls the CSI driver to take a real
storage-level snapshot, binding it to a `VolumeSnapshotContent` — the same
PVC/PV-style two-object pattern Kubernetes already uses for volumes,
applied to point-in-time copies.

## Is "the operator" basically just a pod? And what's the actual process to create/register a CRD?

**Is the operator basically a pod?** The *running instance* of it, yes —
`webapp-operator-controller-manager` is a `Deployment` (confirmed live as
`webapp-operator-scaffold-controller-manager`, 1/1 Running) wrapping a
single container built from `Dockerfile`, running the compiled manager
binary (`main.go`, which registers `WebAppReconciler` and calls
`mgr.Start`). It talks to the API server over the network exactly like
`kubectl` does — no special hooks, no in-process access to etcd.

But "operator" as a concept is bigger than the pod: it's the whole
package — CRD schema + RBAC (ServiceAccount/ClusterRole so the pod is
*allowed* to read/write those resources) + the container image + the
Deployment running it. The pod is just the "process" part. Delete the pod
and the Deployment restarts it; scale it to 0 replicas and the CRD still
exists but goes back to being inert (same point as the "why doesn't it do
anything yet" note below).

**The actual process, from this project's own steps:**

1. **Design the schema in Go** — `api/v1alpha1/webapp_types.go`, with
   `+kubebuilder:validation:*` / `+kubebuilder:default=` marker comments.
   These markers *are* the schema — structured comments read by a
   generator, not compiled Go (`04-api-types-and-crd.md`).
2. **Scaffold the project** —
   `kubebuilder init --domain platformlab.dev --repo platformlab.dev/webapp-operator`,
   then
   `kubebuilder create api --group webapp --version v1alpha1 --kind WebApp --resource --controller`.
   Generates `go.mod`, `main.go`, the API-types stub, the controller stub,
   `config/crd/`, `config/rbac/`, `config/manager/`, and a `Makefile`
   (`03-scaffold-with-kubebuilder.md`).
3. **Generate the CRD YAML from the markers** — `make manifests` runs
   `controller-gen`, which reads the validation comments and writes
   `config/crd/bases/webapp.platformlab.dev_webapps.yaml` (a real
   `CustomResourceDefinition` manifest, OpenAPI schema included).
   `make generate` separately writes `zz_generated.deepcopy.go` — the
   `DeepCopyObject()` methods that make `WebApp` satisfy `runtime.Object`,
   required for `SchemeBuilder.Register` to even compile.
4. **Register it with the cluster** — `make install`, which is just
   `kubectl apply -f config/crd/bases/`. This is the actual "registering"
   step: the API server now accepts, validates, and stores `WebApp`
   objects. Confirmed via `kubectl get crd webapps.webapp.platformlab.dev`.
5. **Write and deploy the controller** — separate from registration.
   `make deploy` applies the RBAC plus a `Deployment` running the built
   image into `webapp-operator-system`. Only once this pod is `Running`
   does anything happen when a `WebApp` is applied.

**Order matters conceptually, not for safety:** applying a `WebApp` after
step 4 but before step 5 doesn't error — it just sits inertly in etcd, no
Deployment appears, until the operator pod starts watching
(`06-build-push-deploy.md`).

## Is Go the only way to build a CRD/operator?

**For the CRD itself: no code required at all.** A `CustomResourceDefinition`
is just a YAML manifest (`apiextensions.k8s.io/v1`) —
`kubectl apply -f` it and you're done, in any language or none.
Kubebuilder's `make manifests` only exists to *generate* that YAML from Go
marker comments instead of hand-writing the OpenAPI schema; the CRD itself
doesn't care how it was produced.

**For the operator (the watch-reconcile loop), Go is just the most
common, not the only option** — because `client-go`/`controller-runtime`
(what Kubebuilder generates against) are the most mature tooling, and
Kubernetes itself is written in Go. Real alternatives:

- **Operator SDK — Helm-based**: wraps an existing Helm chart; reconcile
  logic is "install/upgrade this chart with `spec` as values." No Go.
- **Operator SDK — Ansible-based**: reconcile logic is an Ansible playbook.
  No Go.
- **kopf** (Python) — decorator-based
  (`@kopf.on.create('platformlab.dev', 'v1alpha1', 'webapps')`), popular
  for teams already in Python/data tooling.
- **Java Operator SDK**, **Metacontroller** (language-agnostic — you write
  a webhook in any language returning desired child-object state as JSON;
  Metacontroller's own Go controller does the actual API calls).
- Even a shell script polling `kubectl get webapp -o json` in a loop
  technically works — crude, no informer caching/backoff/leader election,
  but the mechanism itself has zero hard dependency on Go.

Go dominates in practice because `controller-runtime` gives you informer
caching, work-queues, leader election, and owner-reference garbage
collection for free — reimplementing that well elsewhere is real effort.

## Install order: CRD or operator first?

**CRD first, always** — confirmed by this project's own step order
(`make install` before `make deploy` in `06-build-push-deploy.md`), and by
*why*: `controller-runtime`'s manager sets up an informer (a
`LIST`+`WATCH`) for every type in `For()`/`Owns()` at startup. If the CRD
isn't registered yet, that `LIST` call fails with "the server could not
find the requested resource" — the manager treats this as fatal and the
pod crash-loops instead of coming up cleanly.

Deploying the CRD alone first is always safe: a CRD with no operator
watching it is just inert schema (see above) — applying a `WebApp` object
at that point sits in etcd with no Deployment appearing, no error either.

## A Python operator for the same CRD, for comparison

Added [`operators/webapp-operator-python/`](../operators/webapp-operator-python)
— a [`kopf`](https://kopf.readthedocs.io/) reimplementation of
`webapp_controller.go`, reconciling the exact same
`webapp.platformlab.dev/v1alpha1 WebApp` CRD, so the two can be compared
side by side rather than in the abstract.

**Structural differences from the Go version:**

- **No CRD generation step.** `webapp_types.go` + `make manifests` doesn't
  exist on this side — kopf has no schema-from-code story; the CRD YAML
  (`config/crd/bases/webapp.platformlab.dev_webapps.yaml`, already applied
  by the Go tutorial) is reused as-is. Validation/defaulting still lives in
  the CRD, same as the Go version — Python never sees an invalid/undefaulted
  object either.
- **No code generation.** No `DeepCopyObject`/`zz_generated.deepcopy.go`
  equivalent — Python objects don't need it; `spec`/`patch` in a kopf
  handler are just dicts.
- **Ownership via `kopf.adopt()`** instead of
  `controllerutil.SetControllerReference` — same underlying mechanism
  (an `ownerReferences` entry on the Deployment/Service pointing at the
  `WebApp`), different API to set it.
- **Self-healing is the real behavioral difference.** The Go version's
  `Owns(&appsv1.Deployment{})`/`Owns(&corev1.Service{})` (`SetupWithManager`,
  `webapp_controller.go` line 165) makes drift correction *event-driven* —
  edit or delete the Deployment out-of-band and Reconcile fires
  near-instantly. `operator.py` instead uses `@kopf.timer(..., interval=30)`
  (`resync`, mirroring the same `ensure_children` logic the create/update
  handler calls) — drift gets corrected on the next tick, not instantly.
  kopf *can* watch owned resources directly for event-driven self-heal too
  (`@kopf.on.update('apps', 'v1', 'deployments', ...)`, matching the owner
  back via `ownerReferences`), but that's extra hand-written code the Go
  version gets for free from `Owns()` — the timer is the idiomatic
  kopf shortcut, traded for a ~30s worst-case healing delay.
- **No RBAC/manifest generation** — `config/rbac.yaml` here is hand-written,
  not generated from `+kubebuilder:rbac:*` markers like
  `config/rbac/role.yaml` is in the Go version.

**Biggest practical difference — how you run it while developing:** the
Python version can run directly against your local kubeconfig with zero
build/push:

```bash
cd operators/webapp-operator-python
pip install -r requirements.txt
kopf run operator.py --namespace default
```

The Go version has no equivalent fast loop — even `go run ./cmd/main`
locally still needs the CRD applied first, and shipping it to the cluster
always means `docker build` + push to ACR + `make deploy`
(`06-build-push-deploy.md`). This is the classic controller-runtime vs.
kopf tradeoff: Go gets you informer caching, leader election, and typed
compile-time safety; Python gets you a much shorter inner dev loop and no
generated code to keep in sync.

**Don't run both against the same cluster at once** — two controllers
reconciling the same `WebApp` objects will fight (each re-asserting its own
view on every reconcile). Scale the Go one to zero first:

```bash
kubectl scale deploy/webapp-operator-scaffold-controller-manager \
  -n webapp-operator-scaffold-system --replicas=0
```

## Process to deploy the Python operator

Mirrors `06-build-push-deploy.md`, but for
`operators/webapp-operator-python/`. The CRD needs no extra step — it's
already registered (`webapps.webapp.platformlab.dev`) and reused as-is;
only the controller side differs.

**1. Avoid fighting with the Go operator** (both reconcile the same
`WebApp` objects):

```bash
kubectl scale deploy/webapp-operator-scaffold-controller-manager \
  -n webapp-operator-scaffold-system --replicas=0
```

**2. Build and push the image, to the same ACR the Go tutorial uses**
(`akscrdlabacr01.azurecr.io`, confirmed via
`terraform -chdir=infra output -raw acr_login_server`):

```bash
cd operators/webapp-operator-python

export ACR_LOGIN_SERVER=akscrdlabacr01.azurecr.io
export IMG="${ACR_LOGIN_SERVER}/webapp-operator-python:v0.1.0"

docker build -t "$IMG" .
az acr login --name "${ACR_LOGIN_SERVER%%.*}"
docker push "$IMG"
```

**3. Apply RBAC, then the Deployment with the real image substituted in**
(`config/deployment.yaml` ships with a `REPLACE_ME` placeholder so the file
itself never hardcodes a registry):

```bash
kubectl apply -f config/rbac.yaml

sed "s|REPLACE_ME/webapp-operator-python:v0.1.0|$IMG|" config/deployment.yaml \
  | kubectl apply -f -
```

No `imagePullSecrets` needed — same reasoning as the Go version
(`06-build-push-deploy.md`): the AKS kubelet identity already has
`AcrPull` on this registry via `azurerm_role_assignment.aks_acr_pull` in
`infra/main.tf`.

**4. Verify:**

```bash
kubectl get pods -n webapp-operator-python-system
kubectl logs -n webapp-operator-python-system deploy/webapp-operator-python -f
kubectl get webapp hello-webapp -o yaml   # status.availableReplicas should stay populated
kubectl delete deploy hello-webapp        # self-heal check -- Go heals instantly,
                                           # this one heals within 30s (the resync timer)
```

**5. Roll back to the Go operator afterward:**

```bash
kubectl delete -f config/rbac.yaml -f config/deployment.yaml
kubectl scale deploy/webapp-operator-scaffold-controller-manager \
  -n webapp-operator-scaffold-system --replicas=1
```

## Process to install someone else's existing operator — KServe as the example

Different shape entirely from the two operators above: no Go/Python code to
write, no image to build — you're installing *someone else's* published
CRDs + controller, via Helm. Verified against KServe's own docs
(`v0.20.0`, kserve.github.io) rather than assumed:

**1. Pick a deployment mode first — it determines the dependency list:**
- **Standard/RawDeployment** — `InferenceService` becomes a plain
  Deployment + Service (+ optional HPA), using only base Kubernetes
  primitives. Fewer dependencies.
- **Knative/Serverless** — adds scale-to-zero and request-based
  autoscaling, but requires a service mesh/ingress underneath.

**2. Install dependencies** (both modes need cert-manager, for the
CRDs' conversion/validation webhook certs — same reason `02-crd-design.md`
gives for preferring CRD-schema validation over webhooks where possible;
KServe's webhooks are the case where a schema alone isn't enough):

```bash
# Standard mode — cert-manager only:
curl -fsSL https://github.com/kserve/kserve/releases/download/v0.20.0/kserve-standard-mode-dependency-install.sh | bash

# Knative/Serverless mode — cert-manager + Istio + Knative Serving:
curl -fsSL https://github.com/kserve/kserve/releases/download/v0.20.0/kserve-knative-mode-dependency-install.sh | bash
```

cert-manager `v1.17.0+` is required either way; Knative mode additionally
needs Istio `1.27.1` and Knative Serving `1.21.1` (Istio provides the
mesh/ingress — not Envoy Gateway, in KServe's current docs).

**3. Install the CRDs, then the controller — same two-phase order as
every operator in this doc (CRD before controller):**

```bash
helm install kserve-crd oci://ghcr.io/kserve/charts/kserve-crd \
  --version v0.20.0 --namespace kserve --create-namespace

helm install kserve-resources oci://ghcr.io/kserve/charts/kserve-resources \
  --version v0.20.0 --namespace kserve \
  --set kserve.controller.deploymentMode=Standard \
  --wait
```

(`deploymentMode=Knative` instead, if that path was chosen in step 1.)

**4. Verify — same pattern used throughout this doc:**

```bash
kubectl get crd | grep serving.kserve.io   # InferenceService, ServingRuntime,
                                            # ClusterServingRuntime, TrainedModel, ...
kubectl get pods -n kserve                 # the controller-manager Deployment
```

**Compare to this project's own install (`06-build-push-deploy.md`):**
conceptually identical two-phase order (CRD, then controller) and the same
reason a CRD alone isn't enough (inert without a watcher) — but here
neither phase is something you wrote: `helm install` replaces
`make install`/`make deploy`, and the image was built and published by the
KServe maintainers, not by `docker build` against a local `Dockerfile`.

Sources:
- [KServe Installation](https://kserve.github.io/website/docs/next/install/kserve-install)
- [KServe Dependencies](https://kserve.github.io/website/docs/next/install/dependencies)

## Deploying `greeting-operator` for real: two surprises kopf didn't warn about

Built, pushed, and installed `operators/greeting-operator` against the live
cluster (build → ACR push → `kubectl apply -f config/rbac.yaml` → apply
`config/deployment.yaml` with the image substituted in — same steps as
`webapp-operator-python`'s deploy section above). Two things came up that
weren't obvious from the kopf docs or from writing the code:

**1. kopf needs `watch` (not just `get`/`list`) on `customresourcedefinitions`,
cluster-wide.** First boot logged a tight retry loop:

```
APIForbiddenError('customresourcedefinitions.apiextensions.k8s.io is
forbidden: ... cannot watch resource "customresourcedefinitions" ...')
```

`config/rbac.yaml` in both this project and `webapp-operator-python` only
granted `["get", "list"]` on that resource — reasonable-looking, since the
operator never touches other CRDs, but kopf watches CRDs cluster-wide on
its own initiative (it tracks CRD schema changes to keep its internal
resource registry current). Fixed in both operators'
`config/rbac.yaml` by adding `"watch"` to that rule. This has no Go-side
equivalent to compare against — `controller-runtime` doesn't watch CRDs
itself, only the specific kinds you register with `For()`/`Owns()`.

**2. kopf silently adds its own finalizer to every resource it manages,**
regardless of whether an `@kopf.on.delete` handler is defined. Confirmed
live:

```
$ kubectl get greeting alice -o jsonpath='{.metadata.finalizers}'
["kopf.zalando.org/KopfFinalizerMarker"]
```

This directly contradicts the "no finalizer needed" reasoning
`greeting-operator/README.md` borrowed from the Go version's
`02-crd-design.md` — that reasoning is still correct for what *this
project's own code* needs (garbage collection handles the owned
`ConfigMap` fine via the ownerReference), but it doesn't mean no finalizer
exists on the object. kopf adds its own regardless, as a safety mechanism
so a delete event isn't missed if the operator pod happens to be down at
the exact moment `kubectl delete` runs. Practical implication: **a
`Greeting` (or `WebApp`, on the Python operator) won't actually finish
deleting while the operator pod is down** — `kubectl delete` hangs at
`Terminating` until kopf's own process comes back up and removes its
finalizer, which the Go version never does (its finalizer-free design
means deletion always completes via Kubernetes GC alone, operator running
or not).

**End-to-end confirmation, live:**

```
$ kubectl apply -f config/samples/greeting_sample.yaml
$ kubectl get configmap alice-greeting -o jsonpath='{.data.greeting}'
Hello, Alice! Welcome to the cluster.

$ kubectl delete configmap alice-greeting
$ sleep 35   # past the 30s resync timer
$ kubectl get configmap alice-greeting -o jsonpath='{.data.greeting}'
Hello, Alice! Welcome to the cluster.
```

Reconcile-on-create and timer-based self-heal both work as designed.

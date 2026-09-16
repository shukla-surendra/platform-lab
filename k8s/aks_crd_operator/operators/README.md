# Operators

Every operator implementation built in this tutorial, kept side by side on
purpose so they can be compared directly instead of only in the abstract.
Background and design decisions live in [`../docs/qna.md`](../docs/qna.md)
and [`../docs/02-crd-design.md`](../docs/02-crd-design.md); this file is
just "what is each one, and how does it actually work internally."

| Operator | CRD it reconciles | Language / framework | Self-heal mechanism | Status |
|---|---|---|---|---|
| [`webapp-operator/`](./webapp-operator) | `WebApp` (image, replicas, port → Deployment+Service) | Go, Kubebuilder + `controller-runtime` | Event-driven (`Owns()`) | Complete, deployed |
| [`webapp-operator-python/`](./webapp-operator-python) | Same `WebApp` CRD | Python, `kopf` | 30s polling timer | Complete, for comparison |
| [`greeting-operator/`](./greeting-operator) | `Greeting` (name, message → ConfigMap) | Python, `kopf` | 30s polling timer | Complete, awaiting test run |

## `webapp-operator/` — Go, Kubebuilder, `controller-runtime`

**Internal tech:** scaffolded with `kubebuilder create api`, built on
`sigs.k8s.io/controller-runtime`'s `Manager`/`Reconciler` pattern. The CRD's
OpenAPI schema is *generated*, not hand-written — `+kubebuilder:validation:*`
and `+kubebuilder:default=` comments on the Go struct
(`api/v1alpha1/webapp_types.go`) are read by `controller-gen` (`make
manifests`) and compiled into `config/crd/bases/webapp.platformlab.dev_webapps.yaml`.
`make generate` additionally writes `zz_generated.deepcopy.go` — the
`DeepCopyObject()` methods required for `WebApp` to satisfy `runtime.Object`.

**How it works** (`internal/controller/webapp_controller.go`):
1. `SetupWithManager` registers a watch on `WebApp` plus `Owns(&Deployment{})`
   and `Owns(&Service{})` — the manager sets up informer caches for all
   three and re-queues a reconcile whenever any of them changes.
2. `Reconcile` fetches the current `WebApp`, then calls
   `reconcileDeployment`/`reconcileService`, each using
   `controllerutil.CreateOrUpdate` to converge a child object toward
   `WebApp.Spec` (image, replica count, container port).
3. `controllerutil.SetControllerReference` sets an owner reference from
   each child back to the `WebApp` — this is what makes `Owns()`'s watch
   fire on child drift, and what lets Kubernetes garbage-collect both
   children automatically when the `WebApp` is deleted (no finalizer
   needed).
4. `updateStatus` reads the real Deployment's `status.availableReplicas`
   and writes it to `WebApp.Status` via the `status` subresource, so a
   user's `spec` edit and the controller's `status` write never race.

**Deploy:** `make manifests`/`generate` → `make install` (registers the
CRD) → `docker build`/`push` to ACR → `make deploy` (RBAC + a `Deployment`
running the image, into `webapp-operator-system`). Full walkthrough:
[`../docs/06-build-push-deploy.md`](../docs/06-build-push-deploy.md).

## `webapp-operator-python/` — Python, `kopf`

**Internal tech:** [`kopf`](https://kopf.readthedocs.io/) plus the plain
`kubernetes` Python client. No scaffolding tool, no code generation —
`operator.py` is one file. Reconciles the *same* `WebApp` CRD the Go
operator does, reusing its already-applied schema; kopf has no
schema-from-code story, so there's nothing here equivalent to
`webapp_types.go`.

**How it works** (`operator.py`):
1. `@kopf.on.create` / `@kopf.on.update` / `@kopf.on.resume` decorators
   register handlers for the `webapp.platformlab.dev/v1alpha1 webapps`
   resource — kopf's own watch loop calls `reconcile(...)` on each event.
2. `reconcile` delegates to `ensure_children`, which builds a
   `V1Deployment`/`V1Service` from `spec` and applies each via
   `create_namespaced_*` (falling back to `patch_namespaced_*` on a 409
   conflict) — the hand-rolled equivalent of `CreateOrUpdate`.
3. `kopf.adopt(...)` sets the owner reference on each child, same purpose
   as `SetControllerReference` in the Go version.
4. `patch.status["availableReplicas"]` is set from the real Deployment's
   status — kopf commits `patch` back to the object's `status` subresource
   after the handler returns.
5. **Self-heal is the real behavioral difference from the Go version:**
   there's no direct equivalent of `Owns()` wired up here. Instead,
   `@kopf.timer(..., interval=30)` re-runs `ensure_children` every 30
   seconds regardless of whether anything changed — drift gets corrected
   on the next tick, not instantly. (kopf *can* watch owned resources
   directly for event-driven self-heal — `@kopf.on.update('apps', 'v1',
   'deployments', ...)`, matching the owner back via `ownerReferences` —
   but that's extra hand-written code the Go version gets for free from
   `Owns()`.)

**Deploy:** no CRD step (reused). `docker build`/`push` → `kubectl apply -f
config/rbac.yaml` → `kubectl apply -f config/deployment.yaml` (image
substituted in), into `webapp-operator-python-system`. Full walkthrough:
[`../docs/qna.md`](../docs/qna.md) ("Process to deploy the Python
operator"). Can also run directly against a local kubeconfig with zero
build/push: `kopf run operator.py --namespace default` — the fast inner
dev loop the Go version has no equivalent of.

**Don't run this at the same time as `webapp-operator/`** — both reconcile
the same `WebApp` objects and will fight each other.

## `greeting-operator/` — Python, `kopf`

A second, smaller CRD built from scratch by hand, on purpose smaller than
`WebApp`: one CRD field in (`spec.name`), one owned child object out (a
`ConfigMap`, not a Deployment+Service pair), no external API calls. Full
problem statement and CRD design: [`greeting-operator/README.md`](./greeting-operator/README.md).

**Internal tech:** same as `webapp-operator-python/` — `kopf` + the plain
`kubernetes` client, no scaffolding, no code generation. The CRD
([`config/crd/greeting-crd.yaml`](./greeting-operator/config/crd/greeting-crd.yaml))
is hand-written OpenAPI, registering `greeting.platformlab.dev/v1alpha1,
Kind=Greeting` with `spec.name` (required), `spec.message` (defaulted
template), and a `status` subresource (`configMapName`,
`observedGeneration`).

**How it works** (`operator.py`):
1. `@kopf.on.create`/`update`/`resume` watch `Greeting` objects and call
   `ensure_child`.
2. `ensure_child` renders `spec.message` (`{name}` → `spec.name`) and
   applies a `V1ConfigMap` named `<greeting-name>-greeting` via
   `create_namespaced_config_map`, falling back to a patch on a 409.
3. `kopf.adopt(cm)` sets the owner reference (no finalizer needed).
4. `patch.status["configMapName"]`/`["observedGeneration"]` get written
   back every reconcile.
5. Self-heal: `@kopf.timer(..., interval=30)` re-runs `ensure_child` every
   30 seconds — same polling tradeoff as `webapp-operator-python/`.

**Try it:** [`greeting-operator/README.md`](./greeting-operator/README.md#try-it)
has the install/run/test/deploy steps.

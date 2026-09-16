# 2. CRD design

Ties back to the pattern in
[`k8s_explorer/docs/crds-and-operators.md`](../../k8s_explorer/docs/crds-and-operators.md#the-pattern):
a CRD is schema registered with the API server so a new `kind` gets
`kubectl get/apply/describe` support like any built-in type; a controller is
what actually does something when one of those objects changes. This doc is
about the first half — designing the schema — before step 3 scaffolds it and
step 5 writes the controller.

## The resource: `WebApp`

`webapp.platformlab.dev/v1alpha1, Kind=WebApp` — one object standing in for
"run this container image, this many replicas, on this port," with the
operator creating the Deployment and Service underneath. Deliberately the
simplest possible operator example: no child CRDs, no multi-resource
orchestration, no external API calls — just enough surface to show every part
of the mechanism (schema, defaulting, validation, status, garbage collection,
self-healing) without the example itself being the hard part.

## API group naming

`webapp.platformlab.dev` — Kubernetes convention is `<subject>.<your-domain>`,
reversed-DNS style, so it can't collide with any built-in group (`apps`,
`batch`, ...) or another vendor's CRDs (`serving.kserve.io`,
`promotion.kargo.akuity.io`). `platformlab.dev` doesn't need to be a real
registered domain for a lab cluster — it only needs to be unique within
*this* cluster.

## Spec fields

| Field      | Type    | Required | Default | Why |
|------------|---------|----------|---------|-----|
| `image`    | string  | yes      | —       | No sane default for what to run. |
| `replicas` | `*int32`| no       | `1`     | Pointer, not `int32` — see below. |
| `port`     | int32   | no       | `8080`  | The container's listening port; the managed Service always exposes it on port 80 regardless of what this is. |

**Why `replicas *int32` and not `int32`:** a plain `int32` can't distinguish
"the user explicitly asked for 0 replicas" from "the user didn't set this
field at all" — both read back as the zero value. A pointer lets the
controller tell the two apart, which matters once you add validation or
defaulting logic (`+kubebuilder:default=1` in `webapp_types.go` handles the
common case, but the pointer is what makes an explicit `replicas: 0`
distinguishable and honored).

## Status fields

`status.availableReplicas` (mirrors the managed Deployment's own
`status.availableReplicas`) and a `status.conditions` list following the
standard Kubernetes condition shape (`type`, `status`, `reason`, `message`,
`lastTransitionTime`) — the same shape `kubectl describe` renders for
Deployments and Pods, so `kubectl describe webapp hello-webapp` looks
familiar rather than inventing a new status vocabulary.

Status is a separate **subresource** (`+kubebuilder:subresource:status` in
`webapp_types.go`) — meaning `kubectl edit webapp/hello-webapp` (which edits
`spec`) and the controller's `r.Status().Update(...)` (which edits `status`)
go through separate API endpoints and can't stomp on each other's writes.
Skipping this marker is a common first-operator bug: without it, a user's
`spec` edit and the controller's `status` write race on the same object
version and one silently loses.

## What's out of scope here

- **Webhooks** (validating/mutating admission, defaulting via webhook
  instead of CRD defaults) — see
  [`k8s_explorer/practice/admission-webhook-demo`](../../k8s_explorer/practice/admission-webhook-demo)
  for that mechanism on its own; this tutorial relies on
  `+kubebuilder:default` / `+kubebuilder:validation` markers instead, which
  cover the common cases without a second running component.
- **Multiple API versions** (`v1alpha1` → `v1beta1` conversion) — realistic
  operators eventually need this; a single version is enough to learn
  Reconcile.
- **Finalizers** — not needed here because the Deployment/Service are owned
  resources cleaned up by Kubernetes garbage collection (step 5 explains the
  owner-reference wiring). A finalizer only earns its keep when cleanup needs
  to reach something Kubernetes GC can't delete for you — an external cloud
  resource, a record in some other system.

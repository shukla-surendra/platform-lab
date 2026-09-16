# 4. API types and the generated CRD

Walking through
[`api/v1alpha1/webapp_types.go`](../operators/webapp-operator/api/v1alpha1/webapp_types.go)
piece by piece, and what each part turns into once `make manifests` runs
(step 3).

## The markers are the schema

```go
// +kubebuilder:validation:Required
// +kubebuilder:validation:MinLength=1
Image string `json:"image"`
```

`controller-gen` reads these comments and emits the matching OpenAPI v3
schema fragment inside the generated CRD:

```yaml
image:
  type: string
  minLength: 1
properties: {...}
required: ["image"]
```

This is why `kubectl apply -f config/samples/webapp_v1alpha1_webapp.yaml`
with `image` missing or empty fails at the API server, before any
controller code ever runs — validation lives in the CRD, not in Reconcile.
Put validation here whenever possible; only fall back to webhook validation
(out of scope for this tutorial, see `02-crd-design.md`) for rules an
OpenAPI schema literally can't express, like cross-field constraints.

## Defaulting

```go
// +kubebuilder:default=1
Replicas *int32 `json:"replicas,omitempty"`
```

Also enforced at the API server: `kubectl apply` an object with no
`replicas` field and `kubectl get -o yaml` it back — `spec.replicas: 1` is
already there, filled in server-side, before Reconcile ever sees the object.
The controller's own `if webApp.Spec.Replicas != nil` check
(`webapp_controller.go`) is a second line of defense for objects that
existed before this default was added to the CRD, not the primary
mechanism.

## The `+kubebuilder:object:root=true` / `+kubebuilder:subresource:status` pair

```go
// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
type WebApp struct { ... }
```

`object:root=true` marks `WebApp` as a real top-level API type (triggers
DeepCopy generation via `make generate`); `subresource:status` splits
`status` onto its own API endpoint, as covered in `02-crd-design.md`. Both
markers together are what make `WebApp` behave like a first-class built-in
type instead of an inert blob of YAML.

## Printer columns

```go
// +kubebuilder:printcolumn:name="Available",type=integer,JSONPath=`.status.availableReplicas`
```

Controls what `kubectl get webapp` shows beyond the default `NAME`/`AGE` —
this is why step 7's `kubectl get webapp hello-webapp` output includes an
`AVAILABLE` column reading straight from `status.availableReplicas` without
a `-o yaml` round trip.

## Reading the generated CRD

After `make manifests` (step 3):

```bash
cat config/crd/bases/webapp.platformlab.dev_webapps.yaml
```

Confirm `spec.versions[0].schema.openAPIV3Schema.properties.spec.properties.image.minLength`
is `1` and `.required` contains `image` — that's the marker comment above,
compiled. Once applied to the cluster (step 6), the same thing
`k8s_explorer/docs/crds-and-operators.md`'s "Checking what's installed"
section describes works here too:

```bash
kubectl get crd webapps.webapp.platformlab.dev -o jsonpath='{.spec.group}/{.spec.versions[0].name} {.spec.names.kind}'
```

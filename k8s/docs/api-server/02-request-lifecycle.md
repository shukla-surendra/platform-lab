# 2. Request lifecycle

Every request — `kubectl apply`, a controller's `client.Update(...)`, an
`InferenceService` being created — goes through the same fixed pipeline
before anything is written to etcd:

```
 request
    │
    ▼
┌───────────────┐     who are you?
│ Authentication │     (cert, bearer token, OIDC, webhook)
└───────┬───────┘
        ▼
┌───────────────┐     are you allowed to do THIS verb on THIS resource?
│ Authorization  │     (RBAC, Node, Webhook, ...)
└───────┬───────┘
        ▼
┌───────────────────┐   mutate the object (defaults, sidecar injection, ...)
│ Mutating Admission │
└───────┬───────────┘
        ▼
┌────────────────┐   validate against the OpenAPI schema (from the CRD or
│ Schema          │   built-in type) — required fields, min/max, enums
│ validation      │
└───────┬────────┘
        ▼
┌─────────────────────┐   reject the object if it fails a policy
│ Validating Admission │   (can't see the mutating stage's changes twice —
└───────┬─────────────┘   this stage runs on the already-mutated object)
        ▼
┌───────────────┐
│  Persist to    │   writes to etcd; only step that actually changes state
│  etcd          │
└───────┬───────┘
        ▼
┌───────────────┐
│  Notify        │   anyone watching this resource gets the event
│  watchers      │
└───────────────┘
```

## Authentication — "who are you?"

The API server supports several methods simultaneously (tried in order,
first one that succeeds wins): client certificates, static bearer tokens,
[OIDC](https://kubernetes.io/docs/reference/access-authn-authz/authentication/#openid-connect-tokens)
tokens (what most managed clusters wire up for human `kubectl` users via
`az aks get-credentials` / `aws eks update-kubeconfig`), and webhook token
authentication (delegate the decision to an external service). The result
of this stage is just an identity — a username and group memberships —
nothing about permissions yet.

A `ServiceAccount` (what every Pod running in-cluster authenticates as,
including this repo's `webapp-operator`/`greeting-operator` pods via their
mounted token) is one specific case of bearer-token auth: the kubelet
mounts a token tied to that `ServiceAccount` into the Pod automatically.

## Authorization — "are you allowed to do this?"

Given an identity, is `<verb>` (`get`/`list`/`watch`/`create`/`update`/
`patch`/`delete`) on `<resource>` (e.g. `greetings`) allowed? The mode
almost every cluster uses is **RBAC** — this is exactly the `ClusterRole`/
`ClusterRoleBinding`/`ServiceAccount` triad every operator in
`aks_crd_operator/operators/*/config/rbac.yaml` sets up. Authorization
always matches on the resource's **plural name** (`resources: ["greetings"]`),
never its `kind` — see `aks_crd_operator/docs/qna.md`'s naming-convention
entry for why RBAC and the CRD's own `spec.names.plural` line up this way.

`Node` authorization is a second mode running alongside RBAC specifically
for kubelets — restricting each kubelet to only the objects relevant to
pods scheduled on its own node.

## Admission control — mutating, then validating

Admission plugins run as a chain, in two ordered phases:

1. **Mutating admission** — can modify the object before it's stored.
   Built-in examples: setting a default `ServiceAccount`, injecting a
   sidecar. Custom mutating webhooks (`MutatingWebhookConfiguration`) are
   how tools like Istio inject their sidecar container.
2. **Validating admission** — can only accept or reject, never modify.
   Runs *after* mutation, so it validates the final, already-mutated
   object. Custom validating webhooks (`ValidatingWebhookConfiguration`)
   are how cert-manager and KServe enforce rules an OpenAPI schema can't
   express (cross-field constraints, checking a referenced object exists).

Schema validation/defaulting (`+kubebuilder:validation:*` /
`+kubebuilder:default=` markers compiled into a CRD's OpenAPI schema — see
`aks_crd_operator/docs/04-api-types-and-crd.md`) happens as part of this
pipeline too, but it's enforced directly against the CRD's schema, not via
a webhook — which is why an invalid `WebApp` (`image` missing) is rejected
before any admission webhook or controller ever sees it. Prefer schema
validation over a validating webhook whenever the rule is expressible that
way: one less running component, one less network hop, one less thing that
can be down when you need to `kubectl apply`.

## Persistence and notification

Once past admission, the object is written to etcd (`/registry/<group>/
<resource>/<namespace>/<name>` — see the etcd-path examples in
`aks_crd_operator/docs/qna.md`'s first entry) and the API server fans the
change out to every open watch on that resource — see
[`04-watch-and-list.md`](./04-watch-and-list.md) for that mechanism.

## Where this shows up in this repo

- `webapp-operator`'s `+kubebuilder:rbac:*` markers (`webapp_controller.go`)
  compile into exactly the `ClusterRole` rules this pipeline's
  authorization stage checks.
- The RBAC bug found while deploying `greeting-operator` live (kopf needing
  `watch` on `customresourcedefinitions`, not just `get`/`list` —
  `aks_crd_operator/docs/qna.md`) is a direct, concrete instance of the
  authorization stage rejecting a request: the 403 response came straight
  from this stage, before admission or etcd were ever reached.

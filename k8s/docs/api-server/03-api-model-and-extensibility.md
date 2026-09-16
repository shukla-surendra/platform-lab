# 3. API model and extensibility

## Group / Version / Resource (GVR)

Every kind the API server serves is addressed by three coordinates:

- **Group** — a namespace for the API itself (`apps`, `batch`, `""` for the
  legacy "core" group holding `Pod`/`Service`/`ConfigMap`, or a custom
  reversed-DNS group like `webapp.platformlab.dev`).
- **Version** — `v1`, `v1beta1`, `v1alpha1`, ... A group can serve multiple
  versions of the same kind simultaneously (conversion webhooks translate
  between them — out of scope for the single-version CRDs in this repo,
  noted explicitly as "out of scope" in `aks_crd_operator/docs/02-crd-design.md`).
- **Resource** — the plural name (`deployments`, `webapps`, `greetings`) —
  this is what RBAC and the REST path both address, per
  `02-request-lifecycle.md`'s authorization section.

This is why every manifest starts with `apiVersion: <group>/<version>` and
`kind: <Kind>` — `apiVersion` alone is group+version; `kind` maps to the
resource (plural) via the CRD's `spec.names.kind` → `spec.names.plural`
mapping (or the equivalent built-in registration for core types).

## The discovery API

The API server exposes what it can currently serve, discoverable at
runtime rather than requiring every client to hardcode a list:

```
GET /api                                 -> versions of the core (legacy) group
GET /apis                                -> every non-core group
GET /apis/<group>/<version>               -> the resources in that group/version
```

Confirmed against a live cluster in `aks_crd_operator/docs/qna.md`'s first
entry:

```
$ kubectl get --raw /apis/webapp.platformlab.dev/v1alpha1
{"kind":"APIResourceList",...,"resources":[{"name":"webapps","kind":"WebApp",...}]}
```

`kubectl api-resources` is just a formatted client-side view over this
same discovery data. Applying a CRD doesn't require restarting
`kube-apiserver` precisely because discovery is served dynamically — the
built-in CRD controller (part of `kube-apiserver` itself) watches
`CustomResourceDefinition` objects and updates what discovery reports the
instant one is applied.

## Two ways to add a new kind

### Option A: CustomResourceDefinition (CRD)

What every operator in this repo uses. You register a
`CustomResourceDefinition` object; `kube-apiserver`'s own built-in CRD
controller reads it and dynamically opens a REST endpoint, backed by the
*same* etcd and the *same* generic REST handler every built-in type uses.
No new process, no new binary — see `aks_crd_operator/docs/qna.md`'s first
entry for the full walkthrough (etcd path, discovery entry, `kubectl get`
becoming a real request).

Trade-off: you get storage, validation, RBAC, `kubectl` support, and
watch/list for free, but the API server has no idea what a `Greeting` or a
`WebApp` *means* — that's what an operator (a separate watching client) is
for, per `01-architecture-and-role.md`.

### Option B: Aggregated API server (`APIService`)

Instead of describing a schema and letting the existing `kube-apiserver`
serve it, you run your **own** API server process implementing the
Kubernetes API conventions, and register it via an `APIService` object.
`kube-apiserver` then *proxies* matching requests to your server instead of
handling them itself — your server can back its data with anything (its
own database, a live call to another system), not just etcd.

`aks_crd_operator/docs/qna.md`'s CRD entry already frames this trade-off:
"Modeling your own domain object as a first-class citizen ... needs either
your own aggregated API server (heavy) or a CRD hosted by the existing one
(what this tutorial, and every real operator ... does)." `metrics-server`
(behind `kubectl top`) is the most common real-world aggregated API server
you'll actually run into — it doesn't store metrics in etcd; it's serving
live data on request, which a CRD (etcd-backed by design) can't do.

**Rule of thumb:** reach for a CRD by default — it's what every operator in
this repo does, and it's what covers `Greeting`, `WebApp`, and the vast
majority of real controllers (cert-manager, KServe, Prometheus Operator —
see the CRD/operator table in `aks_crd_operator/docs/qna.md`). Reach for an
aggregated API server only when the data genuinely can't live in etcd —
live metrics being the canonical case.

## The `categories` field, and `kubectl get all`

One `spec.names` field neither `WebApp` nor `Greeting` sets:
`categories: ["all"]`. This is the actual mechanism behind whether
`kubectl get all` lists a custom resource — `get all` isn't special-casing
built-in types, it queries every registered resource whose `categories`
includes `all`. Full walkthrough, including why the CRD, the custom
resource, *and* the operator pod all stayed invisible to `kubectl get all`
for three separate reasons, in `aks_crd_operator/docs/qna.md`.

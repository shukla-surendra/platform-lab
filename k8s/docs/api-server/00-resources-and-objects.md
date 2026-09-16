# 0. Resources and objects

Two words used constantly and often interchangeably in casual conversation
("a `Pod` resource," "a `Pod` object") but which mean genuinely different
things. Every other doc in this folder assumes the distinction, so it goes
first.

## Resource — the type; the API endpoint

A **resource** is an endpoint the API server exposes for a particular kind
of thing — what `03-api-model-and-extensibility.md` addresses by
Group/Version/Resource. `pods` is a resource. `deployments` is a resource.
`webapps` (once `aks_crd_operator`'s CRD is applied) is a resource. A
resource is the *type*, not any specific instance of it — the same
distinction as a class vs. an instance of that class in any OOP language.

A resource is defined by:
- the verbs it supports (`get`, `list`, `watch`, `create`, `update`,
  `patch`, `delete` — not every resource supports every verb, see
  "resources with no persisted objects" below),
- a schema (OpenAPI, from a built-in Go type or a CRD's
  `spec.versions[].schema` — see `aks_crd_operator/docs/04-api-types-and-crd.md`),
- and RBAC rules always matching against it by its **plural** name
  (`resources: ["webapps"]`) — never by `kind` — exactly as
  `aks_crd_operator/docs/qna.md`'s naming-convention entry lays out.

`kubectl api-resources` lists exactly this: every resource the cluster
currently serves, not every object that currently exists.

## Object — a specific, persisted instance

An **object** is one particular instance of a resource, identified by
`namespace` (if namespaced) + `name`, persisted in etcd. `pods` is the
resource; the specific Pod named `hello-webapp-96997c959-p5vgq` running in
`default` right now is an object. Applying the same manifest twice with the
same name updates one object; changing the name creates a second, distinct
object of the same resource.

Every object, built-in or custom, shares the same top-level shape:

```yaml
apiVersion: apps/v1        # which resource's schema/version this is
kind: Deployment           # human-facing type name (maps to the resource's plural)
metadata:                  # identity + bookkeeping: name, namespace, uid,
  name: hello-webapp        # resourceVersion, labels, annotations,
  namespace: default         # ownerReferences, creationTimestamp, ...
spec:                       # desired state -- what you (or a controller) want
  replicas: 2
status:                     # observed state -- written back by a controller,
  availableReplicas: 2       # never by the person who created the object
```

`spec` vs. `status` is the same split covered in
`aks_crd_operator/docs/02-crd-design.md`'s "Status fields" section: a
person or a higher-level controller writes `spec`; the controller that
owns this resource writes `status`, through a separate `status`
subresource endpoint precisely so those two writers can't race each other.
`WebApp` and `Greeting` (this repo's own CRDs) both follow this shape
exactly — `spec.image`/`spec.name` alongside `status.availableReplicas`/
`status.configMapName`.

## Where "resource" and "object" stop lining up 1:1

**Subresources** are still part of one object, but exposed as their own
resource endpoint — `pods/log`, `pods/status`, `webapps/status`. Fetching
`pods/log` doesn't return a second object; it's a different *view* into
the same Pod object's data (or, for `/status`, a separately-authorizable
write path into one field of it). This is why RBAC lists `webapps/status`
as its own line in `config/rbac.yaml` alongside `webapps` — same object,
two resource endpoints, independently authorizable.

**Some resources have no persisted objects at all.** `TokenReview`,
`SubjectAccessReview` (both listed in `05-api-groups-reference.md`) are
resources you `POST` to and get a computed response back — nothing is
written to etcd, nothing shows up in a `list`. They exist purely as
RPC-shaped endpoints riding on the same REST conventions (`kubectl auth
can-i` is a thin client over exactly this). A resource is a promise about
*verbs and schema*; persistence is the common case, not a guarantee.

## Why this distinction is what makes `kubectl` and every controller generic

`kubectl get <anything>`, one generic informer implementation in
`client-go`, one generic `CreateOrUpdate` helper in `controller-runtime` —
none of these have per-type logic, because every *object* shares the same
`TypeMeta`/`ObjectMeta` envelope regardless of which *resource* it belongs
to. `03-api-model-and-extensibility.md`'s discovery API is what lets a
generic client discover *which resources exist*; this shared object
envelope is what lets it handle *any of them* the same way once it knows.

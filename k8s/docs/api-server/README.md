# Kubernetes API server

Reference notes on `kube-apiserver` itself — the one control-plane component
everything else in this repo's `k8s/` sub-projects (`aks_crd_operator/`,
`k8s_explorer/`, ...) ultimately talks to. Conceptual/architecture reference,
not walked through against a live cluster like `aks_crd_operator/docs/qna.md`
is — where a claim here matters for something you're building, verify it
against a running cluster the same way that doc does
(`kubectl get --raw ...`, `kubectl explain`, etc.).

Read in order:

0. [`00-resources-and-objects.md`](./00-resources-and-objects.md) — the
   vocabulary every doc below assumes: a resource is a type/API endpoint,
   an object is one persisted instance of it.
1. [`01-architecture-and-role.md`](./01-architecture-and-role.md) — what it
   is, where it sits in the control plane, why it's the only thing that
   talks to etcd, and how it scales.
2. [`02-request-lifecycle.md`](./02-request-lifecycle.md) — what happens to
   one request end to end: authentication → authorization → admission →
   validation/defaulting → etcd → response.
3. [`03-api-model-and-extensibility.md`](./03-api-model-and-extensibility.md)
   — groups/versions/resources, the discovery API, and the two ways to add
   a new kind (CRD vs. aggregated API server) — ties directly into
   [`../../aks_crd_operator/docs/02-crd-design.md`](../../aks_crd_operator/docs/02-crd-design.md).
4. [`04-watch-and-list.md`](./04-watch-and-list.md) — how `kubectl get -w`
   and every controller's informer cache actually work under the hood.
5. [`05-api-groups-reference.md`](./05-api-groups-reference.md) — the
   concrete list: every API group a stock cluster serves and what lives in
   each one. RBAC's own group (`rbac.authorization.k8s.io`) is listed here
   but covered in depth in [`../rbac/`](../rbac).
6. [`06-built-in-resources-reference.md`](./06-built-in-resources-reference.md)
   — one level more granular than #5: every individual built-in resource
   (not just the groups), with its `kind`, namespacing, and what it's for.

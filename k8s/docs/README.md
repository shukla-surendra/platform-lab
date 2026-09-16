# Kubernetes reference docs

General Kubernetes reference material, shared across every sub-project in
`k8s/` — segregated by topic, one subfolder each, so a growing set of
topics doesn't turn into one long undifferentiated file list.

| Topic | What's in it |
|---|---|
| [`api-server/`](./api-server) | `kube-apiserver` itself — resources vs. objects, architecture, request lifecycle (authn/authz/admission), CRD vs. aggregated-API-server extensibility, the watch/list mechanism, and a concrete reference of every API group a stock cluster serves. |
| [`rbac/`](./rbac) | RBAC management — the `Role`/`ClusterRole`/`RoleBinding`/`ClusterRoleBinding` model, the full verb/permission list, where user/group identity actually comes from (and why Kubernetes stores almost none of it), plus an FAQ. |
| [`plugins-and-addons/`](./plugins-and-addons) | Plugins (CNI/CSI/CRI/device-plugins/scheduler/CCM — implementations of a Kubernetes-defined interface) vs. add-ons (any installed extra — mostly CRD+operator, not plugins), the full list of each, and exactly how both relate to CRD+operator. Plus an FAQ. |

Conceptual/architecture reference in general, not walked through against a
live cluster the way `aks_crd_operator/docs/qna.md` is — where a claim here
matters for something you're building, verify it against a running cluster
the same way that doc does (`kubectl get --raw ...`, `kubectl explain`,
`kubectl auth can-i`, etc.).

## Adding a new topic

One subfolder per topic (`api-server/`, `rbac/`, ...), each with its own
`README.md` index and numbered docs inside — same shape `api-server/`
already uses. Add a row to the table above and a bullet point to the `k8s/`
entry in the repo's root [`README.md`](../../README.md) when a new topic
folder is added.

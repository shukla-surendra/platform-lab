# 1. The RBAC model

RBAC is one authorization mode among several (`Node`, `Webhook`, `ABAC` —
legacy — are the others) — see the authorization section of
`../api-server/02-request-lifecycle.md`. It's the one almost every cluster
actually runs, and the only one this folder covers.

## Four objects, two axes

|            | Grants permissions | Scope |
|---|---|---|
| **`Role`** | a set of rules | one namespace |
| **`ClusterRole`** | a set of rules | cluster-wide, *or* reusable across namespaces |
| **`RoleBinding`** | attaches a `Role` (or a `ClusterRole`) to subjects | one namespace |
| **`ClusterRoleBinding`** | attaches a `ClusterRole` to subjects | cluster-wide |

The rules themselves (`Role`/`ClusterRole`) and the grant to a subject
(`RoleBinding`/`ClusterRoleBinding`) are always two separate objects — a
`Role` with no `RoleBinding` pointing at it grants nobody anything, same
"registering something is not the same as it doing anything" pattern
`aks_crd_operator/docs/qna.md` makes about a CRD with no operator watching
it.

**A `ClusterRoleBinding` can bind a `ClusterRole` two different ways:** a
`RoleBinding` can also reference a `ClusterRole` — this grants that
`ClusterRole`'s rules, but scoped down to just the `RoleBinding`'s own
namespace. This is the standard way to reuse one shared, cluster-wide rule
set (e.g. a generic "viewer" `ClusterRole`) namespace by namespace, without
copy-pasting the same rules into a `Role` per namespace.

## Rule shape

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: webapp-operator
rules:
  - apiGroups: ["webapp.platformlab.dev"]
    resources: ["webapps", "webapps/status"]
    verbs: ["get", "list", "watch", "update", "patch"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```

(This is, almost verbatim, `aks_crd_operator/operators/webapp-operator-python/config/rbac.yaml`
— every operator built in this repo uses exactly this shape.) Each rule is:

- **`apiGroups`** — which group (`""` for core, `apps`, a custom group like
  `webapp.platformlab.dev`) — see `../api-server/05-api-groups-reference.md`
  for the full group list.
- **`resources`** — the resource's **plural** name, always — matches
  exactly what `../api-server/00-resources-and-objects.md` calls a
  resource; never the `kind`.
- **`resourceNames`** *(optional)* — restricts the rule to specific named
  objects instead of every object of that resource (e.g. `resourceNames:
  ["hello-webapp"]`). Can't be combined with `create`, since the object
  doesn't exist yet at authorization time — there's no name to check
  against.
- **`verbs`** — see [`02-verbs-and-permissions.md`](./02-verbs-and-permissions.md)
  for the full list.

Multiple rules in one `Role`/`ClusterRole` are additive — there's no
"deny" rule in RBAC, only grants. A request is allowed if *any* rule in
*any* `Role`/`ClusterRole` bound to that identity (directly, or via a
group it belongs to) matches; otherwise it's denied by default.

## Subjects

A `RoleBinding`/`ClusterRoleBinding`'s `subjects` list is who the rules
apply to:

```yaml
subjects:
  - kind: ServiceAccount
    name: webapp-operator
    namespace: webapp-operator-system
  - kind: User
    name: surendra@example.com
  - kind: Group
    name: platform-team
```

`ServiceAccount` is a real, stored Kubernetes object (see
[`03-identity-and-subjects.md`](./03-identity-and-subjects.md)).
`User`/`Group` are **not** — they're free-form strings, matched against
whatever the authentication layer asserted for this request. RBAC doesn't
validate that a `User` named `surendra@example.com` "exists" anywhere,
because there's nowhere for it to exist — that's the whole subject of the
next doc.

## Privilege-escalation guard: `bind` and `escalate`

RBAC has one built-in rule preventing a subject from granting permissions
it doesn't itself hold: creating a `RoleBinding`/`ClusterRoleBinding`
requires either already having every permission the referenced
`Role`/`ClusterRole` grants, or holding the special `bind` verb on that
specific `Role`/`ClusterRole`. Same idea for editing a `Role`/`ClusterRole`
itself, guarded by the special `escalate` verb — both covered in
[`02-verbs-and-permissions.md`](./02-verbs-and-permissions.md).

## Aggregated ClusterRoles

A `ClusterRole` can declare `aggregationRule` instead of `rules` directly,
collecting rules from every other `ClusterRole` matching a label selector.
This is how the built-in `cluster-admin`/`admin`/`edit`/`view` roles stay
extensible — a CRD's own installer can ship a small `ClusterRole` labeled
to match one of those selectors, and its rules get merged in automatically
without editing the built-in role. `make deploy`'s generated RBAC in this
repo's operators doesn't use this (each is self-contained, not merged into
a built-in role), but it's the mechanism real add-ons (metrics-server,
cert-manager) commonly use to extend `view`/`edit` with their own
resources.

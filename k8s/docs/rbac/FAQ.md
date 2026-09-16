# RBAC — FAQ

## Who stores user information in Kubernetes RBAC?

Nobody, for regular human users — Kubernetes has no `User` object at all.
Identity is asserted entirely by whatever **authentication** method is
configured (client cert CN/O fields, OIDC token claims, a webhook
authenticator) and Kubernetes trusts the result without keeping its own
copy. The one exception is `ServiceAccount`, a real stored object with a
derived username `system:serviceaccount:<namespace>:<name>`. Full
explanation: [`03-identity-and-subjects.md`](./03-identity-and-subjects.md).

## Is there a list of RBAC actions/permissions (verbs)?

Yes, and it's a fixed, closed set — you can't invent a new one:
`get`, `list`, `watch`, `create`, `update`, `patch`, `delete`,
`deletecollection`, plus the special `bind`, `escalate`, `impersonate`
(and the mostly-historical `use`). Full list with what each one actually
authorizes: [`02-verbs-and-permissions.md`](./02-verbs-and-permissions.md).

## What's the difference between `Role` and `ClusterRole`?

A `Role`'s rules only ever apply within one namespace. A `ClusterRole`'s
rules can apply cluster-wide (via a `ClusterRoleBinding`) *or* be reused
namespace-by-namespace (via a `RoleBinding` that references a
`ClusterRole` instead of a `Role`) — the second pattern exists so a shared
rule set doesn't have to be copy-pasted into a `Role` per namespace.
Table + example: [`01-rbac-model.md`](./01-rbac-model.md).

## Can a `Role` grant access to a different namespace?

No — a `Role`'s rules are always scoped to the namespace it lives in,
regardless of what a `RoleBinding` referencing it tries to do. To grant
namespaced-resource access across namespaces, use a `ClusterRole` bound
via a `RoleBinding` in each namespace you want it to apply to, or via a
single `ClusterRoleBinding` for genuinely cluster-wide access.

## Why did my operator's ServiceAccount get a 403 even though I granted the resource?

Almost always a **verb** granted for the wrong stage — most commonly
`get`/`list` granted but not `watch`. This is a real, live bug hit while
deploying `greeting-operator` in this repo: kopf needs `watch` on
`customresourcedefinitions` cluster-wide, and the RBAC only granted
`get`/`list`, producing a 403 retry loop on startup
(`aks_crd_operator/docs/qna.md` has the full log and fix). Also check:
the rule's `resources` matches the resource's **plural** name exactly
(never `kind`), and `apiGroups` matches exactly (`""` for core, not
omitted).

## How do I check what permissions a subject actually has?

`kubectl auth can-i <verb> <resource> [--namespace ...] [--as <identity>]`,
or `kubectl auth can-i --list --as <identity>` for the full picture. This
runs a live `SelfSubjectAccessReview`/`SubjectAccessReview` against every
current `Role`/`ClusterRole`/binding — not a static read of YAML. Details:
[`02-verbs-and-permissions.md`](./02-verbs-and-permissions.md)'s last
section.

## Can I grant permissions I don't have myself?

Not by default — RBAC's built-in escalation guard blocks creating a
`RoleBinding`/`ClusterRoleBinding` for a `Role`/`ClusterRole` whose rules
exceed what you already hold, unless you also have the special `bind` verb
on that specific `Role`/`ClusterRole` (or `escalate`, for editing one
directly). Explained in [`01-rbac-model.md`](./01-rbac-model.md) and
[`02-verbs-and-permissions.md`](./02-verbs-and-permissions.md).

## What happens if no rule matches a request?

Denied. RBAC has no explicit "deny" rule type — only grants — so the
absence of a matching rule *is* the deny. This is also why removing access
is "delete or narrow the binding/role," never "add a deny rule."

## Is RBAC the only authorization mode Kubernetes supports?

No — `Node` (restricts each kubelet to objects relevant to its own node)
and `Webhook` (delegates the decision to an external service) can run
alongside it; `ABAC` is legacy and rarely used on any current cluster.
See the authorization section of
[`../api-server/02-request-lifecycle.md`](../api-server/02-request-lifecycle.md).

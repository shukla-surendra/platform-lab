# RBAC (Role-Based Access Control)

How Kubernetes decides *what a given identity is allowed to do* — the
authorization stage from
[`../api-server/02-request-lifecycle.md`](../api-server/02-request-lifecycle.md).
Conceptual reference; verify anything load-bearing against a live cluster
with `kubectl auth can-i`, the same way `aks_crd_operator/docs/qna.md`
verifies its own claims live.

Read in order:

1. [`01-rbac-model.md`](./01-rbac-model.md) — the four objects
   (`Role`/`ClusterRole`/`RoleBinding`/`ClusterRoleBinding`), the shape of a
   rule, and subjects.
2. [`02-verbs-and-permissions.md`](./02-verbs-and-permissions.md) — the full
   action/permission (verb) list, including the special ones
   (`bind`/`escalate`/`impersonate`) most people never encounter until they
   need them.
3. [`03-identity-and-subjects.md`](./03-identity-and-subjects.md) — where
   user/group identity actually comes from, and why Kubernetes itself
   stores almost none of it.
4. [`FAQ.md`](./FAQ.md) — common questions, including "who stores user
   information" and "is there a permission list," answered in short form
   with pointers back to the docs above.

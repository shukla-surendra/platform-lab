# 2. The action/permission list

Every rule's `verbs` field draws from a fixed, known set — there's no way
to invent a custom verb. This is the complete list.

## Standard resource verbs

| Verb | What it authorizes |
|---|---|
| `get` | Fetch one named object. |
| `list` | Fetch a collection (with optional label/field selectors). |
| `watch` | Open a long-lived stream of change events — see `../api-server/04-watch-and-list.md`. This is the one every operator in this repo learned the hard way needs granting *separately* from `get`/`list`: the live RBAC bug in `aks_crd_operator/docs/qna.md` (kopf 403'ing on `customresourcedefinitions`) was exactly a rule granting `get`/`list` but not `watch`. |
| `create` | Create a new object. Can't be combined with `resourceNames` (see `01-rbac-model.md`). |
| `update` | Replace an existing object's full content. |
| `patch` | Modify part of an existing object (what `controllerutil.CreateOrUpdate` and kopf's own apply logic both use — see `aks_crd_operator/operators/*/operator.py`'s fallback-to-patch-on-409 pattern). |
| `delete` | Delete one named object. |
| `deletecollection` | Delete every object matching a selector in one call, instead of one `delete` per object. |

`"*"` as a verb (or as `apiGroups`/`resources`) means "every verb" —
exactly what the built-in `cluster-admin` `ClusterRole` uses. Treat a rule
with `verbs: ["*"]` as a real red flag in review, not a convenience
shortcut — it silently grants verbs added to Kubernetes *after* the rule
was written, too.

## Non-resource URLs

A small number of API server endpoints aren't backed by any resource at
all — `/healthz`, `/version`, `/apis` itself (the discovery endpoints from
`../api-server/03-api-model-and-extensibility.md`). RBAC rules can grant
access to these directly:

```yaml
rules:
  - nonResourceURLs: ["/healthz", "/version"]
    verbs: ["get"]
```

Only valid inside a `ClusterRole` (never a `Role` — these URLs aren't
namespaced, so a namespace-scoped rule can't apply to them), and only
reachable via a `ClusterRoleBinding`.

## Special verbs — not authorizing a request, authorizing a *relationship*

Three verbs don't grant "do X to this object" — they grant "act in a
specific relationship to another identity or role":

- **`bind`** — on a `Role`/`ClusterRole` object: lets a subject create a
  `RoleBinding`/`ClusterRoleBinding` that references *that specific*
  `Role`/`ClusterRole`, even without already holding every permission it
  grants. Exists as the escape hatch for the default privilege-escalation
  guard described in `01-rbac-model.md`.
- **`escalate`** — on a `Role`/`ClusterRole` object: lets a subject edit
  that `Role`/`ClusterRole` to grant permissions the subject doesn't
  itself currently hold. Without it, RBAC's built-in guard silently
  refuses the edit even if the subject otherwise has `update`/`patch` on
  `roles`/`clusterroles` in general.
- **`impersonate`** — on `users`, `groups`, `serviceaccounts` (core group)
  and `userextras` (`authentication.k8s.io`): lets a subject send a request
  *as* another identity, via `kubectl --as=<user>` or the
  `Impersonate-User`/`Impersonate-Group` headers. The API server then runs
  the *entire* rest of the pipeline (authorization, admission) as the
  impersonated identity, not the real caller — genuinely powerful, and
  exactly why it needs its own separate grant rather than riding on
  `get`/`update`.

## `use` — mostly historical

Older clusters (pre-1.25) used `use` on `podsecuritypolicies`
(`policy/v1beta1`, since removed) to control which Pod security profile a
subject's Pods could run under. Pod Security Admission (a built-in
admission controller, not an RBAC-gated resource) replaced this — see the
admission stage in `../api-server/02-request-lifecycle.md`. Still relevant
on older clusters or in RBAC written for OpenShift's
`securitycontextconstraints`, which uses the same `use` verb pattern; not
something a cluster built against a current Kubernetes version needs.

## Checking what a subject can actually do

Don't read `rules:` YAML by hand to answer "can X do Y" — ask the API
server directly, using the exact mechanism from
`../api-server/05-api-groups-reference.md`'s `authorization.k8s.io` entry:

```bash
kubectl auth can-i create deployments --namespace default
kubectl auth can-i create deployments --as system:serviceaccount:webapp-operator-system:webapp-operator
kubectl auth can-i --list --as system:serviceaccount:greeting-operator-system:greeting-operator
```

Each of these is a `SelfSubjectAccessReview` (or `SubjectAccessReview`
with `--as`) under the hood — a live evaluation against every
`Role`/`ClusterRole`/binding currently in the cluster, not a static lookup.

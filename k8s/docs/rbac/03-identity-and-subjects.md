# 3. Identity and subjects — where "user" actually comes from

The single most surprising thing about Kubernetes RBAC to anyone coming
from a system with a user database: **Kubernetes has no `User` object.**
`kubectl get users` isn't a shorter command that happens to not exist —
there is genuinely no such resource, in any API group, ever.

## The one identity that *is* a real, stored object: `ServiceAccount`

`ServiceAccount` (core group, `v1`) is an actual API object — persisted in
etcd, listable, `kubectl get serviceaccounts` works. Every Pod runs as one
(defaulting to `default` in its namespace if unspecified); the kubelet
mounts a token tied to it. Its RBAC-visible username is derived, not
stored as a separate field: `system:serviceaccount:<namespace>:<name>`,
and it automatically belongs to the groups `system:serviceaccounts` and
`system:serviceaccounts:<namespace>`. This is exactly the identity every
operator's own Pod authenticates as — `system:serviceaccount:
webapp-operator-system:webapp-operator`, `system:serviceaccount:
greeting-operator-system:greeting-operator` — confirmed live in this
repo's own deploys (`aks_crd_operator/docs/qna.md`).

## Everything else: asserted by authentication, stored nowhere in the cluster

For a human `kubectl` user, the `User`/`Group` strings that show up in a
`RoleBinding`'s `subjects` (`01-rbac-model.md`) come entirely from
whichever **authentication** method is configured — the stage *before*
authorization in `../api-server/02-request-lifecycle.md`. Kubernetes
trusts the result; it doesn't keep its own copy:

- **Client certificates** — the username is the certificate's `CN`
  (Common Name) field; group memberships are its `O` (Organization)
  fields. The identity lives entirely inside the certificate, signed by a
  CA the API server is configured to trust (`--client-ca-file`).
  Kubernetes stores the *CA*, not any record of who each certificate was
  issued to — that record, if it exists, lives wherever the CA's own
  issuance process keeps it (often nowhere at all, for a small lab CA).
- **OIDC tokens** — username/groups come from claims inside a JWT issued
  by an external identity provider (Azure AD, Okta, Google...). The API
  server only validates the token's signature and reads the configured
  claim names (`--oidc-username-claim`, `--oidc-groups-claim`); the actual
  user/group directory lives entirely in the IdP, outside the cluster.
- **Webhook token authentication** — the API server hands the bearer token
  to an external service and asks "who is this," trusting whatever
  username/groups come back. Same story: identity lives in that external
  service, not in Kubernetes.
- **Static token/password files** (legacy, effectively deprecated) — a
  flat file on the API server's own filesystem mapping tokens to
  usernames. The one case where something resembling "stored user
  information" lives on the cluster's own control-plane node — but as a
  local file the API server reads at startup, not an etcd-backed API
  object, and not recommended on any current cluster.

## The practical consequence

A `RoleBinding` subject `kind: User, name: alice@example.com` is not
validated against anything when you apply it — RBAC will happily bind
permissions to a username that will never actually authenticate as
anything, and just as happily deny a real, successfully-authenticated user
whose username doesn't match any binding. There's no referential integrity
between "users the cluster knows about" and "users referenced in
bindings," because the former set doesn't exist as cluster state at all.

This is also why "who has access to this cluster" is never a
`kubectl`-answerable question on its own for human users — you have to
combine `kubectl get rolebindings,clusterrolebindings -A` (what's granted)
with whatever system issues identities (your CA's issuance log, your
OIDC provider's group membership, your webhook authenticator's own
records) to get the full picture. For `ServiceAccount` subjects alone,
`kubectl get serviceaccounts -A` plus the bindings *is* the full picture,
since both halves live inside the cluster.

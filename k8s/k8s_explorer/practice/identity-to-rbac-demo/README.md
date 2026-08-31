# identity-to-rbac-demo

Companion to [`docs/eks-sso-rbac.md`](../../docs/eks-sso-rbac.md) — that doc covers *how* AWS SSO
(IAM Identity Center) or an external OIDC provider gets a user's groups in front of the
Kubernetes API server. This project proves the piece both paths funnel into: **Kubernetes RBAC
doesn't know or care how an identity's username/groups were established** — an IAM role mapped
via an EKS Access Entry and an OIDC token's `groups` claim both terminate in the exact same
primitive, a `Group` subject on a RoleBinding.

There's no AWS account, IAM Identity Center, or OIDC provider involved here — this uses
`kubectl`'s built-in **impersonation** feature to hand RBAC an identity with a chosen
username/groups directly, which is precisely what authorization sees regardless of which
authentication mechanism produced it. Verifiable for free on any cluster, including the shared
minikube cluster this repo already uses elsewhere.

Assumes a running `minikube` cluster (`minikube status`).

## What problem does it solve?

It's easy to read `docs/eks-sso-rbac.md`'s two paths (IAM-centric vs. OIDC-centric) and come away
thinking they're two different authorization systems. They're not — they're two different ways
of getting to the *same* Kubernetes RBAC, which only ever asks one question: "does this
username/these groups have a binding granting this verb on this resource." Everything upstream
of that — IAM Identity Center, `aws-auth`, Access Entries, an OIDC issuer — exists purely to
answer "who is this and what groups are they in," and none of it is visible to RBAC once that
answer is established. Proving that with impersonation, on a cluster with no cloud dependency at
all, is what makes that claim concrete instead of asserted.

## Setup

```bash
kubectl apply -f rbac.yaml
```

Creates: a `payments` namespace, a `platform-team-viewer` ClusterRole (read-only on
pods/deployments/replicasets), a RoleBinding granting that role to **Group** `eks-platform-team`
in `payments` — and, separately, a `restricted-sa` ServiceAccount with ordinary read permissions
but no `impersonate` rights, used for the second half below.

## Verified — RBAC only sees the group, never how it got there

```bash
kubectl auth can-i list pods -n payments --as=alice@corp.com --as-group=eks-platform-team
kubectl auth can-i delete deployments -n payments --as=alice@corp.com --as-group=eks-platform-team
kubectl auth can-i list pods -n payments --as=bob@corp.com --as-group=eks-viewers
kubectl auth can-i list pods -n payments --as=some-other-person@corp.com --as-group=eks-platform-team
```

Real output:

```
yes
no
no
yes
```

In order: (1) the bound group can do what it was granted; (2) it cannot do what it wasn't
(`delete` was never in the ClusterRole's verb list); (3) an entirely different, unbound group
gets nothing, regardless of username; (4) — the actual point — a **completely different
username**, same group, gets the **identical** answer as (1). The RoleBinding names a group, not
a person; nothing about `alice@corp.com` vs. `some-other-person@corp.com` mattered at all. That's
what "IAM role → group" and "OIDC groups claim → group" both reduce to by the time they reach
here — swap either upstream mechanism for the other and this file doesn't change.

## Verified — impersonation itself is RBAC-gated (a real security boundary, not a convenience flag)

The tests above all ran under this repo's default admin kubeconfig, which has `cluster-admin`
and can freely assert any identity via `--as`. That's worth proving is a *privilege*, not a
default anyone gets:

```bash
./generate-restricted-kubeconfig.sh     # builds a kubeconfig for restricted-sa, a real, separate,
                                         # lower-privileged identity - not just --as on top of admin

kubectl --kubeconfig=restricted-sa.kubeconfig auth can-i list pods -n default
kubectl --kubeconfig=restricted-sa.kubeconfig get pods -n payments \
  --as=alice@corp.com --as-group=eks-platform-team
```

Real output:

```
yes
Error from server (Forbidden): users "alice@corp.com" is forbidden: User
"system:serviceaccount:default:restricted-sa" cannot impersonate resource "users" in API
group "" at the cluster scope
```

`restricted-sa` can use its own real, granted permission (`list pods` in `default` — line 1), but
the moment it tries to *impersonate* anyone, the API server rejects the request outright — it
never even reaches the question of whether `eks-platform-team` could list pods, because
`restricted-sa` itself never had the `impersonate` verb. **This is why granting `--as`/kubectl
impersonation rights broadly is a real privilege-escalation risk**: it's the "become any group"
verb, not a debugging convenience — a ClusterRole with `impersonate` on `groups` effectively grants
whatever every existing RoleBinding grants, all at once, to whoever holds it.

One more real, non-obvious finding from this run worth keeping: `kubectl auth can-i ... --as=...`
against `restricted-sa.kubeconfig` doesn't answer `no` for the hypothetical — it fails outright
with the same `Forbidden` error as the real attempt. The server won't even evaluate "could this
impersonated identity do X" unless the *caller* already holds `impersonate` — asking the question
requires the same privilege as doing the thing.

## Mapping back to the two real paths

| This demo | IAM-centric (Path 1) | OIDC-centric (Path 2) |
|---|---|---|
| `--as-group=eks-platform-team` | `aws-auth` `mapRoles`/EKS Access Entry sets `kubernetes-groups` for an IAM role | The OIDC token's `groups` claim, per `--oidc-groups-claim` |
| `--as=alice@corp.com` | The IAM role's ARN, or an Access Entry's `username` field | The OIDC token's `sub`/email claim, per `--oidc-username-claim` |
| The RoleBinding in `rbac.yaml` | Unchanged — same object, same file, either way | Unchanged |
| Who's gating impersonation | N/A — the mapping happens before the API server sees a request at all, not via impersonation | N/A, same reason |

## Cleanup

```bash
kubectl delete -f rbac.yaml
rm -f restricted-sa.kubeconfig   # holds a live bearer token - gitignored, delete it locally too
```

## Reference

| File | Role |
|---|---|
| `rbac.yaml` | Namespace, the group-bound RoleBinding, and the no-impersonate ServiceAccount |
| `generate-restricted-kubeconfig.sh` | Builds a real, separate kubeconfig for `restricted-sa` |

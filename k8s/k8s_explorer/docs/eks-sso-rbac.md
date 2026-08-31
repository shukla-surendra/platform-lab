# EKS: SSO (IAM Identity Center / OIDC) with Kubernetes RBAC

Like [`eks-setup.md`](./eks-setup.md), **not verified against a live AWS account** — IAM
Identity Center and a real EKS cluster both cost money and need real AWS org setup, so nothing
here was actually provisioned. What *is* verified, on the free local minikube cluster this repo
already uses everywhere else, is the piece both paths below terminate in — Kubernetes RBAC only
ever sees a username/group set, never how it was established. That proof lives in
[`../identity-to-rbac-demo/`](../identity-to-rbac-demo); read it alongside this doc, not
instead of it.

Cross-references: [`rbac.md`](./rbac.md) (the Kubernetes-side RBAC this connects to),
[`eks-setup.md`](./eks-setup.md) §4 (IRSA — a **different, easily-confused** question, see the
callout below).

## What problem does this solve?

Two separate things both look like "OIDC on EKS" and get conflated constantly:

- **IRSA / EKS Pod Identity** (`eks-setup.md` §4): which **Pods** can call **AWS** APIs. Solved
  by EKS's own OIDC provider trusting Kubernetes ServiceAccount tokens.
- **This doc**: which **humans** (via SSO) can call the **Kubernetes** API, and with what RBAC
  permissions. A completely different trust relationship, in the opposite direction — this is
  about an external identity (a person, via IAM Identity Center or a corporate IdP) authenticating
  *to* Kubernetes, not a Pod authenticating *to* AWS.

Both happen to use "OIDC" as the underlying protocol, which is the entire source of the
confusion — they're otherwise unrelated.

## Path 1 — IAM-centric (AWS Identity Center + EKS Access Entries)

```
User logs into AWS IAM Identity Center (SSO portal)
        |
        | Permission Set -> assumes an IAM Role
        v
IAM Role (e.g. arn:aws:iam::ACCOUNT:role/EKSPlatformTeamRole)
        |
        | EKS Access Entry maps this role to Kubernetes group(s)
        v
kubectl / `aws eks get-token` authenticates as that IAM role's ARN
        |
        v
Kubernetes RBAC RoleBinding/ClusterRoleBinding binds the group to a Role/ClusterRole
```

One IAM role per RBAC tier (e.g. `EKSPlatformTeamRole`, `EKSReadOnlyRole`), not one per person —
Identity Center assigns *people* to *Permission Sets*, and each Permission Set assumes one of
these shared roles.

### Access Entries — the current API (replaces hand-editing `aws-auth`)

```bash
# Grant an IAM role a specific Kubernetes group, then bind that group with normal RBAC
aws eks create-access-entry \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::ACCOUNT:role/EKSPlatformTeamRole \
  --kubernetes-groups eks-platform-team

# Or skip custom RBAC entirely and attach an AWS-managed access policy directly
aws eks associate-access-policy \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::ACCOUNT:role/EKSReadOnlyRole \
  --policy-arn arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy \
  --access-scope type=cluster
```

The `--kubernetes-groups eks-platform-team` value is exactly the group name
[`../identity-to-rbac-demo/`](../identity-to-rbac-demo) binds a RoleBinding to — this
API call is the *only* thing Path 1 adds on top of ordinary Kubernetes RBAC; everything
downstream of "the identity now has this group" is identical to any other cluster.

### The older way, for reading legacy clusters

Before Access Entries (EKS 1.23 and earlier, or any cluster that hasn't migrated), the same
mapping lived in a ConfigMap, hand-edited:

```bash
kubectl edit configmap aws-auth -n kube-system
```

```yaml
mapRoles: |
  - rolearn: arn:aws:iam::ACCOUNT:role/EKSPlatformTeamRole
    username: platform-team-user
    groups:
      - eks-platform-team
```

Fragile in a way Access Entries deliberately fix: a bad edit here (wrong indentation, a typo'd
ARN) can lock every IAM-authenticated user out of the cluster simultaneously, with no API-level
validation catching it before you apply it.

### Connecting `kubectl`

```bash
aws sso login --profile eks-platform-team      # opens the Identity Center login flow
aws eks update-kubeconfig --region us-east-2 --name my-cluster --profile eks-platform-team
kubectl get pods -n payments                    # auth token comes from the assumed role, transparently
```

`update-kubeconfig` writes an `exec`-based user entry that calls `aws eks get-token` on every
request — no separate login step for `kubectl` itself once `aws sso login` has a valid session.

## Path 2 — OIDC-centric (external IdP talks to the API server directly)

```bash
aws eks associate-identity-provider-config \
  --cluster-name my-cluster \
  --oidc \
    issuerUrl=https://my-idp.example.com/ \
    clientId=eks-cluster \
    usernameClaim=email \
    groupsClaim=groups
```

This is a **separate trust root** from IAM entirely — once associated, the API server accepts ID
tokens from `my-idp.example.com` directly, and RBAC binds to whatever `email`/`groups` claims that
token carries, with no IAM role, Access Entry, or `aws-auth` entry involved for those users at
all. `kubectl` needs a plugin (`kubelogin`/`kubectl oidc-login`) to fetch and refresh that token,
configured as an `exec` credential plugin the same shape as `aws eks get-token` above, just
pointed at the IdP instead of AWS.

Worth being honest about the operational cost this path adds that Path 1 doesn't: a second,
independent trust relationship to secure, rotate, and reason about — if this IdP is compromised or
misconfigured, it's a direct path into cluster RBAC that bypasses IAM/CloudTrail entirely.

## Which one

| | Path 1 (IAM Identity Center + Access Entries) | Path 2 (direct OIDC) |
|---|---|---|
| Best when | Already living in IAM/Identity Center for AWS access broadly | Want RBAC driven by IdP groups directly, decoupled from IAM |
| Group granularity | Per IAM role — coarser unless you provision many roles | Per IdP group claim — as fine as the IdP's own groups |
| Audit trail | CloudTrail logs the role assumption | Whatever the IdP itself logs — a separate system to check |
| Extra trust surface | None beyond IAM you already manage | A second, independent auth root on the cluster |
| `kubectl` auth flow | `aws sso login` + `aws eks get-token` (built into the AWS CLI) | A third-party `exec` plugin (`kubelogin`) |

Most EKS deployments doing "SSO" mean Path 1 — it needs no extra infrastructure beyond Identity
Center users already have, which is also why it's the one worth defaulting to unless there's a
specific reason (an existing non-AWS IdP with group structure you don't want to re-model as IAM
roles) to reach for Path 2.

## What's actually been verified vs. what's reference only

| Claim | Verification status |
|---|---|
| RBAC only sees username/groups, identical regardless of source | **Verified** — [`../identity-to-rbac-demo/`](../identity-to-rbac-demo), real `kubectl auth can-i` output on live minikube |
| Impersonation itself requires RBAC `impersonate` permission | **Verified** — same demo, a real `Forbidden` error from a genuinely restricted identity |
| `aws eks create-access-entry` / `associate-access-policy` syntax | Reference only — no AWS account exercised this |
| `associate-identity-provider-config` + `kubelogin` flow | Reference only — no external IdP was stood up against a real cluster |

The gap between these two rows is exactly the boundary named in
[`../identity-to-rbac-demo/README.md`](../identity-to-rbac-demo#what-problem-does-it-solve):
everything above the RBAC layer (IAM Identity Center, Access Entries, an OIDC IdP) is genuinely
untested here; everything at or below it is proven, because that part needs no cloud account to
verify at all.

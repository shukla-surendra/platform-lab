# Microsoft Entra ID + Azure RBAC — Module 1: Why it exists, the mental model, and the internal architecture

> Part of the Azure track. See [PROGRESS.md](../../../PROGRESS.md) for the full plan.
> **Epistemics:** claims tagged **[Documented]** (Microsoft Learn / Microsoft security
> docs) or **[Inferred]** (reconstruction from documented behavior — Entra ID's internal
> directory implementation is far less publicly published than VNet's VFP/SmartNIC papers
> were, so more of this module leans on documented *behavior* rather than published
> internal architecture; that's flagged explicitly where it matters, not glossed over).
>
> **AWS contrast note:** unlike VNet (contrasted against the already-written
> `aws/docs/vpc/`), **AWS IAM doesn't have a written doc in this repo yet** — it's still
> "Planned" in the AWS track. This module still contrasts against AWS IAM's real, verified
> behavior (roles, policies, STS) from general AWS knowledge; it just isn't cross-linking to
> a sibling doc the way VNet could.

**Module scope:** spec sections 1–3 + 17. Covers *why Entra ID + Azure RBAC exist as two
separate things*, the *core mental model* (identity vs. authorization as genuinely separate
systems), and the *internal architecture* (directory/tenant model, role-assignment
mechanics, Managed Identities, Conditional Access, the App Registration/Service Principal
split).

---

## 1. Why do these services exist?

### The problem in one sentence

Something has to answer two genuinely different questions before any cloud operation is
allowed to happen: **"who is this, really?"** (authentication) and **"is this specific
identity allowed to do this specific thing, at this specific scope?"** (authorization) —
and answering both, at cloud scale, without hardcoded credentials anywhere, is the whole
problem.

### History: Azure Active Directory → Microsoft Entra ID

[Documented, already verified in `aws-to-azure-transition-guide.md`]: **Azure AD was
renamed Microsoft Entra ID**, announced July 11, 2023, rollout complete by end of 2023 —
same service, new name (Azure AD B2C was the one product not renamed). Before ARM-era RBAC
existed, the Classic/ASM deployment model (retired 2023–2024, per the VNet module) used a
much coarser **Co-Administrator** model — a flat "can do everything in this
subscription/nothing" grant, with none of Azure RBAC's scope hierarchy or role granularity.
RBAC's introduction alongside ARM (2014) is what made fine-grained, scope-aware
authorization possible in Azure at all — structurally the same maturity jump AWS IAM
represents over "give everyone the root credentials."

### How companies solved this before cloud IAM services existed

Pre-cloud: Active Directory (on-prem) for identity, paired with per-system, often
inconsistent authorization — a Windows file share's NTFS ACLs, a database's own grant
system, an application's own login table — none of it unified. **Microsoft Entra ID is,
genealogically, the cloud-native descendant of on-prem Active Directory** — this lineage is
real and matters: it's why Entra ID's object model (Users, Groups, Organizational Units'
spiritual successor being Administrative Units) feels closer to classic AD than AWS IAM
does to anything AWS had before it, since AWS IAM was built cloud-native from the start with
no on-prem predecessor to inherit from.

### Why a Co-Administrator-only model was insufficient

Same shape of reasoning as VPC/VNet's "why the flat model failed": no least-privilege
(everyone with access could do everything), no way to scope a contractor to one resource
group, no audit trail granular enough to answer "who could have done X," no way to
delegate identity management itself without granting full subscription control.

### Why Microsoft built Entra ID and Azure RBAC as two separate systems, not one

This is the single most important framing in this module, worth stating plainly: **Entra ID
answers "who exists and who are you" (authentication); Azure RBAC answers "what can this
identity do, where" (authorization) — and they're separate Azure resources with separate
lifecycles**, not one bundled service. An Entra ID tenant is a directory that can exist
before any Azure subscription does (it's also what backs Microsoft 365 identity, entirely
independent of Azure resources); Azure RBAC role assignments are what connect an identity
from that directory to permissions over specific Azure resources. Compare this to AWS IAM,
which bundles identity (users, roles) and authorization (policies attached to those
identities) inside one account-scoped service with no separately-lifecycled directory
underneath.

### What if this separation didn't exist?

- No single sign-on across Microsoft 365 + Azure + third-party SaaS apps using the same
  directory — every product would need its own user store, the exact fragmentation problem
  named above.
- No way for one directory (tenant) to govern multiple subscriptions consistently — identity
  and billing/resource boundaries would be forced to collapse into one, the way an AWS
  Account does.
- No Conditional Access — a policy engine that reasons about *authentication risk* (device
  compliance, location, sign-in risk) has to live at the identity layer, above any single
  resource's authorization model, or it can't apply consistently everywhere at once.

---

## 2. The core mental model

> **Entra ID is the directory (who can authenticate, tenant-wide). Azure RBAC is the
> authorization layer (what an authenticated identity can do, at a specific scope in the
> resource hierarchy). They compose; neither one alone answers "can this user do this."**

```
   ENTRA ID (the tenant — WHO)
   ┌──────────────────────────────────────────────────────┐
   │  Users · Groups · Service Principals · Managed        │
   │  Identities · App Registrations                       │
   │  — one directory, can span MANY Azure subscriptions   │
   └──────────────────────────────────────────────────────┘
                         │
                 (a role assignment links an
                  Entra identity to a scope)
                         ▼
   AZURE RBAC (the authorization layer — WHAT, WHERE)
   ┌──────────────────────────────────────────────────────┐
   │  Role Definition (a set of Actions/DataActions)        │
   │      assigned to an Entra identity                     │
   │      at a Scope: Mgmt Group › Subscription › RG › Res.  │
   │  — inherits DOWN the hierarchy from wherever assigned   │
   └──────────────────────────────────────────────────────┘
```

The [Documented] structural fact that makes this genuinely different from AWS: **one Entra
ID tenant can be trusted by multiple Azure subscriptions**, and a subscription can even be
transferred between tenants. AWS has no equivalent "directory that outlives and spans
accounts" primitive built in — the closest AWS gets is **IAM Identity Center** (formerly AWS
SSO) layered on top of AWS Organizations, which is an *add-on* pattern rather than the
foundational identity layer every AWS account is required to have. In Azure, by contrast,
**every subscription is required to trust exactly one tenant from the moment it exists** —
identity isn't optional infrastructure you might add later, it's load-bearing from day one
(this point was already flagged in the transition guide as one of the two things AWS
engineers consistently underestimate on first contact with Azure).

---

## 3. Internal architecture

### 3a. Role Definitions: Actions vs. DataActions — the real divergence from AWS IAM policies

[Documented, and this is the sharpest practical contrast in this module]: an Azure Role
Definition's permissions are split into two explicitly different kinds:

- **`Actions` / `NotActions`** — **management-plane** operations, routed through Azure
  Resource Manager: create/delete/configure a resource (e.g. create a storage account,
  resize a VM). This is "control-plane" permission, analogous to what most AWS IAM policy
  statements grant.
- **`DataActions` / `NotDataActions`** — **data-plane** operations: reading a blob's actual
  bytes, inserting a row into a table, sending a message to a queue. **A role that grants
  full management-plane `Actions` over a storage account does NOT automatically grant the
  ability to read the data inside it** — that requires a separate `DataActions` grant (e.g.
  `Storage Blob Data Reader`).

This split is easy for an AWS engineer to miss, because AWS's model doesn't force the same
explicit separation for most services — an AWS IAM policy granting `s3:GetObject` grants
data-plane read access directly, in the same policy document/statement shape as
control-plane actions like `s3:CreateBucket`. Azure deliberately keeps "can manage the
resource" and "can touch the data inside it" as two independently-grantable permission
classes, on every built-in role — a genuinely different default security posture, not just
different syntax.

### 3b. Scope and inheritance — same four levels the resource-hierarchy doc already named

A role assignment is always `(identity, role definition, scope)`. **Scope is one of
Management Group, Subscription, Resource Group, or Resource**, and a role assigned at a
higher scope **inherits down** automatically — assign `Contributor` at the Management Group
level and every subscription, resource group, and resource underneath it inherits that
grant, with no separate propagation step. Structurally similar to how AWS IAM permission
boundaries or SCPs cascade through an OU hierarchy in AWS Organizations, except this is
Azure RBAC's *default* behavior for ordinary role assignments, not a separate
organization-level product layered on top.

### 3c. Managed Identities — Azure's answer to "no hardcoded credentials for a resource calling another service"

Same underlying goal as an AWS IAM Role assumed via STS by an EC2 instance profile or IRSA
(IAM Roles for Service Accounts) in EKS — a resource authenticates as itself, with
automatically-rotated credentials, no secret ever stored in code or config. Two flavors:

- **System-assigned** — created and destroyed with the resource's own lifecycle (delete the
  VM, the identity is gone too). Exactly one per resource; can't be shared.
- **User-assigned** — an independent Entra ID object with its own lifecycle, assignable to
  multiple resources at once (e.g. the same identity shared across a fleet of VMs that all
  need identical downstream permissions).

The user-assigned/system-assigned split doesn't map to a single AWS concept —
AWS's closest equivalent (an IAM role with an instance profile) is inherently more like
"user-assigned" (the role exists independently, attached-and-detachable), so **AWS has no
direct built-in equivalent of Azure's system-assigned, lifecycle-bound identity** — worth
naming explicitly as a one-directional feature gap, not just a naming difference.

### 3d. App Registration vs. Service Principal — a two-object model with no clean AWS analogue

[Documented, and a very common source of confusion even among people using Azure daily]: an
**App Registration** defines an *application* — its identity, API permissions it can
request, redirect URIs — as a global definition. A **Service Principal** is the *local,
tenant-specific instantiation* of that App Registration that actually gets granted role
assignments and can authenticate. Registering an app creates a Service Principal in the home
tenant automatically; using that same app in a *different* tenant (e.g. a multi-tenant SaaS
app) creates a **separate Service Principal object in that other tenant**, still pointing
back to the one App Registration definition.

AWS has nothing structurally equivalent — an IAM Role is a single object, full stop; there's
no separate "application definition" object distinct from "the thing that gets permissions
assigned to it." This two-object split exists in Azure specifically because Entra ID has to
support one application being used *across many different tenants* (the Microsoft 365 /
multi-tenant SaaS heritage referenced in §1's history section) — a problem AWS IAM was never
designed to solve, since an AWS IAM Role is inherently single-account-scoped already.

### 3e. Conditional Access — a policy engine above any single resource's authorization

[Documented]: Conditional Access evaluates *authentication-time* signals — is the device
compliant/managed, what's the sign-in risk score, what network is the request coming from,
is MFA satisfied — and can block or require additional proof **before** Azure RBAC's
authorization check ever runs. It sits architecturally *above* Azure RBAC, at the Entra ID
layer, which is exactly why it can apply consistently across Azure, Microsoft 365, and
third-party apps trusting the same tenant simultaneously — a single policy engine any
resource behind the tenant benefits from, rather than a per-service feature.

AWS's closest equivalents are more piecemeal and service-specific: IAM policy `Condition`
blocks (e.g. requiring MFA, restricting source IP) attached per-policy, or AWS IAM Identity
Center's own access policies once that's layered in — real capability, but not one unified
policy engine sitting above every service by default the way Conditional Access does.

### 3f. Worked example: a real role assignment from this workspace

[Documented — this workspace's own Terraform, not generic]. `personal_assistant/terraform/keyvault/main.tf`
wires up the backend's blob-storage access with exactly the three axes from §2, so this is
what the abstract model looks like actually running rather than as a diagram:

- **Identity**: `azurerm_user_assigned_identity.backend` — the "user-assigned" flavor from
  §3c (an independent Entra ID object, not tied to one resource's lifecycle) — federated,
  with no client secret anywhere, to the AKS cluster's own OIDC issuer via
  `azurerm_federated_identity_credential.backend`, trusting one specific Kubernetes
  ServiceAccount (`system:serviceaccount:<namespace>:<name>` as the token subject). This is
  **Azure Workload Identity** — the same client-credential-free shape as AWS **IRSA** (IAM
  Roles for Service Accounts) in EKS: a pod's ServiceAccount token gets exchanged for a
  cloud credential with no secret stored on either side.
- **Role definition**: `Storage Blob Data Contributor` — a **`DataActions`** grant (§3a), not
  an `Actions` grant. It lets the identity read/write/delete blob *contents*; it grants
  nothing over the storage account's own configuration (access keys, replication, network
  rules) — that would need a separate `Actions`-bearing role like `Storage Account
  Contributor` layered on top.
- **Scope**: `azurerm_storage_account.avatars.id` — the individual storage account, not the
  resource group or subscription it lives in. The same identity is *also* separately granted
  `Key Vault Secrets User` on one specific vault a few lines earlier in the same file
  (`azurerm_role_assignment.backend_kv_secrets_user`) — two independent role assignments, two
  independent scopes, one identity, exactly the "role definition is dumb and reusable, scope
  and assignment are what actually grant anything" point from §2.

```hcl
resource "azurerm_role_assignment" "backend_storage_blob_contributor" {
  scope                = azurerm_storage_account.avatars.id                   # Scope
  role_definition_name = "Storage Blob Data Contributor"                      # Role Definition (DataActions)
  principal_id         = azurerm_user_assigned_identity.backend.principal_id  # Identity
}
```

The three arguments on that one resource block are the three axes from §2, in the same
order: identity, role definition, scope.

**AWS equivalent, and exactly where the mapping breaks down**: the closest AWS shape is an
IAM Role assumed via IRSA, with a policy scoped to one S3 bucket ARN
(`Resource: arn:aws:s3:::this-bucket/*`) granting `s3:PutObject`/`s3:GetObject`/`s3:DeleteObject`.
The mismatch worth naming: AWS expresses "scope" as a `Resource` ARN pattern written *inside*
the policy document attached to the identity; Azure expresses scope as a *separate,
first-class field* on the role-assignment object, entirely independent of which role
definition is used. Practically: reusing `Storage Blob Data Contributor` across ten storage
accounts means ten cheap role-assignment objects all referencing one unchanged role
definition; the AWS equivalent means either one policy listing ten resource ARNs, or ten
near-identical policy documents — there's no single object in AWS that stays constant while
only "where" varies, the way an Azure role definition does.

---

## Distributed-systems / security concepts in play (preview of section-17 depth)

- **Separation of authentication and authorization as distinct systems** — the core
  architectural decision this whole module hangs on.
- **Hierarchical, inheriting authorization scopes** — same "policy cascades down a tree"
  shape as AWS Organizations SCPs, but built into Azure RBAC's base behavior rather than a
  separate product.
- **Explicit control-plane/data-plane permission separation** (`Actions` vs. `DataActions`)
  — a deliberate least-privilege design choice, not an accident of Azure's API shape.
- **Directory as a tenant-spanning trust root, decoupled from any one resource
  container** — Entra ID as identity infrastructure that predates and outlives individual
  subscriptions, the same way a company's on-prem AD predates any individual application
  built on top of it.

---

## Sources

- Microsoft Learn — *"What is Microsoft Entra ID?"*, *"What is Azure role-based access
  control (Azure RBAC)?"*, *"Understand role definitions"* (the Actions/DataActions split in
  §3a).
- Microsoft Learn — *"Managed identities for Azure resources"* (system- vs. user-assigned,
  §3c).
- Microsoft Learn — *"Application and service principal objects in Microsoft Entra ID"*
  (the App Registration/Service Principal split in §3d) — the single most-cited
  clarification doc for this exact confusion.
- Microsoft Learn — *"What is Conditional Access?"* (§3e).
- Microsoft Entra ID rename announcement (July 2023), already cross-referenced from
  `aws-to-azure-transition-guide.md`.
- Best study method: for every AWS IAM concept you already know (role, policy, STS
  AssumeRole, resource-based policy, permission boundary, SCP), explicitly ask "what's the
  Entra ID/Azure RBAC equivalent, and where does the mapping break down" — most of them
  break down somewhere, and that break point is what an interviewer will actually probe.

---

## Gate

Answer the questions in
[`quizzes/entra-id/module-1-gate.md`](../../quizzes/entra-id/module-1-gate.md) before
advancing to **M2 — Conditional Access policy design, PIM (Privileged Identity Management),
cross-tenant B2B/B2C**.

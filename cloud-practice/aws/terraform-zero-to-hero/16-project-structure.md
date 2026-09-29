# 16 · Project structure and blast radius

## 🎯 Goal

Decide **how many states** a system should have and where to draw the
lines, pick a repository layout, and apply the naming and ownership
conventions teams use. This is a favourite senior interview topic because
there's no single right answer. Reasoning is what's tested.

---

## 🧠 Mental model: blast radius

**Blast radius** = everything that *could* be affected by one `terraform apply`.

```
 ONE BIG STATE                          SEVERAL SMALL STATES
 ┌──────────────────────────┐           ┌─────────┐ ┌─────────┐ ┌─────────┐
 │ VPC  IAM  DB  EKS  apps   │           │ network │ │  data   │ │  app    │
 │ DNS  queues  alarms  CDN  │           └─────────┘ └─────────┘ └─────────┘
 └──────────────────────────┘
 a typo in an alarm can                 a typo in an app change can't
 plan a change to the VPC               even see the database
```

Every state you split off makes mistakes **smaller**, plans **faster**,
and permissions **tighter**, at the cost of more **wiring** between states.

---

## 🛠 Walkthrough

### Step 1: signs a state is too big

- `plan` takes minutes, because it refreshes thousands of resources.
- Unrelated teams wait on each other's locks.
- A simple app change needs admin-level credentials, because the same state has IAM and networking.
- People start using `-target` "to make it faster". That's a smell.
- Nobody dares to apply, because the plan is 400 lines.

### Step 2: how to split: by rate of change and ownership

Split along two questions: **how often does it change?** and **who owns it?**

```
 changes rarely, high risk          changes often, lower risk
 ─────────────────────────────────────────────────────────────▶
 org/accounts  →  network  →  data (RDS, S3)  →  platform (EKS)  →  apps/services
   (yearly)       (monthly)     (monthly)          (weekly)          (daily)
```

A typical split for `notes-app`:

| Layer (state) | Contains | Owner | Changes |
|---|---|---|---|
| `bootstrap` | state bucket, CI roles | platform | almost never |
| `network` | VPC, subnets, NAT, endpoints | network/platform | rarely |
| `data` | RDS, ElastiCache, S3 buckets with data | platform + app team | sometimes |
| `app` | ALB, ASG/ECS, IAM roles for the app | app team | often |
| `observability` | dashboards, alarms | app/SRE | often |

**Rules of thumb:**
- Keep **stateful, precious** things (databases, buckets with data) away from **frequently changed** things.
- Things that are always changed **together** belong **together**. Splitting them just means two applies for every change.
- One state per **environment × layer** (e.g. `prod/network`, `prod/app`).

### Step 3: wiring states together

Lower layers publish values, and higher layers read them (lesson 12):

```
 network ──(SSM: /notes/prod/vpc_id, subnet ids)──▶ app
 data    ──(SSM: /notes/prod/db_endpoint, Secrets Manager ARN)──▶ app
```

Apply order follows the arrows: network → data → app. Destroy goes in
reverse. Dependencies should only point **one way** (app reads network,
never the other way round).

### Step 4: repository layouts

**Monorepo** (one repo for all infrastructure):

```
infra/
├── modules/                 # shared building blocks
│   ├── network/
│   ├── rds/
│   └── service/
├── live/
│   ├── dev/
│   │   ├── network/         # a root module = a state
│   │   ├── data/
│   │   └── app/
│   └── prod/
│       ├── network/
│       ├── data/
│       └── app/
└── .github/workflows/       # CI: plan on PR per changed folder
```

**Poly-repo** (split repos):
- `terraform-modules` (versioned, tagged)
- `infra-live` (environment configurations pinning module versions)
- or infrastructure living **next to each app** in the app's repo (`app-repo/infra/`)

| | Monorepo | Poly-repo |
|---|---|---|
| Discoverability | everything in one place | spread out |
| Changing a module + its users | one PR | several PRs + releases |
| Module versioning | often local paths (same commit) | real versions, controlled rollout |
| Access control | coarser (CODEOWNERS helps) | per repo |
| CI | must detect *which* folders changed | naturally scoped |

A very common middle ground: **modules repo (versioned)** + **live repo
(per env/layer)**, with app-specific infrastructure in each app's repo.

### Step 5: files inside one root module

```
live/prod/app/
├── versions.tf          terraform { required_version, required_providers }
├── backend.tf           backend "s3" { key = "notes/prod/app/terraform.tfstate" }
├── providers.tf         provider "aws" { assume_role, default_tags, allowed_account_ids }
├── variables.tf
├── main.tf              module calls (or split: alb.tf, asg.tf, iam.tf)
├── outputs.tf
├── terraform.tfvars
└── README.md            what this state owns, who to ask, how to apply
```

### Step 6: naming conventions

**Terraform names** (local names) use snake_case, describe the role rather
than the type, and don't repeat the type:

```hcl
resource "aws_security_group" "alb" {}         # ✅
resource "aws_security_group" "alb_sg" {}      # ❌ "sg" is already in the type
resource "aws_instance" "this" {}              # ✅ in a module with one instance
```

**AWS names** follow one predictable pattern, for example
`<project>-<env>-<component>[-<qualifier>]`:

```hcl
locals {
  name = "${var.project}-${var.environment}"      # notes-prod
}
# notes-prod-alb, notes-prod-app-sg, notes-prod-db
```

**Tags** always include at least `Project`, `Environment`, `Owner`/`Team`,
`ManagedBy = terraform`, and a pointer to the code (`Repo` or `Stack`).
The last one is gold during incidents: "who created this?" is answered by
the tag. Set them with `default_tags`.

### Step 7: ownership and guard rails

- **CODEOWNERS**: the network team must approve changes under `live/*/network/`.
- **Separate CI identities per layer**: the app pipeline's role can't modify the VPC or IAM boundaries.
- **Prod applies only from CI**, never from laptops (lesson 21).
- **A README per root module**: what it owns, its dependencies, and how to apply.

### Step 8: an enterprise example

A company with 3 environments, 2 regions, and 15 services:

- ~6 **platform** states per environment-region (bootstrap, network, DNS, EKS, shared data, observability) → 36 states;
- 1 state per **service** per environment → 45 states;
- **~80 states** in total, orchestrated by Terragrunt or HCP Terraform stacks, with plan-on-PR and apply-on-merge per changed folder.

That sounds like a lot, but each plan takes seconds, each team owns its
states, and a mistake in one service can't touch another.

---

## ⚠️ Common mistakes

- **One giant state "for simplicity"**, which gets slow, risky, and needs over-privileged credentials.
- **Splitting too fine** (one state per resource), which means endless cross-state wiring and ordering pain.
- **Two-way dependencies between states** (network reads app, app reads network). You can never apply either one first.
- **Databases in the same state as fast-changing app code.**
- **Inconsistent naming**, which makes resources impossible to trace back to code.

---

## 🎤 Interview corner

**Q: How would you structure Terraform for a large organisation?**

> Split state by environment and by layer (bootstrap, network, data,
> platform, services) according to rate of change and ownership, to limit
> blast radius, speed up plans, and scope permissions. Use shared versioned
> modules, with thin root modules per environment and layer. States
> communicate through outputs published to SSM or via data sources, with
> one-way dependencies. Each environment lives in its own account, and CI
> runs plan on PR and apply on merge for the changed stacks, with
> CODEOWNERS for review.

**Q: What's "blast radius" and how do you reduce it?**

> The scope of what a single apply can affect. Reduce it by splitting
> state into smaller units, isolating stateful and critical resources,
> separating accounts per environment, least-privilege roles per pipeline,
> `prevent_destroy` on critical resources, and reviewing saved plans.

**Q: Monorepo or poly-repo?**

> Monorepo gives discoverability and atomic module+consumer changes but
> needs path-aware CI and CODEOWNERS. Poly-repo gives natural isolation
> and versioned module releases, at the cost of coordination. Many teams
> use a versioned modules repo plus a live configuration repo.

---

## ✅ Check yourself

1. Give two signals that a state should be split.
2. Why keep RDS out of the state that deploys the app every day?
3. Your app state reads the network state's outputs. Which must be applied first when building a new environment?
4. What's wrong with `resource "aws_s3_bucket" "logs_bucket"`?

<details><summary>Answers</summary>

1. Any two of: slow plans; lock contention between teams; over-privileged credentials needed; frequent use of `-target`; huge unreadable plans.
2. To keep the blast radius of frequent changes away from the data. A bad app change can't plan a replacement of the database.
3. Network first. Dependencies flow network → app.
4. `_bucket` repeats the type. `aws_s3_bucket.logs` reads better.

</details>

➡️ **Next:** [17 · How Terraform works inside](17-terraform-internals.md)

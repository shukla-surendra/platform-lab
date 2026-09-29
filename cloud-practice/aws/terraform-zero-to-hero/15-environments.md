# 15 · Environments: dev, staging, prod

## 🎯 Goal

Run the same `notes-app` code for dev, staging, and prod safely. Know the
three main strategies (workspaces, a directory per environment, and
Terragrunt), the trade-offs of each, and which to pick.

---

## 🧠 Mental model: one recipe, several kitchens

The **recipe** (your modules) is the same for every environment. What
differs is the **ingredients** (sizes, counts, CIDRs) and the **kitchen**
(the AWS account and the state). The whole question of "environments" is:

1. **Where do the per-environment values live?**
2. **How is each environment's state kept separate?**
3. **How do you stop a dev change from touching prod?**

---

## 🛠 Walkthrough

### Step 1: what should differ between environments?

| Differs | Example |
|---|---|
| size and count | dev `t3.micro` ×1, prod `t3.large` ×3 |
| resilience | prod RDS `multi_az = true`, 30-day backups |
| network | different CIDRs, so the VPCs can be peered later |
| protection | prod `prevent_destroy`, deletion protection |
| **account** | ideally each environment in **its own AWS account** |
| **state** | always a **separate state** per environment |

What should *not* differ is the **structure**. If prod has a resource that
dev doesn't, you can't test your changes before they hit prod.

### Step 2: strategy A: workspaces

A **workspace** is a named, separate state for the *same* configuration
folder:

```bash
terraform workspace new dev
terraform workspace new prod
terraform workspace list          #   default  * dev    prod
terraform workspace select prod
terraform apply -var-file=prod.tfvars
```

Inside code, `terraform.workspace` holds the current name:

```hcl
locals {
  env = terraform.workspace
  settings = {
    dev  = { instance_type = "t3.micro", count = 1 }
    prod = { instance_type = "t3.large", count = 3 }
  }[terraform.workspace]
}
```

With the S3 backend, workspace states are stored under a prefix:
`env:/prod/notes-app/terraform.tfstate` (the `default` workspace uses the
plain key). You can change the prefix with `workspace_key_prefix`.

**Pros:** no code duplication, quick to set up.
**Cons**, and they're serious for prod:
- The environment you're in is **invisible**. It's just shell state. One
  forgotten `workspace select` and you apply dev changes to prod.
- **Same backend, same credentials** for all environments, so no account isolation.
- Every environment must have **identical structure and provider versions**.
- In code reviews, you can't see which environment a change affects.

> HashiCorp's own guidance: CLI workspaces are good for **temporary
> copies** (a feature branch environment, testing a change), **not** for
> separating long-lived dev/prod with different credentials.
> (HCP Terraform "workspaces" are a different, richer concept: a separate
> configuration, state, variables, and permissions each.)

### Step 3: strategy B: a directory per environment (the most common)

```
notes-app-infra/
├── modules/
│   ├── network/
│   ├── app/
│   └── database/
└── environments/
    ├── dev/
    │   ├── main.tf           # calls the modules
    │   ├── backend.tf        # key = "notes-app/dev/terraform.tfstate"
    │   ├── providers.tf      # dev account role
    │   └── terraform.tfvars  # dev sizes
    ├── staging/
    │   └── ...
    └── prod/
        └── ...
```

```hcl
# environments/prod/main.tf
module "network" {
  source = "../../modules/network"
  name   = "notes-prod"
  cidr   = "10.20.0.0/16"
}

module "database" {
  source            = "../../modules/database"
  name              = "notes-prod"
  instance_class    = "db.r6g.large"
  multi_az          = true
  deletion_protection = true
  subnet_ids        = module.network.private_subnet_ids
}
```

```bash
cd environments/prod && terraform plan
```

**Pros:**
- **Obvious**: the folder you're in *is* the environment.
- Each can have **its own backend, account, and credentials**.
- A pull request diff shows exactly which environment changes.
- Environments can differ where they must (prod-only monitoring).

**Cons:** some duplication (the module calls, backend, and provider
files are repeated in each folder). Keep that duplication *thin*: the real
logic lives in modules.

**Promotion** (moving a change from dev to prod): with local module paths,
all environments use the *same commit's* modules, so merging a module
change affects all of them at once (you then apply one by one). With
**versioned** modules (`?ref=v1.4.0`), each environment pins a version, and
you promote by bumping `dev` to v1.5.0, then staging, then prod. That's
safer, but there's more bookkeeping.

### Step 4: strategy C: Terragrunt (DRY wrapper)

[Terragrunt](https://terragrunt.gruntwork.io) is a thin wrapper that
removes strategy B's repetition. Each environment folder has a short
`terragrunt.hcl`:

```hcl
# live/prod/app/terragrunt.hcl
include "root" { path = find_in_parent_folders() }   # shared backend/provider settings

terraform {
  source = "git::https://github.com/acme/modules.git//app?ref=v1.4.0"
}

dependency "network" { config_path = "../network" }   # read another unit's outputs

inputs = {
  instance_type = "t3.large"
  subnet_ids    = dependency.network.outputs.private_subnet_ids
}
```

The root `terragrunt.hcl` **generates** the backend block per folder
(the key comes from the folder path automatically), and `terragrunt run --all plan`
runs across many units in dependency order.

**Pros:** very DRY, automatic backend keys, explicit dependencies between stacks.
**Cons:** another tool, another language layer, and a learning curve for the team.

### Step 5: which one?

| Situation | Choose |
|---|---|
| Learning, or a short-lived test copy | workspaces |
| Most teams, 2–5 environments | **directory per environment + shared modules** |
| Many environments × regions × components (dozens of states) | Terragrunt, or HCP Terraform / Spacelift stacks |

### Step 6: account-per-environment (strongly recommended on AWS)

The strongest isolation isn't a folder, it's an **AWS account boundary**:

```
 AWS Organization
 ├── dev account      (111111111111)  ← terraform-deployer role
 ├── staging account  (222222222222)  ← terraform-deployer role
 └── prod account     (333333333333)  ← terraform-deployer role, tighter access
```

```hcl
# environments/prod/providers.tf
provider "aws" {
  region              = "ap-south-1"
  allowed_account_ids = ["333333333333"]      # refuses to run anywhere else
  assume_role {
    role_arn = "arn:aws:iam::333333333333:role/terraform-deployer"
  }
}
```

A mistake in dev *physically can't* touch prod, because the dev
pipeline's identity can't assume the prod role.

### Step 7: per-environment values

Keep values in the environment, logic in modules:

```hcl
# environments/dev/terraform.tfvars
instance_type = "t3.micro"
min_size      = 1
db_class      = "db.t4g.micro"

# environments/prod/terraform.tfvars
instance_type = "t3.large"
min_size      = 3
db_class      = "db.r6g.large"
```

Avoid giant `env == "prod" ? … : …` conditionals scattered through modules.
Expose an input instead, and let each environment set it.

---

## ⚠️ Common mistakes

- **Workspaces for prod separation.** Invisible context, shared credentials, one wrong `select` away from disaster.
- **One state for all environments.** A dev apply can lock or break prod.
- **Environments with different structures**, where untested prod-only paths break on release day.
- **Copy-pasting whole configurations per environment** instead of calling shared modules.
- **The same CIDR in every environment**, which blocks peering or VPN between them later.

---

## 🎤 Interview corner

**Q: How do you manage multiple environments in Terraform?**

> Shared modules for the logic, a thin root configuration per environment
> (a directory each) with its own backend key, provider role, and tfvars,
> and ideally each environment in its own AWS account with
> `allowed_account_ids` as a guard. Changes are promoted by applying
> dev → staging → prod, often with pinned module versions. At larger
> scale, Terragrunt or HCP Terraform reduce the duplication.

**Q: What are Terraform workspaces and would you use them for prod?**

> CLI workspaces are multiple named states for the same configuration and
> backend, selected with `terraform workspace select` and readable as
> `terraform.workspace`. I use them for ephemeral copies like feature
> environments, not for dev/prod separation. The active environment is
> implicit shell state, credentials and backend are shared, and code
> review can't tell which environment a change targets.

**Q: What does Terragrunt add?**

> It keeps configurations DRY. It generates backend and provider blocks
> (with keys derived from folder paths), declares dependencies between
> stacks and passes outputs between them, and runs commands across many
> stacks in dependency order.

---

## ✅ Check yourself

1. Name two risks of using CLI workspaces for dev and prod.
2. In a directory-per-environment layout, where does the real infrastructure logic live?
3. What does `allowed_account_ids` protect against?
4. Where is the `prod` workspace's state stored with an S3 backend whose key is `notes/terraform.tfstate`?

<details><summary>Answers</summary>

1. Any two of: applying to the wrong environment after forgetting to switch; shared credentials and backend (no account isolation); PRs don't show the target environment; forced identical structure.
2. In shared modules. Environment folders only call them with different inputs.
3. Running against the wrong AWS account (e.g. prod credentials in your shell while in the dev folder).
4. `env:/prod/notes/terraform.tfstate` (with the default `workspace_key_prefix`).

</details>

➡️ **Next:** [16 · Project structure and blast radius](16-project-structure.md)

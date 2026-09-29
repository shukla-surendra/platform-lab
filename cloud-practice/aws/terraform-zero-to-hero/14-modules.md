# 14 · Modules

## 🎯 Goal

Package Terraform code into reusable modules, design good module
interfaces, version them, compose them, and handle the tricky parts:
passing providers, `count`/`for_each` on modules, and refactoring into modules.

---

## 🧠 Mental model: a module is a function

You already know that a configuration is like a function (lesson 07):
variables in, outputs out. A **module is exactly that function, made
callable**:

```
 module "network" {                    ┌─────────── modules/network/ ───────────┐
   source   = "./modules/network"  ──▶ │ variable "cidr"   ← argument            │
   cidr     = "10.0.0.0/16"            │ resource "aws_vpc" ...                  │
   az_count = 2                        │ resource "aws_subnet" ...               │
 }                                     │ output "private_subnet_ids"  → return   │
                                       └─────────────────────────────────────────┘
 module.network.private_subnet_ids  ◀── the caller reads the return value
```

**Every folder of `.tf` files is a module.** The folder you run
`terraform` in is the **root module**. Folders it calls are **child modules**.

---

## 🛠 Walkthrough

### Step 1: why modules?

Without modules, the VPC code for dev, staging, and prod is copied three
times. A bug fix has to be made three times, and they drift apart.
Modules give you:

- **Reuse**: write the VPC once, and call it per environment or per team.
- **Abstraction**: callers set 3 inputs instead of understanding 25 resources.
- **Standards**: security and tagging rules baked into one place.
- **Encapsulation**: a module's internals can change as long as its inputs and outputs don't.

### Step 2: writing a module

```
modules/network/
├── variables.tf     the inputs
├── main.tf          the resources
├── outputs.tf       the outputs
├── versions.tf      required_providers (with a MINIMUM version, see below)
└── README.md        how to use it
```

```hcl
# modules/network/variables.tf
variable "name" {
  description = "Prefix for all resource names."
  type        = string
}

variable "cidr" {
  description = "VPC CIDR block."
  type        = string
  validation {
    condition     = can(cidrnetmask(var.cidr))
    error_message = "cidr must be a valid CIDR block."
  }
}

variable "az_count" {
  description = "Number of availability zones to use."
  type        = number
  default     = 2
}
```

```hcl
# modules/network/main.tf
data "aws_availability_zones" "available" { state = "available" }

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, var.az_count)
}

resource "aws_vpc" "this" {
  cidr_block           = var.cidr
  enable_dns_hostnames = true
  tags                 = { Name = var.name }
}

resource "aws_subnet" "public" {
  for_each                = { for i, az in local.azs : az => i }
  vpc_id                  = aws_vpc.this.id
  availability_zone       = each.key
  cidr_block              = cidrsubnet(var.cidr, 8, each.value)
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.name}-public-${each.key}" }
}

resource "aws_subnet" "private" {
  for_each          = { for i, az in local.azs : az => i }
  vpc_id            = aws_vpc.this.id
  availability_zone = each.key
  cidr_block        = cidrsubnet(var.cidr, 8, each.value + 10)
  tags              = { Name = "${var.name}-private-${each.key}" }
}
# ... internet gateway, NAT, route tables ...
```

```hcl
# modules/network/outputs.tf
output "vpc_id" {
  value = aws_vpc.this.id
}

output "public_subnet_ids" {
  value = [for s in aws_subnet.public : s.id]
}

output "private_subnet_ids" {
  value = [for s in aws_subnet.private : s.id]
}
```

> Naming convention: when a module has one main resource of a type, name
> it `this` (`aws_vpc.this`). It reads well from outside:
> `module.network.aws_vpc.this`.

### Step 3: calling a module

```hcl
# root: environments/dev/main.tf
module "network" {
  source   = "../../modules/network"
  name     = "notes-dev"
  cidr     = "10.0.0.0/16"
  az_count = 2
}

module "app" {
  source     = "../../modules/app"
  name       = "notes-dev"
  vpc_id     = module.network.vpc_id                 # ← a module's output feeds another module
  subnet_ids = module.network.private_subnet_ids
}
```

After adding or changing a `source`, run **`terraform init`** (modules are
downloaded or linked into `.terraform/modules/`).

Addresses inside modules get a prefix: `module.network.aws_vpc.this`,
`module.network.aws_subnet.private["ap-south-1a"]`.

**A module can only see what you pass in.** There are no global
variables. A child can't read the root's `var.x` or `local.y`. This is a
feature: it makes the interface explicit.

### Step 4: module sources

| Source | Example | Versioning |
|---|---|---|
| Local path | `"./modules/network"` | none: it's the same repo, same commit |
| Terraform Registry | `"terraform-aws-modules/vpc/aws"` + `version = "~> 5.0"` | ✅ `version` argument |
| Git | `"git::https://github.com/acme/tf-modules.git//network?ref=v1.4.0"` | ✅ `ref` = tag/commit |
| Git over SSH | `"git::ssh://git@github.com/acme/tf-modules.git//network?ref=v1.4.0"` | ✅ |
| S3 | `"s3::https://s3.amazonaws.com/acme-modules/network-1.4.0.zip"` | by file name |
| Private registry | `"app.terraform.io/acme/network/aws"` + `version` | ✅ |

The `//` separates the repository from a **subfolder** inside it.
**Always pin a version** (a `version` constraint or `?ref=` tag) for
remote modules. `main` changes under your feet.

### Step 5: the public registry: use or build?

`terraform-aws-modules/vpc/aws` and friends (EKS, RDS, security groups,
S3…) are community modules used by thousands of companies:

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name            = "notes-dev"
  cidr            = "10.0.0.0/16"
  azs             = ["ap-south-1a", "ap-south-1b"]
  private_subnets = ["10.0.10.0/24", "10.0.11.0/24"]
  public_subnets  = ["10.0.0.0/24", "10.0.1.0/24"]
  enable_nat_gateway = true
  single_nat_gateway = true
}
```

| Use a public module when… | Write your own when… |
|---|---|
| the domain is standard (VPC, EKS) | you need company-specific rules baked in |
| you want battle-tested edge cases handled | the public module is far more complex than you need |
| | you need tight control over every change |

A common company approach: **thin internal wrapper modules** that call a
pinned public module with the company's defaults.

### Step 6: providers in modules

**Rule: child modules should NOT contain `provider` blocks.** They
**inherit** the default providers from the caller. A module only declares
**which** providers it needs, with a **minimum** version:

```hcl
# modules/network/versions.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"          # minimum only; the ROOT pins the exact range
    }
  }
}
```

**Passing a non-default (aliased) provider** to a module, for example a
module that must deploy to `us-east-1`:

```hcl
# root
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

module "cdn_cert" {
  source = "./modules/acm-cert"
  providers = {
    aws = aws.us_east_1        # "inside the module, 'aws' means this one"
  }
}
```

A module that needs **two** AWS providers at once (e.g. it creates a
cross-region replica) declares **configuration aliases**:

```hcl
# modules/replicated-bucket/versions.tf
terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      configuration_aliases = [aws.primary, aws.replica]
    }
  }
}
# resources inside use: provider = aws.primary / aws.replica

# root
module "bucket" {
  source    = "./modules/replicated-bucket"
  providers = {
    aws.primary = aws
    aws.replica = aws.us_east_1
  }
}
```

Why no provider blocks in modules? A module with its own provider block
**can't be used with `count`/`for_each`**, can't be pointed at different
regions or accounts by callers, and can make resources impossible to
destroy (if you remove the module, you remove its provider config too).

### Step 7: `count` and `for_each` on modules

Since Terraform 0.13, modules take `count`, `for_each`, and `depends_on`:

```hcl
module "service" {
  for_each = {
    api    = { instance_type = "t3.small", min = 2 }
    worker = { instance_type = "t3.micro", min = 1 }
  }

  source        = "./modules/service"
  name          = each.key
  instance_type = each.value.instance_type
  min_size      = each.value.min
  subnet_ids    = module.network.private_subnet_ids
}

# outputs: module.service["api"].url
```

Optional module: `count = var.enable_monitoring ? 1 : 0`, then
`module.monitoring[0].dashboard_url`, or `one(module.monitoring[*].dashboard_url)`.

### Step 8: module design principles

1. **Small, focused interface.** Expose what callers must decide. Hide the rest.
2. **Opinionated defaults.** Encryption on, public access off, sane sizes.
3. **Validate inputs** so errors appear at plan time with clear messages.
4. **Output everything a caller might need** (IDs, ARNs, names, security group IDs). Adding outputs later is easy, but callers can't reach inside.
5. **No hard-coded region, account, or environment.** Take them as inputs or data sources.
6. **Don't over-wrap.** A module that wraps a *single* resource and passes every argument through adds nothing. Modules should represent a **meaningful unit** ("a service", "a network"), not a resource.
7. **Avoid deep nesting.** Root → modules → (maybe) one more level. Deep trees are hard to follow and refactor.
8. **Version and document** with a README, examples, and a CHANGELOG. Use semantic versioning: breaking change = major.

### Step 9: refactoring existing code into a module

You have `aws_vpc.main` in the root and want to move it into
`module.network`. Changing the code alone gives destroy + create. Add
`moved` blocks (lesson 13):

```hcl
moved {
  from = aws_vpc.main
  to   = module.network.aws_vpc.this
}
```

The plan should show **only moves**, with 0 add, 0 change, 0 destroy.

---

## ⚠️ Common mistakes

- **Provider blocks inside child modules.** Declare `required_providers` only, and pass aliased providers explicitly.
- **Unpinned remote modules** (`?ref=main`), which means surprise changes.
- **Exact provider pins in modules** (`= 6.2.0`). They conflict with the root's choice. Modules use `>=`.
- **Forgetting `terraform init`** after changing `source` or `version`.
- **Mega-modules** with 80 variables, which are harder to use than raw resources.
- **Moving code into a module without `moved` blocks.** Everything gets recreated.

---

## 🎤 Interview corner

**Q: Root module vs child module?**

> The root module is the directory where Terraform runs. It owns the
> backend and provider configuration and the state. Child modules are
> called from it (or from other modules) through `module` blocks. They take
> input variables, create resources, and expose outputs, and they can't
> see the caller's variables except what's passed explicitly.

**Q: How should providers be handled in reusable modules?**

> Modules declare `required_providers` with minimum versions but no
> `provider` blocks. They inherit the caller's default providers, and
> aliased providers are passed explicitly via the `providers` map. Modules
> needing several configurations declare `configuration_aliases`. Provider
> blocks inside modules block `count`/`for_each` and cause orphaned-resource
> problems on removal.

**Q: How do you version and distribute modules in a company?**

> In a Git monorepo or per-module repos with semantic-version tags,
> consumed via `?ref=vX.Y.Z` or a private registry with `version`
> constraints. Changes get CI tests (`terraform test`, examples, linting),
> a CHANGELOG, and major bumps for breaking interface changes. `moved`
> blocks are kept in the module so upgrades don't recreate resources.

**Q: When would you *not* create a module?**

> When it would only wrap a single resource and pass arguments through, or
> when the code is used once and unlikely to be reused. Premature modules
> add indirection without benefit.

---

## ✅ Check yourself

1. How does a root module read a child module's value `vpc_id`?
2. Why shouldn't a reusable module contain `provider "aws" { region = ... }`?
3. How do you make a module deploy its resources in `us-east-1` while the rest of your code is in `ap-south-1`?
4. What's `//` in `git::https://github.com/acme/modules.git//network?ref=v1.2.0`?

<details><summary>Answers</summary>

1. `module.<name>.vpc_id`, and only if the child declares `output "vpc_id"`.
2. It couldn't be used with `count`/`for_each`, callers couldn't choose region or account, and removing the module would leave its resources without a provider to destroy them.
3. Define an aliased provider in the root and pass it: `providers = { aws = aws.us_east_1 }`.
4. It separates the repository URL from a subdirectory inside the repository.

</details>

➡️ **Next:** [15 · Environments](15-environments.md)

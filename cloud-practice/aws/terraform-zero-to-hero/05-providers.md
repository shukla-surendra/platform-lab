# 05 · Providers

## 🎯 Goal

Pin provider versions safely, understand the lock file, configure the AWS
provider properly (credentials, default tags, safety checks), and work with
several regions or accounts at once.

---

## 🧠 Mental model: drivers for your printer

Your operating system can print to any printer, but only after you install
that printer's **driver**. Terraform is the same. Terraform Core can
manage anything, but only through a **provider**: a plugin that translates
"`aws_s3_bucket` should exist" into real AWS API calls.

```
 terraform { required_providers { aws = ... } }   ← "I need this driver, this version"
 provider "aws" { region = "ap-south-1" }         ← "configure the driver"
 resource "aws_s3_bucket" ...                     ← "use the driver"
```

---

## 🛠 Walkthrough

### Step 1: declaring a provider

```hcl
terraform {
  required_version = ">= 1.10, < 2.0"     # which Terraform CLI versions may run this

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}
```

**`source`** is a registry address: `[hostname/]namespace/type`. The
hostname defaults to `registry.terraform.io`, so `hashicorp/aws` means
`registry.terraform.io/hashicorp/aws`.

The key (`aws`) is the **local name**. Resources whose type starts with
`aws_` automatically use the provider with local name `aws`.

### Step 2: version constraints

| Constraint | Means | Allows |
|---|---|---|
| `= 6.2.0` | exactly | 6.2.0 only |
| `>= 6.0` | at least | 6.0, 6.5, 7.0, 12.0… (risky: allows major upgrades) |
| `>= 6.0, < 7.0` | a range | any 6.x |
| **`~> 6.0`** | "pessimistic": the **last** number may grow | ≥6.0 and <7.0 |
| **`~> 6.2.1`** | the last number may grow | ≥6.2.1 and <6.3.0 |
| `!= 6.3.0` | exclude a known-bad version | |

`~>` is the one you'll use most. Remember that it only lets the
**rightmost** number you wrote increase.

**Why pin at all?** Major versions of a provider contain breaking changes
(renamed arguments, changed defaults). Without a constraint, a teammate's
`terraform init` next month could pull a new major version and break everything.

### Step 3: the dependency lock file

After `terraform init`, Terraform writes `.terraform.lock.hcl`:

```hcl
provider "registry.terraform.io/hashicorp/aws" {
  version     = "6.4.0"
  constraints = "~> 6.0"
  hashes = [
    "h1:abc...",
    "zh:def...",
  ]
}
```

Two different jobs:

| | `version = "~> 6.0"` in code | `.terraform.lock.hcl` |
|---|---|---|
| Says | which versions are **acceptable** | which exact version was **chosen** |
| Changes when | you edit it | you run `terraform init -upgrade` |
| Protects against | incompatible majors | "works on my machine": everyone uses 6.4.0 |
| Also | | checksums, so a tampered download is rejected |

**Commit the lock file.** To upgrade on purpose: `terraform init -upgrade`,
test, then commit the new lock file.

> Team tip: the lock file stores checksums **per platform**. If you work on
> a Mac and CI runs on Linux, record both:
> `terraform providers lock -platform=darwin_arm64 -platform=linux_amd64`

### Step 4: configuring the AWS provider well

```hcl
provider "aws" {
  region = "ap-south-1"

  # 1. Tags added to EVERY resource this provider creates
  default_tags {
    tags = {
      Project   = "notes-app"
      ManagedBy = "terraform"
    }
  }

  # 2. Safety: refuse to run against any other account
  allowed_account_ids = ["111122223333"]
}
```

**`default_tags`** removes the need to repeat tags on every resource.
Tags set on a resource are **merged** with the defaults (resource tags win
on conflict). Each resource then has two attributes: `tags` (what you
wrote) and `tags_all` (what AWS gets: your tags + default tags).

**`allowed_account_ids`** is a cheap seat belt. If someone's shell is
pointed at the wrong account (say, prod instead of dev), Terraform stops
before doing anything.

### Step 5: assuming a role

In real organisations you rarely use your own user directly. You **assume
a role** in the target account:

```hcl
provider "aws" {
  region = "ap-south-1"

  assume_role {
    role_arn     = "arn:aws:iam::111122223333:role/terraform-deployer"
    session_name = "terraform"
  }
}
```

Your base credentials (profile, SSO, or CI identity) are used to call
`sts:AssumeRole`, and every AWS call after that uses the role. This is how
one CI pipeline deploys to many accounts.

### Step 6: several regions: provider aliases

A classic real case: **CloudFront requires its TLS certificate (ACM) to
live in `us-east-1`**, but the rest of your app is in Mumbai.

```hcl
provider "aws" {                       # the default provider (no alias)
  region = "ap-south-1"
}

provider "aws" {                       # a second configuration of the same plugin
  alias  = "us_east_1"
  region = "us-east-1"
}

resource "aws_s3_bucket" "assets" {    # uses the default → ap-south-1
  bucket = "notes-app-assets-7f3k9"
}

resource "aws_acm_certificate" "cdn" { # uses the alias → us-east-1
  provider          = aws.us_east_1
  domain_name       = "notes.example.com"
  validation_method = "DNS"
}
```

- A provider block **without** `alias` is the default for its type.
- A block **with** `alias` is only used where you say `provider = aws.<alias>`.

> In AWS provider v6 and later, many resources also accept a `region`
> argument directly, which removes the need for an alias in simple
> multi-region cases. Aliases are still how you work with **several
> accounts**, and how you pass providers into modules (lesson 14).

### Step 7: several accounts

The same idea, with a different role per alias:

```hcl
provider "aws" {
  alias  = "network"
  region = "ap-south-1"
  assume_role { role_arn = "arn:aws:iam::222233334444:role/terraform" }
}

provider "aws" {
  alias  = "app"
  region = "ap-south-1"
  assume_role { role_arn = "arn:aws:iam::555566667777:role/terraform" }
}

# e.g. accept a VPC peering request on the network account's side
resource "aws_vpc_peering_connection_accepter" "peer" {
  provider                  = aws.network
  vpc_peering_connection_id = aws_vpc_peering_connection.app_to_network.id
  auto_accept               = true
}
```

### Step 8: the providers you'll meet besides AWS

| Provider | Typical use |
|---|---|
| `hashicorp/random` | random suffixes, passwords (`random_id`, `random_password`) |
| `hashicorp/tls` | generate keys and certificates |
| `hashicorp/archive` | zip a folder (e.g. Lambda code) |
| `hashicorp/http` | fetch a URL at plan time |
| `hashicorp/kubernetes`, `hashicorp/helm` | deploy into EKS after creating it |
| `integrations/github`, `DataDog/datadog`, `cloudflare/cloudflare` | SaaS as code |

A resource from any of these works exactly like an AWS resource.

---

## ⚠️ Common mistakes

- **No version constraint at all.** It works today and breaks on the next major release.
- **`>= 5.0` instead of `~> 5.0`.** That also allows 6.0, 7.0…
- **Not committing the lock file**, or committing it with only a Mac hash so CI fails with a checksum error.
- **Forgetting `provider = aws.us_east_1`** on the ACM certificate. It gets created in the default region, and CloudFront rejects it.
- **Credentials in the provider block.** Use profiles, SSO, roles, or CI identity (OIDC, lesson 21).

---

## 🎤 Interview corner

**Q: What is the `.terraform.lock.hcl` file and should it be committed?**

> It records the exact provider versions selected by `init` plus
> checksums of the packages. Committing it ensures every teammate and CI
> job uses identical provider builds, and the checksums protect against
> tampered downloads. Version constraints in code say what's *allowed*;
> the lock file pins what's *used*. You change it deliberately with
> `terraform init -upgrade`.

**Q: How do you deploy to multiple regions or accounts from one configuration?**

> Define several `provider` blocks for the same provider with different
> `alias` values, each with its own region or `assume_role`. Then set
> `provider = aws.<alias>` on resources, or pass aliased providers into
> modules via the `providers` map. A common example is ACM certificates in
> `us-east-1` for CloudFront.

**Q: What does `~> 1.2.0` allow?**

> 1.2.0 up to but not including 1.3.0. Only the rightmost specified
> component may increase.

---

## ✅ Check yourself

1. What does `~> 6.0` allow? And `~> 6.0.0`?
2. What's the difference between `tags` and `tags_all`?
3. You add an aliased provider for `us-east-1`. Which region does a resource *without* a `provider` argument use?
4. A teammate on Linux gets a checksum error from your lock file. Why, and what's the fix?

<details><summary>Answers</summary>

1. `~> 6.0` → any 6.x. `~> 6.0.0` → only 6.0.x.
2. `tags` is what you wrote on the resource. `tags_all` is that merged with the provider's `default_tags`, which is what AWS actually receives.
3. The default (non-aliased) provider's region.
4. The lock file only has hashes for your platform. Run `terraform providers lock -platform=darwin_arm64 -platform=linux_amd64` and commit the result.

</details>

➡️ **Next:** [06 · Resources, data sources, and references](06-resources-and-data-sources.md)

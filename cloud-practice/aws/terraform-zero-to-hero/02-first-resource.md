# 02 · Your first resource

## 🎯 Goal

Go from nothing to a real S3 bucket created by Terraform, and understand
every line you wrote and every command you ran.

---

## 🧠 Mental model: four commands, one loop

```
 terraform init      "get ready"        downloads the AWS provider plugin
      │
 terraform plan      "what would you do?"   shows changes, touches nothing
      │
 terraform apply     "do it"            makes the changes, records them in state
      │
 terraform destroy   "undo it all"      deletes everything this code created
```

You'll run `plan` → `apply` hundreds of times. `init` runs once per
project, plus again when you add providers or modules.

---

## 🛠 Walkthrough

### Step 1: install Terraform

```bash
# macOS
brew tap hashicorp/tap && brew install hashicorp/tap/terraform

terraform version      # Terraform v1.x.x
```

> Terraform is a single binary. There's no server and no daemon. It runs,
> does its job, and exits.

### Step 2: give Terraform AWS credentials

Terraform's AWS provider finds credentials **the same way the AWS CLI
does**, in this order (first match wins):

1. arguments in the `provider` block (avoid this, since secrets would end up in code);
2. environment variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`;
3. the shared files `~/.aws/credentials` and `~/.aws/config` (with `AWS_PROFILE` to pick a profile, including SSO profiles);
4. container or instance roles (ECS task role, EC2 instance profile), which is how it works inside AWS.

If this works, Terraform will work:

```bash
aws sts get-caller-identity
```

> **Rule for life:** never put access keys in `.tf` files. Code goes into
> Git, and Git is forever.

### Step 3: write the code

Create a folder `notes-app/` with one file, `main.tf`:

```hcl
# 1. Which plugins this project needs, and which versions
terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"   # registry.terraform.io/hashicorp/aws
      version = "~> 6.0"          # any 6.x, never 7.0
    }
  }
}

# 2. Configure the AWS plugin
provider "aws" {
  region = "ap-south-1"
}

# 3. The thing we want to exist
resource "aws_s3_bucket" "assets" {
  bucket = "notes-app-assets-7f3k9"   # bucket names are global: make yours unique

  tags = {
    Project = "notes-app"
  }
}
```

Let's read it slowly.

**The `terraform` block** configures Terraform itself: which Terraform
versions may run this code, and which providers to download.

**The `provider "aws"` block** configures the AWS plugin. Here that's just
the region.

**The `resource` block** is the heart of Terraform. Its anatomy:

```
resource  "aws_s3_bucket"  "assets"  {  bucket = "notes-app-assets-7f3k9"  }
   │            │             │                 │
 keyword    RESOURCE TYPE   LOCAL NAME     ARGUMENTS
            (from provider: (your label,   (settings of the bucket;
            aws_ + service)  used inside    what's allowed is defined
                             your code)     by the provider)
```

- The **type** `aws_s3_bucket` says what kind of thing it is. The prefix
  `aws_` tells Terraform which provider handles it.
- The **local name** `assets` is *your* label. AWS never sees it. It only
  exists so you can refer to this bucket elsewhere in the code as
  `aws_s3_bucket.assets`.
- Together, `aws_s3_bucket.assets` is the resource's **address**, its
  unique name inside this project.

### Step 4: `terraform init`

```bash
cd notes-app
terraform init
```

```
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 6.0"...
- Installing hashicorp/aws v6.x.x...
Terraform has been successfully initialized!
```

What just appeared in your folder:

```
notes-app/
├── main.tf
├── .terraform/             ← downloaded provider binary (big, never commit it)
└── .terraform.lock.hcl     ← exact provider version + checksums (DO commit it)
```

### Step 5: `terraform plan`

```bash
terraform plan
```

```
Terraform will perform the following actions:

  # aws_s3_bucket.assets will be created
  + resource "aws_s3_bucket" "assets" {
      + arn            = (known after apply)
      + bucket         = "notes-app-assets-7f3k9"
      + id             = (known after apply)
      + region         = (known after apply)
      + tags           = {
          + "Project" = "notes-app"
        }
      ...
    }

Plan: 1 to add, 0 to change, 0 to destroy.
```

How to read it:

- `+` means **create**.
- The values you set (`bucket`, `tags`) are shown.
- **`(known after apply)`** marks values AWS decides, like the ARN. Terraform
  can't know them until the bucket exists. This idea becomes very
  important later (lessons 09 and 17).
- The summary line is what you check first, every single time.

`plan` **changes nothing**. It's always safe to run.

### Step 6: `terraform apply`

```bash
terraform apply
```

Terraform shows the plan again and asks:

```
Do you want to perform these actions?
  Enter a value: yes

aws_s3_bucket.assets: Creating...
aws_s3_bucket.assets: Creation complete after 2s [id=notes-app-assets-7f3k9]

Apply complete! Resources: 1 added, 0 changed, 0 destroyed.
```

A new file appears: **`terraform.tfstate`**. Open it and you'll find JSON
recording "`aws_s3_bucket.assets` is the real bucket `notes-app-assets-7f3k9`",
along with all its attributes. That's Terraform's memory.

Run `terraform plan` again:

```
No changes. Your infrastructure matches the configuration.
```

That's idempotence in action.

### Step 7: change something

Add a tag:

```hcl
  tags = {
    Project = "notes-app"
    Owner   = "platform-team"
  }
```

```bash
terraform plan
```

```
  # aws_s3_bucket.assets will be updated in-place
  ~ resource "aws_s3_bucket" "assets" {
      ~ tags = {
          + "Owner"   = "platform-team"
            "Project" = "notes-app"
        }
    }
Plan: 0 to add, 1 to change, 0 to destroy.
```

`~` means **update in place**: the same bucket, just edited. Apply it.

Now change the bucket **name** and plan:

```
  # aws_s3_bucket.assets must be replaced
-/+ resource "aws_s3_bucket" "assets" {
      ~ bucket = "notes-app-assets-7f3k9" -> "notes-app-assets-NEW" # forces replacement
```

`-/+` means **destroy, then create**. S3 can't rename a bucket, so the only
way to "change" the name is a new bucket. The old one, **and its contents**,
would be deleted. Put the name back. You've just learned the most
important habit in Terraform: **always read the plan**.

### Step 8: `terraform destroy`

```bash
terraform destroy
```

```
  # aws_s3_bucket.assets will be destroyed
  - resource "aws_s3_bucket" "assets" { ... }
Plan: 0 to add, 0 to change, 1 to destroy.
  Enter a value: yes
Destroy complete! Resources: 1 destroyed.
```

`destroy` deletes **only what's in this project's state**. It can't touch
anything Terraform didn't create or import.

---

## ⚠️ Common mistakes

- **Committing `.terraform/` or `terraform.tfstate` to Git.** The first is large binaries. The second can contain **secrets** (lesson 19) and belongs in remote storage (lesson 12). Add both to `.gitignore`.
- **Not committing `.terraform.lock.hcl`.** Without it, teammates and CI may download a different provider version than you tested with.
- **Skimming the plan.** `-/+` and `-` lines mean data loss. Read the summary line and search for them every time.
- **Bucket name clash.** S3 names are unique across *all* AWS accounts. `BucketAlreadyExists` means someone somewhere has that name.
- **Hard-coding keys in the provider block.** Use profiles, SSO, or roles.

A good starter `.gitignore`:

```gitignore
.terraform/
*.tfstate
*.tfstate.*
*.tfplan
crash.log
*.tfvars          # if your tfvars contain anything sensitive
```

---

## 🎤 Interview corner

**Q: What does `terraform init` do?**

> It prepares the working directory. It downloads the providers listed in
> `required_providers` (respecting the lock file), downloads any modules,
> and configures the backend where state is stored. It's safe to re-run,
> and you must re-run it after adding providers, modules, or changing the
> backend.

**Q: What's the difference between `plan` and `apply`?**

> `plan` refreshes Terraform's view of real infrastructure, compares it
> with the configuration, and shows the proposed changes without changing
> anything. `apply` creates a plan (or uses a saved one) and executes it,
> then updates the state. In production you usually save the plan
> (`plan -out`) and apply exactly that file, so what was reviewed is what runs.

**Q: What does `(known after apply)` mean?**

> The value is determined by the provider or cloud only when the resource
> is created, like an ID or an ARN. Terraform represents it as an
> *unknown value* during planning and anything that depends on it is also
> unknown until apply.

---

## ✅ Check yourself

1. What's the address of the resource in this lesson, and which part does AWS never see?
2. Which file must you commit: `.terraform/` or `.terraform.lock.hcl`?
3. What do `+`, `~`, and `-/+` mean in a plan?
4. You delete the `resource "aws_s3_bucket" "assets"` block and run `apply`. What happens?

<details><summary>Answers</summary>

1. `aws_s3_bucket.assets`. The local name `assets` exists only in your code.
2. `.terraform.lock.hcl`. `.terraform/` is a download cache.
3. Create, update in place, and replace (destroy then create).
4. Terraform destroys the bucket, because it's in the state but no longer in the code.

</details>

➡️ **Next:** [03 · The core workflow in depth](03-core-workflow.md)

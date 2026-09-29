# 07 · Variables, locals, and outputs

## 🎯 Goal

Make `notes-app` configurable (so the same code builds dev and prod),
tidy repeated expressions with locals, and expose results with outputs.
Know **variable precedence** by heart, because it comes up in almost every interview.

---

## 🧠 Mental model: a function

A Terraform configuration behaves like a function:

```
             ┌─────────────────────────────────┐
 variables → │  locals (private helper values)  │ → outputs
  (inputs)   │  resources, data sources         │   (return values)
             └─────────────────────────────────┘
```

| Concept | Like in programming | Who sets it |
|---|---|---|
| `variable` | function **parameter** | the caller (CLI, tfvars, CI, parent module) |
| `locals` | local **variable** inside the function | the code itself |
| `output` | **return** value | the code; read by humans, scripts, other configs |

---

## 🛠 Walkthrough

### Step 1: declaring variables

By convention, put them in `variables.tf`:

```hcl
variable "environment" {
  description = "Deployment environment: dev, staging, or prod."
  type        = string
  # no default → REQUIRED: Terraform asks for it if not provided
}

variable "instance_type" {
  description = "EC2 size for the web server."
  type        = string
  default     = "t3.micro"         # has a default → OPTIONAL
}

variable "allowed_cidrs" {
  description = "Networks allowed to reach the app."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
```

Use them with `var.<name>`:

```hcl
resource "aws_instance" "web" {
  instance_type = var.instance_type
  tags          = { Environment = var.environment }
}
```

**Always write `description` and `type`.** The description is your
documentation, and the type catches mistakes early.

### Step 2: validation: reject bad input early

```hcl
variable "environment" {
  type = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging, or prod."
  }
}

variable "instance_type" {
  type    = string
  default = "t3.micro"

  validation {
    condition     = can(regex("^t3\\.", var.instance_type))
    error_message = "Only t3 instance types are allowed in this project."
  }
}
```

`terraform plan -var environment=production` now fails **before touching
AWS**, with your message. You can have several `validation` blocks. Since
Terraform 1.9, a condition may also refer to *other* variables (for
example, "`max_size` must be ≥ `min_size`").

### Step 3: other variable options

```hcl
variable "db_password" {
  type      = string
  sensitive = true     # hide the value in plan/apply output: (sensitive value)
}

variable "vpc_id" {
  type     = string
  default  = null
  nullable = true      # (the default) null is an allowed value
}
```

- **`sensitive = true`** only **hides** the value in CLI output. It is
  **still stored in plain text in the state file**. Lesson 19 covers the
  real solutions.
- **`nullable = false`** means that if a caller passes `null`, the default
  is used instead. That's useful in modules.

### Step 4: giving variables values (six ways)

```bash
# 1. Default in the variable block (lowest priority)

# 2. Environment variable: TF_VAR_<name>
export TF_VAR_environment=dev

# 3. terraform.tfvars (loaded automatically)
# 4. terraform.tfvars.json (loaded automatically)
# 5. *.auto.tfvars / *.auto.tfvars.json (loaded automatically, alphabetical order)

# 6. Command line, highest priority, in the order you write them
terraform plan -var-file=prod.tfvars -var 'instance_type=t3.small'
```

A tfvars file is just assignments:

```hcl
# prod.tfvars
environment   = "prod"
instance_type = "t3.small"
allowed_cidrs = ["10.0.0.0/8"]
```

If a required variable has no value from any source, Terraform prompts
you interactively (and in CI, where there's no prompt, it errors).

### Step 5: ⭐ variable precedence (memorise this)

Later in this list **wins** over earlier:

```
 1. default in variable block            ← lowest
 2. TF_VAR_name environment variables
 3. terraform.tfvars
 4. terraform.tfvars.json
 5. *.auto.tfvars / *.auto.tfvars.json   (in lexical filename order)
 6. -var and -var-file on the command line (in the order given; last wins)  ← highest
```

A trick to remember it: **"the closer to the command, the stronger."**
Defaults live in the code, env vars live in your shell, files sit in the
folder, and flags are typed right on the command.

**Example.** `default = "t3.micro"`, `TF_VAR_instance_type=t3.small`,
`terraform.tfvars` says `t3.medium`, and you run `-var instance_type=t3.large`.
Result: **`t3.large`**. Remove the `-var` flag and it's `t3.medium`.

> ⚠️ **Gotcha:** `terraform.tfvars` beats `TF_VAR_…`. People expect the
> environment variable to win and are surprised.

### Step 6: locals: name your intermediate values

When the same expression appears in several places, give it a name:

```hcl
locals {
  name_prefix = "notes-app-${var.environment}"
  is_prod     = var.environment == "prod"

  common_tags = {
    Project     = "notes-app"
    Environment = var.environment
  }
}

resource "aws_s3_bucket" "assets" {
  bucket = "${local.name_prefix}-assets"
  tags   = local.common_tags
}

resource "aws_instance" "web" {
  instance_type = local.is_prod ? "t3.small" : "t3.micro"
  tags          = merge(local.common_tags, { Name = "${local.name_prefix}-web" })
}
```

Note the naming quirk: the block is **`locals`** (plural), but you refer
to a value as **`local.name`** (singular).

| Use a **variable** when… | Use a **local** when… |
|---|---|
| the *caller* should decide the value | the value is *derived* from other values |
| it differs between environments | you'd otherwise repeat an expression |

Don't turn everything into a variable. Each variable is a knob someone
can misconfigure. Expose only what should really change.

### Step 7: outputs: return values

```hcl
output "web_public_ip" {
  description = "Public IP of the web server."
  value       = aws_instance.web.public_ip
}

output "assets_bucket" {
  value = aws_s3_bucket.assets.bucket
}

output "db_connection_string" {
  value     = "postgres://app@${aws_db_instance.main.address}:5432/notes"
  sensitive = true      # REQUIRED if the value includes anything sensitive
}
```

After `apply`:

```bash
terraform output                       # all outputs (sensitive ones shown as <sensitive>)
terraform output -raw web_public_ip    # 13.235.10.20: perfect for scripts
curl "http://$(terraform output -raw web_public_ip)"
terraform output -json                 # everything, machine-readable (sensitive values INCLUDED)
```

Outputs have three audiences:
1. **Humans**: "where's my app?"
2. **Scripts and CI**: `terraform output -raw …`
3. **Other Terraform code**: a parent module reads a child's outputs
   (lesson 14), and another configuration can read them via remote state (lesson 12).

### Step 8: sensitivity is contagious

If a variable is `sensitive`, anything computed from it is sensitive too:

```hcl
variable "db_password" { sensitive = true }

output "conn" {
  value = "postgres://app:${var.db_password}@host/db"
}
```

```
Error: Output refers to sensitive values
  To reduce the risk of accidentally exporting sensitive data that was intended to be
  only internal, Terraform requires that any root module output containing sensitive
  data be explicitly marked as sensitive, to confirm your intent.
```

Terraform won't let a secret leak into an output silently. You have to
add `sensitive = true` to the output. (`nonsensitive()` exists to remove
the mark on purpose, when you're sure.)

### Step 9: the standard file layout

```
notes-app/
├── versions.tf       terraform { required_version, required_providers }
├── providers.tf      provider "aws" { ... }
├── variables.tf      all variable blocks
├── locals.tf         locals (optional, or put them in main.tf)
├── main.tf           resources (or split by area: network.tf, compute.tf…)
├── outputs.tf        all output blocks
└── terraform.tfvars  values for this environment
```

Terraform doesn't care about any of these file names. Your teammates will,
because this layout is what they expect to find.

---

## ⚠️ Common mistakes

- **Secrets in `terraform.tfvars` committed to Git.** Use env vars in CI, a secrets manager, or generated passwords (lesson 19).
- **Thinking `sensitive` encrypts.** It only hides output. The state still has the value in plain text.
- **Too many variables.** Every one is an extra decision for callers. Derive with locals where you can.
- **Using `-var` for everything in CI.** Long command lines are hard to review. Prefer per-environment tfvars files that are committed.
- **Expecting `TF_VAR_` to beat `terraform.tfvars`.** It doesn't.

---

## 🎤 Interview corner

**Q: What's the order of precedence for variable values?**

> From lowest to highest: the variable's default, `TF_VAR_` environment
> variables, `terraform.tfvars`, `terraform.tfvars.json`, `*.auto.tfvars`
> files in lexical order, then `-var` and `-var-file` flags in the order
> given on the command line. The last one wins.

**Q: Variables vs locals?**

> Variables are inputs set by the caller and are part of the interface.
> Locals are internal, derived values that aren't settable from outside.
> They reduce repetition and give names to expressions. Rule of thumb:
> expose a variable only if the value legitimately differs per caller or
> environment.

**Q: Does `sensitive = true` protect my secret?**

> Only from being displayed in plan/apply output and logs. The value is
> still stored in plain text in the state and in saved plan files. Real
> protection comes from an encrypted, access-controlled backend,
> avoiding secrets in state where possible (managed passwords, ephemeral
> values, write-only arguments), and fetching secrets at runtime.

---

## ✅ Check yourself

1. `default = "a"`, `TF_VAR_x=b`, `terraform.tfvars` has `x = "c"`, and `dev.auto.tfvars` has `x = "d"`. What's `var.x`?
2. Same, plus `-var x=e -var-file=other.tfvars` where `other.tfvars` has `x = "f"`?
3. What's the difference between `locals {}` and `local.`?
4. Why does Terraform force you to mark some outputs `sensitive`?

<details><summary>Answers</summary>

1. `"d"`. Auto tfvars beat `terraform.tfvars`, which beats the env var.
2. `"f"`. Both are command-line flags, and the later one (`-var-file=other.tfvars`) wins.
3. `locals` is the block where you define them. `local.<name>` is how you reference one.
4. Their values derive from sensitive values, and Terraform wants explicit confirmation before exposing them.

</details>

➡️ **Next:** [08 · Expressions and functions](08-expressions-and-functions.md)

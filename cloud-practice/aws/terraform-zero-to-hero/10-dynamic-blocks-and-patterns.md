# 10 · Dynamic blocks and advanced patterns

## 🎯 Goal

Generate repeated **nested blocks**, build nested loops, write flexible
object inputs with `optional()`, and know the handful of patterns that
separate intermediate from advanced Terraform code. Also learn when **not**
to use them.

---

## 🧠 Mental model: blocks are not values

This single idea explains why `dynamic` exists:

```hcl
tags = { Name = "web" }      # an ARGUMENT: its value is a map, a VALUE.
                             # You can compute it with for, merge, anything.

ingress {                    # a BLOCK: it's STRUCTURE, not a value.
  from_port = 443            # You can't write "ingress = [for ...]".
}
```

Expressions produce **values**, and blocks aren't values. So to generate
blocks from data, Terraform needs a special construct: the **`dynamic` block**.
(Lesson 18 shows how this falls out of the way HCL is parsed.)

---

## 🛠 Walkthrough

### Step 1: `dynamic`: generate nested blocks

Some resources only accept certain settings as nested blocks. Example: an
S3 lifecycle configuration with one `rule` block per rule. Data:

```hcl
variable "lifecycle_rules" {
  default = {
    logs    = { prefix = "logs/",    expire_days = 30 }
    exports = { prefix = "exports/", expire_days = 7 }
  }
}
```

Without `dynamic`, you'd copy the `rule { }` block by hand. With it:

```hcl
resource "aws_s3_bucket_lifecycle_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  dynamic "rule" {                         # name = the block type to generate
    for_each = var.lifecycle_rules         # one block per item
    content {                              # the body of each generated block
      id     = rule.key                    # iterator is named after the block: "rule"
      status = "Enabled"

      filter {
        prefix = rule.value.prefix
      }

      expiration {
        days = rule.value.expire_days
      }
    }
  }
}
```

This generates two `rule { }` blocks. Things to know:

- Inside `content`, the **iterator** has the block's name (`rule.key`, `rule.value`).
  You can rename it with `iterator = r` (then `r.key`, `r.value`). That's
  useful when nesting.
- `for_each` here takes any list, set, or map, and it can even use values
  unknown until apply. It's not the resource-level `for_each`.
- **Optional block** trick: 0 or 1 blocks based on a condition:

```hcl
dynamic "logging" {
  for_each = var.log_bucket == null ? [] : [var.log_bucket]
  content {
    target_bucket = logging.value
  }
}
```

### Step 2: when NOT to use `dynamic`

Overused `dynamic` blocks make code unreadable. **Prefer, in this order:**

1. A **separate resource** per item if the provider offers one. For
   example, `aws_vpc_security_group_ingress_rule` with `for_each` instead of
   `dynamic "ingress"`. It's clearer, and each rule has its own identity.
2. Plain, literal blocks if there are only 1–3 and they rarely change.
3. `dynamic` when the number of blocks really comes from input data (mostly inside reusable modules).

### Step 3: nested loops: `flatten` into one map

A very common real problem: "for each VPC, for each AZ, make a subnet".
`for_each` needs **one flat map**, but your data is **nested**.

```hcl
variable "vpcs" {
  default = {
    app  = { cidr = "10.0.0.0/16", azs = ["ap-south-1a", "ap-south-1b"] }
    data = { cidr = "10.1.0.0/16", azs = ["ap-south-1a"] }
  }
}
```

Recipe, in three moves:

```hcl
locals {
  # 1. a nested for → a LIST OF LISTS of objects
  # 2. flatten → a single list of objects
  subnet_list = flatten([
    for vpc_name, vpc in var.vpcs : [
      for i, az in vpc.azs : {
        key      = "${vpc_name}-${az}"         # a unique, stable key
        vpc_name = vpc_name
        az       = az
        cidr     = cidrsubnet(vpc.cidr, 8, i)
      }
    ]
  ])

  # 3. turn the list into a MAP keyed by the unique key
  subnets = { for s in local.subnet_list : s.key => s }
}

resource "aws_subnet" "this" {
  for_each          = local.subnets
  vpc_id            = aws_vpc.this[each.value.vpc_name].id
  availability_zone = each.value.az
  cidr_block        = each.value.cidr
}
# addresses: aws_subnet.this["app-ap-south-1a"], ["app-ap-south-1b"], ["data-ap-south-1a"]
```

**nested `for` → `flatten` → `{ for … : key => … }`**. Learn this recipe
once and you'll use it forever. `setproduct(a, b)` is an alternative when
you need *every* combination of two independent lists.

### Step 4: `optional()`: friendly object inputs

Objects with many fields are painful if callers must set every one.
Since Terraform 1.3, attributes can be optional, with defaults:

```hcl
variable "service" {
  type = object({
    name          = string
    instance_type = optional(string, "t3.micro")
    min_size      = optional(number, 1)
    max_size      = optional(number, 3)
    public        = optional(bool, false)
    tags          = optional(map(string), {})
  })
}

# caller only sets what differs:
service = { name = "api", max_size = 6 }
# Terraform fills in: instance_type="t3.micro", min_size=1, public=false, tags={}
```

This works inside maps too (`map(object({ … optional(…) … }))`), which
makes it perfect for "a map of services, each with sensible defaults".

### Step 5: the "merge defaults" tagging pattern

```hcl
locals {
  base_tags = { Project = "notes-app", Environment = var.environment }
}

resource "aws_instance" "web" {
  tags = merge(local.base_tags, var.extra_tags, { Name = "web" })   # later maps win
}
```

With AWS, `default_tags` in the provider (lesson 05) handles the global
tags, and `merge` handles per-resource ones.

### Step 6: `try` and `can` for tolerant code

```hcl
# read a deeply nested optional value with a fallback
port = try(var.config.database.port, 5432)

# validate a format
validation {
  condition     = can(cidrnetmask(var.vpc_cidr))
  error_message = "vpc_cidr must be a valid CIDR block."
}
```

### Step 7: `terraform_data`: a resource that does nothing (usefully)

`terraform_data` (built-in since 1.4, replacing the old `null_resource`)
is a resource that just stores a value. It's used to:

- trigger replacements (`replace_triggered_by`, lesson 09);
- attach provisioners (below) to something.

```hcl
resource "terraform_data" "schema_version" {
  input = var.schema_version     # change it → this resource is replaced
}
```

### Step 8: provisioners, the last resort

Provisioners run commands during create or destroy:

```hcl
resource "terraform_data" "notify" {
  triggers_replace = [aws_instance.web.id]

  provisioner "local-exec" {            # runs on the machine running Terraform
    command = "echo 'deployed ${aws_instance.web.id}' >> deploys.log"
  }
}
```

There's also `remote-exec` (SSH into the server) and `file` (copy a file).

**HashiCorp itself calls provisioners a last resort.** Why:

- Terraform can't plan what a script will do, so it's invisible in the plan.
- If a script fails, the resource is marked **tainted** and gets replaced next time.
- `remote-exec` needs network access and SSH keys from wherever Terraform runs.

Better alternatives: **`user_data`** / cloud-init for boot-time setup;
**pre-baked AMIs** (Packer) for software; **SSM**, Ansible, or your CI
pipeline for app deployments; **Lambda** or Step Functions for workflows.

### Step 9: patterns cheat card

| Need | Pattern |
|---|---|
| resource on/off | `count = var.enabled ? 1 : 0` |
| nested block on/off | `dynamic "x" { for_each = var.enabled ? [1] : [] }` |
| argument on/off | `arg = var.enabled ? value : null` |
| many similar resources | `for_each` over a map |
| nested loop | nested `for` → `flatten` → map |
| every combination | `setproduct` |
| friendly complex input | `object({ … optional(…, default) … })` |
| default + override tags | `merge(defaults, overrides)` |
| read maybe-missing value | `try(a.b.c, default)` |
| force a replacement on some change | `terraform_data` + `replace_triggered_by` |

---

## ⚠️ Common mistakes

- **Using the resource name as the iterator** inside `dynamic`. It's the *block* name (`rule.value`), not `each.value`. (`each` is only for resource-level `for_each`.)
- **Nesting 3 levels of `dynamic`.** Nobody can review that. Flatten the data first, or split into separate resources.
- **Keys that aren't unique** after flattening, which gives a "duplicate object key" error. Build keys from *all* the looping variables.
- **Provisioners for configuration management.** Use user data, images, or SSM.

---

## 🎤 Interview corner

**Q: What is a dynamic block and when shouldn't you use it?**

> It generates repeated nested blocks from a collection, because nested
> blocks are structure, not values, so a `for` expression can't produce
> them. Use it when the number of blocks comes from input, typically in
> modules. Avoid it when a standalone resource exists for each item (like
> separate security group rule resources), or when a few literal blocks
> would be clearer. Heavy `dynamic` nesting hurts readability.

**Q: How do you create resources for a nested data structure, like subnets per AZ per VPC?**

> Flatten it into a single map with stable unique keys: a nested `for`
> expression inside `flatten()`, then a `for` expression that builds a map
> keyed on a composite key like `"${vpc}-${az}"`. Then `for_each` over
> that map.

**Q: Why are provisioners discouraged?**

> Their effects aren't represented in the plan or state, failures taint
> resources, and they require connectivity and credentials from the
> Terraform runner. Declarative alternatives (user data, pre-built images,
> configuration management, or pipelines) are more reliable.

---

## ✅ Check yourself

1. Why can't you write `ingress = [for r in var.rules : {...}]` on an `aws_security_group`, when `tags = {...}` works?
2. Inside `dynamic "rule" { ... }`, how do you read the current item's value?
3. What does `optional(number, 1)` do?
4. You have 3 environments × 2 AZs. What function gives you all 6 pairs?

<details><summary>Answers</summary>

1. `ingress` is defined in the provider schema as a nested **block**, and blocks can't be assigned values. `tags` is an argument whose value is a map.
2. `rule.value` (and `rule.key`), unless you set `iterator = something`.
3. The attribute may be omitted by the caller, and then it defaults to `1`.
4. `setproduct(var.envs, var.azs)`.

</details>

➡️ **Next:** [11 · State deep dive](11-state-deep-dive.md)

# 04 · HCL syntax and types

## 🎯 Goal

Read and write any Terraform file comfortably. Know the few grammar rules
of HCL and every data type, and when each one is used.

---

## 🧠 Mental model: only two building blocks

**HCL** (HashiCorp Configuration Language) is surprisingly small. The
whole language is built from just **two** things:

```
ARGUMENT   name = value               bucket = "notes-app-assets"

BLOCK      type "label" "label" {     resource "aws_s3_bucket" "assets" {
             ...arguments...            bucket = "notes-app-assets"
             ...nested blocks...        tags   = { Project = "notes" }
           }                          }
```

That's it. Every Terraform file is **blocks containing arguments and more
blocks**. What makes it "Terraform" rather than generic HCL is *which*
block types are allowed. That's decided by Terraform (for `resource`,
`variable`, and so on) and by providers (for what goes inside a resource).

---

## 🛠 Walkthrough

### Step 1: blocks

```hcl
resource "aws_instance" "web" {      # block type: resource, 2 labels
  instance_type = "t3.micro"         # argument

  root_block_device {                # NESTED block, 0 labels
    volume_size = 20
  }
}
```

- A **block type** is the first word (`resource`, `variable`, `provider`…).
- **Labels** are the quoted strings after it. How many depends on the
  type: `resource` needs 2 (type + name), `variable` needs 1, `locals` needs 0.
- The **body** `{ … }` holds arguments and nested blocks.

The top-level block types in Terraform (you'll meet all of them in this course):

| Block | Labels | Purpose | Lesson |
|---|---|---|---|
| `terraform` | 0 | settings, required providers, backend | 02, 12 |
| `provider` | 1 (name) | configure a provider | 05 |
| `resource` | 2 (type, name) | something Terraform creates and manages | 06 |
| `data` | 2 (type, name) | something Terraform only *reads* | 06 |
| `variable` | 1 | an input | 07 |
| `locals` | 0 | named intermediate values | 07 |
| `output` | 1 | a value exported from the configuration | 07 |
| `module` | 1 | call another folder of Terraform code | 14 |
| `import` | 0 | adopt an existing resource | 13 |
| `moved` | 0 | tell Terraform a resource was renamed | 13 |
| `removed` | 0 | stop managing a resource | 13 |
| `check` | 1 | continuous assertions | 20 |

### Step 2: arguments, attributes, and the words people use

You'll hear these words used loosely, so here's the precise meaning:

- **Argument**: something **you set** in a block: `instance_type = "t3.micro"`.
- **Attribute**: a value you can **read** from a resource: `aws_instance.web.id`.
  Every argument is also readable as an attribute. Some attributes are
  **computed** only (you can't set them, like `id` and `arn`).

### Step 3: identifiers, comments, and formatting

- Identifiers (names you choose) can use letters, digits, `_`, and `-`, and
  can't start with a digit. The convention is **snake_case**: `web_server`,
  not `webServer`.
- Comments: `#` (preferred), `//`, or `/* multi-line */`.
- Formatting isn't debatable. `terraform fmt` decides: 2 spaces, and `=` signs aligned in a group.

### Step 4: primitive types

```hcl
name      = "notes-app"      # string
port      = 443              # number (integers and decimals share one type)
ratio     = 0.75             # number
enabled   = true             # bool
nothing   = null             # null: "no value", as if the argument wasn't written
```

**`null` is special and useful:** setting an argument to `null` means
"behave as if I didn't set it" (use the default). It's the standard way
to set something *conditionally*:

```hcl
key_name = var.ssh_key_name != "" ? var.ssh_key_name : null
```

### Step 5: strings in depth

```hcl
greeting = "Hello, ${var.name}!"               # interpolation: ${ expression }
path     = "C:\\temp\\file"                     # escapes: \\ \" \n \t
literal  = "Show $${this} literally"           # $$ escapes interpolation → Show ${this} literally

# Heredoc: multi-line strings
user_data = <<-EOT
  #!/bin/bash
  echo "Hello from ${var.name}" > /var/www/html/index.html
  EOT
```

`<<EOT` keeps indentation exactly. **`<<-EOT`** (with a dash) strips the
common leading indentation, so you can indent the text nicely inside your
code. `EOT` is just a marker, and any word works (`EOF`, `SCRIPT`…).

Strings can also contain **directives** for small logic:

```hcl
msg = "Hello, %{ if var.name != "" }${var.name}%{ else }stranger%{ endif }!"
```

### Step 6: collection types: many values of ONE type

| Type | Looks like | Ordered? | Duplicates? | Access |
|---|---|---|---|---|
| `list(string)` | `["a", "b", "a"]` | ✅ | ✅ | `var.l[0]` |
| `set(string)` | `toset(["a", "b"])` | ❌ | ❌ | no index, only iterate |
| `map(string)` | `{ env = "dev", team = "web" }` | by key | keys unique | `var.m["env"]` or `var.m.env` |

All elements must be the **same type** (`list(string)` holds only strings).

### Step 7: structural types: several values of DIFFERENT types

```hcl
# object: fixed set of named attributes, each with its own type
variable "db" {
  type = object({
    engine   = string
    size_gb  = number
    multi_az = bool
  })
}
# value: { engine = "postgres", size_gb = 20, multi_az = false }

# tuple: fixed-length sequence, each position with its own type
# tuple([string, number, bool])   value: ["web", 3, true]
```

The key difference:

- **map vs object**: a map has *any number* of keys, all with the *same*
  value type. An object has *specific* keys, each with its *own* type.
- **list vs tuple**: a list is *any length*, all the *same* type. A tuple
  is a *fixed length* with a type per position.

In practice you write `{ … }` and `[ … ]` literals, and Terraform treats
them as object and tuple until something (like a variable's `type`)
converts them to map and list. That's why this works:

```hcl
variable "tags" { type = map(string) }
tags = { Project = "notes", Owner = "me" }   # object literal → converted to map(string)
```

### Step 8: type constraints and `any`

```hcl
type = string
type = list(number)
type = map(object({ cidr = string, public = bool }))
type = any                  # "figure it out from the value" (use sparingly)
```

Terraform converts between types **automatically when it's safe**:

| From | To | Works? |
|---|---|---|
| `5` | string | ✅ `"5"` |
| `"5"` | number | ✅ `5` |
| `"hello"` | number | ❌ error |
| `true` | string | ✅ `"true"` |
| `["a","b"]` | set(string) | ✅ (order is lost) |
| `{a = 1}` (object) | map(number) | ✅ |

Explicit conversion functions exist too: `tostring()`, `tonumber()`,
`tobool()`, `tolist()`, `toset()`, `tomap()`.

### Step 9: putting it together: a real file

```hcl
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }   # object on one line
  }
}

variable "environment" {
  type    = string
  default = "dev"
}

locals {
  name = "notes-app-${var.environment}"   # string interpolation
  common_tags = {                         # object → used as map(string)
    Project     = "notes-app"
    Environment = var.environment
  }
}

resource "aws_s3_bucket" "assets" {
  bucket = "${local.name}-assets"
  tags   = local.common_tags
}
```

---

## ⚠️ Common mistakes

- **Confusing a nested block with a map argument.**
  `root_block_device { volume_size = 20 }` is a **block** (no `=`).
  `tags = { Name = "x" }` is an **argument** whose value is a map (with `=`).
  Which one to use is decided by the provider's schema, so check the docs.
  Writing `tags { … }` or `root_block_device = { … }` gives an error.
- **Indexing a set.** `toset(["a","b"])[0]` fails, because sets have no order. Use a list, or `for_each` over the set.
- **Using `<<EOT` and getting leading spaces in your script.** Use `<<-EOT`.
- **`"${var.name}"` when `var.name` is enough.** A string that is *only* an interpolation is just noise (old Terraform 0.11 style). Write `bucket = var.name`.

---

## 🎤 Interview corner

**Q: What's the difference between a map and an object in Terraform?**

> A map has an arbitrary number of keys, and all values share one type, like
> `map(string)`. An object has a fixed schema of named attributes, each
> with its own type, like `object({ name = string, port = number })`. Object
> literals written in HCL are converted to maps when a map type is
> expected, provided all values can be converted to one type.

**Q: Why and when would you use a set?**

> Sets are unordered collections of unique values. They're what `for_each`
> accepts (with strings), and many provider attributes (like security group
> IDs) are sets because order doesn't matter to the API. You can't index a
> set; you iterate it or convert it to a list.

**Q: What does `null` do when assigned to an argument?**

> It means "unset": Terraform behaves as if the argument wasn't written, so
> the provider's default applies. That makes it the idiomatic way to set an
> argument conditionally.

---

## ✅ Check yourself

1. Is `ingress { from_port = 80 }` an argument or a block? How do you know which to use?
2. What type is `{ name = "web", port = 80 }` before any conversion? Can it become a `map(string)`?
3. What's the difference between `<<EOT` and `<<-EOT`?
4. What happens if you set `key_name = null` on an `aws_instance`?

<details><summary>Answers</summary>

1. A nested block (no `=`). The provider documentation (the schema) says whether something is a block or an argument.
2. An object `object({name=string, port=number})`. Yes: `80` converts safely to `"80"`, so it becomes `map(string)`.
3. `<<-EOT` removes the common leading indentation. `<<EOT` keeps it exactly.
4. It's treated as not set: the instance has no key pair.

</details>

➡️ **Next:** [05 · Providers](05-providers.md)

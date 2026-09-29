# 08 · Expressions and functions

## 🎯 Goal

Transform data like a pro: conditionals, `for` expressions, splats,
templates, and the handful of built-in functions that cover 90% of real
code. Learn to experiment safely in `terraform console`.

---

## 🧠 Mental model: a spreadsheet, not a script

Think of Terraform expressions like **spreadsheet formulas**. A cell says
`=A1*2`, not "take A1, then multiply". There are no loops that *run* and
no variables you *reassign*. Every expression is a **formula that computes
a value** from other values.

That's why Terraform has `for` **expressions** (which build a new
list or map) rather than `for` **loops** (which run statements).

---

## 🛠 Walkthrough

### Step 0: your playground, `terraform console`

```bash
terraform console
> 1 + 2
3
> upper("notes")
"NOTES"
> [for s in ["a", "b"] : upper(s)]
[
  "A",
  "B",
]
> var.environment          # works too: reads your variables and state
"dev"
```

Try **every** example in this lesson in the console. It's the fastest way
to learn, and it never changes anything.

### Step 1: operators

```hcl
# arithmetic       + - * / %
# comparison       == != < > <= >=
# logical          && || !

local.is_prod && var.enable_backups
length(var.subnets) > 0
```

### Step 2: the conditional (ternary)

```hcl
condition ? value_if_true : value_if_false
```

```hcl
instance_type = var.environment == "prod" ? "t3.small" : "t3.micro"
multi_az      = local.is_prod                       # a bool is already a condition
key_name      = var.key_name != "" ? var.key_name : null   # null = "not set"
```

Both branches must produce **compatible types**. `true ? "a" : 5` gets
converted, but `true ? "a" : ["a"]` is an error.

### Step 3: `for` expressions: transform collections

This is the single most useful expression. There are two shapes:

```hcl
[for ITEM in COLLECTION : RESULT]            → makes a LIST (tuple)
{for ITEM in COLLECTION : KEY => VALUE}      → makes a MAP (object)
```

**List → list:**

```hcl
locals {
  names = ["web", "api", "worker"]
  upper = [for n in local.names : upper(n)]          # ["WEB", "API", "WORKER"]
  fqdns = [for n in local.names : "${n}.notes.internal"]
}
```

**With a filter (`if`):**

```hcl
[for n in local.names : n if n != "worker"]            # ["web", "api"]
```

**List → map** (very common: to feed `for_each`, lesson 09):

```hcl
{for n in local.names : n => "${n}.notes.internal"}
# { api = "api.notes.internal", web = "web.notes.internal", worker = "..." }
```

**Iterating a map** gives you key *and* value:

```hcl
variable "subnets" {
  default = {
    public-a  = "10.0.1.0/24"
    private-a = "10.0.11.0/24"
  }
}

[for name, cidr in var.subnets : "${name}=${cidr}"]    # ["private-a=10.0.11.0/24", "public-a=10.0.1.0/24"]
{for name, cidr in var.subnets : name => cidr if startswith(name, "private")}
```

With a list, the two-variable form gives you **index and value**:
`[for i, n in local.names : "${i}:${n}"]` → `["0:web", "1:api", "2:worker"]`.

**Grouping with `...`**: when several items share a key, collect them into lists:

```hcl
locals {
  servers = [
    { name = "web-1", team = "frontend" },
    { name = "web-2", team = "frontend" },
    { name = "db-1",  team = "data" },
  ]
  by_team = {for s in local.servers : s.team => s.name...}
  # { data = ["db-1"], frontend = ["web-1", "web-2"] }
}
```

Without `...`, a duplicate key is an error.

> Map iteration order is always **sorted by key**, so results are
> predictable.

### Step 4: splat expressions: a shortcut for "attribute of every item"

```hcl
# long form
[for s in aws_subnet.private : s.id]

# splat: the same thing, when aws_subnet.private is a LIST (count)
aws_subnet.private[*].id
```

- `[*]` works on **lists** (such as resources created with `count`).
- For resources created with `for_each` (which are **maps**), use a `for`
  expression or `values()`:
  `values(aws_subnet.private)[*].id`.

A neat trick: `[*]` on a **single value** that might be `null` turns it
into a list of zero or one items. It's handy with `dynamic` blocks (lesson 10).

### Step 5: string templates

Interpolation `${…}` you already know. Templates also have **directives** `%{…}`:

```hcl
locals {
  hosts = ["10.0.1.10", "10.0.1.11"]

  nginx_upstream = <<-EOT
    upstream app {
    %{ for h in local.hosts ~}
      server ${h}:8080;
    %{ endfor ~}
    }
  EOT
}
```

The `~` trims the whitespace and newline next to it, so the output has no
blank lines. For anything longer than a few lines, move the template to a
file (see `templatefile` below).

### Step 6: the function toolbox

Terraform has ~100 built-in functions. **You can't write your own**
(though providers can ship functions since Terraform 1.8, called like
`provider::aws::arn_parse(...)`). These are the ones you'll really use:

**Strings**

| Function | Example | Result |
|---|---|---|
| `format` | `format("%s-%03d", "web", 7)` | `"web-007"` |
| `join` / `split` | `join(",", ["a","b"])` | `"a,b"` |
| `lower` / `upper` | `lower("Prod")` | `"prod"` |
| `replace` | `replace("a.b.c", ".", "-")` | `"a-b-c"` |
| `substr` | `substr("notes-app", 0, 5)` | `"notes"` |
| `trimspace`, `trimprefix`, `trimsuffix` | `trimsuffix("app.zip", ".zip")` | `"app"` |
| `startswith`, `endswith`, `strcontains` | `startswith("prod-db", "prod")` | `true` |
| `regex`, `regexall` | `regex("^([a-z]+)-", "web-01")` | `["web"]` |

**Collections**

| Function | Example | Result |
|---|---|---|
| `length` | `length(["a","b"])` | `2` |
| `contains` | `contains(["dev","prod"], "dev")` | `true` |
| `lookup` | `lookup({a=1}, "b", 0)` | `0` (the default) |
| `merge` | `merge({a=1}, {b=2}, {a=3})` | `{a=3, b=2}` (later wins) |
| `concat` | `concat(["a"], ["b","c"])` | `["a","b","c"]` |
| `flatten` | `flatten([["a"], ["b",["c"]]])` | `["a","b","c"]` |
| `distinct` | `distinct(["a","a","b"])` | `["a","b"]` |
| `keys` / `values` | `keys({b=1, a=2})` | `["a","b"]` |
| `zipmap` | `zipmap(["a","b"], [1,2])` | `{a=1, b=2}` |
| `element` | `element(["a","b"], 3)` | `"b"` (wraps around) |
| `slice` | `slice(["a","b","c"], 0, 2)` | `["a","b"]` |
| `coalesce` | `coalesce("", "x")` | `"x"` (first non-empty) |
| `one` | `one([])` / `one(["a"])` | `null` / `"a"` |
| `setproduct` | `setproduct(["a","b"], [1,2])` | all 4 combinations |

**Networking**: essential on AWS:

```hcl
cidrsubnet("10.0.0.0/16", 8, 1)    # "10.0.1.0/24"
cidrsubnet("10.0.0.0/16", 8, 11)   # "10.0.11.0/24"
cidrhost("10.0.1.0/24", 10)        # "10.0.1.10"
```

`cidrsubnet(prefix, newbits, netnum)` means: take `prefix`, make it
`newbits` longer (/16 + 8 = /24), and give me subnet number `netnum`. This
lets you compute every subnet from one VPC CIDR:

```hcl
locals {
  azs = ["ap-south-1a", "ap-south-1b"]
  public_cidrs  = [for i, az in local.azs : cidrsubnet("10.0.0.0/16", 8, i)]       # 10.0.0.0/24, 10.0.1.0/24
  private_cidrs = [for i, az in local.azs : cidrsubnet("10.0.0.0/16", 8, i + 10)]  # 10.0.10.0/24, 10.0.11.0/24
}
```

**Encoding and files**

```hcl
jsonencode({ Version = "2012-10-17", Statement = [] })   # HCL → JSON string
jsondecode(file("config.json"))                          # JSON string → HCL value
yamldecode(file("settings.yaml"))
base64encode("hello")

file("${path.module}/scripts/init.sh")                   # read a file as-is
templatefile("${path.module}/templates/nginx.conf.tftpl", {   # read + fill in variables
  hosts = local.hosts
})
```

`templatefile` is the right tool for user data scripts and config files.
The template file uses the same `${}` and `%{}` syntax, and it can only see
the variables you pass it.

`path.module` is the folder of the current module. Always use it for file
paths, so the code works no matter where Terraform is run from.

**Type and error handling**

```hcl
try(var.config.db.port, 5432)        # first expression that doesn't error
can(regex("^t3\\.", var.type))       # true / false: "would this work?"
tostring(5), tonumber("5"), tolist(toset(["b","a"])), toset(["a","a"])
```

**Things to avoid:** `timestamp()` and `uuid()` return a new value on
every plan, so any resource using them shows a change **every time**. Use
the `time` provider or `terraform_data` if you need a stable value.

### Step 7: a realistic example

Tag every subnet with its tier, computed from one input map:

```hcl
variable "subnet_plan" {
  default = {
    public  = { count = 2, offset = 0 }
    private = { count = 2, offset = 10 }
  }
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)

  # a flat map: "public-0" => { cidr = ..., az = ..., tier = "public" }, ...
  subnets = merge([
    for tier, cfg in var.subnet_plan : {
      for i in range(cfg.count) :
      "${tier}-${i}" => {
        tier = tier
        az   = local.azs[i]
        cidr = cidrsubnet("10.0.0.0/16", 8, cfg.offset + i)
      }
    }
  ]...)
}
```

`merge([...]...)` takes a *list* of maps and merges them. The trailing
`...` **expands** the list into separate arguments. Paste it into the
console with a fake `azs` list and inspect `local.subnets`: that's the best
way to understand nested expressions.

---

## ⚠️ Common mistakes

- **Splatting a `for_each` resource:** `aws_subnet.private[*].id` fails on a map. Use `[for s in aws_subnet.private : s.id]` or `values(aws_subnet.private)[*].id`.
- **`lookup()` on an object with a missing attribute when you meant `try()`.** Use `try(var.obj.attr, default)` for nested objects.
- **`element()` wrapping around silently** hides off-by-one bugs. Prefer `list[i]`, which errors if out of range.
- **`timestamp()` in tags**, which gives a permanent diff on every plan.
- **Hard-coded paths** like `file("scripts/init.sh")`. Use `${path.module}/…`.

---

## 🎤 Interview corner

**Q: How do you loop in Terraform?**

> There are two levels. To create **multiple resources**, use the `count`
> or `for_each` meta-arguments. To **transform data**, use `for`
> expressions, like `[for x in list : f(x)]` for lists and
> `{for k, v in map : k => f(v)}` for maps, with optional `if` filters and
> `...` grouping. For repeated **nested blocks** inside a resource, use
> `dynamic` blocks. There are no imperative loops: everything is an
> expression that produces a value.

**Q: Can you write custom functions?**

> Not in HCL. Terraform only has built-in functions. Since 1.8, providers
> can export functions (called as `provider::<name>::<fn>`). For reuse,
> you use locals and modules instead.

**Q: What's the difference between `try` and `can`?**

> `try(a, b, …)` returns the first argument that evaluates without an
> error. `can(expr)` returns true or false depending on whether `expr`
> evaluates without an error, and it's typically used in validation conditions.

---

## ✅ Check yourself

1. Write a `for` expression turning `["web","api"]` into `{web = "web-sg", api = "api-sg"}`.
2. What does `cidrsubnet("10.0.0.0/16", 4, 2)` return?
3. Why does `aws_instance.web[*].public_ip` work with `count` but not with `for_each`?
4. What's the result of `merge({a = 1, b = 2}, {b = 3})`?

<details><summary>Answers</summary>

1. `{for n in ["web","api"] : n => "${n}-sg"}`
2. `"10.0.32.0/20"`. /16 + 4 = /20, and each /20 spans 16 values of the third octet, so subnet #2 starts at 10.0.32.0.
3. `count` makes a list, which splat works on. `for_each` makes a map, which needs `values()` or a `for` expression.
4. `{a = 1, b = 3}`. Later maps win on conflicts.

</details>

➡️ **Next:** [09 · Meta-arguments](09-meta-arguments.md)

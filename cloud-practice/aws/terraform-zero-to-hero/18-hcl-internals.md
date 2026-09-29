# 18 · HCL internals

## 🎯 Goal

Understand how Terraform turns the text you write into values: parsing,
bodies and schemas, the `cty` type system, how expressions are analysed
and evaluated, and why that design causes rules like "no variables in the
backend block" and "blocks aren't values". After this lesson, most
"weird" Terraform limitations will make sense.

---

## 🧠 Mental model: three layers

```
 ┌──────────────────────────────────────────────────────────────┐
 │ 3. TERRAFORM LANGUAGE  resource, variable, count, for_each,   │  "what the words MEAN"
 │                        lifecycle, providers' schemas          │
 ├──────────────────────────────────────────────────────────────┤
 │ 2. HCL                 bodies, attributes, blocks,            │  "the GRAMMAR"
 │                        expressions, templates, functions      │
 ├──────────────────────────────────────────────────────────────┤
 │ 1. cty                 types and values: string, number,      │  "the DATA"
 │                        list, object… unknown, null, sensitive │
 └──────────────────────────────────────────────────────────────┘
```

**HCL is a general toolkit** (the Go library `hashicorp/hcl/v2`). Packer,
Nomad, and Consul use it too. HCL knows *nothing* about resources. It only
knows "a body contains attributes and blocks, and attributes hold
expressions". **Terraform** is an application that uses HCL, and it
decides which blocks are valid. **cty** (say "see-tie") is the type
system underneath, the library that represents every value.

---

## 🛠 Walkthrough

### Step 1: from text to syntax tree

```
 main.tf (bytes)
    │  scanner: bytes → tokens         (identifiers, "=", "{", strings, "${" …)
    ▼
 tokens
    │  parser: tokens → AST            (syntax tree)
    ▼
 hcl.File { Body }
```

HCL has **two concrete syntaxes** that produce the *same* abstract structure:

| Native syntax (`.tf`) | JSON syntax (`.tf.json`) |
|---|---|
| `resource "aws_s3_bucket" "b" { bucket = "x" }` | `{"resource": {"aws_s3_bucket": {"b": {"bucket": "x"}}}}` |
| for humans | for **machines that generate config** (scripts, CDK for Terraform) |

Both produce an `hcl.Body`, so the rest of Terraform doesn't care which
one you wrote. In JSON, expressions go inside strings (`"${var.x}"`).
Because JSON can't tell a block from an object by itself, the JSON parser
relies on the **schema** (next step) to interpret it.

### Step 2: bodies are decoded against schemas

This is the most important idea in HCL. **Parsing doesn't know which
arguments are allowed. Decoding does.**

The application says what it expects, by providing a **schema**:

```
 schema for the top level of a .tf file:
   blocks:     terraform (0 labels), provider (1), resource (2), data (2),
               variable (1), locals (0), output (1), module (1), import, moved, removed, check…
   attributes: (none allowed at top level)
```

Then it asks the body: "give me your content according to this schema".
If you write something unexpected:

```hcl
resource "aws_s3_bucket" "b" {
  buckett = "x"
}
```

```
Error: Unsupported argument
  An argument named "buckett" is not expected here. Did you mean "bucket"?
```

The parser accepted it fine, since it's valid HCL grammar. The **decoder**
rejected it, because it isn't in the schema. And **whose** schema? For the
inside of a resource block, it's the **provider's** schema (lesson 17,
`GetProviderSchema`). Terraform decodes in **stages**:

```
 stage 1: Terraform decodes the TOP level with its own schema
          → finds resource "aws_s3_bucket" "b" { …body kept raw… }
 stage 2: Terraform pulls out its OWN meta-arguments from that body
          (count, for_each, provider, depends_on, lifecycle)
 stage 3: the REST of the body is decoded with the AWS provider's schema
          for aws_s3_bucket
```

That's why meta-arguments work on every resource type (Terraform handles
them before the provider sees the body), and why a provider can never
define an argument called `count`.

### Step 3: attributes vs blocks, from the inside

In a schema, every name is declared as either:

- an **attribute**: has a value, written `name = expression`;
- a **block type**: structure, written `name { … }`, with a **nesting mode**:

| Nesting mode | Meaning | Example |
|---|---|---|
| single | at most one block | `versioning_configuration { }` |
| list | ordered, repeatable | `ebs_block_device { }` (some) |
| set | unordered, repeatable | `ingress { }` on `aws_security_group` |
| map | repeatable, with a label key | rare in AWS |

So "should I write `x = {}` or `x {}`?" isn't a style choice. **The schema
decides**, and the docs reflect the schema ("Argument Reference" vs "Block").

**Why `dynamic` exists (the internals answer):** expressions produce
values, but blocks are **structure that the decoder reads before any
evaluation**. You can't produce structure from an expression. So HCL
provides an extension, `dynamic` blocks (`hcl/ext/dynblock`), which
**rewrites the body**: it evaluates the `for_each` and generates real
nested blocks *before* the schema decoding sees them.

### Step 4: expressions are trees, evaluated later

When HCL parses `instance_type = var.env == "prod" ? "t3.large" : "t3.micro"`,
it doesn't compute anything. It stores an **expression tree**:

```
            ConditionalExpr
           /       |        \
   BinaryOp(==)  "t3.large"  "t3.micro"
      /     \
 var.env   "prod"
```

Evaluation happens later, given an **evaluation context**: the variables
and functions available at that moment. Separating "parse" from
"evaluate" enables two things.

**1. Static reference analysis.** Every expression can report which
variables it *refers to* **without being evaluated**. This is how
Terraform builds the dependency graph (lesson 17, Step 5):

```
 expression:  "http://${aws_instance.web.public_ip}:${var.port}/"
 references:  aws_instance.web.public_ip,  var.port
 graph edges: aws_instance.web → this,   var.port → this
```

These references are called **traversals**: a root name plus steps
(`.public_ip`, `[0]`, `["key"]`).

This has a consequence: **references must be written out literally**.
Terraform can't follow a reference that's built at runtime:

```hcl
lookup(local.all_instances, var.name)       # ✅ fine: local.all_instances is a literal reference
"aws_instance.${var.name}.id"               # ❌ just a string, NOT a reference
```

There's no `eval()` in Terraform, by design. The graph must be knowable
before evaluating anything.

**2. Lazy, graph-ordered evaluation.** `locals`, `variables`, and `outputs`
are **nodes in the graph** too. A local is evaluated when the walker
reaches it, after everything it references. So locals can appear in any
order in any file, and a local that refers to itself (directly or through
others) is a **cycle error**, not an infinite loop.

### Step 5: why some places accept only literal values

Some parts of the configuration are needed **before the graph exists**,
during `init` or configuration loading. Terraform decodes those with **no
evaluation context at all**, so only literal values work:

| Place | Why it must be static |
|---|---|
| `backend "s3" { … }` | must know where state is **before** reading state or variables |
| `required_providers`, `required_version` | must know which plugins to install **before** anything runs |
| `module "x" { source = …, version = … }` | modules must be downloaded during `init` |
| `lifecycle { ignore_changes = [ … ] }` | a list of attribute *paths*, read as references, not evaluated |
| `provider = aws.alias` / `depends_on = [ … ]` | references used to build the graph itself |

So `backend "s3" { bucket = var.bucket }` fails with
**"Variables may not be used here"**. It's not an arbitrary rule. The
evaluation machinery isn't running yet. (Workaround: partial
configuration, `init -backend-config=…`, lesson 12.)

> Interview bonus: **OpenTofu** (the open-source fork) added "early
> evaluation" in v1.8, allowing variables and locals in backend and module
> source blocks by evaluating a restricted set of values before `init`.
> Terraform itself doesn't do this.

### Step 6: `cty`, the type system

Every value in Terraform is a `cty.Value`, which has a **type** plus flags.
The types:

```
 primitive      string · number · bool
 collection     list(T) · set(T) · map(T)          ← ONE element type T
 structural     object({a=T1, b=T2}) · tuple([T1, T2])   ← a type per attribute/position
 dynamic        "any" (DynamicPseudoType): "not decided yet"
```

Some facts that explain real behaviour:

- **number is arbitrary-precision** (a big float, not a 64-bit double).
  `0.1 + 0.2` in `terraform console` gives `0.3`, not `0.30000000000000004`.
- **strings are Unicode and normalised** (NFC), so two visually identical strings compare equal.
- **Sets have no order and compare elements by value.** When one attribute
  of a set element (like a security group `ingress` block) changes, it's a
  *different* element. That's why plans for set-based blocks show the
  whole element removed and re-added (you saw this in lesson 10).
- **Literals start as structural types.** `["a", 1]` is a `tuple([string, number])`
  and `{a = 1}` is an `object`. They're converted to `list`/`map` only when a
  type constraint asks for it.

**Conversion and unification.** When two values must share a type (both
branches of a conditional, or elements of a list), cty finds a common
type. `true ? 5 : "x"` unifies to `string` ("5"). `true ? "x" : ["x"]` has no
common type, which is an error. Conversions are either **safe** (always
succeed: number → string) or **unsafe** (might fail: `"abc"` → number), and
unsafe ones fail at evaluation time with a clear message.

### Step 7: three special kinds of value

A cty value isn't just "a value". It can also be:

| Kind | Meaning | Where you see it |
|---|---|---|
| **null** | "absent", but *typed* (a null string is different from a null list) | setting `arg = null` = "not set" |
| **unknown** | "will exist, not known yet", also typed | `(known after apply)` |
| **marked** | carries a label, e.g. **sensitive** | `(sensitive value)` in plans |

**Unknowns propagate** through almost every operation: `unknown + 1` is
unknown, and `upper(unknown)` is unknown. Some operations can still give
a known result: `length()` of a list whose *length* is known but whose
*elements* aren't gives a known number. And since Terraform 1.6,
**refinements** let an unknown carry partial facts (not null, a prefix, a
range), so more results can be known at plan time.

**Marks propagate too.** That's the mechanism behind "sensitivity is
contagious" (lesson 07): `"postgres://${var.password}@host"` carries the
`sensitive` mark because one input did. `nonsensitive()` removes the mark
explicitly. **Ephemeral** values (Terraform 1.10+, lesson 19) are another
mark, meaning "never write this to state or plan".

### Step 8: templates

A quoted string with `${…}` or `%{…}` isn't a string literal. It's a
**template expression**: a list of parts (literal text, interpolations,
and directives) that is evaluated into a string. Heredocs are the same
thing written across lines. `templatefile()` parses a file with the same
template grammar at runtime, and it can only see the variables you pass
it (not `var.` or `local.`). That keeps templates self-contained.

### Step 9: `terraform fmt` and comments

`fmt` uses a different HCL package, **`hclwrite`**, which works on the
token stream instead of the syntax tree, so it keeps **comments and
layout** that the AST discards. That's also how tools can edit `.tf` files
programmatically without destroying your comments.

### Step 10: the whole journey of one argument

```
 instance_type = local.is_prod ? "t3.large" : "t3.micro"
 │
 ├─ 1. scanned + parsed          → ConditionalExpr tree            (HCL)
 ├─ 2. top-level decode          → inside resource "aws_instance" "web"   (Terraform schema)
 ├─ 3. meta-args extracted       → none here
 ├─ 4. body decoded              → "instance_type" is an attribute of type string (AWS provider schema)
 ├─ 5. references analysed       → local.is_prod  → graph edge local.is_prod → aws_instance.web
 ├─ 6. graph walk reaches node   → local.is_prod evaluated first (= false)
 ├─ 7. expression evaluated      → cty.StringVal("t3.micro")       (cty)
 ├─ 8. sent to provider          → PlanResourceChange(config: {instance_type: "t3.micro", …})
 └─ 9. provider plans the change → "~ instance_type = t3.small → t3.micro" or no-op
```

If you can narrate this chain, you understand Terraform's language more
deeply than most people who use it daily.

---

## ⚠️ Common confusions this lesson resolves

| Confusion | Explanation |
|---|---|
| "Why can't I use a variable in the backend?" | It's decoded before any evaluation context exists (Step 5). |
| "Why do I need `dynamic` for nested blocks?" | Blocks are schema structure, decoded before evaluation (Step 3). |
| "Why can't I build a resource reference from a string?" | References are found by static analysis to build the graph (Step 4). |
| "Why does changing one SG rule show remove + add?" | Set elements are identified by their whole value (Step 6). |
| "Why is `validate` impossible before `init`?" | Resource bodies are decoded with the provider's schema (Step 2). |
| "Why does a secret leak error appear on my output?" | The sensitive mark propagated through expressions (Step 7). |

---

## 🎤 Interview corner

**Q: What is HCL and how does it relate to Terraform?**

> HCL is HashiCorp's configuration language toolkit. It defines a
> grammar (bodies of attributes and blocks, an expression language,
> templates) with two concrete syntaxes, native and JSON, and it decodes
> bodies against application-supplied schemas. Terraform is an
> application built on it: it defines the top-level schema (resource,
> variable, module…) and delegates resource bodies to provider schemas.
> Values are represented with the `cty` type system.

**Q: How does Terraform know dependencies without running your code?**

> HCL expressions are parsed into ASTs that can report their variable
> traversals without evaluation. Terraform statically collects those
> references (`aws_vpc.main.id`, `var.x`, `local.y`) to build graph edges,
> then evaluates expressions during the graph walk in dependency order.
> That's also why references can't be constructed dynamically from strings.

**Q: Explain unknown values and how they propagate.**

> An unknown is a typed placeholder in `cty` for a value that'll only exist
> after apply. Operations on unknowns generally yield unknowns, so derived
> values show as "known after apply". Some operations can still produce
> known results (like length of a known-length list), and refinements
> since 1.6 let unknowns carry constraints. Unknowns can't be used where
> Terraform must decide graph shape, like `count` and `for_each` keys.

**Q: Why can't you use variables in a `backend` block or module `source`?**

> Those are processed during initialisation, before Terraform builds the
> graph or evaluates any expressions. Terraform needs to know where state
> lives and which code to download first. They're decoded without an
> evaluation context, so only literals are allowed. Workarounds are
> partial backend config at `init`, or wrapper tools. OpenTofu added
> limited early evaluation for this.

**Q: What's the difference between a map and an object at the type-system level?**

> In `cty`, a map is a collection type with one element type and any keys.
> An object is a structural type with a fixed set of attribute names, each
> with its own type. HCL literals start as objects and tuples and are
> converted to maps and lists when a type constraint requires it.

---

## ✅ Check yourself

1. Is `buckett = "x"` in a resource a parse error or a decode error? Why does the difference matter?
2. Name two places in a configuration where only literal values are allowed, and explain why.
3. Why does `0.1 + 0.2` equal `0.3` in `terraform console`?
4. What three special states can a `cty` value be in, besides a normal known value?
5. Why does changing the port of one inline `ingress` block show a removal and an addition?

<details><summary>Answers</summary>

1. A decode error. It's valid HCL grammar, but not in the provider's schema. It matters because decoding needs the provider schema, which is why `validate` needs `init`.
2. Any two of: `backend` (state location needed before evaluation), `required_providers` / `required_version` (plugins needed before evaluation), module `source`/`version` (downloaded at init), `lifecycle.ignore_changes` (attribute paths, not expressions).
3. `cty` numbers are arbitrary-precision, not IEEE-754 doubles.
4. Null, unknown, and marked (e.g. sensitive). Also ephemeral on newer versions.
5. `ingress` blocks are a set. Set elements are identified by their whole value, so a changed element is a different element: the old one is removed and the new one added.

</details>

➡️ **Next:** [19 · Security and secrets](19-security-and-secrets.md)

# 09 · Meta-arguments: count, for_each, depends_on, provider, lifecycle

## 🎯 Goal

Create many resources from one block, choose correctly between `count` and
`for_each` (the classic interview question), and control a resource's
life with `lifecycle` rules.

---

## 🧠 Mental model: instructions for Terraform, not for AWS

Most arguments in a resource block go to **AWS** (`instance_type`, `cidr_block`).
**Meta-arguments** go to **Terraform itself**, and they work on *every*
resource type:

| Meta-argument | Tells Terraform… |
|---|---|
| `count` | "make N copies of this" |
| `for_each` | "make one copy per item in this map or set" |
| `depends_on` | "wait for this other thing, even though I don't reference it" |
| `provider` | "use this specific provider configuration" (lesson 05) |
| `lifecycle` | "handle create, update, and delete this special way" |

---

## 🛠 Walkthrough

### Step 1: `count`: N copies

```hcl
resource "aws_instance" "web" {
  count         = 3
  ami           = data.aws_ami.al2023.id
  instance_type = "t3.micro"

  tags = { Name = "web-${count.index}" }    # count.index = 0, 1, 2
}
```

- One block creates **three** resources: `aws_instance.web[0]`, `[1]`, and `[2]`.
- `aws_instance.web` is now a **list**. Reference one with `aws_instance.web[0].id`, or all of them with `aws_instance.web[*].id`.

**The most common use of `count`: optional resources.**

```hcl
resource "aws_cloudwatch_metric_alarm" "cpu" {
  count = var.enable_alarms ? 1 : 0     # 1 = create, 0 = don't
  # ...
}

# referring to something that might not exist:
alarm_arn = one(aws_cloudwatch_metric_alarm.cpu[*].arn)   # the ARN, or null
```

### Step 2: the `count` trap: indexes shift

Say you create subnets from a list:

```hcl
variable "azs" { default = ["ap-south-1a", "ap-south-1b", "ap-south-1c"] }

resource "aws_subnet" "private" {
  count             = length(var.azs)
  availability_zone = var.azs[count.index]
  cidr_block        = cidrsubnet("10.0.0.0/16", 8, count.index)
  vpc_id            = aws_vpc.main.id
}
```

```
 [0] → ap-south-1a    [1] → ap-south-1b    [2] → ap-south-1c
```

Now remove `"ap-south-1a"` from the list. You expected "delete one subnet".
You get this instead:

```
 [0] → ap-south-1b   ← was 1a: REPLACED
 [1] → ap-south-1c   ← was 1b: REPLACED
 [2]                 ← DESTROYED
```

Everything after the removed item **shifted by one**, so Terraform
replaces subnets that you never meant to touch. Instances inside them
would be destroyed too.

### Step 3: `for_each`: one copy per **key**

```hcl
resource "aws_subnet" "private" {
  for_each = toset(["ap-south-1a", "ap-south-1b", "ap-south-1c"])

  availability_zone = each.key
  cidr_block        = cidrsubnet("10.0.0.0/16", 8, index(["ap-south-1a", "ap-south-1b", "ap-south-1c"], each.key))
  vpc_id            = aws_vpc.main.id
}
```

Now the resources are named **by key**:

```
 aws_subnet.private["ap-south-1a"]
 aws_subnet.private["ap-south-1b"]
 aws_subnet.private["ap-south-1c"]
```

Remove `"ap-south-1a"` and **only** `aws_subnet.private["ap-south-1a"]` is
destroyed. The others keep their identity, because their keys didn't change.

`for_each` accepts:
- a **set of strings**: `each.key` and `each.value` are both the string;
- a **map**: `each.key` is the key, `each.value` is the value (which can be an object).

A map is usually best, because it keeps the settings with the key:

```hcl
variable "private_subnets" {
  default = {
    "ap-south-1a" = "10.0.10.0/24"
    "ap-south-1b" = "10.0.11.0/24"
  }
}

resource "aws_subnet" "private" {
  for_each          = var.private_subnets
  vpc_id            = aws_vpc.main.id
  availability_zone = each.key
  cidr_block        = each.value
  tags              = { Name = "private-${each.key}" }
}
```

A resource with `for_each` is a **map** of instances. Reference them like
this:

```hcl
aws_subnet.private["ap-south-1a"].id
[for s in aws_subnet.private : s.id]          # all IDs as a list
values(aws_subnet.private)[*].id              # same
```

**Chaining.** You can `for_each` over another `for_each` resource, and the
keys carry through:

```hcl
resource "aws_route_table_association" "private" {
  for_each       = aws_subnet.private            # same keys as the subnets
  subnet_id      = each.value.id
  route_table_id = aws_route_table.private.id
}
```

### Step 4: ⭐ count vs for_each: the decision

| Question | `count` | `for_each` |
|---|---|---|
| Instances identified by | position `[0]`, `[1]` | key `["web"]`, `["api"]` |
| Remove an item from the middle | later items **shift and get replaced** | only that item is destroyed |
| Input | a number | a map, or a set of strings |
| Best for | "0 or 1" (optional resources); N truly identical copies | anything with a natural name or distinct settings |

> **Rule of thumb:** use `count` only for on/off switches or truly
> interchangeable copies. Use `for_each` for everything else.

### Step 5: the "known at plan time" rule

`count` and `for_each` decide **how many resources exist**, and Terraform
must know that while **planning**. So their values can't depend on things
that are `(known after apply)`:

```hcl
resource "aws_eip" "web" {
  for_each = toset(aws_instance.web[*].id)   # ❌ IDs don't exist yet
}
```

```
Error: Invalid for_each argument
  The "for_each" set includes values derived from resource attributes that
  cannot be determined until apply...
```

**The fix:** key the collection by something known in advance (names you
chose), and use the unknown values only *inside*:

```hcl
resource "aws_instance" "web" {
  for_each = toset(["a", "b"])
  # ...
}

resource "aws_eip" "web" {
  for_each = aws_instance.web          # keys "a","b" are known; IDs are only used as values
  instance = each.value.id
}
```

Lesson 17 explains *why* this is a hard limit.

### Step 6: `depends_on`: dependencies Terraform can't see

References create dependencies automatically. Occasionally there's a
real dependency with **no reference**. The classic case:

```hcl
resource "aws_iam_role_policy" "app_s3" {
  role   = aws_iam_role.app.id
  policy = data.aws_iam_policy_document.s3.json
}

resource "aws_instance" "app" {
  iam_instance_profile = aws_iam_instance_profile.app.name
  # The app reads S3 at boot. It references the PROFILE, not the POLICY,
  # so Terraform might start the instance before the policy is attached.
  depends_on = [aws_iam_role_policy.app_s3]
}
```

Use `depends_on` **only** for these hidden dependencies. Overusing it
makes plans slower and more pessimistic, because more values become
"known after apply".

### Step 7: `lifecycle`: special create, update, and delete rules

```hcl
resource "aws_launch_template" "web" {
  # ...
  lifecycle {
    create_before_destroy = true
    prevent_destroy       = false
    ignore_changes        = [tags["LastDeployedBy"]]
    replace_triggered_by  = [terraform_data.app_version]

    precondition {
      condition     = data.aws_ami.al2023.architecture == "x86_64"
      error_message = "The AMI must be x86_64."
    }
    postcondition {
      condition     = self.latest_version > 0
      error_message = "Launch template has no versions."
    }
  }
}
```

One at a time:

**`create_before_destroy = true`.** When replacement is needed, build the
new resource **first**, then delete the old one (`+/-` instead of `-/+`).
This gives you zero downtime for things like launch templates, certificates,
and security groups in use.
⚠️ The new and old resources exist at the same time, so **names must not
clash**. Use `name_prefix` instead of `name` where the resource offers it.

**`prevent_destroy = true`.** Any plan that would destroy this resource
**fails**. Use it for databases, state buckets, and KMS keys.
⚠️ It only works while the block is in the code. If someone deletes the
whole resource block, the protection goes with it.

**`ignore_changes = [ … ]`.** Don't treat changes to these attributes as
drift. Typical uses:
- `desired_capacity` on an Auto Scaling group (the autoscaler changes it all day);
- `tags` that another system adds;
- `ami` when you roll AMIs through a separate process.

`ignore_changes = all` ignores everything after creation. That's rarely a
good idea.

**`replace_triggered_by = [ … ]`.** Replace this resource when **another**
resource or attribute changes, even if nothing on this one changed:

```hcl
resource "terraform_data" "app_version" {
  input = var.app_version          # change this → replaces anything that lists it
}
```

**`precondition` / `postcondition`.** Assertions that make failures
readable. A precondition is checked **before** the resource is planned
(validate your assumptions). A postcondition is checked **after** (it can
use `self` to validate the result). They also work on `data` blocks and
`output`s.

### Step 8: the timeline of a replacement

```
 default (-/+):           destroy OLD ──▶ create NEW            (gap = downtime)
 create_before_destroy:   create NEW ──▶ switch refs ──▶ destroy OLD   (no gap)
```

`create_before_destroy` is **contagious**: resources that the replaced
resource depends on are also treated as create-before-destroy, because
otherwise the graph would have a cycle. Don't be surprised to see it spread.

---

## ⚠️ Common mistakes

- **`count` over a list of things with names**, followed by painful "why is it replacing everything" moments. Use `for_each`.
- **`for_each` over a list.** It needs a map or a **set**, so wrap it: `for_each = toset(var.names)`.
- **Keys derived from unknown values**, which gives "Invalid for_each argument". Use names you choose as keys.
- **`create_before_destroy` with a fixed `name`**, which gives an "already exists" error. Switch to `name_prefix`.
- **Trusting `prevent_destroy` to protect against deleting the block.** It can't.
- **`depends_on` everywhere "to be safe"**, which gives slower, noisier plans.

---

## 🎤 Interview corner

**Q: count vs for_each, when do you use each?**

> `count` identifies instances by index, so removing an item from the
> middle of the input shifts every later index and Terraform replaces
> those resources. `for_each` identifies instances by map key or set
> element, so adding or removing an item only affects that item. I use
> `count` for conditional creation (`count = var.enabled ? 1 : 0`) or truly
> identical copies, and `for_each` for everything with a natural identity.
> Both need their values to be known at plan time.

**Q: How would you migrate a resource from `count` to `for_each` without destroying it?**

> Change the code to `for_each`, then tell Terraform the new address of
> each instance with `moved` blocks (`from = aws_subnet.private[0]`,
> `to = aws_subnet.private["ap-south-1a"]`), or `terraform state mv` in
> older versions. The plan should show moves and no replacements (lesson 13).

**Q: Explain `create_before_destroy` and a pitfall.**

> On replacement it creates the new object before destroying the old one,
> which avoids downtime. The pitfalls: unique names clash because both
> exist at once (use `name_prefix`), and the setting propagates to
> dependencies to avoid dependency cycles.

**Q: When is `depends_on` necessary?**

> Only for dependencies that can't be expressed through references. The
> classic example is an IAM policy that must be attached before an instance
> or Lambda uses it at runtime, when the compute resource only references
> the role or profile. Otherwise implicit dependencies are preferred.

---

## ✅ Check yourself

1. `count = 3` on `aws_instance.web`. What are the three addresses?
2. You have `for_each = toset(["a","b","c"])` and remove `"b"`. What does the plan show?
3. Why must `for_each` keys be known at plan time?
4. Which lifecycle setting would you put on the production RDS instance, and what are its limits?

<details><summary>Answers</summary>

1. `aws_instance.web[0]`, `aws_instance.web[1]`, `aws_instance.web[2]`.
2. One destroy: `["b"]`. `"a"` and `"c"` are untouched.
3. The keys define *which resources exist*. Terraform has to know that to build the plan, before anything is created.
4. `prevent_destroy = true`. It doesn't protect against deleting the resource block itself, or against deletion outside Terraform. Pair it with RDS deletion protection (`deletion_protection = true`) and backups.

</details>

➡️ **Next:** [10 · Dynamic blocks and advanced patterns](10-dynamic-blocks-and-patterns.md)

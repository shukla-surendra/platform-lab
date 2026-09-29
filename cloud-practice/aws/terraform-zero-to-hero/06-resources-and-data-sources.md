# 06 · Resources, data sources, and references

## 🎯 Goal

Connect resources to each other with references, understand how that
creates the **dependency graph**, and use **data sources** to look up
things Terraform doesn't manage. We'll grow `notes-app` into a real web
server in its own network.

---

## 🧠 Mental model: build vs look up

```
 resource "aws_vpc" "main"        → "BUILD and OWN this"   (create, update, destroy)
 data     "aws_ami" "al2023"      → "LOOK THIS UP"         (read-only, never changes AWS)
```

And **references** are the strings that tie them together:

```
 aws_subnet.public.vpc_id = aws_vpc.main.id
                            └────┬─────┘
            "the id attribute of the aws_vpc called main"
```

Every reference is also a promise about **order**: the VPC must exist
before the subnet, because the subnet needs its ID.

---

## 🛠 Walkthrough

### Step 1: referencing another resource

The syntax is always `<TYPE>.<NAME>.<ATTRIBUTE>`:

```hcl
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "notes-app" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id          # ← reference
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "ap-south-1a"
  map_public_ip_on_launch = true
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}
```

Where do attribute names like `id` or `arn` come from? From the provider
docs. Every resource page on the Terraform Registry has an **"Attribute
Reference"** section listing what you can read.

### Step 2: the dependency graph falls out automatically

You never wrote "create the VPC first". Terraform worked it out from the
references:

```
                 aws_vpc.main
               ┌──────┼──────────────┐
               ▼      ▼              ▼
     aws_subnet  aws_internet_gateway  (aws_route_table needs both ↓)
      .public         .main ─────────▶ aws_route_table.public
          │                                   │
          └──────────────┬────────────────────┘
                         ▼
          aws_route_table_association.public
```

- **Create** walks the graph top-down. Independent branches (the subnet and
  the gateway) are created **in parallel**.
- **Destroy** walks it bottom-up, in reverse.

These are called **implicit dependencies**, and they're the normal way
ordering works in Terraform. File order and block order in the file
**don't matter at all**.

### Step 3: data sources: reading what exists

We need an AMI ID for our server. AMI IDs are different in every region
and change with every patch, so **don't hard-code them**. Look them up:

```hcl
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023*-x86_64"]
  }
}
```

A data source has the same shape as a resource, starting with `data`. You
reference it with the extra `data.` prefix:

```hcl
ami = data.aws_ami.al2023.id
```

> 💡 An even more robust option for Amazon's own images: AWS publishes the
> latest AMI IDs as public SSM parameters.
> ```hcl
> data "aws_ssm_parameter" "al2023" {
>   name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
> }
> # ami = data.aws_ssm_parameter.al2023.value
> ```

### Step 4: data sources you'll use constantly

```hcl
data "aws_caller_identity" "current" {}     # who am I? → .account_id, .arn
data "aws_region" "current" {}              # which region? → .region (v6) / .name (older)
data "aws_availability_zones" "available" { # AZs in this region
  state = "available"
}

# Look up something another team manages, by tag
data "aws_vpc" "shared" {
  tags = { Name = "shared-services" }
}
```

A very important one is `aws_iam_policy_document`. It writes IAM JSON
**in HCL**, with validation and references, instead of error-prone
JSON strings:

```hcl
data "aws_iam_policy_document" "read_assets" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.assets.arn}/*"]
  }
}

resource "aws_iam_policy" "read_assets" {
  name   = "notes-app-read-assets"
  policy = data.aws_iam_policy_document.read_assets.json
}
```

### Step 5: when are data sources read?

Usually **during `plan`**, so the values are known and shown in the plan.
But if a data source's arguments depend on something that doesn't exist
yet (`known after apply`), Terraform has to wait:

```
  # data.aws_iam_policy_document.x will be read during apply
  # (config refers to values not yet known)
 <= data "aws_iam_policy_document" "x" {
```

The `<=` symbol is harmless, but everything depending on it also becomes
"known after apply".

### Step 6: the web server

Now everything connects:

```hcl
resource "aws_security_group" "web" {
  name   = "notes-app-web"
  vpc_id = aws_vpc.main.id
}

resource "aws_vpc_security_group_ingress_rule" "http" {
  security_group_id = aws_security_group.web.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.web.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"       # all traffic
}

resource "aws_instance" "web" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.web.id]

  user_data = <<-EOT
    #!/bin/bash
    dnf install -y nginx
    echo "<h1>notes-app</h1>" > /usr/share/nginx/html/index.html
    systemctl enable --now nginx
  EOT

  tags = { Name = "notes-app-web" }
}
```

> Why separate `aws_vpc_security_group_ingress_rule` resources instead of
> `ingress { }` blocks inside the security group? Each rule becomes its own
> resource with its own ID, so adding one rule never rewrites the others,
> and it can't fight with rules managed elsewhere. It's the current AWS
> provider recommendation. Inline blocks own the *whole* list (lesson 10).

### Step 7: what makes a change "in place" or "replace"?

The **provider schema** marks some arguments as **ForceNew**: AWS can't
change them on an existing object. From this lesson:

| Resource | In-place (`~`) | Forces replacement (`-/+`) |
|---|---|---|
| `aws_instance` | `instance_type` (Terraform stops, resizes, starts), tags | `ami`, `subnet_id`, `availability_zone` |
| `aws_subnet` | tags, `map_public_ip_on_launch` | `cidr_block`, `vpc_id`, `availability_zone` |
| `aws_vpc` | tags, DNS settings | `cidr_block` |
| `aws_s3_bucket` | tags | `bucket` (the name) |

You don't need to memorise these. The plan always tells you with
`# forces replacement`. But it helps to have a feel for it: **identity
things** (names, placement, network) usually force replacement, while
**settings** usually don't.

### Step 8: `timeouts`: when AWS is slow

Some resources accept a `timeouts` block, for operations that can take a
long time:

```hcl
resource "aws_db_instance" "main" {
  # ...
  timeouts {
    create = "60m"
    delete = "2h"
  }
}
```

---

## ⚠️ Common mistakes

- **Hard-coding IDs** (`vpc_id = "vpc-0abc"`). Use a reference if Terraform manages it, or a data source if it doesn't. Hard-coded IDs break the graph, so Terraform doesn't know the order.
- **Hard-coding AMI IDs.** They differ per region and get outdated. Use `data "aws_ami"` or the SSM parameter.
- **Using a data source to read something the *same* configuration creates.** Just reference the resource. A data source there can even read "nothing" because it runs before the resource exists.
- **`most_recent = true` without pinning in prod.** The next plan after Amazon publishes a new AMI shows your instance being **replaced**. Fine for dev. For prod, pin the AMI in a variable, or use `ignore_changes = [ami]` (lesson 09).

---

## 🎤 Interview corner

**Q: What's the difference between a resource and a data source?**

> A resource is managed: Terraform creates, updates, and destroys it and
> tracks it in state. A data source is read-only: it queries existing
> information (an AMI, the account ID, a VPC someone else owns) during plan
> and exposes it as attributes, and it never changes infrastructure.

**Q: How does Terraform decide the order in which to create resources?**

> It builds a directed acyclic graph from references between blocks. If
> resource B references an attribute of A, there's an edge A → B, so A is
> created first and destroyed last. Independent nodes run in parallel.
> File and block order are irrelevant. `depends_on` adds edges only for
> dependencies that references can't express.

**Q: Why did Terraform want to replace my EC2 instance when I didn't change anything?**

> Most likely the AMI came from a data source with `most_recent = true`
> and a newer AMI was published. `ami` forces replacement, so the plan
> shows `-/+`. The fixes are to pin the AMI, or add `lifecycle { ignore_changes = [ami] }`
> and roll AMIs deliberately.

---

## ✅ Check yourself

1. Write the reference to the ARN of a data source `data "aws_iam_role" "ci"`.
2. The subnet and the internet gateway both depend only on the VPC. In what order are they created?
3. Why is `aws_iam_policy_document` better than a JSON string?
4. What does `<=` mean in a plan?

<details><summary>Answers</summary>

1. `data.aws_iam_role.ci.arn`
2. In parallel, after the VPC. Neither depends on the other.
3. It's HCL: it gets syntax checking, you can use references and expressions, and its output is valid, normalised JSON.
4. A data source that will be read during apply, because its arguments depend on values not known until then.

</details>

➡️ **Next:** [07 · Variables, locals, and outputs](07-variables-locals-outputs.md)

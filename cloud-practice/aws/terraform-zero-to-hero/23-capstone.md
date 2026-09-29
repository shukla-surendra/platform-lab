# 23 · Capstone: notes-app, production-shaped

## 🎯 Goal

See every concept from this course working together in one realistic
design, and be able to explain **why** each decision was made. That
explanation is exactly what a senior interview or a design review asks for.

---

## 🧠 The architecture

```
                         Internet
                            │
                   ┌────────▼────────┐
                   │  ALB (public)    │  public subnets ×2 AZ
                   └────────┬────────┘
                            │ :8080 (SG → SG)
               ┌────────────▼────────────┐
               │ Auto Scaling group       │  private subnets ×2 AZ
               │ EC2 (launch template,    │  → NAT gateway for outbound
               │ SSM access, no SSH)      │
               └────────────┬────────────┘
                            │ :5432 (SG → SG)
               ┌────────────▼────────────┐
               │ RDS PostgreSQL           │  private subnets, Multi-AZ in prod
               │ password in Secrets Mgr  │
               └──────────────────────────┘
```

Three **states** per environment (lesson 16): `network` → `data` → `app`.

---

## 🗂 Repository layout

```
notes-infra/
├── modules/
│   ├── network/          VPC, subnets, NAT, routes; publishes IDs to SSM
│   ├── database/         RDS + subnet group + SG; publishes endpoint & secret ARN
│   └── web-service/      ALB, target group, launch template, ASG, IAM, scaling
├── live/
│   ├── dev/{network,data,app}/
│   └── prod/{network,data,app}/      each folder = one root module = one state
├── .github/workflows/terraform.yml   plan on PR, apply on merge (lesson 21)
├── .tflint.hcl
└── .pre-commit-config.yaml
```

---

## 🛠 The code, with the reasoning

### 1. `modules/network`: the foundation

```hcl
# modules/network/variables.tf
variable "name"     { type = string }
variable "cidr"     { type = string }
variable "az_count" {
  type    = number
  default = 2
}
variable "single_nat_gateway" {
  description = "One NAT for all AZs (cheaper, less resilient). Use false in prod."
  type        = bool
  default     = true
}
```

```hcl
# modules/network/main.tf
data "aws_availability_zones" "available" { state = "available" }

locals {
  azs = { for i, az in slice(data.aws_availability_zones.available.names, 0, var.az_count) : az => i }
  nat_azs = var.single_nat_gateway ? { (keys(local.azs)[0]) = 0 } : local.azs     # (key) = expression as key
}

resource "aws_vpc" "this" {
  cidr_block           = var.cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = { Name = var.name }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
}

resource "aws_subnet" "public" {
  for_each                = local.azs                               # lesson 09: stable keys
  vpc_id                  = aws_vpc.this.id
  availability_zone       = each.key
  cidr_block              = cidrsubnet(var.cidr, 8, each.value)     # lesson 08
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.name}-public-${each.key}", Tier = "public" }
}

resource "aws_subnet" "private" {
  for_each          = local.azs
  vpc_id            = aws_vpc.this.id
  availability_zone = each.key
  cidr_block        = cidrsubnet(var.cidr, 8, each.value + 10)
  tags              = { Name = "${var.name}-private-${each.key}", Tier = "private" }
}

resource "aws_eip" "nat" {
  for_each = local.nat_azs
  domain   = "vpc"
}

resource "aws_nat_gateway" "this" {
  for_each      = local.nat_azs
  allocation_id = aws_eip.nat[each.key].id
  subnet_id     = aws_subnet.public[each.key].id
  depends_on    = [aws_internet_gateway.this]     # lesson 09: a real hidden dependency
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }
}

resource "aws_route_table_association" "public" {
  for_each       = aws_subnet.public                 # chained for_each: same keys
  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  for_each = local.azs
  vpc_id   = aws_vpc.this.id
  route {
    cidr_block = "0.0.0.0/0"
    # this AZ's NAT if it has one, otherwise the single shared NAT
    nat_gateway_id = try(aws_nat_gateway.this[each.key].id, one(values(aws_nat_gateway.this)).id)
  }
}

resource "aws_route_table_association" "private" {
  for_each       = aws_subnet.private
  subnet_id      = each.value.id
  route_table_id = aws_route_table.private[each.key].id
}

# Publish for other states (lesson 12: decoupled via SSM, not remote_state)
resource "aws_ssm_parameter" "outputs" {
  for_each = {
    vpc_id             = aws_vpc.this.id
    public_subnet_ids  = join(",", [for s in aws_subnet.public : s.id])
    private_subnet_ids = join(",", [for s in aws_subnet.private : s.id])
  }
  name  = "/${var.name}/network/${each.key}"
  type  = "String"
  value = each.value
}
```

**Why these choices:**
- `for_each` keyed by AZ name: adding a third AZ later doesn't disturb the first two.
- `single_nat_gateway` as a variable: dev saves ~$30/month per NAT, and prod gets one per AZ for resilience.
- SSM outputs: the `app` state needs only `ssm:GetParameter` on `/notes-prod/network/*`, not the network state.

### 2. `modules/database`: stateful and protected

```hcl
# modules/database/main.tf
resource "aws_db_subnet_group" "this" {
  name       = var.name
  subnet_ids = var.subnet_ids
}

resource "aws_security_group" "db" {
  name_prefix = "${var.name}-db-"            # name_prefix: safe with create_before_destroy
  vpc_id      = var.vpc_id
  lifecycle { create_before_destroy = true }
}

resource "aws_db_instance" "this" {
  identifier     = var.name
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.instance_class

  allocated_storage     = 20
  max_allocated_storage = 200               # storage autoscaling
  storage_encrypted     = true

  db_name                     = "notes"
  username                    = "notes_admin"
  manage_master_user_password = true        # lesson 19: the secret never touches Terraform

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]
  multi_az               = var.multi_az

  backup_retention_period   = var.backup_retention_days
  deletion_protection       = var.deletion_protection
  skip_final_snapshot       = !var.deletion_protection
  final_snapshot_identifier = var.deletion_protection ? "${var.name}-final" : null

  lifecycle {
    prevent_destroy = true                 # lesson 09 (see note below)
    ignore_changes  = [engine_version]     # minor upgrades are handled by AWS auto minor version upgrade
  }
}

resource "aws_ssm_parameter" "outputs" {
  for_each = {
    endpoint          = aws_db_instance.this.address
    secret_arn        = aws_db_instance.this.master_user_secret[0].secret_arn
    security_group_id = aws_security_group.db.id
  }
  name  = "/${var.name}/data/${each.key}"
  type  = "String"
  value = each.value
}
```

> **An internals lesson hiding here.** You might want
> `prevent_destroy = var.protect`. That **isn't allowed**: `lifecycle`
> arguments must be literal, because they're read while building the graph,
> before variables are evaluated (lesson 18). So the module hard-codes
> `prevent_destroy = true`, and the per-environment switch is the AWS-side
> `deletion_protection` variable.

### 3. `modules/web-service`: the app tier

```hcl
# modules/web-service/main.tf (key parts)

resource "aws_security_group" "alb" {
  name_prefix = "${var.name}-alb-"
  vpc_id      = var.vpc_id
  lifecycle { create_before_destroy = true }
}

resource "aws_security_group" "app" {
  name_prefix = "${var.name}-app-"
  vpc_id      = var.vpc_id
  lifecycle { create_before_destroy = true }
}

# Separate rule resources: no cycles, no inline-ownership surprises (lessons 06, 17)
resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "app_from_alb" {
  security_group_id            = aws_security_group.app.id
  referenced_security_group_id = aws_security_group.alb.id     # SG → SG, not CIDRs
  from_port                    = 8080
  to_port                      = 8080
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "db_from_app" {
  security_group_id            = var.db_security_group_id
  referenced_security_group_id = aws_security_group.app.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

# IAM: the instance can use SSM Session Manager (no SSH keys, no port 22) and read ONE secret
data "aws_iam_policy_document" "assume_ec2" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app" {
  name_prefix        = "${var.name}-app-"
  assume_role_policy = data.aws_iam_policy_document.assume_ec2.json
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "read_db_secret" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.db_secret_arn]
  }
}

resource "aws_iam_role_policy" "read_db_secret" {
  role   = aws_iam_role.app.id
  policy = data.aws_iam_policy_document.read_db_secret.json
}

resource "aws_iam_instance_profile" "app" {
  name_prefix = "${var.name}-app-"
  role        = aws_iam_role.app.name
}

resource "aws_launch_template" "app" {
  name_prefix   = "${var.name}-"
  image_id      = var.ami_id                       # pinned per environment: no surprise replacements
  instance_type = var.instance_type

  iam_instance_profile { arn = aws_iam_instance_profile.app.arn }
  vpc_security_group_ids = [aws_security_group.app.id]

  metadata_options {
    http_tokens = "required"                       # IMDSv2 only
  }

  user_data = base64encode(templatefile("${path.module}/templates/user_data.sh.tftpl", {
    app_version   = var.app_version
    db_endpoint   = var.db_endpoint
    db_secret_arn = var.db_secret_arn              # the ARN, not the password
    region        = var.region
  }))
}

resource "aws_lb" "this" {
  name_prefix        = substr(var.name, 0, 6)      # name_prefix has a 6-character limit on ALBs
  load_balancer_type = "application"
  subnets            = var.public_subnet_ids
  security_groups    = [aws_security_group.alb.id]
}

resource "aws_lb_target_group" "app" {
  name_prefix = substr(var.name, 0, 6)
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  health_check { path = "/health" }
  lifecycle { create_before_destroy = true }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = var.certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

resource "aws_autoscaling_group" "app" {
  name_prefix         = "${var.name}-"
  vpc_zone_identifier = var.private_subnet_ids
  target_group_arns   = [aws_lb_target_group.app.arn]
  health_check_type   = "ELB"
  min_size            = var.min_size
  max_size            = var.max_size
  desired_capacity    = var.min_size

  launch_template {
    id      = aws_launch_template.app.id
    version = aws_launch_template.app.latest_version
  }

  instance_refresh {                               # new launch template version → rolling replacement
    strategy = "Rolling"
    preferences { min_healthy_percentage = 50 }
  }

  lifecycle {
    ignore_changes = [desired_capacity]            # the scaling policy owns it (lesson 09)
  }
}

resource "aws_autoscaling_policy" "cpu" {
  name                   = "cpu-target-50"
  autoscaling_group_name = aws_autoscaling_group.app.name
  policy_type            = "TargetTrackingScaling"
  target_tracking_configuration {
    predefined_metric_specification { predefined_metric_type = "ASGAverageCPUUtilization" }
    target_value = 50
  }
}

check "app_health" {                               # lesson 20: warns if the app is down
  data "http" "health" {
    url      = "https://${aws_lb.this.dns_name}/health"
    insecure = true                                # the cert is for the domain, not the ALB DNS name
  }
  assert {
    condition     = data.http.health.status_code == 200
    error_message = "notes-app /health is not returning 200."
  }
}
```

**How a deployment works:** change `app_version` → the rendered user data
changes → a new launch template version → the ASG's `instance_refresh`
rolls instances 50% at a time, behind the ALB, with **zero downtime** and
no Terraform replacement of the ASG itself.

### 4. `live/prod/app`: a thin root module

```hcl
# live/prod/app/backend.tf
terraform {
  backend "s3" {
    bucket       = "acme-tfstate-333333333333"
    key          = "notes/prod/app/terraform.tfstate"
    region       = "ap-south-1"
    encrypt      = true
    use_lockfile = true
  }
}
```

```hcl
# live/prod/app/providers.tf
provider "aws" {
  region              = "ap-south-1"
  allowed_account_ids = ["333333333333"]
  default_tags {
    tags = {
      Project     = "notes-app"
      Environment = "prod"
      ManagedBy   = "terraform"
      Stack       = "notes-infra/live/prod/app"
    }
  }
}
```

```hcl
# live/prod/app/main.tf
locals { name = "notes-prod" }

data "aws_ssm_parameter" "net" {
  for_each = toset(["vpc_id", "public_subnet_ids", "private_subnet_ids"])
  name     = "/${local.name}/network/${each.key}"
}

data "aws_ssm_parameter" "data" {
  for_each = toset(["endpoint", "secret_arn", "security_group_id"])
  name     = "/${local.name}/data/${each.key}"
}

module "web" {
  source = "../../../modules/web-service"

  name               = local.name
  region             = "ap-south-1"
  vpc_id             = data.aws_ssm_parameter.net["vpc_id"].value
  public_subnet_ids  = split(",", data.aws_ssm_parameter.net["public_subnet_ids"].value)
  private_subnet_ids = split(",", data.aws_ssm_parameter.net["private_subnet_ids"].value)

  db_endpoint          = data.aws_ssm_parameter.data["endpoint"].value
  db_secret_arn        = data.aws_ssm_parameter.data["secret_arn"].value
  db_security_group_id = data.aws_ssm_parameter.data["security_group_id"].value

  ami_id          = var.ami_id
  instance_type   = var.instance_type
  min_size        = var.min_size
  max_size        = var.max_size
  app_version     = var.app_version
  certificate_arn = var.certificate_arn
}

output "url" { value = "https://${module.web.alb_dns_name}" }
```

```hcl
# live/prod/app/terraform.tfvars
ami_id          = "ami-0123456789abcdef0"   # bumped deliberately via PR
instance_type   = "t3.large"
min_size        = 3
max_size        = 9
app_version     = "2.14.0"
certificate_arn = "arn:aws:acm:ap-south-1:333333333333:certificate/…"
```

`live/dev/app` has the same files with `t3.micro`, `min_size = 1`, and
account `111111111111`.

---

## 🔁 Building a new environment from scratch

```bash
# 0. once per account: the bootstrap state (state bucket, OIDC, CI roles)
# 1. network
cd live/prod/network && terraform init && terraform apply
# 2. data (reads network params)
cd ../data && terraform init && terraform apply
# 3. app (reads network + data params)
cd ../app && terraform init && terraform apply
```

In CI, the pipeline applies changed stacks in this dependency order.
Destroying goes the **reverse** way: app → data (after removing
protection deliberately) → network.

---

## 🗺 Where every lesson shows up

| Lesson | In the capstone |
|---|---|
| 05 providers | `default_tags`, `allowed_account_ids`, pinned versions |
| 06 references | SG → SG rules, implicit ordering everywhere |
| 07 variables | per-environment tfvars, validated module inputs |
| 08 functions | `cidrsubnet`, `templatefile`, `split`/`join`, `try`/`one` |
| 09 meta-args | `for_each` by AZ, `create_before_destroy` + `name_prefix`, `ignore_changes`, `prevent_destroy` |
| 11–12 state | three S3 states per env, native locking, SSM instead of remote_state |
| 14 modules | three focused modules, no provider blocks inside |
| 15–16 environments | directory per env/layer, account per environment |
| 17–18 internals | why lifecycle can't use variables; no cycles thanks to separate SG rules |
| 19 security | managed RDS password, IMDSv2, SSM instead of SSH, least-privilege instance role |
| 20 testing | `check` block, module tests, policies in CI |
| 21 CI/CD | plan on PR / apply on merge per stack |

---

## 🏋 Exercises (design, not typing)

1. **Add a Redis cache.** Which state does it belong in, and why? What does the app need from it, and how does it get it?
2. **Blue/green deployments.** How would you change `web-service` to run two target groups and switch the listener between them?
3. **Multi-region DR.** What changes if prod must be able to run in `ap-southeast-1` too? (Hint: providers, keys, AMIs, RDS replicas, and which states get duplicated.)
4. **Migrate an existing hand-built RDS** into the `data` state without downtime. List every step (lesson 13).
5. **Cost-cut dev** without making it structurally different from prod. Which variables would you change?

<details><summary>Hints</summary>

1. `data` (stateful, changes rarely). Publish endpoint and SG ID to SSM, and add an SG rule from the app SG.
2. Two target groups plus two ASGs (blue/green) and a variable `active_color`, where the listener's `target_group_arn` uses it. Or switch to ECS with CodeDeploy.
3. Aliased providers or per-region root modules; keys like `notes/prod/ap-southeast-1/app`; per-region AMI IDs; `aws_db_instance` cross-region read replica with `replicate_source_db`; network/data/app all duplicated per region.
4. Write the module call matching the existing DB exactly → `import` block → plan to 0 changes → apply → remove the import block → publish SSM outputs.
5. `single_nat_gateway = true`, `multi_az = false`, smaller instance classes, `min_size = 1`, shorter backups. Same modules, different values.

</details>

➡️ **Next:** [24 · Interview question bank](24-interview-question-bank.md)

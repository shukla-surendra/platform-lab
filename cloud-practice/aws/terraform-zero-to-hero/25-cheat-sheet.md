# 25 · Cheat sheet

## Commands

```bash
# setup
terraform init                                  # providers, modules, backend
terraform init -upgrade                         # allow newer provider/module versions
terraform init -reconfigure -backend-config=dev.hcl   # switch backend config
terraform init -migrate-state                   # move state to a new backend
terraform providers lock -platform=linux_amd64 -platform=darwin_arm64

# everyday
terraform fmt -recursive                        # format
terraform validate                              # static check (needs init)
terraform plan                                  # preview
terraform plan -out=tfplan                      # save the plan
terraform apply tfplan                          # apply exactly that plan
terraform apply -auto-approve                   # CI only
terraform destroy                               # delete everything in this state
terraform plan -destroy                         # preview a destroy

# targeted / special
terraform plan -var-file=prod.tfvars -var 'x=1'
terraform apply -replace='aws_instance.web'     # force recreation
terraform plan -refresh-only                    # show drift only
terraform apply -refresh-only                   # accept drift into state
terraform plan -detailed-exitcode               # 0 none · 1 error · 2 changes
terraform apply -target='module.network'        # emergencies only
terraform apply -parallelism=5 -lock-timeout=5m

# inspect
terraform output [-raw NAME | -json]
terraform show [tfplan] [-json]
terraform state list ['filter']
terraform state show 'ADDR'
terraform console                               # REPL for expressions
terraform graph | dot -Tsvg > graph.svg
terraform providers
terraform version

# state surgery (prefer moved/import/removed blocks)
terraform state mv 'OLD' 'NEW'
terraform state rm 'ADDR'
terraform import 'ADDR' ID
terraform state pull > backup.json
terraform force-unlock LOCK_ID

# workspaces
terraform workspace list | new NAME | select NAME | show | delete NAME

# testing
terraform test [-filter=tests/x.tftest.hcl]

# debugging
TF_LOG=DEBUG TF_LOG_PATH=tf.log terraform plan
```

## Plan symbols

| `+` create | `~` update | `-/+` replace (destroy first) | `+/-` replace (create first) | `-` destroy | `<=` read at apply |
|---|---|---|---|---|---|

Always check: **summary line → any destroy/replace → `# forces replacement`**.

## Block skeletons

```hcl
terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
  backend "s3" {
    bucket       = "…"
    key          = "app/env/terraform.tfstate"
    region       = "ap-south-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region              = "ap-south-1"
  allowed_account_ids = ["111122223333"]
  default_tags { tags = { Project = "x", ManagedBy = "terraform" } }
  assume_role { role_arn = "arn:aws:iam::111122223333:role/tf" }
}
provider "aws" {              # use it with: provider = aws.use1
  alias  = "use1"
  region = "us-east-1"
}

variable "name" {
  type        = string
  description = "…"
  default     = "x"
  sensitive   = false
  nullable    = false
  validation {
    condition     = length(var.name) > 2
    error_message = "Too short."
  }
}

locals { prefix = "${var.project}-${var.env}" }

resource "TYPE" "NAME" {
  count      = 2                          # OR for_each = map/set
  provider   = aws.use1
  depends_on = [OTHER.x]
  lifecycle {
    create_before_destroy = true
    prevent_destroy       = true
    ignore_changes        = [tags]
    replace_triggered_by  = [terraform_data.v]
    precondition {
      condition     = …
      error_message = "…"
    }
    postcondition {
      condition     = self.x != ""
      error_message = "…"
    }
  }
}

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023*-x86_64"]
  }
}

output "id" {
  value     = aws_instance.web.id
  sensitive = false
}

module "net" {
  source    = "./modules/network"         # or registry + version, or git::…?ref=v1.2.3
  version   = "~> 5.0"                    # registry only
  providers = { aws = aws.use1 }
  for_each  = var.networks
  cidr      = each.value
}

import {
  to = aws_s3_bucket.b
  id = "bucket-name"
}

moved {
  from = aws_instance.web
  to   = aws_instance.app
}

removed {
  from = aws_s3_bucket.old
  lifecycle { destroy = false }
}

check "health" {
  data "http" "h" { url = "https://…/health" }
  assert {
    condition     = data.http.h.status_code == 200
    error_message = "down"
  }
}
```

> HCL rule: a block written on **one line** may contain only **one**
> argument (`lifecycle { destroy = false }` is fine). Object *values* on one
> line separate items with commas: `{ source = "hashicorp/aws", version = "~> 6.0" }`.

## Expressions

```hcl
cond ? a : b
[for x in list : f(x) if g(x)]
{for k, v in map : k => f(v)}
{for x in list : x.group => x.name...}         # group into lists
list[*].attr                                    # splat (lists only)
values(map_resource)[*].attr
"${a}-${b}"   "%{ if c }yes%{ else }no%{ endif }"
<<-EOT … EOT
dynamic "blk" {
  for_each = x
  content { a = blk.value }
}
merge([ for … : { … } ]...)                     # expand a list into arguments
```

## Functions you'll actually use

| Area | Functions |
|---|---|
| strings | `format` `join` `split` `lower` `upper` `replace` `substr` `trimspace` `trimprefix` `trimsuffix` `startswith` `endswith` `regex` |
| collections | `length` `contains` `lookup` `merge` `concat` `flatten` `distinct` `keys` `values` `zipmap` `slice` `coalesce` `one` `setproduct` `range` `index` |
| types | `tostring` `tonumber` `tolist` `toset` `tomap` `try` `can` `nonsensitive` |
| network | `cidrsubnet` `cidrhost` `cidrnetmask` |
| encoding | `jsonencode` `jsondecode` `yamlencode` `yamldecode` `base64encode` |
| files | `file` `templatefile` `fileset` `filebase64` with `path.module` |
| avoid in args | `timestamp()` `uuid()` (a diff on every plan) |

## Variable precedence (low → high)

`default` → `TF_VAR_x` → `terraform.tfvars` → `terraform.tfvars.json` → `*.auto.tfvars` (lexical) → `-var` / `-var-file` (last wins)

## Decision tables

| Need | Use |
|---|---|
| N copies with names | `for_each` (map) |
| on/off | `count = cond ? 1 : 0` |
| rename without recreating | `moved` |
| adopt existing | `import` |
| forget without deleting | `removed { lifecycle { destroy = false } }` |
| recreate a broken one | `-replace` |
| accept drift into state | `-refresh-only` |
| cross-stack values | SSM parameter / data source (> `terraform_remote_state`) |
| secrets | managed secrets / runtime fetch / ephemeral + write-only (> `sensitive`) |
| environments | directory per env + shared modules (> CLI workspaces) |

## Version-feature map (when things arrived)

| Version | Feature |
|---|---|
| 0.13 | `count`/`for_each` on modules |
| 1.1 | `moved` blocks |
| 1.2 | pre/postconditions, `replace_triggered_by` |
| 1.3 | `optional()` object attributes with defaults |
| 1.4 | `terraform_data` |
| 1.5 | `import` blocks, `-generate-config-out`, `check` blocks |
| 1.6 | `terraform test`, unknown value refinements |
| 1.7 | `removed` blocks, `for_each` on import, test mocks |
| 1.8 | provider-defined functions |
| 1.9 | variable validations can reference other objects |
| 1.10 | S3 native state locking (`use_lockfile`), ephemeral values/resources |
| 1.11 | write-only arguments; S3 native locking GA, DynamoDB locking deprecated |

## File hygiene

```
commit:  *.tf  .terraform.lock.hcl  *.tftest.hcl  non-secret *.tfvars  README.md
ignore:  .terraform/  *.tfstate*  tfplan  *.tfplan  crash.log  secret tfvars
```

⬅️ Back to the [course map](README.md)

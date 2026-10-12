# Run ONCE per AWS account (local state), creates:
#   - S3 bucket for remote state (versioned, encrypted, private)
#   - GitHub OIDC provider + one deploy role per environment (no static keys)
terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.80" }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "state_bucket_name" {
  type        = string
  description = "Globally unique bucket name for Terraform state"
}

variable "github_repo" {
  type        = string
  description = "owner/repo allowed to assume the deploy roles, e.g. my-org/infra"
}

variable "environments" {
  type    = list(string)
  default = ["dev", "qa", "stage", "prod"]
}

resource "aws_s3_bucket" "state" {
  bucket = var.state_bucket_name
  lifecycle { prevent_destroy = true }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "aws:kms" }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---- GitHub Actions OIDC ----
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

# One role per env: the trust policy is pinned to a GitHub *Environment*,
# so only jobs running in that environment (with its approval rules) can assume it.
data "aws_iam_policy_document" "trust" {
  for_each = toset(var.environments)
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:environment:${each.key}"]
    }
  }
}

resource "aws_iam_role" "deploy" {
  for_each           = toset(var.environments)
  name               = "tf-deploy-${each.key}"
  assume_role_policy = data.aws_iam_policy_document.trust[each.key].json
}

# Demo scope: PowerUser. In real life use a least-privilege custom policy,
# and put prod in a separate AWS account.
resource "aws_iam_role_policy_attachment" "deploy" {
  for_each   = aws_iam_role.deploy
  role       = each.value.name
  policy_arn = "arn:aws:iam::aws:policy/PowerUserAccess"
}

# State access for the roles (each env may only touch its own state key).
data "aws_iam_policy_document" "state" {
  for_each = toset(var.environments)
  statement {
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.state.arn]
  }
  statement {
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.state.arn}/env/${each.key}/*"]
  }
}

resource "aws_iam_role_policy" "state" {
  for_each = toset(var.environments)
  name     = "state-access"
  role     = aws_iam_role.deploy[each.key].id
  policy   = data.aws_iam_policy_document.state[each.key].json
}

output "state_bucket" { value = aws_s3_bucket.state.id }
output "deploy_role_arns" { value = { for k, r in aws_iam_role.deploy : k => r.arn } }
